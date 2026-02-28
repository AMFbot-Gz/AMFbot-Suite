"""
OverlayWindow — Fenêtre flottante transparente PyQt6.

Design :
- Fenêtre frameless, toujours au-dessus, fond semi-transparent
- 3 zones : transcription STT / réponse LLM (avec animation) / liste d'actions
- QTimer à 100ms pour rafraîchissement fluide
- Draggable par clic-glisser
"""

import sys
from typing import List

from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal, QThread
from PyQt6.QtGui import QColor, QFont, QPainter, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
)


# ── Styles ─────────────────────────────────────────────────────────────────────

OVERLAY_STYLE = """
QWidget#overlay {
    background-color: rgba(10, 10, 20, 200);
    border-radius: 14px;
    border: 1px solid rgba(100, 150, 255, 80);
}
QLabel#transcription {
    color: rgba(180, 200, 255, 220);
    font-size: 12px;
    padding: 4px 10px;
    font-style: italic;
}
QLabel#response {
    color: rgba(230, 240, 255, 240);
    font-size: 14px;
    font-weight: bold;
    padding: 6px 10px;
    min-height: 40px;
}
QLabel#status {
    color: rgba(100, 200, 120, 200);
    font-size: 11px;
    padding: 2px 10px;
}
QListWidget#actions {
    background: transparent;
    color: rgba(160, 220, 160, 200);
    font-size: 11px;
    border: none;
    padding: 0 10px;
    max-height: 80px;
}
QListWidget#actions::item {
    padding: 1px 0;
}
"""

# Nombre de points dans l'animation de réflexion
THINKING_FRAMES = ["", ".", "..", "..."]


class OverlayWindow(QMainWindow):
    """
    Fenêtre overlay JARVIS — transparente, frameless, always on top.

    Utilisation depuis le thread principal Qt :
        window = OverlayWindow()
        window.show()
        window.set_transcription("ouvre Chrome")
        window.set_llm_response("Ouverture en cours...")
        window.add_action("open_app(Chrome)")
    """

    def __init__(self):
        super().__init__()
        self._drag_pos = QPoint()
        self._thinking_frame = 0
        self._is_thinking = False
        self._response_text = ""

        self._setup_window()
        self._setup_ui()
        self._setup_timer()

    # ── Configuration fenêtre ──────────────────────────────────────────────────

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedWidth(360)
        # Position : coin supérieur droit
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.geometry()
            self.move(geo.width() - 380, 40)

    # ── Construction UI ────────────────────────────────────────────────────────

    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("overlay")
        central.setStyleSheet(OVERLAY_STYLE)
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(2)

        # Label transcription (ce que l'utilisateur a dit)
        self._lbl_transcription = QLabel("En attente...")
        self._lbl_transcription.setObjectName("transcription")
        self._lbl_transcription.setWordWrap(True)
        layout.addWidget(self._lbl_transcription)

        # Séparateur
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(100,150,255,60);")
        layout.addWidget(sep)

        # Label réponse LLM
        self._lbl_response = QLabel("")
        self._lbl_response.setObjectName("response")
        self._lbl_response.setWordWrap(True)
        self._lbl_response.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        layout.addWidget(self._lbl_response)

        # Liste des actions
        self._list_actions = QListWidget()
        self._list_actions.setObjectName("actions")
        self._list_actions.setMaximumHeight(80)
        layout.addWidget(self._list_actions)

        # Barre de statut
        self._lbl_status = QLabel("JARVIS")
        self._lbl_status.setObjectName("status")
        self._lbl_status.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._lbl_status)

        self.adjustSize()

    # ── Timer de rafraîchissement ──────────────────────────────────────────────

    def _setup_timer(self):
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(100)  # 100ms

    def _refresh(self):
        if self._is_thinking:
            self._thinking_frame = (self._thinking_frame + 1) % len(THINKING_FRAMES)
            dots = THINKING_FRAMES[self._thinking_frame]
            self._lbl_response.setText(f"{self._response_text}{dots}")
        self.adjustSize()

    # ── API publique (thread-safe via signaux Qt) ──────────────────────────────

    def set_transcription(self, text: str) -> None:
        """Met à jour le label de transcription."""
        self._lbl_transcription.setText(f'"{text}"')
        self._is_thinking = True
        self._response_text = ""
        self._lbl_response.setText("...")
        self._list_actions.clear()

    def set_llm_response(self, text: str) -> None:
        """Affiche la réponse LLM (arrête l'animation de réflexion)."""
        self._is_thinking = False
        self._response_text = text
        self._lbl_response.setText(text[:200] + ("…" if len(text) > 200 else ""))

    def add_action(self, action: str) -> None:
        """Ajoute une action à la liste."""
        item = QListWidgetItem(f"▶ {action}")
        self._list_actions.addItem(item)
        self._list_actions.scrollToBottom()
        # Garder max 5 items visibles
        while self._list_actions.count() > 5:
            self._list_actions.takeItem(0)

    def set_status(self, status: str) -> None:
        self._lbl_status.setText(f"JARVIS • {status}")

    def reset(self) -> None:
        """Remet l'overlay en état d'attente."""
        self._is_thinking = False
        self._lbl_transcription.setText("En attente...")
        self._lbl_response.setText("")
        self._list_actions.clear()
        self._lbl_status.setText("JARVIS")

    # ── Draggable ──────────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseDoubleClickEvent(self, event):
        """Double-clic = masquer/afficher."""
        if self.isVisible():
            self.hide()
        else:
            self.show()
