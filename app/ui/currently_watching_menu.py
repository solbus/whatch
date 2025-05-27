from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
)
from PyQt6.QtCore import Qt


class CurrentlyWatchingMenu(QWidget):
    """Simple menu showing what is currently being watched."""

    def __init__(self, back_callback, parent=None):
        super().__init__(parent)
        self.back_callback = back_callback
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Currently Watching")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        button_layout = QHBoxLayout()
        back_button = QPushButton("Back")
        back_button.clicked.connect(self.back_callback)
        button_layout.addWidget(back_button)
        layout.addLayout(button_layout)
