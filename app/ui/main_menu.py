from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontMetrics


class MainMenu(QWidget):
    """Minimal main menu with a single button to open the People menu."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

        labels = ["Watching", "List", "Library", "People"]
        menu_font = QFont(self.font())
        menu_font.setPixelSize(18)
        metrics = QFontMetrics(menu_font)
        button_width = max(metrics.horizontalAdvance(label) for label in labels) + 12

        self.watching_button = self._build_menu_button(
            "Watching", button_width, menu_font, self.open_watching_menu
        )
        layout.addWidget(self.watching_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.list_button = self._build_menu_button("List", button_width, menu_font, self.open_list_menu)
        layout.addWidget(self.list_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.library_button = self._build_menu_button(
            "Library", button_width, menu_font, self.open_library_menu
        )
        layout.addWidget(self.library_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.people_button = self._build_menu_button(
            "People", button_width, menu_font, self.open_people_menu
        )
        layout.addWidget(self.people_button, alignment=Qt.AlignmentFlag.AlignHCenter)

    def _build_menu_button(self, text, width, font, on_click):
        button = QPushButton(text)
        button.setFixedSize(width, 40)
        button.setFont(font)
        button.setStyleSheet(
            "border: none; background: transparent; text-align: left; padding-left: 0px;"
        )
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(on_click)
        return button

    def open_people_menu(self):
        main_window = self.window()

        def back_to_main_menu():
            main_window.setCentralWidget(MainMenu(parent=main_window))

        from app.ui.people_menu import PeopleMenu

        people_menu = PeopleMenu(back_callback=back_to_main_menu, parent=main_window)
        main_window.setCentralWidget(people_menu)

    def open_watching_menu(self):
        main_window = self.window()

        def back_to_main_menu():
            main_window.setCentralWidget(MainMenu(parent=main_window))

        from app.ui.currently_watching_menu import CurrentlyWatchingMenu

        watching_menu = CurrentlyWatchingMenu(
            back_callback=back_to_main_menu, parent=main_window
        )
        main_window.setCentralWidget(watching_menu)

    def open_library_menu(self):
        main_window = self.window()

        def back_to_main_menu():
            main_window.setCentralWidget(MainMenu(parent=main_window))

        from app.ui.library_menu import LibraryMenu

        library_menu = LibraryMenu(back_callback=back_to_main_menu, parent=main_window)
        main_window.setCentralWidget(library_menu)

    def open_list_menu(self):
        main_window = self.window()

        def back_to_main_menu():
            main_window.setCentralWidget(MainMenu(parent=main_window))

        from app.ui.list_menu import ListMenu

        list_menu = ListMenu(back_callback=back_to_main_menu, parent=main_window)
        main_window.setCentralWidget(list_menu)

