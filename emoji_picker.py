"""The emoji popup that opens from the 😊 button."""
from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QPushButton, QScrollArea, QTabWidget, QVBoxLayout, QWidget,
)

from emojis import EMOJIS


class EmojiPicker(QFrame):
    emoji_clicked = pyqtSignal(str)          # sent when the user clicks an emoji

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
        """One tab: a scrollable grid with a button for every emoji."""
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
        """Open the popup just above a widget (the emoji button)."""
        corner = widget.mapToGlobal(QPoint(0, 0))
        self.move(corner.x(), corner.y() - self.height() - 6)
        self.show()
