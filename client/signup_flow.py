<<<<<<< HEAD
from PyQt6.QtWidgets import QMessageBox, QPushButton


def show_signup_success(parent=None):
    message = QMessageBox(parent)

    message.setWindowTitle("Registration Successful")
    message.setIcon(QMessageBox.Icon.Information)

    message.setText("Account Created Successfully!")
    message.setInformativeText(
        "Your ChatGo account has been created successfully.\n\n"
        "You can now log in using your new username and password."
    )

    message.setStandardButtons(QMessageBox.StandardButton.Ok)

    message.setStyleSheet("""
        QMessageBox {
            background-color: #070B09;
        }

        QMessageBox QLabel {
            color: #FFFFFF;
            font-size: 13px;
        }

        QPushButton {
            background-color: #22C55E;
            color: #04120A;
            border: none;
            border-radius: 8px;
            padding: 8px 25px;
            font-weight: bold;
        }

        QPushButton:hover {
            background-color: #4ADE80;
        }
    """)

    message.exec()
=======
from PyQt6.QtWidgets import QMessageBox


def show_signup_success(parent=None) -> None:
    QMessageBox.information(
        parent,
        "Registration Successful",
        "Your account has been created successfully!\n\n"
        "Please log in with your new credentials."
    )

>>>>>>> origin/main
