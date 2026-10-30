# -*- coding: utf-8 -*-
"""
ESP32-S3-DevKitC-1 板载 WS2812 仿真器 (PySide6)
==============================================
模拟 Arduino 下位机行为：
  串口收到 'R' -> 红灯    'G' -> 绿灯    'B' -> 蓝灯    'C' -> 关灯
  收到 'T'   -> 仅查询状态（不改变灯光）
  每次收到 R/G/B/C/T 后通过 Serial.println 回发当前状态字符 + '\\n'
  其他字符忽略，不回发

上位机测试时请使用虚拟串口对（如 Windows 的 com0com）：
  仿真器占用一端，你的上位机程序占用另一端
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

# WS2812 是全彩 PWM 灯珠，这里做一个平滑过渡的仿真
FADE_INTERVAL_MS = 15      # 动画帧间隔
FADE_STEP = 12             # 每帧颜色步进（模拟 PWM 渐变）
BRIGHTNESS = 255           # 对应 strip.setBrightness(255)


class Ws2812Widget(QWidget):
    """模拟板载 WS2812 灯珠的显示控件（带辉光）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current = QColor(0, 0, 0)   # 当前显示颜色
        self._target = QColor(0, 0, 0)    # 目标颜色
        self._timer = QTimer(self)
        self._timer.setInterval(FADE_INTERVAL_MS)
        self._timer.timeout.connect(self._fade_step)
        self.setMinimumSize(180, 180)

    def set_color(self, r, g, b):
        """设置目标颜色（WS2812 显示经亮度缩放后的实际颜色）"""
        self._target = QColor(
            r * BRIGHTNESS // 255,
            g * BRIGHTNESS // 255,
            b * BRIGHTNESS // 255,
        )
        if not self._timer.isActive():
            self._timer.start()

    def _fade_step(self):
        """向目标颜色逼近一帧，模拟 WS2812 的 PWM 渐变"""
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
        radius = min(w, h) * 0.20          # 灯珠本体半径
        glow = radius * 2.6                # 辉光半径

        c = self._current
        # 背景
        p.fillRect(self.rect(), QColor(28, 28, 32))

        if c.value() > 0:
            # 外圈辉光（径向渐变）
            grad = QRadialGradient(cx, cy, radius * 0.3)
            grad.setColorAt(0.0, QColor(c.red(), c.green(), c.blue(), 180))
            grad.setColorAt(0.4, QColor(c.red(), c.green(), c.blue(), 90))
            grad.setColorAt(1.0, QColor(c.red(), c.green(), c.blue(), 0))
            p.setBrush(grad)
            p.setPen(Qt.NoPen)
            p.drawEllipse(int(cx - glow), int(cy - glow),
                          int(glow * 2), int(glow * 2))

        # 灯珠本体
        p.setBrush(c if c.value() > 8 else QColor(50, 50, 55))
        p.setPen(QPen(QColor(70, 70, 75), 2))
        p.drawEllipse(int(cx - radius), int(cy - radius),
                      int(radius * 2), int(radius * 2))

        # 高光，模拟 LED 透镜反光
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
        self.setWindowTitle("ESP32-S3-DevKitC-1 板载 WS2812 仿真器")
        self.resize(560, 620)

        self.serial = QSerialPort(self)
        self.serial.readyRead.connect(self._on_ready_read)
        self.serial.errorOccurred.connect(self._on_serial_error)

        self.current_state = "C"   # 对应 Arduino 的 currentState

        # ---------- 左侧：串口设置 ----------
        port_box = QGroupBox("串口设置（仿真器占用的端口）")
        grid = QGridLayout(port_box)
        self.port_combo = QComboBox()
        self.refresh_ports()
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.setCurrentText("115200")
        btn_refresh = QPushButton("刷新")
        btn_refresh.clicked.connect(self.refresh_ports)
        self.btn_open = QPushButton("打开串口")
        self.btn_open.clicked.connect(self.toggle_port)
        grid.addWidget(QLabel("端口:"), 0, 0)
        grid.addWidget(self.port_combo, 0, 1)
        grid.addWidget(btn_refresh, 0, 2)
        grid.addWidget(QLabel("波特率:"), 1, 0)
        grid.addWidget(self.baud_combo, 1, 1)
        grid.addWidget(self.btn_open, 1, 2)

        # ---------- 中间：WS2812 显示 ----------
        led_box = QGroupBox("板载 WS2812 (GPIO48)")
        led_lay = QVBoxLayout(led_box)
        self.led = Ws2812Widget()
        led_lay.addWidget(self.led, alignment=Qt.AlignCenter)
        self.state_label = QLabel("当前状态: C（熄灭）")
        led_lay.addWidget(self.state_label, alignment=Qt.AlignCenter)

        # ---------- 右侧：手动测试发送 ----------
        test_box = QGroupBox("测试发送（模拟上位机）")
        tl = QHBoxLayout(test_box)
        for ch, tip in [("R", "红色"), ("G", "绿色"), ("B", "蓝色"),
                        ("C", "关闭"), ("T", "查询状态")]:
            b = QPushButton(f"{ch} {tip}")
            b.clicked.connect(lambda _, c=ch: self.send_command(c))
            tl.addWidget(b)

        # ---------- 日志 ----------
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log_signal.connect(self.log.appendPlainText)

        # 布局
        root = QWidget()
        lay = QVBoxLayout(root)
        lay.addWidget(port_box)
        lay.addWidget(led_box)
        lay.addWidget(test_box)
        lay.addWidget(QLabel("通信日志:"))
        lay.addWidget(self.log)
        self.setCentralWidget(root)

    # ---------------- 串口 ----------------
    def refresh_ports(self):
        self.port_combo.clear()
        ports = QSerialPortInfo.availablePorts()
        for info in ports:
            self.port_combo.addItem(info.portName(), info.systemLocation())
        if not ports:
            self.port_combo.addItem("（未发现串口）", "")
        self.log_signal.emit(f"[系统] 发现 {len(ports)} 个串口")

    def toggle_port(self):
        if self.serial.isOpen():
            self.serial.close()
            self.btn_open.setText("打开串口")
            self.log_signal.emit("[串口] 已关闭")
            return
        loc = self.port_combo.currentData()
        if not loc:
            QMessageBox.warning(self, "提示", "没有可用串口")
            return
        self.serial.setPortName(loc)
        self.serial.setBaudRate(int(self.baud_combo.currentText()))
        self.serial.setDataBits(QSerialPort.Data8)
        self.serial.setParity(QSerialPort.NoParity)
        self.serial.setStopBits(QSerialPort.OneStop)
        self.serial.setFlowControl(QSerialPort.NoFlowControl)
        if self.serial.open(QSerialPort.ReadWrite):
            self.btn_open.setText("关闭串口")
            self.log_signal.emit(
                f"[串口] 已打开 {loc} @ {self.baud_combo.currentText()}")
        else:
            QMessageBox.critical(self, "错误", f"打开串口失败: {loc}")
            self.log_signal.emit(f"[串口] 打开失败 {loc}")

    def _on_serial_error(self, err):
        if err != QSerialPort.NoError:
            self.log_signal.emit(f"[串口] 错误: {self.serial.errorString()}")

    # ---------------- 固件逻辑 ----------------
    def _on_ready_read(self):
        data = self.serial.readAll().data()
        for byte in data:
            ch = chr(byte)
            if ch in self.COLORS:
                r, g, b = self.COLORS[ch]
                self.led.set_color(r, g, b)
                self.current_state = ch
                self.state_label.setText(
                    f"当前状态: {ch}（"
                    + {"R": "红色", "G": "绿色", "B": "蓝色", "C": "熄灭"}[ch]
                    + "）")
                self._reply(ch)
            elif ch == "T":
                self._reply(self.current_state)
            # 其他字符忽略，不回发（与 default 分支一致）

    def _reply(self, state):
        if self.serial.isOpen():
            self.serial.write((state + "\n").encode("ascii"))
            self.log_signal.emit(f"[固件] 收到指令 -> 回发状态 '{state}'")

    # ---------------- 测试发送 ----------------
    def send_command(self, ch):
        """从另一端无法直接写自己，这里仅演示指令效果"""
        if not self.serial.isOpen():
            self.log_signal.emit(
                "[提示] 串口未打开。此按钮只是把指令喂给仿真逻辑，"
                "实际联调请用虚拟串口对 + 上位机程序。")
        r, g, b = self.COLORS.get(ch, (0, 0, 0))
        if ch in self.COLORS:
            self.led.set_color(r, g, b)
            self.current_state = ch
            self.state_label.setText(f"当前状态: {ch}")
        self.log_signal.emit(f"[测试] 发送 '{ch}'，状态 = {self.current_state}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Esp32S3Sim()
    win.show()
    sys.exit(app.exec())