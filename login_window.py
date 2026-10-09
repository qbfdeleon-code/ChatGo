"""Login / Sign Up screen."""
import re

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QApplication, QButtonGroup, QDialog, QFileDialog, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

import config
import styles
from helpers import make_avatar, make_logo, picture_file_to_text, place_window, text_to_pixmap
from network import LoginError, ServerConnection


class LoginWindow(QDialog):
    def __init__(self, slot=0):
        super().__init__()
        self.setWindowTitle("ChatGo")
        self.setWindowIcon(QIcon(make_logo(64)))
        place_window(self, slot)

        self.connection = None       # set after a successful login
        self.session = None          # the server's login_ok packet
        self.picture = None          # profile picture (text), only used when signing up

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 20)
        layout.setSpacing(8)

        # logo and title
        logo = QLabel()
        logo.setPixmap(make_logo(76))
        title = QLabel("ChatGo")
        title.setObjectName("loginTitle")
        subtitle = QLabel("Connect • Share • Be You")
        subtitle.setObjectName("small")
        for widget in (logo, title, subtitle):
            widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(widget)

        # Log In / Sign Up switch
        tabs = QHBoxLayout()
        self.login_tab = QPushButton("Log In")
        self.signup_tab = QPushButton("Sign Up")
        group = QButtonGroup(self)
        for tab in (self.login_tab, self.signup_tab):
            tab.setObjectName("tab")
            tab.setCheckable(True)
            tab.setAutoDefault(False)
            group.addButton(tab)
            tabs.addWidget(tab)
        self.login_tab.setChecked(True)
        group.buttonClicked.connect(self.update_mode)
        layout.addLayout(tabs)

        # username and password
        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        layout.addWidget(self.username)

        password_row = QHBoxLayout()
        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        show_button = QPushButton("👁")
        show_button.setObjectName("ghost")
        show_button.setCheckable(True)
        show_button.setAutoDefault(False)
        show_button.setFixedWidth(44)
        show_button.toggled.connect(self.show_password)
        password_row.addWidget(self.password)
        password_row.addWidget(show_button)
        layout.addLayout(password_row)

        # extra fields that only appear on the Sign Up tab
        self.signup_fields = QWidget()
        signup_layout = QVBoxLayout(self.signup_fields)
        signup_layout.setContentsMargins(0, 0, 0, 0)
        signup_layout.setSpacing(8)

        self.confirm = QLineEdit()
        self.confirm.setPlaceholderText("Confirm password")
        self.confirm.setEchoMode(QLineEdit.EchoMode.Password)
        signup_layout.addWidget(self.confirm)

        label = QLabel("Choose your avatar")
        label.setObjectName("small")
        signup_layout.addWidget(label)

        grid = QGridLayout()
        self.avatar_buttons = QButtonGroup(self)
        for i, emoji in enumerate(config.AVATARS):
            button = QPushButton(emoji)
            button.setObjectName("avatarChoice")
            button.setCheckable(True)
            button.setAutoDefault(False)
            button.setFixedSize(40, 40)
            self.avatar_buttons.addButton(button)
            grid.addWidget(button, i // 5, i % 5, Qt.AlignmentFlag.AlignHCenter)
        self.avatar_buttons.buttons()[0].setChecked(True)
        self.avatar_buttons.buttonClicked.connect(self.update_preview)
        signup_layout.addLayout(grid)

        picture_row = QHBoxLayout()
        self.preview = QLabel()
        self.preview.setFixedSize(62, 62)
        picture_column = QVBoxLayout()
        self.picture_button = QPushButton("📷  Upload profile picture (optional)")
        self.picture_button.setObjectName("ghost")
        self.picture_button.setAutoDefault(False)
        self.picture_button.clicked.connect(self.choose_picture)
        self.remove_button = QPushButton("✖ Remove picture")
        self.remove_button.setObjectName("link")
        self.remove_button.setAutoDefault(False)
        self.remove_button.clicked.connect(self.remove_picture)
        hint = QLabel("No picture? Your emoji is your avatar.")
        hint.setObjectName("small")
        picture_column.addWidget(self.picture_button)
        picture_column.addWidget(self.remove_button)
        picture_column.addWidget(hint)
        picture_row.addWidget(self.preview)
        picture_row.addLayout(picture_column)
        signup_layout.addLayout(picture_row)
        layout.addWidget(self.signup_fields)

        # server address (hidden until needed)
        server_link = QPushButton("⚙  Server settings")
        server_link.setObjectName("link")
        server_link.setAutoDefault(False)
        server_link.clicked.connect(self.toggle_server_box)
        layout.addWidget(server_link)

        self.server_box = QWidget()
        server_layout = QHBoxLayout(self.server_box)
        server_layout.setContentsMargins(0, 0, 0, 0)
        self.host = QLineEdit(config.HOST)
        self.port = QLineEdit(str(config.PORT))
        self.port.setFixedWidth(90)
        server_layout.addWidget(self.host)
        server_layout.addWidget(self.port)
        self.server_box.hide()
        layout.addWidget(self.server_box)

        layout.addStretch()
        self.error = QLabel("")
        self.error.setObjectName("error")
        self.error.setWordWrap(True)
        self.error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.error)

        self.submit_button = QPushButton("Log In")
        self.submit_button.setObjectName("primary")
        self.submit_button.setDefault(True)             # Enter key submits
        self.submit_button.clicked.connect(self.submit)
        layout.addWidget(self.submit_button)

        self.update_mode()
        self.username.setFocus()

    # ------------------------------------------------------------ the form
    def is_signup(self):
        return self.signup_tab.isChecked()

    def update_mode(self):
        """Show or hide the Sign Up fields."""
        signup = self.is_signup()
        self.signup_fields.setVisible(signup)
        self.submit_button.setText("Create Account" if signup else "Log In")
        self.error.setText("")
        self.update_preview()

    def show_password(self, visible):
        mode = QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        self.password.setEchoMode(mode)
        self.confirm.setEchoMode(mode)

    def toggle_server_box(self):
        self.server_box.setVisible(not self.server_box.isVisible())

    def chosen_avatar(self):
        return self.avatar_buttons.checkedButton().text()

    def update_preview(self):
        picture = text_to_pixmap(self.picture)
        self.preview.setPixmap(make_avatar(self.chosen_avatar(), picture, 62, styles.GREEN))
        self.remove_button.setVisible(self.picture is not None)

    def choose_picture(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose a profile picture", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if path == "":
            return
        text = picture_file_to_text(path)
        if text is None:
            self.error.setText("That image could not be used. Try a PNG or JPG file.")
            return
        self.error.setText("")
        self.picture = text
        self.update_preview()

    def remove_picture(self):
        self.picture = None
        self.update_preview()

    # ------------------------------------------------------------- submit
    def submit(self):
        username = self.username.text().strip()
        password = self.password.text()

        # check the form before talking to the server
        if not re.fullmatch(r"[A-Za-z0-9_]{2,20}", username):
            self.error.setText("Username must be 2-20 letters, numbers or _.")
            return
        if password == "":
            self.error.setText("Please enter your password.")
            return
        if self.is_signup():
            if len(password) < config.MIN_PASSWORD_LENGTH:
                self.error.setText(
                    f"Password must be at least {config.MIN_PASSWORD_LENGTH} characters.")
                return
            if password != self.confirm.text():
                self.error.setText("The two passwords do not match.")
                return
        try:
            port = int(self.port.text())
        except ValueError:
            self.error.setText("Port must be a number.")
            self.server_box.show()
            return

        self.error.setText("")
        self.submit_button.setEnabled(False)
        self.submit_button.setText("Connecting...")
        QApplication.processEvents()

        mode = "register" if self.is_signup() else "login"
        connection = ServerConnection()
        try:
            session = connection.connect_and_login(
                self.host.text().strip(), port, mode, username, password,
                self.chosen_avatar(), self.picture)
        except LoginError as e:
            self.error.setText(str(e))
        except ConnectionError:
            self.error.setText("Could not connect to the server.\n"
                               "Make sure server.py is running.")
            self.server_box.show()
        else:
            self.connection = connection
            self.session = session
            self.accept()
            return

        self.submit_button.setEnabled(True)
        self.submit_button.setText("Create Account" if self.is_signup() else "Log In")
