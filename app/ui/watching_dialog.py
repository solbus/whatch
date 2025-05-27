from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
    QWidget,
)
from PyQt6.QtCore import Qt


class WatchingDialog(QDialog):
    """Dialog to collect series or film information."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Series")
        self.result_data = None
        self.init_ui()

    def init_ui(self):
        form = QFormLayout(self)

        self.title_field = QLineEdit()
        form.addRow("Title:", self.title_field)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["TV", "Film"])
        form.addRow("Type:", self.type_combo)

        # TV widgets
        self.tv_widget = QWidget()
        tv_form = QFormLayout(self.tv_widget)
        self.seasons_field = QLineEdit()
        tv_form.addRow("Seasons:", self.seasons_field)
        self.episodes_field = QLineEdit()
        tv_form.addRow("Episodes/season:", self.episodes_field)
        self.length_field = QLineEdit()
        tv_form.addRow("Avg length:", self.length_field)
        self.last_episode_field = QLineEdit()
        tv_form.addRow("Last watched ep:", self.last_episode_field)
        form.addRow(self.tv_widget)

        # Film widgets
        self.film_widget = QWidget()
        film_form = QFormLayout(self.film_widget)
        self.film_count_field = QLineEdit()
        film_form.addRow("Films:", self.film_count_field)
        self.film_titles_field = QLineEdit()
        film_form.addRow("Titles:", self.film_titles_field)
        self.film_lengths_field = QLineEdit()
        film_form.addRow("Lengths:", self.film_lengths_field)
        self.last_film_idx_field = QLineEdit()
        film_form.addRow("Last index:", self.last_film_idx_field)
        form.addRow(self.film_widget)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.validate_and_accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        form.addRow(button_layout)

        self.type_combo.currentTextChanged.connect(self.update_view)
        self.update_view()

    def update_view(self):
        if self.type_combo.currentText() == "TV":
            self.tv_widget.show()
            self.film_widget.hide()
        else:
            self.tv_widget.hide()
            self.film_widget.show()

    def _warn(self, message: str):
        QMessageBox.warning(self, "Input Error", message)

    def validate_and_accept(self):
        title = self.title_field.text().strip()
        if not title:
            self._warn("Title cannot be empty.")
            return

        if self.type_combo.currentText() == "TV":
            try:
                seasons = int(self.seasons_field.text())
                episodes = [int(e.strip()) for e in self.episodes_field.text().split(',') if e.strip()]
                if len(episodes) != seasons:
                    raise ValueError
                avg_len = int(self.length_field.text())
                last_ep = self.last_episode_field.text().strip()
                if not last_ep:
                    raise ValueError
            except ValueError:
                self._warn("Invalid TV data.")
                return
            self.result_data = {
                "title": title,
                "type": "TV",
                "seasons": seasons,
                "episodes_per_season": episodes,
                "average_length": avg_len,
                "last_watched_episode": last_ep,
            }
        else:
            try:
                count = int(self.film_count_field.text())
                titles = [t.strip() for t in self.film_titles_field.text().split(',') if t.strip()]
                lengths = [int(l.strip()) for l in self.film_lengths_field.text().split(',') if l.strip()]
                if len(titles) != count or len(lengths) != count:
                    raise ValueError
                last_idx = int(self.last_film_idx_field.text())
                if not 1 <= last_idx <= count:
                    raise ValueError
            except ValueError:
                self._warn("Invalid film data.")
                return
            self.result_data = {
                "title": title,
                "type": "Film",
                "film_count": count,
                "film_titles": titles,
                "film_lengths": lengths,
                "last_watched_index": last_idx,
            }
        self.accept()
