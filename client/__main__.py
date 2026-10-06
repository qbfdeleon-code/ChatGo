"""Run the client:  python -m client"""
import sys

from PyQt6.QtWidgets import QApplication, QDialog

from client.chat_window import ChatWindow
from client.config import APP_NAME, ORG_NAME
from client.login_window import LoginWindow
from client.network import NetworkClient
from client.styles import APP_STYLE


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setStyleSheet(APP_STYLE)

    while True:                                  # loop so "Log out" returns to the login screen
        network = NetworkClient()
        login = LoginWindow(network)
        if login.exec() != QDialog.DialogCode.Accepted:
            return 0
        window = ChatWindow(network, login.session)
        window.show()
        app.exec()
        if not window.logged_out:
            return 0


if __name__ == "__main__":
    sys.exit(main())
