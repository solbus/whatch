from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QProgressBar
)
from PyQt6.QtCore import Qt

class CurrentlyWatchingMenu(QWidget):
    """Display a list of items the user is currently watching with progress."""

    def __init__(self, items=None, back_callback=None, parent=None):
        super().__init__(parent)
        self.items = items or []
        self.back_callback = back_callback
        self.init_ui()
        self.load_items()

    def init_ui(self):
        layout = QVBoxLayout(self)
        title = QLabel("Currently Watching")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Title", "Progress"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(self.table.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(self.table.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        button_layout = QHBoxLayout()
        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(self.go_back)
        button_layout.addStretch()
        button_layout.addWidget(self.back_button)
        layout.addLayout(button_layout)

    def compute_percentage(self, details, last_watched):
        """Return progress percentage based on item details and last watched."""
        if not details or not last_watched:
            return 0
        try:
            if "runtime" in details and "position" in last_watched:
                runtime = float(details.get("runtime", 0))
                position = float(last_watched.get("position", 0))
                if runtime > 0:
                    return max(0, min(100, int(position / runtime * 100)))
            if "total_episodes" in details and "episode" in last_watched:
                total = int(details.get("total_episodes", 0))
                episode = int(last_watched.get("episode", 0))
                if total > 0:
                    return max(0, min(100, int(episode / total * 100)))
        except Exception:
            pass
        return 0

    def load_items(self):
        self.table.setRowCount(0)
        for item in self.items:
            row = self.table.rowCount()
            self.table.insertRow(row)
            title_item = QTableWidgetItem(item.get("title", ""))
            self.table.setItem(row, 0, title_item)

            progress_bar = QProgressBar()
            pct = self.compute_percentage(item.get("details"), item.get("last_watched"))
            progress_bar.setValue(pct)
            progress_bar.setFormat(f"{pct}%")
            # Placeholder for future color-coding per season or film segment
            self.table.setCellWidget(row, 1, progress_bar)

    def go_back(self):
        if self.back_callback:
            self.back_callback()
