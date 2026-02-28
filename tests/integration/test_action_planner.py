"""
Tests d'intégration — ActionPlanner (boucle ReAct).

Couvre :
  - Requête simple sans action (FINAL_ANSWER direct)
  - Requête en deux étapes avec deux actions successives
  - Vérification des noms de skills dans le plan d'exécution

Les appels LLM et les skills sont mockés via unittest.mock
pour ne dépendre d'aucune ressource externe (Ollama, système).
"""

import asyncio
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from llm.action_planner import ActionPlanner
from llm.llm_client import LLMResponse
from skills.base_skill import ExecutionContext, SkillResult


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_llm_response(text: str) -> LLMResponse:
    """Crée une LLMResponse avec un texte donné."""
    return LLMResponse(text=text)


def make_mock_skill(result_message: str = "Action effectuée.") -> Any:
    """Crée un skill mocké qui retourne toujours SkillResult.ok()."""
    skill = MagicMock()
    skill.run = AsyncMock(return_value=SkillResult.ok(result_message))
    skill.description = "Mock skill"
    skill.params_schema = {"type": "object", "properties": {}, "required": []}
    return skill


def make_mock_registry(skill_names: list = None) -> MagicMock:
    """Crée un SkillRegistry mocké avec des skills génériques."""
    registry = MagicMock()
    registry.list_names.return_value = skill_names or []

    mock_skill = make_mock_skill()
    registry.get.return_value = mock_skill

    return registry


def make_ctx() -> ExecutionContext:
    return ExecutionContext(session_id="test-session", confirmed=False)


# ── Test 1 : Requête simple sans action ───────────────────────────────────────

class TestSimpleRequest:
    """Le LLM répond directement par FINAL_ANSWER sans déclencher d'action."""

    @pytest.mark.asyncio
    async def test_bonjour_returns_final_answer(self):
        """
        'Dis bonjour' → le LLM doit retourner un FINAL_ANSWER textuel
        sans passer par une action/skill.
        """
        # Arrange
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(
            return_value=make_llm_response(
                "FINAL_ANSWER: Bonjour ! Comment puis-je vous aider ?"
            )
        )
        mock_registry = make_mock_registry(skill_names=[])
        planner = ActionPlanner(mock_llm, mock_registry)

        # Act
        result = await planner.plan_and_execute("Dis bonjour", make_ctx())

        # Assert
        assert result.success is True
        assert "Bonjour" in result.answer
        assert result.step_count == 1
        # Aucun skill exécuté
        mock_registry.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_simple_question_no_action(self):
        """
        Une question factuelle simple ne doit pas déclencher de skill.
        """
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(
            return_value=make_llm_response(
                "FINAL_ANSWER: Il est 14h30."
            )
        )
        mock_registry = make_mock_registry(skill_names=["get_time"])
        planner = ActionPlanner(mock_llm, mock_registry)

        result = await planner.plan_and_execute("Quelle heure est-il ?", make_ctx())

        assert result.success is True
        assert result.error == ""
        # Le LLM a été appelé exactement une fois
        assert mock_llm.generate.call_count == 1


# ── Test 2 : Plan en deux étapes ──────────────────────────────────────────────

class TestMultiStepPlan:
    """
    'Ouvre Chrome puis prends une capture d'écran' :
    le LLM doit déclencher deux actions successives
    avant de fournir la réponse finale.
    """

    @pytest.mark.asyncio
    async def test_two_step_plan_correct_skill_names(self):
        """
        Vérifie que le plan exécuté contient exactement deux actions
        avec les bons noms de skills : open_url et take_screenshot.
        """
        # Arrange : LLM mocké pour répondre en 3 appels
        # Appel 1 → ACTION open_url
        # Appel 2 → ACTION take_screenshot
        # Appel 3 → FINAL_ANSWER
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(
            side_effect=[
                make_llm_response(
                    "THOUGHT: Je dois d'abord ouvrir Chrome.\n"
                    "ACTION: open_url\n"
                    'PARAMS: {"url": "https://google.com"}'
                ),
                make_llm_response(
                    "THOUGHT: Chrome est ouvert, je prends la capture.\n"
                    "ACTION: take_screenshot\n"
                    'PARAMS: {"filename": "capture.png"}'
                ),
                make_llm_response(
                    "FINAL_ANSWER: J'ai ouvert Chrome sur google.com et pris une capture d'écran."
                ),
            ]
        )

        # Registry avec les deux skills nécessaires
        open_url_skill = make_mock_skill("Navigateur ouvert sur : Google")
        screenshot_skill = make_mock_skill("Capture enregistrée : capture.png")

        mock_registry = MagicMock()
        mock_registry.list_names.return_value = ["open_url", "take_screenshot"]

        def get_skill_by_name(name: str):
            return {"open_url": open_url_skill, "take_screenshot": screenshot_skill}.get(name)

        mock_registry.get.side_effect = get_skill_by_name

        planner = ActionPlanner(mock_llm, mock_registry)

        # Act
        result = await planner.plan_and_execute(
            "Ouvre Chrome puis prends une capture d'écran",
            make_ctx(),
        )

        # Assert — résultat final réussi
        assert result.success is True
        assert "Chrome" in result.answer or "capture" in result.answer.lower()

        # Exactement 3 étapes (2 actions + 1 final)
        assert result.step_count == 3

        # Filtrer les étapes d'action (non finales)
        action_steps = [s for s in result.steps if not s.is_final]
        assert len(action_steps) == 2

        # Vérifier les noms de skills dans le bon ordre
        assert action_steps[0].action == "open_url"
        assert action_steps[1].action == "take_screenshot"

    @pytest.mark.asyncio
    async def test_two_step_plan_params_passed_correctly(self):
        """
        Vérifie que les paramètres JSON sont correctement parsés
        et transmis aux skills.
        """
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(
            side_effect=[
                make_llm_response(
                    "THOUGHT: Ouvrir l'URL demandée.\n"
                    "ACTION: open_url\n"
                    'PARAMS: {"url": "https://github.com", "headless": false}'
                ),
                make_llm_response("FINAL_ANSWER: URL ouverte avec succès."),
            ]
        )

        received_params = {}

        async def capture_params(params, ctx):
            received_params.update(params)
            return SkillResult.ok("Navigateur ouvert")

        mock_skill = MagicMock()
        mock_skill.run = capture_params

        mock_registry = MagicMock()
        mock_registry.list_names.return_value = ["open_url"]
        mock_registry.get.return_value = mock_skill

        planner = ActionPlanner(mock_llm, mock_registry)
        result = await planner.plan_and_execute("Ouvre github.com", make_ctx())

        assert result.success is True
        assert received_params.get("url") == "https://github.com"
        assert received_params.get("headless") is False


# ── Test 3 : Gestion des erreurs ──────────────────────────────────────────────

class TestErrorHandling:

    @pytest.mark.asyncio
    async def test_unknown_skill_returns_error_message(self):
        """
        Un skill inconnu doit retourner un résultat d'erreur,
        pas lever une exception.
        """
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(
            side_effect=[
                make_llm_response(
                    "THOUGHT: Je vais utiliser un skill qui n'existe pas.\n"
                    "ACTION: skill_inexistant\n"
                    'PARAMS: {}'
                ),
                make_llm_response("FINAL_ANSWER: Je ne peux pas exécuter cette action."),
            ]
        )

        mock_registry = MagicMock()
        mock_registry.list_names.return_value = []
        mock_registry.get.return_value = None  # Skill inconnu

        planner = ActionPlanner(mock_llm, mock_registry)
        result = await planner.plan_and_execute("Fais quelque chose d'impossible", make_ctx())

        # Ne doit pas crasher
        assert result is not None
        # L'erreur est gérée et le pipeline continue jusqu'au FINAL_ANSWER
        assert result.success is True

    @pytest.mark.asyncio
    async def test_max_steps_reached(self):
        """
        Si le LLM ne fournit jamais de FINAL_ANSWER,
        la boucle doit s'arrêter après MAX_STEPS.
        """
        # LLM toujours en boucle infinie sur la même action
        mock_llm = MagicMock()
        mock_llm.generate = AsyncMock(
            return_value=make_llm_response(
                "THOUGHT: Je dois réfléchir encore.\n"
                "ACTION: get_time\n"
                'PARAMS: {}'
            )
        )

        mock_skill = make_mock_skill("Il est 14h30.")
        mock_registry = MagicMock()
        mock_registry.list_names.return_value = ["get_time"]
        mock_registry.get.return_value = mock_skill

        planner = ActionPlanner(mock_llm, mock_registry)
        result = await planner.plan_and_execute("Quelle heure est-il ?", make_ctx())

        # Doit échouer proprement après MAX_STEPS
        assert result.success is False
        assert result.error == "max_steps"
        assert result.step_count == ActionPlanner.MAX_STEPS
