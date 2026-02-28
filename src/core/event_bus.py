"""
EventBus — Bus d'événements asynchrone central.

Permet le découplage total entre les modules :
  publisher (STT, LLM, Skills...) → EventBus → subscribers (Orchestrator, UI...)
"""

import asyncio
import logging
from typing import Any, Callable, Coroutine, Dict, List, Union

logger = logging.getLogger(__name__)

# Type pour un handler : sync ou async acceptant (event_type: str, data: dict)
HandlerType = Union[
    Callable[[str, dict], None],
    Callable[[str, dict], Coroutine[Any, Any, None]],
]


class EventBus:
    """
    Bus pub/sub asynchrone. Thread-safe via asyncio.

    Utilisation :
        bus = EventBus()
        bus.subscribe("stt.result", handle_transcription)
        await bus.publish("stt.result", {"text": "ouvre Chrome"})
    """

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[HandlerType]] = {}
        self._queue: asyncio.Queue[dict] = asyncio.Queue()
        self._running: bool = False

    # ── Abonnement ────────────────────────────────────────────────────────────

    def subscribe(self, event_type: str, handler: HandlerType) -> None:
        """Enregistre un handler pour un type d'événement."""
        self._subscribers.setdefault(event_type, []).append(handler)
        logger.debug("Subscribe: %s → %s", event_type, handler.__name__)

    def unsubscribe(self, event_type: str, handler: HandlerType) -> None:
        """Retire un handler."""
        handlers = self._subscribers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    # ── Publication ───────────────────────────────────────────────────────────

    async def publish(self, event_type: str, data: dict) -> None:
        """
        Publie un événement. Tous les handlers abonnés sont appelés
        en parallèle via asyncio.gather (non-bloquant).
        """
        handlers = self._subscribers.get(event_type, [])
        if not handlers:
            logger.debug("Event '%s' publié sans subscribers", event_type)
            return

        logger.debug("Event '%s' → %d handler(s)", event_type, len(handlers))

        loop = asyncio.get_running_loop()
        tasks: List[asyncio.Task[Any]] = []
        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                tasks.append(asyncio.create_task(handler(event_type, data)))
            else:
                # Handler synchrone : wrap dans un executor
                tasks.append(
                    asyncio.create_task(
                        loop.run_in_executor(None, handler, event_type, data)
                    )
                )

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for handler, result in zip(handlers, results):
            if isinstance(result, Exception):
                logger.error(
                    "Handler '%s' a levé une exception pour '%s': %s",
                    handler.__name__, event_type, result
                )

    # ── Événements connus ─────────────────────────────────────────────────────

    # Convention de nommage : module.action
    #   stt.result          → transcription disponible
    #   llm.response        → réponse LLM générée
    #   skill.start         → skill en cours d'exécution
    #   skill.done          → skill terminé
    #   skill.error         → skill en erreur
    #   safety.blocked      → plan bloqué par SafetyGuard
    #   safety.confirm      → demande de confirmation utilisateur
    #   tts.speak           → texte à synthétiser
    #   system.shutdown     → arrêt propre demandé
