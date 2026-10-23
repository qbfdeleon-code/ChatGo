"""Small helper functions: logo, avatars, profile pictures, time and window size."""
import base64
from datetime import datetime

from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRect, QRectF, Qt
from PyQt6.QtGui import (
    QBrush, QColor, QFont, QGuiApplication, QImage, QLinearGradient, QPainter,
    QPainterPath, QPen, QPixmap,
)

import config
import styles


def make_logo(size):
    """Draw the ChatGo logo: a green chat bubble with 'go' arrows and a pink dot."""
    s = float(size)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # dark rounded tile with a green border
    tile = QLinearGradient(0, 0, 0, s)
    tile.setColorAt(0, QColor("#10241A"))
    tile.setColorAt(1, QColor("#020504"))
    p.setPen(QPen(QColor(34, 197, 94, 170), max(1.0, s * 0.02)))
    p.setBrush(QBrush(tile))
    p.drawRoundedRect(QRectF(s * 0.02, s * 0.02, s * 0.96, s * 0.96), s * 0.26, s * 0.26)

    # speech bubble = rounded rectangle + small tail
    bubble = QPainterPath()
    bubble.addRoundedRect(QRectF(s * 0.16, s * 0.17, s * 0.68, s * 0.52), s * 0.2, s * 0.2)
    tail = QPainterPath()
    tail.moveTo(QPointF(s * 0.28, s * 0.62))
    tail.lineTo(QPointF(s * 0.24, s * 0.84))
    tail.lineTo(QPointF(s * 0.47, s * 0.67))
    tail.closeSubpath()
    green = QLinearGradient(0, 0, s, s)
    green.setColorAt(0, QColor("#4ADE80"))
    green.setColorAt(1, QColor("#16A34A"))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(green))
    p.drawPath(bubble.united(tail))

    # two ">" arrows inside the bubble = "go"
    pen = QPen(QColor(styles.ON_GREEN), s * 0.065)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    for x in (0.36, 0.55):
        arrow = QPainterPath()
        arrow.moveTo(QPointF(s * x, s * 0.28))
        arrow.lineTo(QPointF(s * (x + 0.14), s * 0.43))
        arrow.lineTo(QPointF(s * x, s * 0.58))
        p.drawPath(arrow)

    # pink notification dot (the complementary color)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#0A140F"))
    p.drawEllipse(QPointF(s * 0.80, s * 0.20), s * 0.1, s * 0.1)
    p.setBrush(QColor(styles.PINK))
    p.drawEllipse(QPointF(s * 0.80, s * 0.20), s * 0.075, s * 0.075)
    p.end()
    return pixmap


def make_avatar(emoji, picture, size, color):
    """Round avatar: the profile picture if there is one, otherwise the emoji on a color."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    circle = QPainterPath()
    circle.addEllipse(0, 0, size, size)
    p.setClipPath(circle)

    if picture is not None:
        p.drawPixmap(0, 0, size, size, picture)
    else:
        p.fillRect(0, 0, size, size, QColor(color))
        font = QFont()
        font.setPixelSize(int(size * 0.5))
        p.setFont(font)
        p.setPen(QColor("white"))
        p.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, emoji)
    p.end()
    return pixmap


def picture_file_to_text(path):
    """Turn an image file into a small square JPEG, saved as text so we can send it.

    Returns None if the file is not an image.
    """
    image = QImage(path)
    if image.isNull():
        return None
    side = min(image.width(), image.height())                       # crop to a square
    image = image.copy((image.width() - side) // 2, (image.height() - side) // 2, side, side)
    image = image.scaled(96, 96, Qt.AspectRatioMode.IgnoreAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)

    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "JPG", 85)
    text = base64.b64encode(data.data()).decode("ascii")
    return text if len(text) <= config.MAX_PICTURE_TEXT else None


def text_to_pixmap(text):
    """The opposite of picture_file_to_text. Returns None if there is no picture."""
    if not text:
        return None
    pixmap = QPixmap()
    if pixmap.loadFromData(base64.b64decode(text)):
        return pixmap
    return None


def format_time(timestamp):
    """Example: September 12, 2026 • 08:45 AM"""
    return datetime.fromtimestamp(timestamp).strftime("%B %d, %Y • %I:%M %p")


def short_time(timestamp):
    """Short time for the chat list: 8:45 AM, Yesterday, or Sep 12."""
    moment = datetime.fromtimestamp(timestamp)
    days = (datetime.now().date() - moment.date()).days
    if days == 0:
        return moment.strftime("%I:%M %p").lstrip("0")
    if days == 1:
        return "Yesterday"
    return moment.strftime("%b %d")


def wrap_long_words(text, limit=25):
    """Cut very long words (no spaces) so they wrap inside a message bubble."""
    pieces = []
    for word in text.split(" "):
        while len(word) > limit:
            pieces.append(word[:limit])
            word = word[limit:]
        pieces.append(word)
    return " ".join(pieces)


def place_window(window, slot=0):
    """Give a window phone dimensions. `slot` puts several windows side by side."""
    screen = QGuiApplication.primaryScreen().availableGeometry()
    height = max(600, min(config.PHONE_HEIGHT, screen.height() - 70))   # fit small screens
    window.setFixedSize(config.PHONE_WIDTH, height)
    x = screen.x() + 30 + slot * (config.PHONE_WIDTH + 24)
    if x + config.PHONE_WIDTH > screen.right():
        x = screen.x() + 30
    window.move(x, screen.y() + max(10, (screen.height() - height) // 2 - 10))
