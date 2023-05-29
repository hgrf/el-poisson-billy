from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QPushButton
from PyQt5.QtBluetooth import (
    QBluetoothAddress, QBluetoothServiceInfo, QBluetoothSocket, QBluetoothUuid
)


class MainWidget(QLabel):
    BODY_STATES = ["h", "s", "t", "s"]

    def __init__(self):
        super().__init__()

        self.mouthIsOpen = False
        self.bodyState = 0

        self.setWindowTitle("El Poisson Billy")
        self.setPixmap(QPixmap("poisson.png"))

        self.socket = QBluetoothSocket(
            QBluetoothServiceInfo.Protocol.RfcommProtocol
        )
        self.socket.connected.connect(self.onConnected)

        self.socket.connectToService(
            QBluetoothAddress("4C:11:AE:74:BB:56"),
            QBluetoothUuid(QBluetoothUuid.SerialPort)
        )

        self.btnMouth = QPushButton("Mouth", self)
        self.btnMouth.clicked.connect(self.toggleMouth)
        self.btnMouth.setGeometry(10, 250, 100, 30)

        self.btnBody = QPushButton("Body", self)
        self.btnBody.clicked.connect(self.toggleBody)
        self.btnBody.setGeometry(300, 250, 100, 30)

        self.show()

    def onConnected(self):
        print("Connected")

    def toggleMouth(self):
        if self.mouthIsOpen:
            self.socket.write(b"c")
        else:
            self.socket.write(b"o")
        self.mouthIsOpen = not self.mouthIsOpen

    def toggleBody(self):
        self.socket.write(self.BODY_STATES[self.bodyState].encode())
        self.bodyState = (self.bodyState + 1) % len(self.BODY_STATES)


if __name__ == "__main__":
    app = QApplication([])
    w = MainWidget()
    app.exec()
