#!venv/bin/python3

import sys
import serial

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64
SCREEN_RATIO = 20

class Worker(QThread):
    screen = pyqtSignal(bytes)
    def run(self):
        while True:
            try:
                ser = serial.Serial(sys.argv[1])
                break
            except serial.SerialException as e:
                if e.errno == 13:
                    raise e
                pass
            except OSError:
                pass

        ser.write(b"screen_stream\r")
        while True:
            ser.read_until(bytes.fromhex('F0E1D2C3'))
            data = ser.read(1024)
            self.screen.emit(data)

class Screen(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resize(SCREEN_WIDTH * SCREEN_RATIO, SCREEN_HEIGHT * SCREEN_RATIO)
        self.canvas = QImage(128, 64, QImage.Format_RGB32)
        self.canvas.fill(1)

        p = QPainter()
        p.begin(self.canvas)
        p.drawText(self.canvas.rect(), Qt.AlignCenter, "Connecting");
        p.end();

        self.adjusted_to_size = (-1, -1)
        self.ratio = 2/1
        self.setSizePolicy(QSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored))

        self.worker = Worker(self)
        self.worker.screen.connect(self.data)
        self.worker.setTerminationEnabled(True)
        self.worker.start()

    def paintEvent(self, event):
        qp = QPainter()
        #qcolor = QColor(255, 152, 63, 255)
        #qcolor = QColor(255, 255, 255, 50)
        qcolor = QColor(0, 0, 0, 50)
        qp.begin(self)
        qp.drawImage(self.rect(), self.canvas)

        w = self.rect().width()
        h = self.rect().height()
        wp = self.rect().width() / SCREEN_WIDTH
        hp = self.rect().height() / SCREEN_HEIGHT
        for x in range(SCREEN_WIDTH):
            qp.setPen(QPen(qcolor, 1, Qt.SolidLine))
            qp.drawLine(int(x * wp), 0, int(x * wp), h)
        for y in range(SCREEN_HEIGHT):
            qp.setPen(QPen(qcolor, 1, Qt.SolidLine))
            qp.drawLine(0, int(y * hp), w, int(y * hp))
        qp.end()

    def resizeEvent(self, event):
        size = event.size()
        if size == self.adjusted_to_size:
            # Avoid infinite recursion. I suspect Qt does this for you,
            # but it's best to be safe.
            return
        self.adjusted_to_size = size

        full_width = size.width()
        full_height = size.height()

        width = int(min(full_width, full_height * self.ratio))
        height = int(min(full_height, full_width / self.ratio))

        self.resize(width, height)

    def closeEvent(self, evnt):
        self.worker.terminate()

    def isPixelSet(self, frame, x:int, y:int):
        i = int(y / 8) * 128
        y &= 7
        i = int(i + x)
        return (frame[i] & (1 << y)) == 0

    @pyqtSlot(bytes)
    def data(self, data):
        for y in range(SCREEN_HEIGHT):
            for x in range(SCREEN_WIDTH):
                color = self.isPixelSet(data, x, y)
                self.canvas.setPixel(x, y, 0xff8c29 if color else 0x111111)
        self.update()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Path to serial is required")
        exit(255)
    app = QApplication(sys.argv)
    monitor = QDesktopWidget().screenGeometry(1)
    widget = Screen()
    top = (monitor.height() / 2) - (widget.rect().height() / 2)
    left = (monitor.width() / 2) - (widget.rect().width() / 2)
    widget.move(monitor.left() + int(left), monitor.top() + int(top))
    widget.show()
    app.exec_()
