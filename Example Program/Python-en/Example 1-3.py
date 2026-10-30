from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QPlainTextEdit, QMessageBox

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

        self.button.clicked.connect(self.handleCalc)

    def handleCalc(self):
        info = self.textEdit.toPlainText()

        # Lists of employees with salaries at or above 20,000 and below 20,000
        salary_above_20k = ''
        salary_below_20k = ''
        for line in info.splitlines():
            if not line.strip():
                continue
            parts = line.split(' ')
            # Remove empty strings from the list
            parts = [p for p in parts if p]
            name, salary, age = parts
            if int(salary) >= 20000:
                salary_above_20k += name + '\n'
            else:
                salary_below_20k += name + '\n'

        QMessageBox.about(self.window,
                    'Calculation Results',
                    f'''Employees with salaries of 20,000 or more:\n{salary_above_20k}
                    \nEmployees with salaries below 20,000:\n{salary_below_20k}'''
                    )

app = QApplication()
stats = Stats()
stats.window.show()
app.exec()