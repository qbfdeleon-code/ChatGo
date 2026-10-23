"""Emoji popup."""
from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QPushButton, QScrollArea, QTabWidget, QVBoxLayout, QWidget,
)

from emojis import EMOJIS


class EmojiPicker(QFrame):
    emoji_clicked = pyqtSignal(str)          # an emoji was clicked

    def __init__(self, parent):
        super().__init__(parent, Qt.WindowType.Popup)
        self.setObjectName("picker")
        self.setFixedSize(350, 290)

        tabs = QTabWidget()
        for category, emojis in EMOJIS.items():
            tabs.addTab(self.make_grid(emojis), category)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addWidget(tabs)

    def make_grid(self, emojis):
        """One tab of emojis."""
        content = QWidget()
        grid = QGridLayout(content)
        grid.setSpacing(2)
        for i, emoji in enumerate(emojis):
            button = QPushButton(emoji)
            button.setObjectName("emojiItem")
            button.setFixedSize(38, 38)
            button.clicked.connect(lambda checked, e=emoji: self.emoji_clicked.emit(e))
            grid.addWidget(button, i // 8, i % 8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        return scroll

    def show_above(self, widget):
        """Show the popup above a button."""
        corner = widget.mapToGlobal(QPoint(0, 0))
        self.move(corner.x(), corner.y() - self.height() - 6)
        self.show()
