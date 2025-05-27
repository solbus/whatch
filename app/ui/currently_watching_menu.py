from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt
from app.core.watching_db import WatchingDB


class CurrentlyWatchingMenu(QWidget):
    def __init__(self, back_callback, parent=None):
        super().__init__(parent)
        self.back_callback = back_callback
        self.db = WatchingDB()
        self.init_ui()
        self.load_series()

    def init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Currently Watching")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["ID", "Title", "Last Watched"])
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(self.table.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        button_layout = QHBoxLayout()
        self.update_button = QPushButton("Update Progress")
        self.update_button.clicked.connect(self.update_progress)
        button_layout.addWidget(self.update_button)

        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self.go_back)
        button_layout.addWidget(self.back_button)

        layout.addLayout(button_layout)

    def load_series(self):
        series = self.db.get_all()
        self.table.setRowCount(0)
        for row in series:
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            id_item = QTableWidgetItem(str(row[0]))
            title_item = QTableWidgetItem(row[1])
            last_item = QTableWidgetItem(str(row[2]))
            self.table.setItem(row_position, 0, id_item)
            self.table.setItem(row_position, 1, title_item)
            self.table.setItem(row_position, 2, last_item)
        self.table.resizeColumnsToContents()

    def update_progress(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "Selection Error", "Please select a series to update.")
            return
        row = self.table.currentRow()
        series_id = int(self.table.item(row, 0).text())
        current_val = int(self.table.item(row, 2).text())
        new_val, ok = QInputDialog.getInt(self, "Update Progress", "Last watched index:", value=current_val, min=0)
        if ok:
            self.db.update_last_watched(series_id, new_val)
            self.load_series()

    def go_back(self):
        self.db.close()
        self.back_callback()
