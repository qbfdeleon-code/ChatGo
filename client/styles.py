"""Colour palette and global stylesheet (purple / complementary theme)."""

PRIMARY = "#6C63FF"
PRIMARY_DARK = "#584FE0"
PRIMARY_SOFT = "#E8E5FF"
BACKGROUND = "#F5F3FF"
BORDER = "#D8D4FF"
TEXT = "#1F1B3A"
MUTED = "#8A87A8"
SURFACE = "#FFFFFF"
ONLINE = "#22C55E"
DANGER = "#DC2626"
ACCENT = "#FF9F0A"   # complementary warm accent (unread badges)

APP_STYLE = f"""
* {{ font-family: "Segoe UI", "Noto Sans", "Helvetica Neue", Arial, sans-serif; }}
QWidget {{ color: {TEXT}; }}
QLineEdit {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px;
    padding: 9px 12px; font-size: 14px; selection-background-color: {PRIMARY};
}}
QLineEdit:focus {{ border: 1px solid {PRIMARY}; }}
QPushButton#Primary {{
    background: {PRIMARY}; color: white; border: none; border-radius: 10px;
    padding: 10px 18px; font-weight: bold; font-size: 14px;
}}
QPushButton#Primary:hover {{ background: {PRIMARY_DARK}; }}
QPushButton#Primary:disabled {{ background: {BORDER}; color: white; }}
QPushButton#Flat {{
    background: {SURFACE}; color: {PRIMARY}; border: 1px solid {BORDER};
    border-radius: 10px; padding: 8px 14px; font-weight: 600;
}}
QPushButton#Flat:hover {{ background: {PRIMARY_SOFT}; }}
QPushButton#Flat:disabled {{ color: {MUTED}; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""
