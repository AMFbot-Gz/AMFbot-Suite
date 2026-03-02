"""
ActionPlanner — Cerveau ReAct de JARVIS.

Implémente la boucle Reason + Act :
    1. THINK   → LLM analyse l'objectif et choisit une action
    2. ACT     → exécute le skill via SkillRegistry
    3. OBSERVE → récupère le résultat et l'injecte dans le prompt suivant
    4. REPEAT  → jusqu'à FINAL_ANSWER ou max_steps atteint

Format de réponse attendu du LLM :
    THOUGHT: <raisonnement>
    ACTION: <skill_name>
    PARAMS: <json dict des paramètres>
    ---
    ou
    FINAL_ANSWER: <réponse finale à donner à l'utilisateur>
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Prompt système ReAct
REACT_SYSTEM_PROMPT = """Tu es JARVIS, un assistant IA personnel. Tu réponds TOUJOURS dans ce format strict :

Pour effectuer une action :
THOUGHT: <ton raisonnement sur ce qu'il faut faire>
ACTION: <nom_exact_du_skill>
PARAMS: <objet JSON avec les paramètres>

Pour donner la réponse finale (quand la tâche est terminée ou ne nécessite pas d'action) :
FINAL_ANSWER: <ta réponse à l'utilisateur>

Skills disponibles :
{skills_list}

Règles :
- Utilise FINAL_ANSWER dès que tu as toutes les informations nécessaires
- Si une action échoue, essaie une alternative ou explique pourquoi c'est impossible
- Sois concis dans tes raisonnements
- Les PARAMS doivent être un JSON valide
"""

REACT_STEP_TEMPLATE = """Objectif : {objective}

{context}

Historique des étapes :
{history}

Quelle est la prochaine étape ?"""


@dataclass
class ReActStep:
    """Une étape de la boucle ReAct."""
    thought:   str
    action:    str = ""       # skill_name ou "" pour FINAL_ANSWER
    params:    Dict[str, Any] = field(default_factory=dict)
    result:    str = ""       # résultat de l'action
    is_final:  bool = False
    answer:    str = ""       # contenu de FINAL_ANSWER


@dataclass
class ReActResult:
    """Résultat complet d'une planification ReAct."""
    success:   bool
    answer:    str
    steps:     List[ReActStep] = field(default_factory=list)
    error:     str = ""

    @property
    def step_count(self) -> int:
        return len(self.steps)


class ActionPlanner:
    """
    Planificateur ReAct — orchestre la boucle Thought/Action/Observe.

    Implémente le cycle Reason + Act (ReAct) :
    à chaque itération, le LLM réfléchit (THOUGHT), choisit une action (ACTION),
    un skill est exécuté, et le résultat (OBSERVE) est injecté dans le prochain prompt.
    La boucle se termine dès que le LLM émet FINAL_ANSWER ou que MAX_STEPS est atteint.

    Attributes:
        MAX_STEPS: Nombre maximum d'itérations avant abandon (défaut : 6).
        TIMEOUT_STEP: Délai maximum en secondes par étape LLM ou skill (défaut : 30s).

    Example:
        planner = ActionPlanner(llm_client, registry)
        result  = await planner.plan_and_execute(
            "Ouvre Chrome et va sur google.fr", ctx
        )
        print(result.answer)   # → "Chrome ouvert sur google.fr."
    """

    MAX_STEPS    = 6
    TIMEOUT_STEP = 60.0   # secondes par étape

    def __init__(self, llm_client, registry):
        self._llm      = llm_client
        self._registry = registry

    # ── Point d'entrée principal ───────────────────────────────────────────────

    async def plan_and_execute(
        self,
        objective: str,
        ctx,                        # ExecutionContext
        context_block: str = "",    # Bloc mémoire injecté par MemoryManager
    ) -> ReActResult:
        """
        Exécute la boucle ReAct principale jusqu'à obtenir une réponse finale.

        À chaque itération :
        1. ``_think_step`` construit le prompt et interroge le LLM.
        2. Si le LLM émet ``FINAL_ANSWER``, la boucle s'arrête (succès).
        3. Sinon, ``_execute_action`` exécute le skill désigné.
        4. Le résultat est injecté dans le prochain prompt (OBSERVE).

        Args:
            objective: Requête ou objectif formulé par l'utilisateur.
            ctx: Contexte d'exécution (session_id, dry_run, confirmed…).
            context_block: Bloc de contexte mémoire pré-construit par
                MemoryManager (historique + faits sémantiques pertinents).

        Returns:
            ReActResult avec :
            - ``success=True`` et ``answer`` si FINAL_ANSWER reçu.
            - ``success=False`` et ``error`` si timeout, erreur LLM,
              ou MAX_STEPS atteint.

        Raises:
            Aucune exception levée — toutes les erreurs sont capturées
            et retournées dans ``ReActResult.error``.

        Example:
            result = await planner.plan_and_execute(
                "Quel temps fait-il à Paris ?", ctx
            )
            if result.success:
                print(result.answer)
        """
        steps: List[ReActStep] = []
        skills_desc = self._build_skills_description()

        for i in range(self.MAX_STEPS):
            try:
                step = await asyncio.wait_for(
                    self._think_step(objective, steps, context_block, skills_desc),
                    timeout=self.TIMEOUT_STEP,
                )
            except asyncio.TimeoutError:
                logger.warning("ReAct step %d timeout", i + 1)
                return ReActResult(
                    success=False,
                    answer="Je n'ai pas pu répondre à temps.",
                    steps=steps,
                    error="timeout",
                )
            except Exception as e:
                logger.error("ReAct LLM error at step %d: %s", i + 1, e)
                return ReActResult(
                    success=False,
                    answer=f"Erreur LLM : {e}",
                    steps=steps,
                    error=str(e),
                )

            steps.append(step)
            logger.info("ReAct [%d/%d] THOUGHT=%s ACTION=%s",
                        i + 1, self.MAX_STEPS, step.thought[:80], step.action)

            if self._is_task_complete(step):
                return ReActResult(success=True, answer=step.answer, steps=steps)

            result_str = await self._execute_step(step, ctx)
            step.result = result_str
            logger.info("ReAct [%d/%d] RESULT=%s", i + 1, self.MAX_STEPS, result_str[:100])

        # Max steps atteint
        last_thought = steps[-1].thought if steps else "inconnu"
        return ReActResult(
            success=False,
            answer=f"Limite d'étapes atteinte. Dernier raisonnement : {last_thought}",
            steps=steps,
            error="max_steps",
        )

    # ── Étapes privées de la boucle ReAct ─────────────────────────────────────

    async def _think_step(
        self,
        objective: str,
        history: List[ReActStep],
        context_block: str,
        skills_desc: str,
    ) -> ReActStep:
        """
        Construit le prompt ReAct et interroge le LLM pour l'étape courante.

        Args:
            objective: Objectif initial de l'utilisateur.
            history: Étapes déjà exécutées dans la boucle courante.
            context_block: Bloc mémoire injecté par MemoryManager.
            skills_desc: Description formatée des skills disponibles.

        Returns:
            ReActStep parsé depuis la réponse du LLM.
        """
        system_prompt = REACT_SYSTEM_PROMPT.format(skills_list=skills_desc)
        history_str = self._format_history(history)
        user_prompt = REACT_STEP_TEMPLATE.format(
            objective=objective,
            context=context_block if context_block else "(pas de contexte mémorisé)",
            history=history_str if history_str else "(première étape)",
        )
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        response = await self._llm.generate(full_prompt)
        text = response.text.strip() if response else ""
        return self._parse_react_response(text)

    async def _execute_step(self, step: ReActStep, ctx) -> str:
        """
        Exécute le skill désigné par une étape ReAct et retourne le résultat.

        Args:
            step: Étape ReAct contenant le nom du skill et ses paramètres.
            ctx: ExecutionContext transmis au skill.

        Returns:
            Chaîne décrivant le résultat (succès ou erreur), injectée dans
            le prochain prompt LLM comme observation.
        """
        return await self._execute_action(step, ctx)

    def _is_task_complete(self, step: ReActStep) -> bool:
        """
        Détermine si la boucle ReAct doit s'arrêter après cette étape.

        Args:
            step: Étape ReAct à évaluer.

        Returns:
            True si le LLM a émis FINAL_ANSWER (tâche terminée),
            False si la boucle doit continuer.
        """
        return step.is_final

    def _parse_react_response(self, text: str) -> ReActStep:
        """
        Parse la réponse LLM au format ReAct.

        Formats acceptés :
            THOUGHT: ...
            ACTION: skill_name
            PARAMS: {...}

            FINAL_ANSWER: ...
        """
        # FINAL_ANSWER
        fa_match = re.search(r"FINAL_ANSWER\s*:\s*(.+)", text, re.DOTALL | re.IGNORECASE)
        if fa_match:
            return ReActStep(
                thought="",
                is_final=True,
                answer=fa_match.group(1).strip(),
            )

        # THOUGHT
        thought = ""
        th_match = re.search(r"THOUGHT\s*:\s*(.+?)(?=ACTION\s*:|PARAMS\s*:|$)",
                              text, re.DOTALL | re.IGNORECASE)
        if th_match:
            thought = th_match.group(1).strip()

        # ACTION
        action = ""
        ac_match = re.search(r"ACTION\s*:\s*(\S+)", text, re.IGNORECASE)
        if ac_match:
            action = ac_match.group(1).strip()

        # PARAMS
        params: Dict[str, Any] = {}
        pa_match = re.search(r"PARAMS\s*:\s*(\{.*?\})", text, re.DOTALL | re.IGNORECASE)
        if pa_match:
            try:
                params = json.loads(pa_match.group(1))
            except json.JSONDecodeError:
                logger.warning("ReAct: impossible de parser les PARAMS JSON: %s",
                               pa_match.group(1)[:100])

        if not action and not thought:
            # Réponse non structurée → traiter comme réponse finale
            return ReActStep(thought="", is_final=True, answer=text)

        return ReActStep(thought=thought, action=action, params=params)

    # ── Execute Action ─────────────────────────────────────────────────────────

    async def _execute_action(self, step: ReActStep, ctx) -> str:
        """Exécute un skill et retourne une string résultat."""
        skill_name = step.action
        skill = self._registry.get(skill_name)

        if skill is None:
            # Essai insensible à la casse
            skill = self._registry.get(skill_name.lower())

        if skill is None:
            available = ", ".join(self._registry.list_names())
            return f"ERREUR: skill '{skill_name}' inconnu. Skills disponibles: {available}"

        try:
            result = await asyncio.wait_for(
                skill.run(step.params, ctx),
                timeout=self.TIMEOUT_STEP,
            )
            if result.success:
                return result.message or "Action effectuée."
            else:
                return f"ÉCHEC: {result.message}"
        except asyncio.TimeoutError:
            return f"TIMEOUT: le skill '{skill_name}' a dépassé {self.TIMEOUT_STEP}s"
        except Exception as e:
            logger.error("ReAct skill '%s' error: %s", skill_name, e)
            return f"ERREUR: {e}"

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _build_skills_description(self) -> str:
        """Génère la liste des skills pour le prompt système."""
        lines = []
        for name in self._registry.list_names():
            skill = self._registry.get(name)
            if skill:
                schema = getattr(skill, "params_schema", {})
                params_hint = ", ".join(schema.keys()) if schema else "aucun"
                lines.append(f"  - {name}: {skill.description} (params: {params_hint})")
        return "\n".join(lines) if lines else "  (aucun skill disponible)"

    @staticmethod
    def _format_history(steps: List[ReActStep]) -> str:
        """Formate l'historique des étapes pour le prompt."""
        if not steps:
            return ""
        lines = []
        for i, step in enumerate(steps, 1):
            if step.is_final:
                lines.append(f"Étape {i}: FINAL_ANSWER: {step.answer[:100]}")
            else:
                lines.append(f"Étape {i}:")
                if step.thought:
                    lines.append(f"  THOUGHT: {step.thought[:150]}")
                if step.action:
                    lines.append(f"  ACTION: {step.action} {json.dumps(step.params, ensure_ascii=False)}")
                if step.result:
                    lines.append(f"  RÉSULTAT: {step.result[:200]}")
        return "\n".join(lines)
