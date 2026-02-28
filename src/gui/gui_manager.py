"""
GUIManager — Pont thread-safe entre asyncio (JARVIS) et Qt (overlay).

Architecture (macOS-compatible) :
    Main thread   → QApplication + Qt event loop
    Background    → asyncio pipeline (JARVIS)

    asyncio thread  →  GUIManager._invoke()  →  queue.Queue.put()
    Qt main thread  →  QTimer(50ms)._drain_queue()  →  overlay.method()
"""

import logging
import queue
from typing import Optional

logger = logging.getLogger(__name__)


class GUIManager:
    """
    Interface thread-safe entre JARVIS (asyncio) et l'overlay Qt.

    start() doit être appelé depuis le main thread Qt (QApplication déjà créé).

    Utilisation :
        gui = GUIManager()
        # (depuis main thread, après QApplication créé)
        gui.start()
        # (depuis n'importe quel thread)
        gui.set_transcription("ouvre Chrome")
        gui.set_llm_response("Ouverture en cours...")
        gui.add_action("open_app(Chrome)")
        gui.stop()
    """

    def __init__(self):
        self._overlay = None
        self._queue   = queue.Queue()   # thread-safe : asyncio → Qt
        self._timer   = None
        self._enabled = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> bool:
        """
        Crée l'overlay et démarre le timer de drain.
        Doit être appelé depuis le main thread Qt (QApplication déjà en place).
        """
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import QTimer
            from .overlay_window import OverlayWindow

            if QApplication.instance() is None:
                logger.error("GUIManager.start() appelé sans QApplication — abandonné")
                return False

            self._overlay = OverlayWindow()
            self._overlay.show()

            self._timer = QTimer()
            self._timer.timeout.connect(self._drain_queue)
            self._timer.start(50)   # poll toutes les 50 ms

            self._enabled = True
            logger.info("GUIManager: overlay prêt (main thread Qt)")
            return True

        except Exception as e:
            logger.error("GUIManager: impossible de démarrer: %s", e)
            return False

    def _drain_queue(self):
        """Exécuté sur le main thread Qt par QTimer — consomme la queue."""
        while not self._queue.empty():
            try:
                name, args = self._queue.get_nowait()
                if name == "__stop__":
                    self._timer.stop()
                    return
                method = getattr(self._overlay, name, None)
                if method is not None:
                    method(*args)
            except Exception as e:
                logger.debug("GUIManager._drain_queue error: %s", e)

    def stop(self) -> None:
        self._enabled = False
        # Signale au drain loop (Qt main thread) d'arrêter le timer
        if self._timer:
            self._queue.put(("__stop__", ()))

    # ── API publique (thread-safe) ─────────────────────────────────────────────

    def set_transcription(self, text: str) -> None:
        self._invoke("set_transcription", text)

    def set_llm_response(self, text: str) -> None:
        self._invoke("set_llm_response", text)

    def add_action(self, action: str) -> None:
        self._invoke("add_action", action)

    def set_status(self, status: str) -> None:
        self._invoke("set_status", status)

    def reset(self) -> None:
        self._invoke("reset")

    # ── Dispatch thread-safe ──────────────────────────────────────────────────

    def _invoke(self, method_name: str, *args) -> None:
        """Enfile une commande pour exécution sur le thread Qt."""
        if self._enabled:
            self._queue.put((method_name, args))


class NullGUIManager:
    """
    Implémentation no-op du GUIManager (quand Qt n'est pas disponible).
    Permet au reste du code de fonctionner sans GUI.
    """

    def start(self) -> bool:            return False
    def stop(self) -> None:             pass
    def set_transcription(self, t):     pass
    def set_llm_response(self, t):      pass
    def add_action(self, a):            pass
    def set_status(self, s):            pass
    def reset(self):                    pass


def create_gui_manager(enabled: bool = True) -> "GUIManager | NullGUIManager":
    """Factory : retourne un vrai GUIManager ou un NullGUIManager."""
    if not enabled:
        return NullGUIManager()
    try:
        import PyQt6.QtWidgets  # noqa: F401
        return GUIManager()
    except ImportError:
        logger.warning("PyQt6 non disponible — GUI désactivé")
        return NullGUIManager()
