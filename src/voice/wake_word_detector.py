"""
WakeWordDetector — Détection du mot de réveil ("hey jarvis").

Stratégies supportées :
  - "keyword"  : comparaison simple de transcript STT (rapide, sans modèle dédié)
  - "openwakeword" : modèle neuronal léger (précis, ~5ms/frame)
"""

import asyncio
import logging
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


class WakeWordDetector:
    """
    Écoute en permanence et publie un événement quand le wake word est détecté.

    Utilisation :
        detector = WakeWordDetector(keywords=["jarvis", "hey jarvis"])
        detector.on_detected(callback)
        await detector.start()
    """

    def __init__(
        self,
        keywords: Optional[List[str]] = None,
        strategy: str = "keyword",
        sensitivity: float = 0.5,
    ):
        self.keywords    = [kw.lower() for kw in (keywords or ["jarvis", "hey jarvis"])]
        self.strategy    = strategy
        self.sensitivity = sensitivity
        self._callbacks: List[Callable] = []
        self._running    = False

    def on_detected(self, callback: Callable) -> None:
        """Enregistre un callback appelé quand le wake word est détecté."""
        self._callbacks.append(callback)

    def check_transcript(self, text: str) -> bool:
        """Vérifie si le transcript contient un wake word."""
        text_lower = text.lower()
        return any(kw in text_lower for kw in self.keywords)

    async def process_transcript(self, text: str) -> bool:
        """Vérifie et déclenche les callbacks si wake word détecté."""
        if self.check_transcript(text):
            logger.info("Wake word détecté dans: '%s'", text)
            for cb in self._callbacks:
                if asyncio.iscoroutinefunction(cb):
                    await cb(text)
                else:
                    cb(text)
            return True
        return False

    async def start(self) -> None:
        """Démarre la détection (placeholder pour mode openwakeword)."""
        self._running = True
        logger.info("WakeWordDetector démarré — mots: %s", self.keywords)

    async def stop(self) -> None:
        self._running = False
        logger.info("WakeWordDetector arrêté")
