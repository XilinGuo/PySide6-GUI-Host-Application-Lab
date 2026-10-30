from PySide6.QtWidgets import QApplication
from PySide6.QtUiTools import QUiLoader

class SerialController:
 
    def __init__(self):
        # 从文件中加载UI定义
 
        # 从 UI 定义中动态 创建一个相应的窗口对象
        # 注意：里面的控件对象也成为窗口对象的属性了
        # 比如 self.ui.button
        self.ui = QUiLoader().load('main_window.ui')
 
 
app = QApplication()
serial_controller = SerialController()
serial_controller.ui.show()
app.exec()