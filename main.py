import sys
from PySide6.QtWidgets import QApplication
from main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Terminal Board")
    app.setOrganizationName("Terminal Board")

    window = MainWindow()
    window.resize(860, 600)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
