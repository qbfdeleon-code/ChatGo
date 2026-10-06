"""Client entry point: login dialog -> chat window."""
import sys

from PyQt6.QtWidgets import QApplication, QDialog

from client.chat_window import ChatWindow
from client.login_window import LoginWindow
from client.theme import APP_STYLESHEET


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("ChatWave")
    app.setStyleSheet(APP_STYLESHEET)

    login = LoginWindow()
    if login.exec() != QDialog.DialogCode.Accepted:
        return 0

    window = ChatWindow(login.client, login.session)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
