"""Colors and the stylesheet (green and black theme)."""

BG = "#070B09"
PANEL = "#15211A"
GREEN = "#22C55E"
DARK_GREEN = "#0A3D1D"
TEXT = "#ECFDF5"
MUTED = "#8FB3A0"
BORDER = "#1F3A2B"
OTHER_BUBBLE = "#18281F"
ON_GREEN = "#04120A"        # near-black text that sits on green
PINK = "#FF4D8D"            # complementary color of green

AVATAR_COLORS = ["#16A34A", "#0D9488", "#65A30D", "#0891B2", "#CA8A04", "#059669"]


def color_for(name):
    """Give every user their own avatar color."""
    return AVATAR_COLORS[sum(ord(c) for c in name) % len(AVATAR_COLORS)]


STYLE = """
QWidget { color: %(text)s; font-family: "Segoe UI", Arial, sans-serif; font-size: 14px; }
QDialog, QWidget#screen { background-color: %(bg)s; }
QMessageBox { background-color: %(bg)s; }

QLineEdit {
    background-color: %(panel)s; border: 1px solid %(border)s; border-radius: 14px;
    padding: 9px 14px;
    selection-background-color: %(green)s; selection-color: %(on_green)s;
}
QLineEdit:focus { border: 1px solid %(green)s; }

QPushButton#primary {
    background-color: %(green)s; color: %(on_green)s; border: none;
    border-radius: 12px; padding: 11px; font-weight: bold;
}
QPushButton#primary:hover { background-color: #4ADE80; }
QPushButton#primary:disabled { background-color: %(border)s; color: %(muted)s; }

QPushButton#ghost {
    background: transparent; border: 1px solid %(border)s; border-radius: 10px;
    padding: 7px 12px; color: %(muted)s;
}
QPushButton#ghost:hover { background-color: %(panel)s; color: %(text)s; }

QPushButton#tab {
    background-color: %(panel)s; border: 1px solid %(border)s; border-radius: 12px;
    padding: 10px; color: %(muted)s; font-weight: bold;
}
QPushButton#tab:checked { background-color: %(green)s; border-color: %(green)s; color: %(on_green)s; }

QPushButton#link {
    background: transparent; border: none; color: %(muted)s;
    font-size: 12px; text-align: left; padding: 4px 0;
}
QPushButton#link:hover { color: %(text)s; }

QPushButton#avatarChoice {
    background-color: %(panel)s; border: 2px solid transparent;
    border-radius: 20px; font-size: 18px;
}
QPushButton#avatarChoice:checked { border: 2px solid %(green)s; }

QPushButton#emojiButton {
    background-color: %(panel)s; border: 1px solid %(border)s; border-radius: 12px;
    font-size: 18px; min-width: 44px; max-width: 44px; min-height: 38px;
}
QPushButton#emojiButton:hover { background-color: %(border)s; }

QPushButton#back {
    background: transparent; border: none; color: %(on_green)s;
    font-size: 30px; font-weight: bold; min-width: 34px; max-width: 34px; padding-bottom: 4px;
}
QPushButton#editButton {
    background: transparent; border: 1px solid %(pink)s; border-radius: 10px;
    padding: 6px 12px; color: %(pink)s; font-size: 12px;
}
QPushButton#editButton:hover { background-color: %(panel)s; }
QPushButton#editButton:disabled { border-color: %(border)s; color: %(muted)s; }
QPushButton#avatarButton { background: transparent; border: none; }

QLabel#appName { font-size: 24px; font-weight: bold; }
QLabel#loginTitle { font-size: 30px; font-weight: bold; }
QLabel#small { color: %(muted)s; font-size: 12px; }
QLabel#error { color: #FF6B7A; font-size: 12px; }
QLabel#counter { color: %(muted)s; font-size: 11px; }
QLabel#notice { color: %(muted)s; font-size: 11px; }
QLabel#banner { background-color: #7A2E3A; border-radius: 8px; padding: 8px 12px; }

QListWidget { background: transparent; border: none; outline: none; }
QListWidget::item {
    background-color: %(panel)s; border: 1px solid %(border)s;
    border-radius: 14px; padding: 8px; margin-bottom: 8px;
}
QListWidget::item:hover { background-color: #1B2B21; }
QListWidget::item:selected { background-color: #1B2B21; color: %(text)s; }

QFrame#header { background-color: %(green)s; border-radius: 14px; }
QFrame#header QLabel { color: %(on_green)s; background: transparent; }
QFrame#header QLabel#headerTitle { font-size: 18px; font-weight: bold; }
QFrame#header QLabel#headerStatus { font-size: 12px; }

QFrame#mine { background-color: %(green)s; border-radius: 16px; }
QFrame#mine QLabel { color: %(on_green)s; background: transparent; }
QFrame#theirs { background-color: %(other)s; border: 1px solid %(border)s; border-radius: 16px; }
QFrame#theirs QLabel { color: %(text)s; background: transparent; }
QFrame#mine QLabel#bubbleInfo, QFrame#theirs QLabel#bubbleInfo { font-size: 10px; }
QFrame#theirs QLabel#bubbleInfo { color: %(muted)s; }

QScrollArea { border: none; background: transparent; }
QWidget#messages { background-color: %(bg)s; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
QScrollBar::handle:vertical { background: %(border)s; border-radius: 4px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QFrame#picker { background-color: %(panel)s; border: 1px solid %(border)s; border-radius: 12px; }
QTabWidget::pane { border: none; }
QTabBar::tab { background: transparent; color: %(muted)s; padding: 6px 12px; font-size: 16px; }
QTabBar::tab:selected { border-bottom: 2px solid %(green)s; }
QPushButton#emojiItem { background: transparent; border: none; border-radius: 8px; font-size: 22px; }
QPushButton#emojiItem:hover { background-color: %(border)s; }

QMenu { background-color: %(panel)s; border: 1px solid %(border)s; padding: 4px; }
QMenu::item { padding: 8px 18px; border-radius: 6px; }
QMenu::item:selected { background-color: %(border)s; }
""" % {"bg": BG, "panel": PANEL, "green": GREEN, "text": TEXT, "muted": MUTED,
       "border": BORDER, "other": OTHER_BUBBLE, "on_green": ON_GREEN, "pink": PINK}
