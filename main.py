import sys

from PyQt5.QtWidgets import QApplication

from application import App
from store.state import State

if __name__ == "__main__":
    app = QApplication(sys.argv)
    State.load_settings()
    ex = App()
    sys.exit(app.exec())
