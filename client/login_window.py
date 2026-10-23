"""Phone-sized Log In / Sign Up screen (username + password, avatar, optional picture)."""
from __future__ import annotations

import re

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtWidgets import (
    QApplication, QButtonGroup, QDialog, QFileDialog, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

from client import theme
from client.images import encode_picture_file, pixmap_from_b64
from client.network import LoginError, NetworkClient
from client.phone import place
from client.widgets import ClickableAvatar, LogoWidget
from common import protocol


class LoginWindow(QDialog):
    """On success, ``self.client`` (connected) and ``self.session`` (login_ok) are set."""

    def __init__(self, slot: int = 0) -> None:
        super().__init__()
        self.client: NetworkClient | None = None
        self.session: dict | None = None
        self.picture: str | None = None             # base64 profile picture (Sign Up only)
        self.settings = QSettings("ChatGo", "Client")
        self._key = f"slot{slot}/"                  # each local window remembers its own user

        self.setWindowTitle("ChatGo")
        place(self, slot)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 20)
        root.setSpacing(8)

        title = QLabel("ChatGo")
        title.setObjectName("LoginTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel("Connect • Share • Be You")
        subtitle.setObjectName("LoginSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(LogoWidget(76), alignment=Qt.AlignmentFlag.AlignHCenter)
        root.addWidget(title)
        root.addWidget(subtitle)
        root.addSpacing(6)

        # ---- Log In / Sign Up switch
        tabs = QHBoxLayout()
        tabs.setSpacing(8)
        self.login_tab = QPushButton("Log In")
        self.signup_tab = QPushButton("Sign Up")
        self.tab_group = QButtonGroup(self)
        for tab in (self.login_tab, self.signup_tab):
            tab.setObjectName("SegButton")
            tab.setCheckable(True)
            tab.setAutoDefault(False)
            self.tab_group.addButton(tab)
            tabs.addWidget(tab)
        self.login_tab.setChecked(True)
        self.tab_group.buttonClicked.connect(lambda _b: self._apply_mode())
        root.addLayout(tabs)

        # ---- username + password
        self.username = QLineEdit(str(self.settings.value(self._key + "username", "")))
        self.username.setPlaceholderText("Username")
        root.addWidget(self.username)

        pw_row = QHBoxLayout()
        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
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

        # ---- Sign Up extras: confirm password, avatar, optional picture
        self.signup_box = QWidget()
        box = QVBoxLayout(self.signup_box)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(8)

        self.confirm = QLineEdit()
        self.confirm.setPlaceholderText("Confirm password")
        self.confirm.setEchoMode(QLineEdit.EchoMode.Password)
        box.addWidget(self.confirm)

        label = QLabel("Choose your avatar")
        label.setObjectName("FieldLabel")
        box.addWidget(label)
        grid = QGridLayout()
        grid.setSpacing(6)
        self.avatar_group = QButtonGroup(self)
        saved = str(self.settings.value(self._key + "avatar", protocol.AVATARS[0]))
        if saved not in protocol.AVATARS:
            saved = protocol.AVATARS[0]
        for i, glyph in enumerate(protocol.AVATARS):
            btn = QPushButton(glyph)
            btn.setObjectName("AvatarChoice")
            btn.setCheckable(True)
            btn.setAutoDefault(False)
            btn.setFixedSize(40, 40)
            btn.setStyleSheet("border-radius: 20px; font-size: 18px;")
            btn.setChecked(glyph == saved)
            self.avatar_group.addButton(btn)
            grid.addWidget(btn, i // 5, i % 5, Qt.AlignmentFlag.AlignHCenter)
        box.addLayout(grid)
        self.avatar_group.buttonClicked.connect(lambda _b: self._refresh_preview())

        pic_row = QHBoxLayout()
        pic_row.setSpacing(12)
        self.preview = ClickableAvatar(self._selected_avatar(), theme.ACCENT, 62)
        self.preview.clicked.connect(self._choose_picture)
        pic_col = QVBoxLayout()
        pic_col.setSpacing(2)
        self.pick_button = QPushButton("📷  Upload profile picture (optional)")
        self.pick_button.setObjectName("Ghost")
        self.pick_button.setAutoDefault(False)
        self.pick_button.clicked.connect(self._choose_picture)
        self.remove_link = QPushButton("✖ Remove picture")
        self.remove_link.setObjectName("Link")
        self.remove_link.setAutoDefault(False)
        self.remove_link.clicked.connect(self._remove_picture)
        self.remove_link.hide()
        hint = QLabel("No picture? Your emoji is your avatar.")
        hint.setObjectName("Hint")
        pic_col.addWidget(self.pick_button)
        pic_col.addWidget(self.remove_link)
        pic_col.addWidget(hint)
        pic_row.addWidget(self.preview)
        pic_row.addLayout(pic_col, 1)
        box.addLayout(pic_row)
        root.addWidget(self.signup_box)

        # ---- server settings (hidden until needed)
        self.server_link = QPushButton("⚙  Server settings")
        self.server_link.setObjectName("Link")
        self.server_link.setAutoDefault(False)
        self.server_link.clicked.connect(self._toggle_server)
        root.addWidget(self.server_link)
        self.server_box = QWidget()
        srv = QHBoxLayout(self.server_box)
        srv.setContentsMargins(0, 0, 0, 0)
        self.host = QLineEdit(str(self.settings.value("host", protocol.DEFAULT_HOST)))
        self.host.setPlaceholderText("Server address")
        self.port = QLineEdit(str(self.settings.value("port", protocol.DEFAULT_PORT)))
        self.port.setFixedWidth(90)
        srv.addWidget(self.host)
        srv.addWidget(self.port)
        self.server_box.hide()
        root.addWidget(self.server_box)

        root.addStretch()
        self.error = QLabel("")
        self.error.setObjectName("Error")
        self.error.setWordWrap(True)
        self.error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.error)

        self.submit = QPushButton("Log In")
        self.submit.setObjectName("Primary")
        self.submit.setDefault(True)               # Enter submits the form
        self.submit.clicked.connect(self._on_submit)
        root.addWidget(self.submit)

        self._apply_mode()
        (self.password if self.username.text() else self.username).setFocus()

    # ---------------------------------------------------------------- helpers
    @property
    def mode(self) -> str:
        return "register" if self.signup_tab.isChecked() else "login"

    def _apply_mode(self) -> None:
        signup = self.mode == "register"
        self.signup_box.setVisible(signup)
        self.submit.setText("Create Account" if signup else "Log In")
        self.password.setPlaceholderText("Password (min. 4 characters)" if signup else "Password")
        self.error.setText("")

    def _toggle_password(self, visible: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        self.password.setEchoMode(mode)
        self.confirm.setEchoMode(mode)

    def _toggle_server(self) -> None:
        self.server_box.setVisible(not self.server_box.isVisible())

    def _selected_avatar(self) -> str:
        button = self.avatar_group.checkedButton() if hasattr(self, "avatar_group") else None
        return button.text() if button else protocol.AVATARS[0]

    def _refresh_preview(self) -> None:
        self.preview.set_avatar(self._selected_avatar(), theme.ACCENT, None,
                                pixmap_from_b64(self.picture))
        self.remove_link.setVisible(self.picture is not None)
        self.pick_button.setText("📷  Change picture" if self.picture
                                 else "📷  Upload profile picture (optional)")

    def _choose_picture(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose a profile picture", "",
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp)")
        if not path:
            return
        data = encode_picture_file(path)
        if data is None:
            self.error.setText("That image could not be used. Try a PNG or JPG file.")
            return
        self.error.setText("")
        self.picture = data
        self._refresh_preview()

    def _remove_picture(self) -> None:
        self.picture = None
        self._refresh_preview()

    # ----------------------------------------------------------------- submit
    def _on_submit(self) -> None:
        username = self.username.text().strip()
        password = self.password.text()
        register = self.mode == "register"

        if not re.match(protocol.USERNAME_PATTERN, username):
            self.error.setText("Username must be 2-20 characters: letters, numbers, _ . -")
            return
        if not password:
            self.error.setText("Please enter your password.")
            return
        if register:
            if len(password) < protocol.MIN_PASSWORD_LENGTH:
                self.error.setText(
                    f"Password must be at least {protocol.MIN_PASSWORD_LENGTH} characters.")
                return
            if password != self.confirm.text():
                self.error.setText("The two passwords do not match.")
                return
        host = self.host.text().strip() or protocol.DEFAULT_HOST
        try:
            port = int(self.port.text())
        except ValueError:
            self.error.setText("Port must be a number.")
            self.server_box.show()
            return

        self.error.setText("")
        self.submit.setEnabled(False)
        self.submit.setText("Connecting…")
        QApplication.processEvents()

        client = NetworkClient()
        try:
            session = client.authenticate(
                host, port, self.mode, username, password,
                avatar=self._selected_avatar() if register else None,
                picture=self.picture if register else None)
        except LoginError as exc:
            self.error.setText(str(exc))
        except ConnectionError:
            self.error.setText(f"Could not connect to {host}:{port}.\n"
                               "Make sure the server is running (run_server.py).")
            self.server_box.show()
        else:
            self.settings.setValue("host", host)
            self.settings.setValue("port", port)
            self.settings.setValue(self._key + "username", session["username"])
            self.settings.setValue(self._key + "avatar", session["avatar"])
            self.client, self.session = client, session
            self.accept()
            return
        self.submit.setEnabled(True)
        self.submit.setText("Create Account" if register else "Log In")   # keep the error visible
