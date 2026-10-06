"""Reusable custom widgets: avatar, conversation tile, message bubble, emoji picker."""
from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QSizePolicy, QTabWidget, QVBoxLayout, QWidget,
)

from client import theme
from client.emoji_data import EMOJI_CATEGORIES
from common.protocol import format_timestamp


class AvatarWidget(QWidget):
    """Round avatar showing an emoji, with an optional online/offline dot."""

    def __init__(self, glyph: str = "👤", color: str = theme.ACCENT, size: int = 46,
                 online: bool | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.set_avatar(glyph, color, online)

    def set_avatar(self, glyph: str, color: str, online: bool | None = None) -> None:
        self._glyph, self._color, self._online = glyph, color, online
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        diameter = self.width() - 6
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor(self._color)))
        p.drawEllipse(2, 2, diameter, diameter)

        font = QFont()
        font.setPointSize(max(8, int(self.width() * 0.3)))
        p.setFont(font)
        p.setPen(QColor("white"))
        p.drawText(2, 2, diameter, diameter, Qt.AlignmentFlag.AlignCenter, self._glyph)

        if self._online is not None:
            dot = max(10, self.width() // 4)
            x = self.width() - dot - 1
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(theme.SIDEBAR)))
            p.drawEllipse(x - 2, x - 2, dot + 4, dot + 4)
            p.setBrush(QBrush(QColor(theme.ONLINE if self._online else theme.OFFLINE)))
            p.drawEllipse(x, x, dot, dot)


class ConversationTile(QFrame):
    """One row of the chat list (name, last message, time, unread badge)."""

    clicked = pyqtSignal(str)

    def __init__(self, key: str, title: str, glyph: str, color: str, preview: str,
                 time_text: str, unread: int, online: bool | None, selected: bool) -> None:
        super().__init__()
        self.key = key
        self.setObjectName("ChatTile")
        self.setProperty("selected", selected)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        layout.addWidget(AvatarWidget(glyph, color, 46, online))

        info = QVBoxLayout()
        info.setSpacing(3)
        top = QHBoxLayout()
        name = QLabel(title)
        name.setObjectName("TileName")
        when = QLabel(time_text)
        when.setObjectName("TileTime")
        top.addWidget(name)
        top.addStretch()
        top.addWidget(when)

        bottom = QHBoxLayout()
        text = QLabel(preview if len(preview) <= 30 else preview[:29] + "…")
        text.setObjectName("TilePreview")
        text.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        bottom.addWidget(text, 1)
        if unread > 0:
            badge = QLabel(str(min(unread, 99)))
            badge.setObjectName("Badge")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            bottom.addWidget(badge)

        info.addLayout(top)
        info.addLayout(bottom)
        layout.addLayout(info, 1)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.key)


class MessageBubble(QFrame):
    """Chat bubble in the spec format: ``😎 Hail [September 12, 2026 • 08:45 AM]``."""

    def __init__(self, msg: dict, own: bool) -> None:
        super().__init__()
        self.setObjectName("BubbleOwn" if own else "BubbleOther")
        self.setMaximumWidth(460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 9, 14, 9)
        layout.setSpacing(4)

        header = QLabel(f"{msg['avatar']} {msg['sender']}  [{format_timestamp(msg['ts'])}]")
        header.setObjectName("BubbleHeader")
        body = QLabel(msg["text"])
        body.setObjectName("BubbleBody")
        body.setWordWrap(True)
        body.setTextFormat(Qt.TextFormat.PlainText)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        layout.addWidget(header)
        layout.addWidget(body)
        if msg.get("edited"):
            tag = QLabel("(edited)")
            tag.setObjectName("BubbleEdited")
            layout.addWidget(tag, alignment=Qt.AlignmentFlag.AlignRight)


class EmojiPicker(QFrame):
    """Popup with tabs of emoji; emits ``emoji_selected`` when one is clicked."""

    emoji_selected = pyqtSignal(str)
    COLUMNS = 8

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Popup)
        self.setObjectName("EmojiPicker")
        self.setFixedSize(370, 300)

        tabs = QTabWidget()
        for category, emojis in EMOJI_CATEGORIES.items():
            tabs.addTab(self._build_grid(emojis), category)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(tabs)

    def _build_grid(self, emojis: list[str]) -> QScrollArea:
        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(4, 4, 4, 4)
        grid.setSpacing(2)
        for i, emoji in enumerate(emojis):
            button = QPushButton(emoji)
            button.setObjectName("EmojiButton")
            button.setFixedSize(38, 38)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _=False, e=emoji: self.emoji_selected.emit(e))
            grid.addWidget(button, i // self.COLUMNS, i % self.COLUMNS)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(container)
        return scroll

    def show_above(self, anchor: QWidget) -> None:
        origin = anchor.mapToGlobal(QPoint(0, 0))
        self.move(origin.x(), origin.y() - self.height() - 6)
        self.show()
