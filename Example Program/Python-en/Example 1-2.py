from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QPlainTextEdit

class Stats:
    def __init__(self):
        self.window = QMainWindow()
        self.window.resize(500, 400)
        self.window.move(300, 300)
        self.window.setWindowTitle('Salary Statistics')

        self.textEdit = QPlainTextEdit(self.window)
        self.textEdit.setPlaceholderText("Please enter the salary data")
        self.textEdit.move(10, 25)
        self.textEdit.resize(300, 350)

        self.button = QPushButton('Calculate', self.window)
        self.button.move(380, 80)

app = QApplication()
stats = Stats()
stats.window.show()
app.exec()