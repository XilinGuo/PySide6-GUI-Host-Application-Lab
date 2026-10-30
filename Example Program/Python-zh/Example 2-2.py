from PySide6.QtWidgets import QApplication
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import  QIODevice
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo

# 状态字符 -> (显示文字, 状态标签背景色)
STATE_MAP = {
    "R": ("红色", "rgb(220, 80, 80)"),
    "G": ("绿色", "rgb(80, 180, 80)"),
    "B": ("蓝色", "rgb(80, 120, 220)"),
    "C": ("已关闭", "rgb(180, 180, 180)"),
}

BAUD_RATES = ["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"]

class SerialController():
 
    def __init__(self):
        # 从文件中加载UI定义
        self.ui = QUiLoader().load('main_window.ui')

        self.serial = QSerialPort()
        self._init_ui()
        self._init_serial()
        self.refresh_ports()

    def _init_ui(self):
        # 波特率下拉框填充
        self.ui.comboBoxBaud.addItems(BAUD_RATES)
        self.ui.comboBoxBaud.setCurrentText("115200")

        # 按钮信号连接到发送槽函数
        self.ui.pushButtonConnect.clicked.connect(self.connect_serial)
        self.ui.pushButtonDisconnect.clicked.connect(self.disconnect_serial)
        self.ui.pushButtonR.clicked.connect(lambda: self.send_command("R"))
        self.ui.pushButtonG.clicked.connect(lambda: self.send_command("G"))
        self.ui.pushButtonB.clicked.connect(lambda: self.send_command("B"))
        self.ui.pushButtonC.clicked.connect(lambda: self.send_command("C"))
        self.ui.pushButtonRefresh.clicked.connect(lambda: self.send_command("T"))

        self._set_connected_ui(False)
        self.log("程序启动, 请连接串口")

    # ---------- 串口逻辑 ----------
    def _init_serial(self):
        self.serial.readyRead.connect(self.on_ready_read) # 当串口有数据可读时（信号）连接到 self.on_ready_read（槽函数）
        self.serial.errorOccurred.connect(self.on_serial_error) # 当串口错误时（信号）连接到 self.on_serial_error（槽函数）

    def refresh_ports(self):
        self.ui.comboBoxPort.clear()
        ports = QSerialPortInfo.availablePorts()
        for info in ports:
            # 显示: 端口名 (描述), 实际使用 portName()
            self.ui.comboBoxPort.addItem(f"{info.portName()} ({info.description()})", info.portName())
        if not ports:
            self.ui.comboBoxPort.addItem("未检测到串口", "")
            self.log("未检测到可用串口")
        else:
            self.log(f"检测到 {len(ports)} 个串口")

    def connect_serial(self):
        port_name = self.ui.comboBoxPort.currentData()
        if not port_name:
            self.log("错误: 没有可用串口")
            return
        baud = int(self.ui.comboBoxBaud.currentText())

        self.serial.setPortName(port_name)
        self.serial.setBaudRate(baud)
        self.serial.setDataBits(QSerialPort.Data8)
        self.serial.setParity(QSerialPort.NoParity)
        self.serial.setStopBits(QSerialPort.OneStop)
        self.serial.setFlowControl(QSerialPort.NoFlowControl)

        if self.serial.open(QIODevice.ReadWrite):
            self._set_connected_ui(True)
            self.log(f"已连接 {port_name} @ {baud}")
        else:
            self.log(f"连接失败: {self.serial.errorString()}")

    def disconnect_serial(self):
        if self.serial.isOpen():
            self.serial.close()
        self._set_connected_ui(False)
        self.log("已断开连接")

    def send_command(self, ch):
        if not self.serial.isOpen():
            self.log("错误: 串口未连接")
            return
        data = ch.encode("ascii")
        written = self.serial.write(data)
        self.serial.flush()
        self.log(f"发送: {ch} ({written} 字节)")

    # ---------- 接收处理 ----------
    def on_ready_read(self):
        data = self.serial.readAll().data()
        try:
            text = data.decode("ascii", errors="ignore")
        except Exception:
            return
        for ch in text:
            if ch in STATE_MAP:
                self.update_status(ch)
                self.log(f"收到: {ch} -> 状态更新为 {STATE_MAP[ch][0]}")
            elif ch in ("\n", "\r"):
                continue
            else:
                self.log(f"收到未知字符: {ch!r}")

    def on_serial_error(self, error):
        if error == QSerialPort.NoError:
            return
        self.log(f"串口错误: {self.serial.errorString()}")
        if not self.serial.isOpen():
            self._set_connected_ui(False)

    # ---------- 界面辅助 ----------
    def update_status(self, ch):
        name, color = STATE_MAP[ch]
        self.ui.labelStatus.setText(f"当前状态: {name}")
        self.ui.labelStatus.setStyleSheet(
            f"background-color: {color}; color: white; "
            "border: 1px solid gray; font: bold 18pt;"
        )

    def _set_connected_ui(self, connected):
        self.ui.pushButtonConnect.setEnabled(not connected)
        self.ui.pushButtonDisconnect.setEnabled(connected)
        self.ui.comboBoxPort.setEnabled(not connected)
        self.ui.comboBoxBaud.setEnabled(not connected)
        for btn in (self.ui.pushButtonR, self.ui.pushButtonG,
                    self.ui.pushButtonB, self.ui.pushButtonC,
                    self.ui.pushButtonRefresh):
            btn.setEnabled(connected)
        self.ui.statusbar.showMessage("已连接" if connected else "未连接")

    def log(self, msg):
        self.ui.textBrowserLog.append(msg)

    def cleanup(self):
        if self.serial.isOpen():
            self.serial.close()
 

if __name__ == "__main__":
    app = QApplication()
    serial_controller = SerialController()
    serial_controller.ui.show()
    app.aboutToQuit.connect(serial_controller.cleanup) # 退出前调用清理，结束串口占用
    app.exec()