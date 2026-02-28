"""
FunctionDispatcher v2 — Parsing LLM → ExecutionPlan avec gestion réponses mixtes.

Nouvelles fonctionnalités :
- parse_response() : gère à la fois les tool_calls et les réponses textuelles
- get_tool_definitions() : génère dynamiquement depuis le SkillRegistry
- Gestion des arguments JSON encodés en string (bug courant des LLMs)
"""

import json
import logging
from typing import Dict, List, Optional, Tuple

from core.safety_guard import ExecutionPlan, ExecutionStep
from skills.registry import SkillRegistry
from llm.llm_client import LLMResponse

logger = logging.getLogger(__name__)


class DispatchResult:
    """Résultat du parsing d'une réponse LLM."""

    def __init__(
        self,
        plan: Optional[ExecutionPlan] = None,
        text: str = "",
        is_action: bool = False,
    ):
        self.plan      = plan
        self.text      = text
        self.is_action = is_action  # True = plan à exécuter, False = réponse textuelle

    @property
    def has_plan(self) -> bool:
        return self.plan is not None and bool(self.plan.steps)


class DispatchError(Exception):
    pass


class FunctionDispatcher:
    """
    Traduit les réponses LLM en actions JARVIS.

    Utilisation :
        dispatcher = FunctionDispatcher(registry)
        tools = dispatcher.get_tool_definitions()
        response = await llm.generate(prompt, tools=tools)
        result = dispatcher.parse_response(response, intent=prompt)
        if result.is_action:
            safety_guard.check(result.plan)
        else:
            tts.speak(result.text)
    """

    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    # ── Génération des tool definitions ───────────────────────────────────────

    def get_tool_definitions(self) -> List[dict]:
        """
        Génère dynamiquement les définitions d'outils depuis le SkillRegistry.
        Compatible format Ollama / OpenAI.
        """
        tools = []
        for skill in self.registry.all():
            tools.append({
                "type": "function",
                "function": {
                    "name":        skill.name,
                    "description": skill.description,
                    "parameters":  skill.params_schema,
                },
            })
        logger.debug("Tool definitions générées: %d outils", len(tools))
        return tools

    # ── Parsing de la réponse LLM ─────────────────────────────────────────────

    def parse_response(
        self,
        response: LLMResponse,
        intent: str = "",
    ) -> DispatchResult:
        """
        Parse une LLMResponse et retourne un DispatchResult.

        Logique :
        1. Si tool_calls présents → construire ExecutionPlan
        2. Sinon → réponse textuelle simple
        """
        if response.has_tool_calls:
            plan = self._build_plan(response.tool_calls, intent=intent)
            if plan.steps:
                return DispatchResult(plan=plan, text=response.text, is_action=True)
            # tool_calls mais tous inconnus → fallback texte
            logger.warning("tool_calls présents mais aucun skill reconnu, fallback texte")

        return DispatchResult(text=response.text, is_action=False)

    def _build_plan(
        self,
        tool_calls: List[dict],
        intent: str = "",
    ) -> ExecutionPlan:
        plan = ExecutionPlan(intent=intent)

        for call in tool_calls:
            skill_name = call.get("name", "").strip()
            arguments  = call.get("arguments", {})

            # Certains LLMs encodent les arguments en JSON string
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    logger.warning("Impossible de parser les arguments JSON: %s", arguments)
                    arguments = {}

            skill = self.registry.get(skill_name)
            if skill is None:
                logger.warning("Skill inconnu: '%s' — ignoré", skill_name)
                continue

            # Validation des paramètres
            errors = skill.validate_params(arguments)
            if errors:
                logger.warning("Paramètres invalides pour '%s': %s", skill_name, errors)

            step = ExecutionStep(
                skill_name=skill_name,
                params=arguments,
                risk_level=skill.risk_level,
                description=f"{skill.description} | params={arguments}",
            )
            plan.add_step(step)
            logger.info(
                "Step: %s %s [risk=%s]",
                skill_name, arguments, skill.risk_level,
            )

        return plan

    # ── Compatibilité Phase 1 ─────────────────────────────────────────────────

    def build_plan(
        self,
        tool_calls: List[dict],
        intent: str = "",
    ) -> ExecutionPlan:
        """Alias Phase 1 — préférer parse_response() en Phase 2."""
        return self._build_plan(tool_calls, intent=intent)
