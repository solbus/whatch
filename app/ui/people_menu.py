from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QLineEdit, QDialog, QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt
from app.core.people_db import PeopleDB

class PeopleMenu(QWidget):
    def __init__(self, back_callback, parent=None):
        """
        :param back_callback: a callable to invoke when the user clicks “Back”
        """
        super().__init__(parent)
        self.back_callback = back_callback
        self.db = PeopleDB()
        self.init_ui()
        self.load_people()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Title
        title = QLabel("People")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        # Table to display users
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["ID", "Name"])
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(self.table.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        # Buttons: Add, Edit, Delete, Back
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add User")
        self.add_button.clicked.connect(self.add_user)
        button_layout.addWidget(self.add_button)

        self.edit_button = QPushButton("Edit User")
        self.edit_button.clicked.connect(self.edit_user)
        button_layout.addWidget(self.edit_button)

        self.delete_button = QPushButton("Delete User")
        self.delete_button.clicked.connect(self.delete_user)
        button_layout.addWidget(self.delete_button)

        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self.go_back)
        button_layout.addWidget(self.back_button)

        layout.addLayout(button_layout)

    def load_people(self):
        """Fetch people from the database and load them into the table."""
        people = self.db.get_people()
        self.table.setRowCount(0)
        for person in people:
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            id_item = QTableWidgetItem(str(person[0]))
            name_item = QTableWidgetItem(person[1])
            self.table.setItem(row_position, 0, id_item)
            self.table.setItem(row_position, 1, name_item)
        self.table.resizeColumnsToContents()

    def add_user(self):
        dialog = UserDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = dialog.name_field.text().strip()
            if name:
                self.db.add_person(name)
                self.load_people()
            else:
                QMessageBox.warning(self, "Input Error", "Name cannot be empty.")

    def edit_user(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Selection Error", "Please select a user to edit.")
            return

        row = self.table.currentRow()
        user_id = int(self.table.item(row, 0).text())
        current_name = self.table.item(row, 1).text()
        dialog = UserDialog(current_name)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_name = dialog.name_field.text().strip()
            if new_name:
                self.db.update_person(user_id, new_name)
                self.load_people()
            else:
                QMessageBox.warning(self, "Input Error", "Name cannot be empty.")

    def delete_user(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Selection Error", "Please select a user to delete.")
            return

        row = self.table.currentRow()
        user_id = int(self.table.item(row, 0).text())
        reply = QMessageBox.question(
            self,
            "Delete User",
            f"Are you sure you want to delete the user with ID {user_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_person(user_id)
            self.load_people()

    def go_back(self):
        self.db.close()  # Optional cleanup
        self.back_callback()

class UserDialog(QDialog):
    """A simple dialog to input a user’s name."""
    def __init__(self, name="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("User Details")
        self.setModal(True)
        self.name_field = QLineEdit(name)
        form_layout = QFormLayout(self)
        form_layout.addRow("Name:", self.name_field)

        # OK and Cancel buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        form_layout.addRow(button_layout)
