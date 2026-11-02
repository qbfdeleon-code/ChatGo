"""Profile-picture helpers: file -> small base64 JPEG, and base64 -> QPixmap."""
from __future__ import annotations

import base64

from PyQt6.QtCore import QBuffer, QIODevice, Qt
from PyQt6.QtGui import QImage, QPixmap

from common.protocol import MAX_PICTURE_B64, PICTURE_SIZE


def encode_picture_file(path: str) -> str | None:
    """Centre-crop to a square, scale to 96x96 and return base64 (``None`` if unreadable)."""
    image = QImage(path)
    if image.isNull():
        return None
    side = min(image.width(), image.height())
    image = image.copy((image.width() - side) // 2, (image.height() - side) // 2, side, side)
    image = image.scaled(PICTURE_SIZE, PICTURE_SIZE, Qt.AspectRatioMode.IgnoreAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
    for fmt, quality in (("JPG", 85), ("PNG", -1)):
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if image.save(buffer, fmt, quality):
            data = base64.b64encode(bytes(buffer.data())).decode("ascii")
            if len(data) <= MAX_PICTURE_B64:
                return data
    return None


def pixmap_from_b64(data: str | None) -> QPixmap | None:
    if not data:
        return None
    try:
        raw = base64.b64decode(data)
    except ValueError:
        return None
    pixmap = QPixmap()
    return pixmap if pixmap.loadFromData(raw) else None
