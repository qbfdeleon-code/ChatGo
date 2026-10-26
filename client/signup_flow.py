from PyQt6.QtWidgets import QMessageBox


def show_signup_success(parent=None) -> None:
    QMessageBox.information(
        parent,
        "Registration Successful",
        "Your account has been created successfully!\n\n"
        "Please log in with your new credentials."
    )

