from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QLineEdit, QDialog, QFormLayout, QMessageBox
)
from PyQt6.QtCore import Qt
from app.core.people_db import PeopleDB

class WatchingMenu(QWidget):
    def __init__(self, back_callback, parent=None):
        super().__init__(parent)
        self.back_callback = back_callback
        self.db = PeopleDB()
        self.init_ui()
        self.load_series()

    def init_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel("Watching")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["ID", "Series", "Progress"])
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(self.table.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        buttons = QHBoxLayout()
        self.add_button = QPushButton("Add Series")
        self.add_button.clicked.connect(self.add_series)
        buttons.addWidget(self.add_button)

        self.edit_button = QPushButton("Edit Progress")
        self.edit_button.clicked.connect(self.edit_progress)
        buttons.addWidget(self.edit_button)

        self.delete_button = QPushButton("Delete Series")
        self.delete_button.clicked.connect(self.delete_series)
        buttons.addWidget(self.delete_button)

        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self.go_back)
        buttons.addWidget(self.back_button)

        layout.addLayout(buttons)

    def load_series(self):
        shows = self.db.get_watching()
        self.table.setRowCount(0)
        for show in shows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(show[0])))
            self.table.setItem(row, 1, QTableWidgetItem(show[1]))
            self.table.setItem(row, 2, QTableWidgetItem(str(show[2])))
        self.table.resizeColumnsToContents()

    def add_series(self):
        dialog = SeriesDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            title = dialog.title_field.text().strip()
            if title:
                self.db.add_series(title)
                self.load_series()
            else:
                QMessageBox.warning(self, "Input Error", "Title cannot be empty.")

    def edit_progress(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Selection Error", "Please select a series to edit.")
            return
        row = self.table.currentRow()
        series_id = int(self.table.item(row, 0).text())
        current_title = self.table.item(row, 1).text()
        current_progress = self.table.item(row, 2).text()
        dialog = SeriesDialog(current_title, current_progress)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            progress_text = dialog.progress_field.text().strip()
            try:
                progress_val = int(progress_text)
            except ValueError:
                QMessageBox.warning(self, "Input Error", "Progress must be a number.")
                return
            self.db.update_progress(series_id, progress_val)
            self.load_series()

    def delete_series(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Selection Error", "Please select a series to delete.")
            return
        row = self.table.currentRow()
        series_id = int(self.table.item(row, 0).text())
        reply = QMessageBox.question(
            self,
            "Delete Series",
            f"Are you sure you want to delete the series with ID {series_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_series(series_id)
            self.load_series()

    def go_back(self):
        self.db.close()
        self.back_callback()

class SeriesDialog(QDialog):
    def __init__(self, title="", progress="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Series Details")
        self.setModal(True)
        self.title_field = QLineEdit(title)
        self.progress_field = QLineEdit(progress)
        form = QFormLayout(self)
        form.addRow("Series:", self.title_field)
        form.addRow("Progress:", self.progress_field)

        buttons = QHBoxLayout()
        ok = QPushButton("OK")
        ok.clicked.connect(self.accept)
        buttons.addWidget(ok)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(cancel)
        form.addRow(buttons)

