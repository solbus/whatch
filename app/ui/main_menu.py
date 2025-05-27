from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt


class MainMenu(QWidget):
    """Minimal main menu with a single button to open the People menu."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.people_button = QPushButton("\U0001F464")  # Unicode bust in silhouette
        self.people_button.setFixedSize(40, 40)
        self.people_button.setStyleSheet(
            "font-size: 18px; border: none; background: transparent;"
        )
        self.people_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.people_button.clicked.connect(self.open_people_menu)
        layout.addWidget(
            self.people_button,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
        )

        self.watching_button = QPushButton("\U0001F4F9")  # Unicode video camera
        self.watching_button.setFixedSize(40, 40)
        self.watching_button.setStyleSheet(
            "font-size: 18px; border: none; background: transparent;"
        )
        self.watching_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.watching_button.clicked.connect(self.open_currently_watching_menu)
        layout.addWidget(
            self.watching_button,
            alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
        )

    def open_people_menu(self):
        main_window = self.window()

        def back_to_main_menu():
            main_window.setCentralWidget(MainMenu(parent=main_window))

        from app.ui.people_menu import PeopleMenu

        people_menu = PeopleMenu(back_callback=back_to_main_menu, parent=main_window)
        main_window.setCentralWidget(people_menu)

    def open_currently_watching_menu(self):
        main_window = self.window()

        def back_to_main_menu():
            main_window.setCentralWidget(MainMenu(parent=main_window))

        from app.ui.currently_watching_menu import CurrentlyWatchingMenu

        menu = CurrentlyWatchingMenu(items=[], back_callback=back_to_main_menu, parent=main_window)
        main_window.setCentralWidget(menu)

