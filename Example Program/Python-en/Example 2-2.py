from PySide6.QtWidgets import QApplication
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import QIODevice
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo

# State character -> (display text, status label background color)
STATE_MAP = {
    "R": ("Red", "rgb(220, 80, 80)"),
    "G": ("Green", "rgb(80, 180, 80)"),
    "B": ("Blue", "rgb(80, 120, 220)"),
    "C": ("Off", "rgb(180, 180, 180)"),
}

BAUD_RATES = ["9600", "19200", "38400", "57600", "115200", "230400", "460800", "921600"]

class SerialController():

    def __init__(self):
        # Load the UI definition from a file
        self.ui = QUiLoader().load('main_window.ui')

        self.serial = QSerialPort()
        self._init_ui()
        self._init_serial()
        self.refresh_ports()

    def _init_ui(self):
        # Populate the baud rate combo box
        self.ui.comboBoxBaud.addItems(BAUD_RATES)
        self.ui.comboBoxBaud.setCurrentText("115200")

        # Connect button signals to their corresponding slot functions
        self.ui.pushButtonConnect.clicked.connect(self.connect_serial)
        self.ui.pushButtonDisconnect.clicked.connect(self.disconnect_serial)
        self.ui.pushButtonR.clicked.connect(lambda: self.send_command("R"))
        self.ui.pushButtonG.clicked.connect(lambda: self.send_command("G"))
        self.ui.pushButtonB.clicked.connect(lambda: self.send_command("B"))
        self.ui.pushButtonC.clicked.connect(lambda: self.send_command("C"))
        self.ui.pushButtonRefresh.clicked.connect(lambda: self.send_command("T"))

        self._set_connected_ui(False)
        self.log("Application started. Please connect to a serial port.")

    # ---------- Serial Port Logic ----------
    def _init_serial(self):
        # Connect the readyRead signal to the on_ready_read slot
        self.serial.readyRead.connect(self.on_ready_read)
        # Connect the errorOccurred signal to the on_serial_error slot
        self.serial.errorOccurred.connect(self.on_serial_error)

    def refresh_ports(self):
        self.ui.comboBoxPort.clear()
        ports = QSerialPortInfo.availablePorts()
        for info in ports:
            # Display: port name (description); use portName() as the actual value
            self.ui.comboBoxPort.addItem(f"{info.portName()} ({info.description()})", info.portName())
        if not ports:
            self.ui.comboBoxPort.addItem("No serial ports detected", "")
            self.log("No available serial ports detected")
        else:
            self.log(f"Detected {len(ports)} serial port(s)")

    def connect_serial(self):
        port_name = self.ui.comboBoxPort.currentData()
        if not port_name:
            self.log("Error: No serial port available")
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
            self.log(f"Connected to {port_name} @ {baud}")
        else:
            self.log(f"Connection failed: {self.serial.errorString()}")

    def disconnect_serial(self):
        if self.serial.isOpen():
            self.serial.close()
        self._set_connected_ui(False)
        self.log("Disconnected")

    def send_command(self, ch):
        if not self.serial.isOpen():
            self.log("Error: Serial port is not connected")
            return
        data = ch.encode("ascii")
        written = self.serial.write(data)
        self.serial.flush()
        self.log(f"Sent: {ch} ({written} bytes)")

    # ---------- Receive Handling ----------
    def on_ready_read(self):
        data = self.serial.readAll().data()
        try:
            text = data.decode("ascii", errors="ignore")
        except Exception:
            return
        for ch in text:
            if ch in STATE_MAP:
                self.update_status(ch)
                self.log(f"Received: {ch} -> State updated to {STATE_MAP[ch][0]}")
            elif ch in ("\n", "\r"):
                continue
            else:
                self.log(f"Received unknown character: {ch!r}")

    def on_serial_error(self, error):
        if error == QSerialPort.NoError:
            return
        self.log(f"Serial port error: {self.serial.errorString()}")
        if not self.serial.isOpen():
            self._set_connected_ui(False)

    # ---------- UI Helpers ----------
    def update_status(self, ch):
        name, color = STATE_MAP[ch]
        self.ui.labelStatus.setText(f"Current state: {name}")
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
        self.ui.statusbar.showMessage("Connected" if connected else "Disconnected")

    def log(self, msg):
        self.ui.textBrowserLog.append(msg)

    def cleanup(self):
        if self.serial.isOpen():
            self.serial.close()


if __name__ == "__main__":
    app = QApplication()
    serial_controller = SerialController()
    serial_controller.ui.show()
    # Clean up before exiting to release the serial port
    app.aboutToQuit.connect(serial_controller.cleanup)
    app.exec()