"""Purple palette (with a warm orange complement) and the application stylesheet."""

BG = "#1A1330"
SIDEBAR = "#211A3A"
PANEL = "#2A2150"
ACCENT = "#6C63FF"
ACCENT_HOVER = "#584FE0"
COMPLEMENT = "#FF9F43"        # orange: unread badges
TEXT = "#F5F3FF"
MUTED = "#A9A3D6"
BORDER = "#3B3170"
BUBBLE_OTHER = "#332A63"
ONLINE = "#22C55E"
OFFLINE = "#6B6590"

AVATAR_COLORS = ["#FF9F0A", "#0A84FF", "#BF5AF2", "#5E5CE6", "#30D158",
                 "#64D2FF", "#FF453A", "#FF375F"]


def color_for(name: str) -> str:
    """Stable avatar colour derived from a name."""
    return AVATAR_COLORS[sum(map(ord, name)) % len(AVATAR_COLORS)]


_QSS = """
* { font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif; }
QWidget { color: @TEXT@; }
QDialog, QWidget#Root { background-color: @BG@; }
QMessageBox { background-color: @BG@; }

QLineEdit {
    background-color: @PANEL@; border: 1px solid @BORDER@; border-radius: 14px;
    padding: 9px 14px; font-size: 14px; selection-background-color: @ACCENT@;
}
QLineEdit:focus { border: 1px solid @ACCENT@; }
QLineEdit:disabled { color: @MUTED@; }

QPushButton#Primary {
    background-color: @ACCENT@; color: white; border: none; border-radius: 12px;
    padding: 10px 20px; font-weight: bold; font-size: 14px;
}
QPushButton#Primary:hover { background-color: @ACCENT_HOVER@; }
QPushButton#Primary:disabled { background-color: @BORDER@; color: @MUTED@; }

QPushButton#Ghost {
    background: transparent; border: 1px solid @BORDER@; border-radius: 10px;
    padding: 7px 14px; color: @MUTED@;
}
QPushButton#Ghost:hover { background-color: @PANEL@; color: @TEXT@; }

QPushButton#EmojiToggle {
    background-color: @PANEL@; border: 1px solid @BORDER@; border-radius: 12px;
    font-size: 18px; min-width: 44px; max-width: 44px; min-height: 38px;
}
QPushButton#EmojiToggle:hover { background-color: @BORDER@; }

QPushButton#AvatarChoice {
    background-color: @PANEL@; border: 2px solid transparent; border-radius: 22px; font-size: 20px;
}
QPushButton#AvatarChoice:hover { background-color: @BORDER@; }
QPushButton#AvatarChoice:checked { border: 2px solid @ACCENT@; background-color: @BORDER@; }

QLabel#LoginTitle { font-size: 28px; font-weight: 800; }
QLabel#LoginSubtitle { color: @MUTED@; font-size: 12px; }
QLabel#FieldLabel { color: @MUTED@; font-size: 12px; font-weight: bold; }
QLabel#Error { color: #FF6B7A; font-size: 12px; }

QFrame#Sidebar { background-color: @SIDEBAR@; border-right: 1px solid @BORDER@; }
QLabel#Brand { font-size: 24px; font-weight: 800; }
QLabel#Me { color: @MUTED@; font-size: 12px; }

QFrame#ChatTile {
    background-color: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
}
QFrame#ChatTile:hover { background-color: rgba(255,255,255,0.12); }
QFrame#ChatTile[selected="true"] {
    background-color: rgba(108,99,255,0.30); border: 1px solid @ACCENT@;
}
QFrame#ChatTile QLabel { background: transparent; }
QLabel#TileName { font-weight: 700; font-size: 14px; }
QLabel#TileTime { color: @MUTED@; font-size: 11px; }
QLabel#TilePreview { color: #CBC6EE; font-size: 12px; }
QLabel#Badge {
    background-color: @COMPLEMENT@; color: #2B1B00; font-weight: bold; font-size: 10px;
    border-radius: 9px; min-width: 18px; max-width: 18px; min-height: 18px; max-height: 18px;
}

QFrame#ChatHeader { background-color: @ACCENT@; border-radius: 14px; }
QFrame#ChatHeader QLabel { background: transparent; color: white; }
QLabel#HeaderTitle { font-size: 18px; font-weight: bold; }
QLabel#HeaderStatus { font-size: 12px; color: rgba(255,255,255,0.8); }
QLabel#Banner { background-color: #7A2E3A; border-radius: 8px; padding: 8px 12px; font-weight: bold; }

QScrollArea { border: none; background: transparent; }
QWidget#MessageArea { background-color: @BG@; }
QWidget#TileContainer { background: transparent; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
QScrollBar::handle:vertical { background: @BORDER@; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }

QFrame#BubbleOwn { background-color: @ACCENT@; border-radius: 16px; }
QFrame#BubbleOther { background-color: @BUBBLE_OTHER@; border-radius: 16px; }
QFrame#BubbleOwn QLabel, QFrame#BubbleOther QLabel { background: transparent; }
QLabel#BubbleHeader { font-size: 11px; color: rgba(255,255,255,0.72); }
QLabel#BubbleBody { font-size: 14px; }
QLabel#BubbleEdited { font-size: 10px; color: rgba(255,255,255,0.6); }
QLabel#SystemNote { color: @MUTED@; font-size: 11px; }

QFrame#EmojiPicker { background-color: @PANEL@; border: 1px solid @BORDER@; border-radius: 12px; }
QTabWidget::pane { border: none; }
QTabBar::tab { background: transparent; color: @MUTED@; padding: 6px 10px; font-size: 12px; }
QTabBar::tab:selected { color: @TEXT@; border-bottom: 2px solid @ACCENT@; }
QPushButton#EmojiButton { background: transparent; border: none; border-radius: 8px; font-size: 22px; }
QPushButton#EmojiButton:hover { background-color: @BORDER@; }
QToolTip { background-color: @PANEL@; color: @TEXT@; border: 1px solid @BORDER@; }
"""

APP_STYLESHEET = _QSS
for _name, _value in {"BG": BG, "SIDEBAR": SIDEBAR, "PANEL": PANEL, "ACCENT": ACCENT,
                      "ACCENT_HOVER": ACCENT_HOVER, "COMPLEMENT": COMPLEMENT, "TEXT": TEXT,
                      "MUTED": MUTED, "BORDER": BORDER, "BUBBLE_OTHER": BUBBLE_OTHER}.items():
    APP_STYLESHEET = APP_STYLESHEET.replace(f"@{_name}@", _value)
