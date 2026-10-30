from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QPlainTextEdit

app = QApplication()

window = QMainWindow()
window.resize(500, 400)
window.move(300, 310)
window.setWindowTitle('Salary Statistics')

textEdit = QPlainTextEdit(window)
textEdit.setPlaceholderText("Please enter the salary data")
textEdit.move(10, 25)
textEdit.resize(300, 350)

button = QPushButton('Calculate', window)
button.move(380, 80)

window.show()

app.exec()  # PySide6 uses exec instead of exec_