"""
SafetyGuard — Validation des plans d'exécution avant action.

Niveaux de risque :
  low      → exécution directe
  medium   → log + exécution
  high     → demande confirmation Telegram/vocale
  critical → bloqué sauf whitelist explicite
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Set

logger = logging.getLogger(__name__)

RiskLevel = Literal["low", "medium", "high", "critical"]


# ── Structures de données ──────────────────────────────────────────────────────

@dataclass
class ExecutionStep:
    """Une étape atomique d'un plan (appel de skill, commande shell, etc.)."""
    skill_name: str
    params: dict
    risk_level: RiskLevel = "low"
    description: str = ""


@dataclass
class ExecutionPlan:
    """Séquence d'étapes produite par le LLM/Dispatcher."""
    steps: List[ExecutionStep] = field(default_factory=list)
    intent: str = ""

    def add_step(self, step: ExecutionStep) -> None:
        self.steps.append(step)


@dataclass
class StepVerdict:
    step: ExecutionStep
    allowed: bool
    requires_confirmation: bool
    reason: str = ""


@dataclass
class SafetyReport:
    """Résultat de la validation d'un plan complet."""
    plan: ExecutionPlan
    verdicts: List[StepVerdict] = field(default_factory=list)

    @property
    def is_safe(self) -> bool:
        """True si toutes les étapes sont autorisées (même avec confirmation)."""
        return all(v.allowed for v in self.verdicts)

    @property
    def needs_confirmation(self) -> bool:
        return any(v.requires_confirmation for v in self.verdicts)

    @property
    def blocked_steps(self) -> List[StepVerdict]:
        return [v for v in self.verdicts if not v.allowed]

    @property
    def confirm_steps(self) -> List[StepVerdict]:
        return [v for v in self.verdicts if v.requires_confirmation and v.allowed]

    def summary(self) -> str:
        lines = [f"Plan: '{self.plan.intent}' — {len(self.verdicts)} étape(s)"]
        for v in self.verdicts:
            icon = "✅" if v.allowed else "🚫"
            conf = " [CONFIRM]" if v.requires_confirmation else ""
            lines.append(f"  {icon} {v.step.skill_name}{conf}: {v.reason}")
        return "\n".join(lines)


# ── SafetyGuard ────────────────────────────────────────────────────────────────

class SafetyGuard:
    """
    Valide chaque étape d'un ExecutionPlan avant exécution.

    Règles (par ordre de priorité) :
    1. Chemin dans forbidden_paths → BLOQUÉ
    2. App dans app_blacklist → BLOQUÉ
    3. Skill dans skill_blacklist → BLOQUÉ
    4. risk_level == 'critical' → BLOQUÉ (sauf skill_whitelist)
    5. risk_level == 'high' → AUTORISÉ + CONFIRMATION requise
    6. App dans app_whitelist → AUTORISÉ direct
    7. Tout le reste → AUTORISÉ direct
    """

    def __init__(self):
        # Applications autorisées sans confirmation
        self.app_whitelist: Set[str] = {
            "VSCode", "Chrome", "Safari", "Terminal",
            "iTerm2", "Finder", "Slack", "Notion",
        }
        # Applications totalement interdites
        self.app_blacklist: Set[str] = {
            "rm", "sudo", "chmod", "chown",
        }
        # Chemins système protégés
        self.forbidden_paths: Set[str] = {
            "/System", "/usr/bin", "/usr/sbin",
            "/private/etc", "/Library/System",
            "/bin", "/sbin",
        }
        # Skills explicitement interdits
        self.skill_blacklist: Set[str] = {
            "format_disk", "delete_all", "factory_reset",
        }
        # Skills toujours autorisés même si critical
        self.skill_whitelist: Set[str] = {
            "get_time", "get_weather", "read_clipboard",
        }

    def check(self, plan: ExecutionPlan) -> SafetyReport:
        """Valide toutes les étapes du plan et retourne un SafetyReport."""
        report = SafetyReport(plan=plan)

        for step in plan.steps:
            verdict = self._check_step(step)
            report.verdicts.append(verdict)
            logger.info(
                "SafetyGuard [%s] %s → allowed=%s confirm=%s | %s",
                step.risk_level, step.skill_name,
                verdict.allowed, verdict.requires_confirmation, verdict.reason
            )

        return report

    def _check_step(self, step: ExecutionStep) -> StepVerdict:
        """Applique les règles sur une étape individuelle."""

        # Règle 1 : chemins interdits
        for path in self.forbidden_paths:
            for val in step.params.values():
                if isinstance(val, str) and val.startswith(path):
                    return StepVerdict(
                        step=step, allowed=False, requires_confirmation=False,
                        reason=f"Chemin système interdit : {val}"
                    )

        # Règle 2 : app blacklist
        app = step.params.get("app_name", "")
        if app in self.app_blacklist:
            return StepVerdict(
                step=step, allowed=False, requires_confirmation=False,
                reason=f"Application interdite : {app}"
            )

        # Règle 3 : skill blacklist
        if step.skill_name in self.skill_blacklist:
            return StepVerdict(
                step=step, allowed=False, requires_confirmation=False,
                reason=f"Skill interdit : {step.skill_name}"
            )

        # Règle 4 : critical (sauf whitelist)
        if step.risk_level == "critical":
            if step.skill_name in self.skill_whitelist:
                return StepVerdict(
                    step=step, allowed=True, requires_confirmation=False,
                    reason="Skill critique mais dans la whitelist"
                )
            return StepVerdict(
                step=step, allowed=False, requires_confirmation=False,
                reason="Niveau critique : action bloquée par défaut"
            )

        # Règle 5 : high → confirmation
        if step.risk_level == "high":
            return StepVerdict(
                step=step, allowed=True, requires_confirmation=True,
                reason="Risque élevé : confirmation utilisateur requise"
            )

        # Règle 6 & 7 : low/medium → OK
        return StepVerdict(
            step=step, allowed=True, requires_confirmation=False,
            reason="OK"
        )
