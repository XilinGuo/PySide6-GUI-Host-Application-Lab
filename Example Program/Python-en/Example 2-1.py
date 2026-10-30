from PySide6.QtWidgets import QApplication
from PySide6.QtUiTools import QUiLoader

class SerialController:

    def __init__(self):
        # Load the UI definition from a file

        # Dynamically create a corresponding window object from the UI definition
        # Note: the widget objects also become attributes of the window object
        # For example: self.ui.button
        self.ui = QUiLoader().load('main_window.ui')


app = QApplication()
serial_controller = SerialController()
serial_controller.ui.show()
app.exec()