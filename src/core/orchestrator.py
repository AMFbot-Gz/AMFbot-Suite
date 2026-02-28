"""
CoreOrchestrator v3 — Pipeline avec streaming TTS, GUI et mémoire.

Nouveautés v3 :
- Intégration MemoryManager (recherche contexte avant LLM, sauvegarde après)
- Intégration ContextManager (résolution de coréférences)
"""

import asyncio
import logging
from datetime import datetime
from typing import Callable, List, Optional

from .event_bus import EventBus
from .state_manager import StateManager, JarvisState
from .safety_guard import SafetyGuard, ExecutionPlan

logger = logging.getLogger(__name__)


class Interaction:
    """Enregistrement d'une interaction pour l'historique."""
    def __init__(self, user_input: str, response: str, actions: List[str] = None):
        self.ts         = datetime.now().isoformat(timespec="seconds")
        self.user_input = user_input
        self.response   = response
        self.actions    = actions or []

    def to_dict(self) -> dict:
        return {
            "ts":         self.ts,
            "user_input": self.user_input,
            "response":   self.response,
            "actions":    self.actions,
        }


class CoreOrchestrator:
    """
    Orchestre le pipeline complet JARVIS v2.

    Pipeline streaming :
      STT → EventBus(stt.result)
          → LLM generate_stream() → token_queue
          → TTSEngine.speak_async_stream(token_queue)   [en parallèle]
          → dispatcher.parse_response()
          → SafetyGuard → Skills → EventBus(skill.done)
    """

    MAX_HISTORY = 50

    def __init__(
        self,
        event_bus: EventBus,
        state_manager: StateManager,
        safety_guard: SafetyGuard,
        gui_manager=None,      # GUIManager optionnel (Phase 2)
        memory_manager=None,   # MemoryManager optionnel (Phase 3)
        context_manager=None,  # ContextManager optionnel (Phase 3)
    ):
        self.bus     = event_bus
        self.state   = state_manager
        self.safety  = safety_guard
        self.gui     = gui_manager
        self.memory  = memory_manager
        self.ctx_mgr = context_manager
        self._running   = False
        self._history: List[Interaction] = []

        # Queue de tokens LLM → TTS streaming
        self._token_queue: asyncio.Queue = asyncio.Queue()

    # ── Cycle de vie ──────────────────────────────────────────────────────────

    async def start(self) -> None:
        self._running = True
        self._register_handlers()
        logger.info("CoreOrchestrator v2 démarré")

    async def stop(self) -> None:
        self._running = False
        await self._token_queue.put(None)  # Signal d'arrêt au TTS streaming
        await self.state.transition(JarvisState.SHUTDOWN)
        logger.info("CoreOrchestrator arrêté")

    def _register_handlers(self) -> None:
        self.bus.subscribe("stt.result",       self._on_stt_result)
        self.bus.subscribe("llm.response",     self._on_llm_response)
        self.bus.subscribe("llm.stream_token", self._on_llm_token)
        self.bus.subscribe("skill.done",       self._on_skill_done)
        self.bus.subscribe("skill.error",      self._on_skill_error)
        self.bus.subscribe("safety.confirmed", self._on_safety_confirmed)
        self.bus.subscribe("system.shutdown",  self._on_shutdown)

    # ── Propriétés publiques ──────────────────────────────────────────────────

    @property
    def history(self) -> List[dict]:
        return [i.to_dict() for i in self._history[-self.MAX_HISTORY:]]

    @property
    def token_queue(self) -> asyncio.Queue:
        """Exposé pour que jarvis_main puisse câbler le TTS streaming."""
        return self._token_queue

    # ── Handlers EventBus ────────────────────────────────────────────────────

    async def _on_stt_result(self, event_type: str, data: dict) -> None:
        transcript = data.get("text", "").strip()
        if not transcript:
            await self.state.transition(JarvisState.IDLE)
            return

        logger.info("STT: '%s'", transcript)

        # ── Phase 3 : résolution de coréférences ──────────────────────────────
        if self.ctx_mgr and self.memory:
            last_ep = self.memory.get_last_user_episode()
            last_jarvis = None
            if self._history:
                last_jarvis = self._history[-1].response
            transcript = self.ctx_mgr.resolve(
                current_query=transcript,
                last_user_turn=last_ep.text if last_ep else None,
                last_jarvis_turn=last_jarvis,
            )
            if transcript != data.get("text", ""):
                logger.info("Coréférence résolue: '%s'", transcript)

        await self.state.transition(JarvisState.PROCESSING, last_transcript=transcript)

        if self.gui:
            self.gui.set_transcription(transcript)

        # ── Phase 3 : contexte mémoire ────────────────────────────────────────
        context_block = ""
        if self.memory:
            context_block = self.memory.build_context_prompt(transcript)
            if self.memory:
                self.memory.add_interaction(transcript, role="user")

        await self.bus.publish("llm.request", {
            "prompt": transcript,
            "context_block": context_block,
        })

    async def _on_llm_token(self, event_type: str, data: dict) -> None:
        """Reçoit un token du stream LLM et l'envoie au TTS."""
        token = data.get("token", "")
        if token:
            await self._token_queue.put(token)

    async def _on_llm_response(self, event_type: str, data: dict) -> None:
        """Reçoit la réponse LLM complète (avec ou sans plan)."""
        plan: Optional[ExecutionPlan] = data.get("plan")
        text: str = data.get("text", "")
        intent: str = data.get("intent", "")

        if self.gui and text:
            self.gui.set_llm_response(text)

        if not plan or not plan.steps:
            # Réponse purement textuelle
            await self._token_queue.put(None)
            await self.state.transition(JarvisState.IDLE)
            self._record(intent, text)
            # ── Phase 3 : sauvegarder la réponse JARVIS ───────────────────────
            if self.memory and text:
                self.memory.add_interaction(text, role="jarvis", intent=intent)
            return

        # Valider le plan
        report = self.safety.check(plan)
        logger.info(report.summary())

        if not report.is_safe:
            blocked_reasons = " ".join(v.reason for v in report.blocked_steps)
            msg = f"Impossible d'exécuter ça. {blocked_reasons}"
            await self._speak_text(msg)
            await self.bus.publish("safety.blocked", {"report": report})
            self._record(intent, msg)
            return

        if report.needs_confirmation:
            steps_desc = ", ".join(v.step.description for v in report.confirm_steps)
            confirm_msg = f"Voulez-vous vraiment : {steps_desc} ?"
            await self._speak_text(confirm_msg)
            await self.bus.publish("safety.confirm", {
                "plan": plan, "report": report, "description": steps_desc,
            })
            await self.state.transition(JarvisState.CONFIRMING)
            return

        # Exécution directe
        await self.state.transition(JarvisState.EXECUTING)
        if self.gui:
            for step in plan.steps:
                self.gui.add_action(f"Exécution: {step.skill_name}")
        await self.bus.publish("skill.execute", {"plan": plan, "intent": intent})

    async def _on_skill_done(self, event_type: str, data: dict) -> None:
        message    = data.get("message", "C'est fait.")
        intent     = data.get("intent", "")
        skill_name = data.get("skill_name", "")
        await self._speak_text(message)
        self._record(intent, message, actions=[skill_name])
        if self.gui:
            self.gui.add_action(f"OK: {message}")
        # ── Phase 3 : sauvegarder la réponse JARVIS en mémoire ────────────────
        if self.memory:
            self.memory.add_interaction(
                message, role="jarvis",
                intent=intent, actions=[skill_name] if skill_name else [],
            )

    async def _on_skill_error(self, event_type: str, data: dict) -> None:
        error = data.get("error", "Erreur inconnue")
        logger.error("Skill error: %s", error)
        await self._speak_text(f"Erreur : {error}")
        await self.state.transition(JarvisState.ERROR, error_message=error)
        await asyncio.sleep(1)
        await self.state.reset_to_idle()

    async def _on_safety_confirmed(self, event_type: str, data: dict) -> None:
        """L'utilisateur a confirmé — exécuter le plan."""
        plan = data.get("plan")
        if plan:
            await self.state.transition(JarvisState.EXECUTING)
            await self.bus.publish("skill.execute", {"plan": plan})

    async def _on_shutdown(self, event_type: str, data: dict) -> None:
        await self.stop()

    # ── Utilitaires ───────────────────────────────────────────────────────────

    async def _speak_text(self, text: str) -> None:
        """Publie un texte pour synthèse vocale."""
        await self._token_queue.put(None)  # Vider le stream courant
        self._token_queue = asyncio.Queue()  # Nouvelle queue
        await self.bus.publish("tts.speak", {"text": text})
        await self.state.transition(JarvisState.SPEAKING)

    def _record(self, user_input: str, response: str, actions: List[str] = None) -> None:
        """Enregistre une interaction dans l'historique."""
        interaction = Interaction(user_input, response, actions)
        self._history.append(interaction)
        if len(self._history) > self.MAX_HISTORY:
            self._history.pop(0)
