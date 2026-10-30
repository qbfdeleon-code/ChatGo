<<<<<<< HEAD

=======
>>>>>>> origin/main
"""Green & black palette with a rose complementary accent, plus the stylesheet."""

BG = "#070B09"
SIDEBAR = "#0D1410"
PANEL = "#15211A"
ACCENT = "#22C55E"
ACCENT_HOVER = "#16A34A"
ACCENT_DARK = "#0A3D1D"       # avatar discs placed on top of the accent colour
ON_ACCENT = "#04120A"         # near-black text on green
COMPLEMENT = "#FF4D8D"        # rose-magenta, the complement of green: badges, edit, alerts
<<<<<<< HEAD
TEXT = "#FFFFFF"
MUTED = "#B0B0B0"
=======
TEXT = "#ECFDF5"
MUTED = "#8FB3A0"
>>>>>>> origin/main
BORDER = "#1F3A2B"
BUBBLE_OTHER = "#18281F"
ONLINE = "#4ADE80"
OFFLINE = "#4B5D53"

AVATAR_COLORS = ["#16A34A", "#0D9488", "#65A30D", "#0891B2", "#CA8A04",
                 "#059669", "#7C3AED", "#DB2777"]


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
    padding: 9px 14px; font-size: 14px;
    selection-background-color: @ACCENT@; selection-color: @ON_ACCENT@;
}
QLineEdit:focus { border: 1px solid @ACCENT@; }
QLineEdit:disabled { color: @MUTED@; }

QPushButton#Primary {
    background-color: @ACCENT@; color: @ON_ACCENT@; border: none; border-radius: 12px;
    padding: 10px 20px; font-weight: bold; font-size: 14px;
}
QPushButton#Primary:hover { background-color: #4ADE80; }
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

QLabel#LoginTitle { font-size: 30px; font-weight: 800; }
QLabel#LoginSubtitle { color: @MUTED@; font-size: 12px; }
QLabel#FieldLabel { color: @MUTED@; font-size: 12px; font-weight: bold; }
QLabel#Error { color: #FF6B7A; font-size: 12px; }

QFrame#Sidebar { background-color: @SIDEBAR@; border-right: 1px solid @BORDER@; }
QLabel#Brand { font-size: 24px; font-weight: 800; }
QLabel#Me { color: @MUTED@; font-size: 12px; }

QFrame#ChatTile {
    background-color: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.07);
    border-radius: 16px;
}
QFrame#ChatTile:hover { background-color: rgba(255,255,255,0.10); }
QFrame#ChatTile[selected="true"] {
    background-color: rgba(34,197,94,0.20); border: 1px solid @ACCENT@;
}
QFrame#ChatTile QLabel { background: transparent; }
QLabel#TileName { font-weight: 700; font-size: 14px; }
QLabel#TileTime { color: @MUTED@; font-size: 11px; }
QLabel#TilePreview { color: #B5D3C3; font-size: 12px; }
QLabel#Badge {
    background-color: @COMPLEMENT@; color: white; font-weight: bold; font-size: 10px;
    border-radius: 9px; min-width: 18px; max-width: 18px; min-height: 18px; max-height: 18px;
}

QFrame#ChatHeader { background-color: @ACCENT@; border-radius: 14px; }
QFrame#ChatHeader QLabel { background: transparent; color: @ON_ACCENT@; }
QLabel#HeaderTitle { font-size: 18px; font-weight: bold; }
QLabel#HeaderStatus { font-size: 12px; color: rgba(4,18,10,0.75); }
QLabel#Banner { background-color: #7A2E3A; border-radius: 8px; padding: 8px 12px; font-weight: bold; }

QScrollArea { border: none; background: transparent; }
QWidget#MessageArea { background-color: @BG@; }
QWidget#TileContainer { background: transparent; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
QScrollBar::handle:vertical { background: @BORDER@; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }

<<<<<<< HEAD
QFrame#BubbleOwn { background-color: #2563EB; border-radius: 16px; }
QFrame#BubbleOther { background-color: @BUBBLE_OTHER@; border: 1px solid @BORDER@; border-radius: 16px; }
QFrame#BubbleOwn QLabel, QFrame#BubbleOther QLabel { background: transparent; }
QFrame#BubbleOwn QLabel { color: #FFFFFF; }
QFrame#BubbleOther QLabel { color: @TEXT@; }
QLabel#BubbleBody { font-size: 14px; }
QFrame#BubbleOwn QLabel#BubbleHeader, QFrame#BubbleOwn QLabel#BubbleEdited { color: rgba(255,255,255,0.75); }
=======
QFrame#BubbleOwn { background-color: @ACCENT@; border-radius: 16px; }
QFrame#BubbleOther { background-color: @BUBBLE_OTHER@; border: 1px solid @BORDER@; border-radius: 16px; }
QFrame#BubbleOwn QLabel, QFrame#BubbleOther QLabel { background: transparent; }
QFrame#BubbleOwn QLabel { color: @ON_ACCENT@; }
QFrame#BubbleOther QLabel { color: @TEXT@; }
QLabel#BubbleBody { font-size: 14px; }
QFrame#BubbleOwn QLabel#BubbleHeader, QFrame#BubbleOwn QLabel#BubbleEdited { color: rgba(4,18,10,0.7); }
>>>>>>> origin/main
QFrame#BubbleOther QLabel#BubbleHeader, QFrame#BubbleOther QLabel#BubbleEdited { color: @MUTED@; }
QLabel#BubbleHeader { font-size: 11px; }
QLabel#BubbleEdited { font-size: 10px; }
QLabel#SystemNote { color: @MUTED@; font-size: 11px; }

QFrame#EmojiPicker { background-color: @PANEL@; border: 1px solid @BORDER@; border-radius: 12px; }
QTabWidget::pane { border: none; }
QTabBar::tab { background: transparent; color: @MUTED@; padding: 6px 10px; font-size: 12px; }
QTabBar::tab:selected { color: @TEXT@; border-bottom: 2px solid @ACCENT@; }
QPushButton#EmojiButton { background: transparent; border: none; border-radius: 8px; font-size: 22px; }
QPushButton#EmojiButton:hover { background-color: @BORDER@; }

QPushButton#Back {
    background: transparent; border: none; color: @ON_ACCENT@; font-size: 30px; font-weight: bold;
    min-width: 34px; max-width: 34px; min-height: 34px; padding-bottom: 4px;
}
QPushButton#Back:hover { background-color: rgba(4,18,10,0.15); border-radius: 17px; }

QPushButton#EditButton {
    background: transparent; border: 1px solid rgba(255,77,141,0.55); border-radius: 10px;
    padding: 6px 12px; color: @COMPLEMENT@; font-size: 12px;
}
QPushButton#EditButton:hover { background-color: rgba(255,77,141,0.15); }
QPushButton#EditButton:disabled { color: @MUTED@; border-color: @BORDER@; }
QLabel#Counter { color: @MUTED@; font-size: 11px; }
QLabel#Counter[warn="true"] { color: @COMPLEMENT@; font-weight: bold; }

QPushButton#SegButton {
    background-color: @PANEL@; border: 1px solid @BORDER@; color: @MUTED@;
    padding: 10px; font-weight: bold; font-size: 13px; border-radius: 12px;
}
QPushButton#SegButton:checked { background-color: @ACCENT@; color: @ON_ACCENT@; border-color: @ACCENT@; }
QPushButton#Link {
    background: transparent; border: none; color: @MUTED@; font-size: 12px;
    text-align: left; padding: 4px 0;
}
QPushButton#Link:hover { color: @TEXT@; }
QLabel#Hint { color: @MUTED@; font-size: 11px; }

QMenu { background-color: @PANEL@; border: 1px solid @BORDER@; border-radius: 10px; padding: 6px; }
QMenu::item { padding: 8px 22px; border-radius: 6px; }
QMenu::item:selected { background-color: @ACCENT@; color: @ON_ACCENT@; }
QMenu::item:disabled { color: @MUTED@; }
QMenu::separator { height: 1px; background: @BORDER@; margin: 4px 8px; }
QToolTip { background-color: @PANEL@; color: @TEXT@; border: 1px solid @BORDER@; }
"""

APP_STYLESHEET = _QSS
for _name, _value in {"BG": BG, "SIDEBAR": SIDEBAR, "PANEL": PANEL, "ACCENT": ACCENT,
                      "ON_ACCENT": ON_ACCENT, "COMPLEMENT": COMPLEMENT, "TEXT": TEXT,
                      "MUTED": MUTED, "BORDER": BORDER, "BUBBLE_OTHER": BUBBLE_OTHER}.items():
    APP_STYLESHEET = APP_STYLESHEET.replace(f"@{_name}@", _value)
