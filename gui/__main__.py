from PyQt5.QtWidgets import QApplication

from .gui import MainWidget

app = QApplication([])
w = MainWidget()
app.exec()
