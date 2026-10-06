"""Login dialog: server address, username, optional password, avatar picker."""
from __future__ import annotations

import re

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtWidgets import (
    QApplication, QButtonGroup, QDialog, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QVBoxLayout,
)

from client.network import LoginError, NetworkClient
from common import protocol


class LoginWindow(QDialog):
    """On success, ``self.client`` (connected) and ``self.session`` (login_ok) are set."""

    def __init__(self) -> None:
        super().__init__()
        self.client: NetworkClient | None = None
        self.session: dict | None = None
        self.settings = QSettings("ChatWave", "Client")

        self.setWindowTitle("ChatWave — Login")
        self.setFixedSize(400, 640)

        root = QVBoxLayout(self)
        root.setContentsMargins(36, 28, 36, 28)
        root.setSpacing(8)

        logo = QLabel("💬")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet("font-size: 44px;")
        title = QLabel("ChatWave")
        title.setObjectName("LoginTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("Connect • Share • Be You")
        subtitle.setObjectName("LoginSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for w in (logo, title, subtitle):
            root.addWidget(w)
        root.addSpacing(10)

        # Server
        root.addWidget(self._label("Server"))
        server_row = QHBoxLayout()
        self.host = QLineEdit(self.settings.value("host", protocol.DEFAULT_HOST))
        self.host.setPlaceholderText("Server address")
        self.port = QLineEdit(str(self.settings.value("port", protocol.DEFAULT_PORT)))
        self.port.setFixedWidth(90)
        server_row.addWidget(self.host)
        server_row.addWidget(self.port)
        root.addLayout(server_row)

        # Username
        root.addWidget(self._label("Username"))
        self.username = QLineEdit(self.settings.value("username", ""))
        self.username.setPlaceholderText("Username")
        root.addWidget(self.username)

        # Password (optional) with show/hide toggle
        root.addWidget(self._label("Password (optional)"))
        pw_row = QHBoxLayout()
        self.password = QLineEdit()
        self.password.setPlaceholderText("Password (optional)")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.show_pw = QPushButton("👁")
        self.show_pw.setObjectName("Ghost")
        self.show_pw.setCheckable(True)
        self.show_pw.setAutoDefault(False)
        self.show_pw.setFixedWidth(44)
        self.show_pw.toggled.connect(self._toggle_password)
        pw_row.addWidget(self.password)
        pw_row.addWidget(self.show_pw)
        root.addLayout(pw_row)

        # Avatar picker
        root.addWidget(self._label("Choose avatar"))
        grid = QGridLayout()
        grid.setSpacing(6)
        self.avatar_group = QButtonGroup(self)
        saved = self.settings.value("avatar", protocol.AVATARS[0])
        for i, glyph in enumerate(protocol.AVATARS):
            btn = QPushButton(glyph)
            btn.setObjectName("AvatarChoice")
            btn.setCheckable(True)
            btn.setAutoDefault(False)
            btn.setFixedSize(44, 44)
            btn.setChecked(glyph == saved or (i == 0 and saved not in protocol.AVATARS))
            self.avatar_group.addButton(btn)
            grid.addWidget(btn, i // 5, i % 5)
        root.addLayout(grid)

        root.addStretch()
        self.error = QLabel("")
        self.error.setObjectName("Error")
        self.error.setWordWrap(True)
        self.error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.error)

        self.join_button = QPushButton("Join Chat →")
        self.join_button.setObjectName("Primary")
        self.join_button.setDefault(True)          # Enter key submits the form
        self.join_button.clicked.connect(self._on_join)
        root.addWidget(self.join_button)

        (self.password if self.username.text() else self.username).setFocus()

    @staticmethod
    def _label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("FieldLabel")
        return label

    def _toggle_password(self, visible: bool) -> None:
        self.password.setEchoMode(
            QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password)

    def _selected_avatar(self) -> str:
        button = self.avatar_group.checkedButton()
        return button.text() if button else protocol.AVATARS[0]

    def _on_join(self) -> None:
        username = self.username.text().strip()
        if not re.match(protocol.USERNAME_PATTERN, username):
            self.error.setText("Username must be 2-20 characters: letters, numbers, _ . -")
            return
        host = self.host.text().strip() or protocol.DEFAULT_HOST
        try:
            port = int(self.port.text())
        except ValueError:
            self.error.setText("Port must be a number.")
            return

        self.error.setText("")
        self.join_button.setEnabled(False)
        self.join_button.setText("Connecting…")
        QApplication.processEvents()

        client = NetworkClient()
        try:
            session = client.connect_and_login(
                host, port, username, self.password.text(), self._selected_avatar())
        except LoginError as exc:
            self.error.setText(str(exc))
        except ConnectionError:
            self.error.setText(f"Could not connect to {host}:{port}.\n"
                               "Make sure run_server.py is running.")
        else:
            self.settings.setValue("host", host)
            self.settings.setValue("port", port)
            self.settings.setValue("username", username)
            self.settings.setValue("avatar", self._selected_avatar())
            self.client, self.session = client, session
            self.accept()
            return
        self.join_button.setEnabled(True)
        self.join_button.setText("Join Chat →")
