"""Client entry point: login dialog -> phone-sized chat window.

    python run_client.py            # one window
    python run_client.py --slot 1   # position the window next to slot 0 (used by run_local.py)
"""
from __future__ import annotations

import argparse
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QDialog

from client.chat_window import ChatWindow
from client.login_window import LoginWindow
from client.theme import APP_STYLESHEET
from client.widgets import make_logo_pixmap


def main() -> int:
    parser = argparse.ArgumentParser(description="ChatGo client")
    parser.add_argument("--slot", type=int, default=0, help="screen position of the phone window")
    args, qt_args = parser.parse_known_args(sys.argv[1:])

    app = QApplication([sys.argv[0], *qt_args])
    app.setApplicationName("ChatGo")
    app.setStyleSheet(APP_STYLESHEET)
    app.setWindowIcon(QIcon(make_logo_pixmap(128)))

    login = LoginWindow(args.slot)
    if login.exec() != QDialog.DialogCode.Accepted:
        return 0

    window = ChatWindow(login.client, login.session, args.slot)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
