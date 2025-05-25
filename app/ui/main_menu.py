from PyQt6.QtWidgets import (
    QWidget, QGridLayout, QMessageBox, QSizePolicy,
    QStyleOptionButton, QStyle, QPushButton
)
from PyQt6.QtGui import QPainter, QPen
from PyQt6.QtCore import Qt

class MainMenu(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Set up a 2x2 grid layout.
        grid_layout = QGridLayout()
        self.setLayout(grid_layout)
        grid_layout.setSpacing(10)
        grid_layout.setContentsMargins(10, 10, 10, 10)
        grid_layout.setRowStretch(0, 1)
        grid_layout.setRowStretch(1, 1)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)

        # Define tile names and their grid positions.
        tiles = {
            "Pick": (0, 0),
            "Suggestions": (0, 1),
            "List": (1, 0),
            "People": (1, 1)
        }

        # Base colors and hover colors.
        base_colors = {
            "Pick": "#3498db",         # Bright blue
            "Suggestions": "#2ecc71",  # Bright green
            "List": "#e67e22",         # Bright orange
            "People": "#9b59b6"        # Bright purple
        }
        hover_colors = {
            "Pick": "#5dade2",         # Lighter blue
            "Suggestions": "#58d68d",  # Lighter green
            "List": "#eb984e",         # Lighter orange
            "People": "#af7ac5"        # Lighter purple
        }

        # Create each tile as an OutlineButton.
        for tile_name, position in tiles.items():
            btn = OutlineButton(tile_name)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            # Style the button with background, rounded corners, and hover effect.
            style = f"""
            QPushButton {{
                background-color: {base_colors[tile_name]};
                border: none;
                border-radius: 5px;
            }}
            QPushButton:hover {{
                background-color: {hover_colors[tile_name]};
            }}
            """
            btn.setStyleSheet(style)
            if tile_name == "People":
                btn.clicked.connect(self.open_people_menu)
            else:
                btn.clicked.connect(lambda checked, name=tile_name: self.show_placeholder(name))
            grid_layout.addWidget(btn, position[0], position[1])

    def show_placeholder(self, tile_name: str):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Placeholder")
        msg_box.setText(f"You clicked on '{tile_name}'. This view is not yet implemented.")
        msg_box.exec()

    def open_people_menu(self):
        # Get the main window (using self.window() is safer than self.parent())
        main_window = self.window()
        from app.ui.people_menu import PeopleMenu
        people_menu = PeopleMenu(back_callback=self.back_to_main_menu, parent=main_window)
        main_window.setCentralWidget(people_menu)

    def back_to_main_menu(self):
        main_window = self.window()
        # Recreate the MainMenu. (If you need to preserve state, consider alternatives such as QStackedWidget.)
        from app.ui.main_menu import MainMenu
        main_menu = MainMenu(parent=main_window)
        main_window.setCentralWidget(main_menu)

class OutlineButton(QPushButton):
    """
    A custom QPushButton that draws its text with a black outline.
    """
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        font = self.font()
        font.setPointSize(26)
        font.setBold(True)
        self.setFont(font)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Prepare style option and draw the button background (without text)
        option = QStyleOptionButton()
        self.initStyleOption(option)
        text = option.text
        option.text = ""
        self.style().drawControl(QStyle.ControlElement.CE_PushButton, option, painter, self)
        
        # Draw text with a black outline
        rect = self.rect()
        painter.setFont(self.font())
        pen = QPen(Qt.GlobalColor.black)
        painter.setPen(pen)
        offsets = [(-2, -2), (-2, 0), (-2, 2),
                   (0, -2),           (0, 2),
                   (2, -2),  (2, 0),  (2, 2)]
        for dx, dy in offsets:
            painter.drawText(rect.adjusted(dx, dy, dx, dy), Qt.AlignmentFlag.AlignCenter, text)
        
        # Draw the main white text on top
        painter.setPen(Qt.GlobalColor.white)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)