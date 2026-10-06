"""Pop-up emoji picker with category tabs (faces, hands, hearts, objects, animals)."""
from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QScrollArea, QTabWidget, QToolButton, QVBoxLayout, QWidget,
)

from client.styles import BORDER, PRIMARY_SOFT, SURFACE

EMOJI_CATEGORIES: dict[str, tuple[str, list[str]]] = {
    "😊": ("Faces", """😀 😃 😄 😁 😆 😅 😂 🤣 😊 😇 🙂 🙃 😉 😌 😍 🥰 😘 😗 😙 😚 😋 😛 😝 😜 🤪 🤨 🧐 🤓
        😎 🤩 🥳 😏 😒 😞 😔 😟 😕 🙁 😣 😖 😫 😩 🥺 😢 😭 😤 😠 😡 🤬 🤯 😳 🥵 🥶 😱 😨 😰 😥 😓
        🤗 🤔 🫡 🤭 🤫 😶 😐 😑 😬 🙄 😯 😦 😧 😮 😲 🥱 😴 🤤 😪 😵 🤐 🤢 🤮 🤧 😷 🤠 😈 👿 💀 👻 👽 🤖 💩""".split()),
    "👍": ("Gestures", "👍 👎 👌 ✌️ 🤞 🤟 🤘 🤙 👏 🙌 🙏 💪 👋 🤝 ✋ 🖐️ 👊 ✊ 🤚 👆 👇 👈 👉 🫶".split()),
    "❤️": ("Hearts & symbols", "❤️ 🧡 💛 💚 💙 💜 🖤 🤍 🤎 💔 💕 💖 💗 💓 💞 💝 💯 🔥 ✨ ⭐ 🌟 🎉 🎊 ⚡ 🌈".split()),
    "🎮": ("Objects", """🎮 💻 📱 🎧 🎸 🎹 📚 ✏️ 📷 🎬 ⚽ 🏀 🚗 ✈️ 🏠 🎁 💡 🔔 ☕ 🍕 🍔 🍟 🍰 🍎 🍌 🍓
        🥤 🍿 🎂 📌 🔑 ⏰ ☀️ 🌙""".split()),
    "🐱": ("Animals", "🐱 🐶 🐼 🐸 🐵 🦊 🐻 🐨 🐯 🦁 🐮 🐷 🐭 🐹 🐰 🐔 🐧 🐦 🦆 🦉 🦄 🐝 🦋 🐢 🐙 🐬 🐳 🦈".split()),
}
COLUMNS = 8


class EmojiPicker(QFrame):
    """Click an emoji -> ``emoji_selected`` is emitted and the picker closes."""

    emoji_selected = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Popup)
        self.setObjectName("EmojiPicker")
        self.setFixedSize(372, 300)
        self.setStyleSheet(f"""
            QFrame#EmojiPicker {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px; }}
            QTabWidget::pane {{ border: none; }}
            QTabBar::tab {{ font-size: 16px; padding: 4px 12px; border-radius: 8px; margin: 2px; }}
            QTabBar::tab:selected {{ background: {PRIMARY_SOFT}; }}
            QToolButton {{ border: none; border-radius: 8px; font-size: 22px; background: transparent; }}
            QToolButton:hover {{ background: {PRIMARY_SOFT}; }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        tabs = QTabWidget()
        for index, (icon, (name, emojis)) in enumerate(EMOJI_CATEGORIES.items()):
            tabs.addTab(self._build_page(emojis), icon)
            tabs.setTabToolTip(index, name)
        layout.addWidget(tabs)

    def _build_page(self, emojis: list[str]) -> QScrollArea:
        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(4, 4, 4, 4)
        grid.setSpacing(2)
        for index, emoji in enumerate(emojis):
            button = QToolButton()
            button.setText(emoji)
            button.setFixedSize(40, 40)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, e=emoji: self._pick(e))
            grid.addWidget(button, index // COLUMNS, index % COLUMNS)
        grid.setRowStretch(len(emojis) // COLUMNS + 1, 1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(container)
        return scroll

    def _pick(self, emoji: str) -> None:
        self.emoji_selected.emit(emoji)
        self.close()

    def show_above(self, anchor: QWidget) -> None:
        origin = anchor.mapToGlobal(QPoint(0, 0))
        self.move(origin.x(), origin.y() - self.height() - 6)
        self.show()
