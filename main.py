import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from app.ui.main_menu import MainMenu

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Whatch")
        self.setMinimumSize(555, 444)
        self.main_menu = MainMenu(self)
        self.setCentralWidget(self.main_menu)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
