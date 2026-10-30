"""Reusable custom widgets: logo, avatar, conversation tile, message bubble, emoji picker."""
from __future__ import annotations

import re

from PyQt6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap,
)
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QSizePolicy, QTabWidget, QVBoxLayout, QWidget,
)

from client import theme
from client.emoji_data import EMOJI_CATEGORIES
from common.protocol import format_timestamp


class LogoWidget(QWidget):
    """ChatGo logo: a dark app tile, a neon-green speech bubble holding a fast-forward
    "go" chevron pair, and a rose notification dot (the complementary colour)."""

    def __init__(self, size: int = 64, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = float(self.width())

        # app tile
        tile = QLinearGradient(0, 0, s, s)
        tile.setColorAt(0.0, QColor("#12301F"))
        tile.setColorAt(1.0, QColor("#030504"))
        p.setPen(QPen(QColor("#1F5A37"), max(1.0, s * 0.018)))
        p.setBrush(QBrush(tile))
        inset = s * 0.012
        p.drawRoundedRect(QRectF(inset, inset, s - 2 * inset, s - 2 * inset), s * 0.24, s * 0.24)

        # speech bubble (rounded body + tail)
        bubble = QPainterPath()
        bubble.addRoundedRect(QRectF(s * 0.17, s * 0.19, s * 0.66, s * 0.47), s * 0.17, s * 0.17)
        tail = QPainterPath()
        tail.moveTo(QPointF(s * 0.27, s * 0.60))
        tail.lineTo(QPointF(s * 0.21, s * 0.82))
        tail.lineTo(QPointF(s * 0.48, s * 0.64))
        tail.closeSubpath()
        shape = bubble.united(tail)

        glow = QPen(QColor(74, 222, 128, 70), s * 0.07)
        glow.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(glow)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(shape)

        fill = QLinearGradient(s * 0.2, s * 0.2, s * 0.8, s * 0.8)
        fill.setColorAt(0.0, QColor("#4ADE80"))
        fill.setColorAt(1.0, QColor("#16A34A"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(fill))
        p.drawPath(shape)

        # ">>" go chevrons (the first one fainter, for a sense of speed)
        for dx, alpha in ((0.0, 120), (s * 0.17, 255)):
            color = QColor(theme.ON_ACCENT)
            color.setAlpha(alpha)
            pen = QPen(color, s * 0.062)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            chevron = QPainterPath()
            chevron.moveTo(QPointF(s * 0.36 + dx, s * 0.31))
            chevron.lineTo(QPointF(s * 0.46 + dx, s * 0.425))
            chevron.lineTo(QPointF(s * 0.36 + dx, s * 0.54))
            p.drawPath(chevron)

        # notification dot
        cx, cy = s * 0.80, s * 0.21
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(QColor("#07130C")))
        p.drawEllipse(QPointF(cx, cy), s * 0.118, s * 0.118)
        p.setBrush(QBrush(QColor(theme.COMPLEMENT)))
        p.drawEllipse(QPointF(cx, cy), s * 0.085, s * 0.085)


def make_logo_pixmap(size: int = 128) -> QPixmap:
    """Render the logo to a pixmap (window icon, README image)."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    LogoWidget(size).render(pixmap)
    return pixmap


class AvatarWidget(QWidget):
    """Round avatar: a profile picture if there is one, otherwise an emoji on a colour disc."""

    def __init__(self, glyph: str = "👤", color: str = theme.ACCENT, size: int = 46,
                 online: bool | None = None, pixmap: QPixmap | None = None,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.set_avatar(glyph, color, online, pixmap)

    def set_avatar(self, glyph: str, color: str, online: bool | None = None,
                   pixmap: QPixmap | None = None) -> None:
        self._glyph, self._color, self._online, self._pixmap = glyph, color, online, pixmap
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        diameter = self.width() - 6

        if self._pixmap is not None:
            clip = QPainterPath()
            clip.addEllipse(QRectF(2, 2, diameter, diameter))
            p.save()
            p.setClipPath(clip)
            p.drawPixmap(QRect(2, 2, diameter, diameter), self._pixmap)
            p.restore()
        else:
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
            p.setBrush(QBrush(QColor(theme.BG)))
            p.drawEllipse(x - 2, x - 2, dot + 4, dot + 4)
            p.setBrush(QBrush(QColor(theme.ONLINE if self._online else theme.OFFLINE)))
            p.drawEllipse(x, x, dot, dot)


class ClickableAvatar(AvatarWidget):
    clicked = pyqtSignal()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()


class ConversationTile(QFrame):
    """One row of the chat list (avatar, name, last message, time, unread badge)."""

    clicked = pyqtSignal(str)

    def __init__(self, key: str, title: str, glyph: str, color: str, preview: str,
                 time_text: str, unread: int, online: bool | None,
                 pixmap: QPixmap | None = None) -> None:
        super().__init__()
        self.key = key
        self.setObjectName("ChatTile")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        layout.addWidget(AvatarWidget(glyph, color, 50, online, pixmap))

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


def soft_wrap(text: str, width: int = 24) -> str:
    """Let very long words (no spaces) wrap inside a bubble by adding invisible break points."""
    return re.sub(rf"(\S{{{width}}})(?=\S)", "\\1\u200b", text)


class MessageBubble(QFrame):
    """Chat bubble: ``😎 Hail [September 12, 2026 • 08:45 AM]`` then the message."""

    def __init__(self, msg: dict, own: bool, pixmap: QPixmap | None = None,
                 max_width: int = 300) -> None:
        super().__init__()
        self.setObjectName("BubbleOwn" if own else "BubbleOther")
        self.setMaximumWidth(max_width)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 9, 14, 9)
        layout.setSpacing(4)

        head = QHBoxLayout()
        head.setSpacing(6)
        stamp = f"[{format_timestamp(msg['ts'])}]"
        if pixmap is not None:      # profile picture instead of the emoji avatar
            head.addWidget(AvatarWidget(msg["avatar"], theme.color_for(msg["sender"]), 26,
                                        pixmap=pixmap))
            title = f"{msg['sender']}  {stamp}"
        else:
            title = f"{msg['avatar']} {msg['sender']}  {stamp}"
        header = QLabel(title)
        header.setObjectName("BubbleHeader")
        header.setWordWrap(True)
        head.addWidget(header, 1)

        body = QLabel(soft_wrap(msg["text"]))
        body.setObjectName("BubbleBody")
        body.setWordWrap(True)
        body.setTextFormat(Qt.TextFormat.PlainText)
        body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        layout.addLayout(head)
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
        self.setFixedSize(350, 290)

        tabs = QTabWidget()
        for category, emojis in EMOJI_CATEGORIES.items():
            tabs.addTab(self._build_grid(emojis), category.split(" ")[0])   # icon-only tabs
            tabs.setTabToolTip(tabs.count() - 1, category.split(" ", 1)[1])
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
        """Pop up over ``anchor``, kept inside the phone window."""
        window = anchor.window()
        left = window.mapToGlobal(QPoint(0, 0)).x()
        origin = anchor.mapToGlobal(QPoint(0, 0))
        x = max(left + 6, min(origin.x(), left + window.width() - self.width() - 6))
        self.move(x, origin.y() - self.height() - 6)
        self.show()
