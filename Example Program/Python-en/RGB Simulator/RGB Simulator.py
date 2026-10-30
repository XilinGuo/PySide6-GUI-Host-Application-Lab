# -*- coding: utf-8 -*-
"""
ESP32-S3-DevKitC-1 Onboard WS2812 Simulator (PySide6)
==================================================
Simulates the behavior of the Arduino device firmware:
  Receive 'R' via serial -> Red LED    'G' -> Green LED
  Receive 'B' via serial -> Blue LED   'C' -> LED off
  Receive 'T' -> Query the current state without changing the LED
  After receiving R/G/B/C/T, use Serial.println to send back
  the current state character followed by '\\n'
  Ignore all other characters without sending a response

Use a virtual serial port pair when testing the host application
(e.g., com0com on Windows):
  The simulator uses one end, and the host application uses the other.
"""

import sys

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QRadialGradient, QPen
from PySide6.QtSerialPort import QSerialPort, QSerialPortInfo
from PySide6.QtWidgets import (
    QApplication, QComboBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QPushButton, QPlainTextEdit, QVBoxLayout,
    QWidget,
)

# The WS2812 is a full-color PWM LED; smooth transitions are simulated here
FADE_INTERVAL_MS = 15      # Animation frame interval
FADE_STEP = 12             # Color step per frame (simulates PWM fading)
BRIGHTNESS = 255           # Corresponds to strip.setBrightness(255)


class Ws2812Widget(QWidget):
    """Widget that simulates the onboard WS2812 LED with a glow effect."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current = QColor(0, 0, 0)   # Currently displayed color
        self._target = QColor(0, 0, 0)    # Target color
        self._timer = QTimer(self)
        self._timer.setInterval(FADE_INTERVAL_MS)
        self._timer.timeout.connect(self._fade_step)
        self.setMinimumSize(180, 180)

    def set_color(self, r, g, b):
        """Set the target color, scaled by the WS2812 brightness setting."""
        self._target = QColor(
            r * BRIGHTNESS // 255,
            g * BRIGHTNESS // 255,
            b * BRIGHTNESS // 255,
        )
        if not self._timer.isActive():
            self._timer.start()

    def _fade_step(self):
        """Move one frame toward the target color to simulate WS2812 PWM fading."""
        c, t = self._current, self._target

        def step_channel(cur, tgt):
            if cur == tgt:
                return cur
            diff = tgt - cur
            if abs(diff) <= FADE_STEP:
                return tgt
            return cur + (FADE_STEP if diff > 0 else -FADE_STEP)

        nr = step_channel(c.red(), t.red())
        ng = step_channel(c.green(), t.green())
        nb = step_channel(c.blue(), t.blue())
        self._current = QColor(nr, ng, nb)

        if (nr, ng, nb) == (t.red(), t.green(), t.blue()):
            self._timer.stop()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        radius = min(w, h) * 0.20          # LED body radius
        glow = radius * 2.6                # Glow radius

        c = self._current
        # Background
        p.fillRect(self.rect(), QColor(28, 28, 32))

        if c.value() > 0:
            # Outer glow (radial gradient)
            grad = QRadialGradient(cx, cy, radius * 0.3)
            grad.setColorAt(0.0, QColor(c.red(), c.green(), c.blue(), 180))
            grad.setColorAt(0.4, QColor(c.red(), c.green(), c.blue(), 90))
            grad.setColorAt(1.0, QColor(c.red(), c.green(), c.blue(), 0))
            p.setBrush(grad)
            p.setPen(Qt.NoPen)
            p.drawEllipse(int(cx - glow), int(cy - glow),
                          int(glow * 2), int(glow * 2))

        # LED body
        p.setBrush(c if c.value() > 8 else QColor(50, 50, 55))
        p.setPen(QPen(QColor(70, 70, 75), 2))
        p.drawEllipse(int(cx - radius), int(cy - radius),
                      int(radius * 2), int(radius * 2))

        # Highlight to simulate reflection from the LED lens
        if c.value() > 8:
            hl = QRadialGradient(cx - radius * 0.35, cy - radius * 0.35,
                                 radius * 0.5)
            hl.setColorAt(0.0, QColor(255, 255, 255, 160))
            hl.setColorAt(1.0, QColor(255, 255, 255, 0))
            p.setBrush(hl)
            p.setPen(Qt.NoPen)
            p.drawEllipse(int(cx - radius), int(cy - radius),
                          int(radius * 2), int(radius * 2))
        p.end()


class Esp32S3Sim(QMainWindow):
    log_signal = Signal(str)

    COLORS = {
        "R": (255, 0, 0),
        "G": (0, 255, 0),
        "B": (0, 0, 255),
        "C": (0, 0, 0),
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ESP32-S3-DevKitC-1 Onboard WS2812 Simulator")
        self.resize(560, 620)

        self.serial = QSerialPort(self)
        self.serial.readyRead.connect(self._on_ready_read)
        self.serial.errorOccurred.connect(self._on_serial_error)

        self.current_state = "C"   # Corresponds to currentState in Arduino

        # ---------- Left: Serial Port Settings ----------
        port_box = QGroupBox("Serial Port Settings (Simulator Port)")
        grid = QGridLayout(port_box)
        self.port_combo = QComboBox()
        self.refresh_ports()
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.setCurrentText("115200")
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh_ports)
        self.btn_open = QPushButton("Open Port")
        self.btn_open.clicked.connect(self.toggle_port)
        grid.addWidget(QLabel("Port:"), 0, 0)
        grid.addWidget(self.port_combo, 0, 1)
        grid.addWidget(btn_refresh, 0, 2)
        grid.addWidget(QLabel("Baud Rate:"), 1, 0)
        grid.addWidget(self.baud_combo, 1, 1)
        grid.addWidget(self.btn_open, 1, 2)

        # ---------- Center: WS2812 Display ----------
        led_box = QGroupBox("Onboard WS2812 (GPIO48)")
        led_lay = QVBoxLayout(led_box)
        self.led = Ws2812Widget()
        led_lay.addWidget(self.led, alignment=Qt.AlignCenter)
        self.state_label = QLabel("Current state: C (Off)")
        led_lay.addWidget(self.state_label, alignment=Qt.AlignCenter)

        # ---------- Right: Manual Test Commands ----------
        test_box = QGroupBox("Test Commands (Simulate Host Application)")
        tl = QHBoxLayout(test_box)
        for ch, tip in [("R", "Red"), ("G", "Green"), ("B", "Blue"),
                        ("C", "Off"), ("T", "Query State")]:
            b = QPushButton(f"{ch} {tip}")
            b.clicked.connect(lambda _, c=ch: self.send_command(c))
            tl.addWidget(b)

        # ---------- Log ----------
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log_signal.connect(self.log.appendPlainText)

        # Layout
        root = QWidget()
        lay = QVBoxLayout(root)
        lay.addWidget(port_box)
        lay.addWidget(led_box)
        lay.addWidget(test_box)
        lay.addWidget(QLabel("Communication Log:"))
        lay.addWidget(self.log)
        self.setCentralWidget(root)

    # ---------------- Serial Port ----------------
    def refresh_ports(self):
        self.port_combo.clear()
        ports = QSerialPortInfo.availablePorts()
        for info in ports:
            self.port_combo.addItem(info.portName(), info.systemLocation())
        if not ports:
            self.port_combo.addItem("(No serial ports found)", "")
        self.log_signal.emit(f"[System] Found {len(ports)} serial port(s)")

    def toggle_port(self):
        if self.serial.isOpen():
            self.serial.close()
            self.btn_open.setText("Open Port")
            self.log_signal.emit("[Serial] Port closed")
            return
        loc = self.port_combo.currentData()
        if not loc:
            QMessageBox.warning(self, "Notice", "No serial port available")
            return
        self.serial.setPortName(loc)
        self.serial.setBaudRate(int(self.baud_combo.currentText()))
        self.serial.setDataBits(QSerialPort.Data8)
        self.serial.setParity(QSerialPort.NoParity)
        self.serial.setStopBits(QSerialPort.OneStop)
        self.serial.setFlowControl(QSerialPort.NoFlowControl)
        if self.serial.open(QSerialPort.ReadWrite):
            self.btn_open.setText("Close Port")
            self.log_signal.emit(
                f"[Serial] Opened {loc} @ {self.baud_combo.currentText()}")
        else:
            QMessageBox.critical(self, "Error", f"Failed to open serial port: {loc}")
            self.log_signal.emit(f"[Serial] Failed to open {loc}")

    def _on_serial_error(self, err):
        if err != QSerialPort.NoError:
            self.log_signal.emit(f"[Serial] Error: {self.serial.errorString()}")

    # ---------------- Firmware Logic ----------------
    def _on_ready_read(self):
        data = self.serial.readAll().data()
        for byte in data:
            ch = chr(byte)
            if ch in self.COLORS:
                r, g, b = self.COLORS[ch]
                self.led.set_color(r, g, b)
                self.current_state = ch
                self.state_label.setText(
                    f"Current state: {ch} ("
                    + {"R": "Red", "G": "Green", "B": "Blue", "C": "Off"}[ch]
                    + ")")
                self._reply(ch)
            elif ch == "T":
                self._reply(self.current_state)
            # Ignore other characters without replying (same as the default branch)

    def _reply(self, state):
        if self.serial.isOpen():
            self.serial.write((state + "\n").encode("ascii"))
            self.log_signal.emit(f"[Firmware] Command received -> Replied with state '{state}'")

    # ---------------- Test Commands ----------------
    def send_command(self, ch):
        """Demonstrate command effects locally without sending through the other port."""
        if not self.serial.isOpen():
            self.log_signal.emit(
                "[Notice] Serial port is not open. These buttons only pass commands "
                "to the simulation logic. For integration testing, use a virtual "
                "serial port pair and the host application.")
        r, g, b = self.COLORS.get(ch, (0, 0, 0))
        if ch in self.COLORS:
            self.led.set_color(r, g, b)
            self.current_state = ch
            self.state_label.setText(f"Current state: {ch}")
        self.log_signal.emit(f"[Test] Sent '{ch}', state = {self.current_state}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Esp32S3Sim()
    win.show()
    sys.exit(app.exec())