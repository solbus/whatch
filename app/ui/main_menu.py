from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt


class MainMenu(QWidget):
"""Minimal main menu with buttons to open other menus."""

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

        self.watch_button = QPushButton("\U0001F4FA")  # Television icon
        self.watch_button.setFixedSize(40, 40)
        self.watch_button.setStyleSheet(
            "font-size: 18px; border: none; background: transparent;"
        )
        self.watch_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.watch_button.clicked.connect(self.open_currently_watching_menu)
        layout.addWidget(
            self.watch_button,
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

        watching_menu = CurrentlyWatchingMenu(back_callback=back_to_main_menu, parent=main_window)
        main_window.setCentralWidget(watching_menu)

