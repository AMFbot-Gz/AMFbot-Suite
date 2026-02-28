"""
StateManager — État global de JARVIS (thread-safe, observable).

Centralise toutes les variables d'état pour éviter les états éparpillés.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class JarvisState(Enum):
    IDLE        = auto()   # En attente du wake word
    LISTENING   = auto()   # Capture audio active
    PROCESSING  = auto()   # LLM en cours de traitement
    SPEAKING    = auto()   # TTS en cours
    EXECUTING   = auto()   # Skill en cours d'exécution
    CONFIRMING  = auto()   # Attente confirmation utilisateur
    ERROR       = auto()   # Erreur récupérable
    SHUTDOWN    = auto()   # Arrêt en cours


@dataclass
class StateSnapshot:
    state: JarvisState
    last_transcript: str = ""
    last_intent: str = ""
    active_skill: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class StateManager:
    """
    Gère les transitions d'état de JARVIS.

    Règles de transition valides :
      IDLE → LISTENING → PROCESSING → EXECUTING → IDLE
      PROCESSING → SPEAKING → IDLE
      EXECUTING → CONFIRMING → EXECUTING
      * → ERROR → IDLE
      * → SHUTDOWN
    """

    VALID_TRANSITIONS: Dict[JarvisState, List[JarvisState]] = {
        JarvisState.IDLE:       [JarvisState.LISTENING, JarvisState.SHUTDOWN],
        JarvisState.LISTENING:  [JarvisState.PROCESSING, JarvisState.IDLE, JarvisState.ERROR],
        JarvisState.PROCESSING: [JarvisState.EXECUTING, JarvisState.SPEAKING, JarvisState.IDLE, JarvisState.ERROR],
        JarvisState.SPEAKING:   [JarvisState.IDLE, JarvisState.LISTENING, JarvisState.ERROR],
        JarvisState.EXECUTING:  [JarvisState.CONFIRMING, JarvisState.SPEAKING, JarvisState.IDLE, JarvisState.ERROR],
        JarvisState.CONFIRMING: [JarvisState.EXECUTING, JarvisState.IDLE, JarvisState.ERROR],
        JarvisState.ERROR:      [JarvisState.IDLE, JarvisState.SHUTDOWN],
        JarvisState.SHUTDOWN:   [],
    }

    def __init__(self):
        self._state = JarvisState.IDLE
        self._snapshot = StateSnapshot(state=JarvisState.IDLE)
        self._lock = asyncio.Lock()
        self._observers: List[Callable] = []

    @property
    def current(self) -> JarvisState:
        return self._state

    @property
    def snapshot(self) -> StateSnapshot:
        return self._snapshot

    def add_observer(self, callback: Callable) -> None:
        """Callback appelé à chaque changement d'état : callback(old, new, snapshot)."""
        self._observers.append(callback)

    async def transition(
        self,
        new_state: JarvisState,
        **metadata
    ) -> bool:
        """
        Effectue une transition vers new_state.
        Retourne True si succès, False si transition invalide.
        """
        async with self._lock:
            allowed = self.VALID_TRANSITIONS.get(self._state, [])
            if new_state not in allowed:
                logger.warning(
                    "Transition invalide : %s → %s (autorisées: %s)",
                    self._state.name, new_state.name,
                    [s.name for s in allowed]
                )
                return False

            old_state = self._state
            self._state = new_state
            self._snapshot = StateSnapshot(state=new_state, **metadata)

            logger.info("State: %s → %s", old_state.name, new_state.name)

            # Notifier les observers
            for observer in self._observers:
                try:
                    if asyncio.iscoroutinefunction(observer):
                        asyncio.create_task(observer(old_state, new_state, self._snapshot))
                    else:
                        observer(old_state, new_state, self._snapshot)
                except Exception as e:
                    logger.error("Observer error: %s", e)

            return True

    async def reset_to_idle(self) -> None:
        """Retour forcé à IDLE (récupération d'erreur)."""
        self._state = JarvisState.IDLE
        self._snapshot = StateSnapshot(state=JarvisState.IDLE)
        logger.info("State forcé → IDLE")
