from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QHBoxLayout,
    QLineEdit,
    QDialog,
    QFormLayout,
    QMessageBox,
    QInputDialog,
)
from PyQt6.QtCore import Qt
from app.core.watching_db import WatchingDB


class WatchingItemDialog(QDialog):
    """Dialog for adding a new item to the watching list."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Item")
        self.title_field = QLineEdit()
        self.type_field = QLineEdit()
        self.progress_field = QLineEdit("0")

        form = QFormLayout(self)
        form.addRow("Title:", self.title_field)
        form.addRow("Type:", self.type_field)
        form.addRow("Progress:", self.progress_field)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        form.addRow(button_layout)


class CurrentlyWatchingMenu(QWidget):
    def __init__(self, back_callback, parent=None):
        super().__init__(parent)
        self.back_callback = back_callback
        self.db = WatchingDB()
        self.init_ui()
        self.load_items()

    def init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Currently Watching")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Title", "Type", "Progress"])
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(self.table.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add New")
        self.add_button.clicked.connect(self.add_item)
        button_layout.addWidget(self.add_button)

        self.update_button = QPushButton("Update Progress")
        self.update_button.clicked.connect(self.update_progress)
        button_layout.addWidget(self.update_button)

        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self.go_back)
        button_layout.addWidget(self.back_button)

        layout.addLayout(button_layout)

    def load_items(self):
        items = self.db.get_items()
        self.table.setRowCount(0)
        for item in items:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(item[0])))
            self.table.setItem(row, 1, QTableWidgetItem(item[1]))
            self.table.setItem(row, 2, QTableWidgetItem(item[2]))
            self.table.setItem(row, 3, QTableWidgetItem(item[3]))
        self.table.resizeColumnsToContents()

    def add_item(self):
        dialog = WatchingItemDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            title = dialog.title_field.text().strip()
            type_ = dialog.type_field.text().strip()
            progress = dialog.progress_field.text().strip()
            if not title or not type_:
                QMessageBox.warning(self, "Input Error", "Title and Type cannot be empty.")
                return
            self.db.add_item(title, type_, progress)
            self.load_items()

    def update_progress(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Selection Error", "Please select an item to update.")
            return
        row = self.table.currentRow()
        item_id = int(self.table.item(row, 0).text())
        current_progress = self.table.item(row, 3).text()
        progress, ok = QInputDialog.getText(self, "Update Progress", "Progress:", text=current_progress)
        if ok:
            self.db.update_progress(item_id, progress)
            self.load_items()

    def go_back(self):
        self.db.close()
        self.back_callback()
