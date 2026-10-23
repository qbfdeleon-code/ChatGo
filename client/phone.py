"""Standard phone dimensions for every ChatGo window."""
from __future__ import annotations

from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QWidget

PHONE_WIDTH = 390          # logical pixels, same as an iPhone 14 / Pixel-class screen
PHONE_HEIGHT = 844


def phone_size() -> tuple[int, int]:
    """390x844, shortened only if the computer screen is too small to show it."""
    height = PHONE_HEIGHT
    screen = QGuiApplication.primaryScreen()
    if screen is not None:
        height = min(height, screen.availableGeometry().height() - 70)
    return PHONE_WIDTH, max(height, 600)


def place(widget: QWidget, slot: int = 0) -> None:
    """Give ``widget`` the phone size and put it side by side with other slots."""
    width, height = phone_size()
    widget.setFixedSize(width, height)
    screen = QGuiApplication.primaryScreen()
    if screen is None:
        return
    area = screen.availableGeometry()
    x = area.x() + 30 + slot * (width + 24)
    if x + width > area.right():
        x = area.x() + 30
    y = area.y() + max(10, (area.height() - height) // 2 - 10)
    widget.move(x, y)
