"""ChatGo client. Start the server first (python server.py), then run:

    python main.py
"""
import sys

from PyQt6.QtWidgets import QApplication, QDialog

from chat_window import ChatWindow
from login_window import LoginWindow
from styles import STYLE


def main():
    # --slot N moves the window to the right so several clients fit side by side
    slot = 0
    if "--slot" in sys.argv:
        slot = int(sys.argv[sys.argv.index("--slot") + 1])

    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)

    login = LoginWindow(slot)
    if login.exec() != QDialog.DialogCode.Accepted:
        return

    window = ChatWindow(login.connection, login.session, slot)
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
