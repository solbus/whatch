import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QSettings
from app.ui.main_menu import MainMenu

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Whatch")
        self.setMinimumSize(555, 444)
        self._settings = QSettings("Whatch", "Whatch")
        geometry = self._settings.value("main_window/geometry")
        if geometry:
            self.restoreGeometry(geometry)
        self.main_menu = MainMenu(self)
        self.setCentralWidget(self.main_menu)

    def closeEvent(self, event):
        self._settings.setValue("main_window/geometry", self.saveGeometry())
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
