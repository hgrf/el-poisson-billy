import cv2
import numpy as np
import rtmidi
import sys

from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtGui import QCloseEvent, QKeyEvent, QImage, QPixmap
from PyQt5.QtWidgets import QLabel, QPushButton
from PyQt5.QtBluetooth import (
    QBluetoothServiceInfo,
    QBluetoothSocket,
    QBluetoothDeviceDiscoveryAgent,
    QBluetoothDeviceInfo,
    QBluetoothUuid,
)

from enum import IntEnum

from .videothread import VideoThread


class MainWidget(QLabel):
    class Note(IntEnum):
        OPEN = 60
        CLOSE = 61
        HEAD = 62
        TAIL = 63
        STOP = 64

    noteToCommand = {
        Note.OPEN: "o",
        Note.CLOSE: "c",
        Note.HEAD: "h",
        Note.TAIL: "t",
        Note.STOP: "s",
    }

    keyToNote = {
        "q": Note.OPEN,
        "z": Note.CLOSE,
        "s": Note.HEAD,
        "e": Note.TAIL,
        "d": Note.STOP,
    }

    def __init__(self):
        super().__init__()

        self.socket = None

        self.midiin = rtmidi.MidiIn()
        self.portName = "El Poisson"
        self.midiin.open_virtual_port(self.portName)
        self.midiin.set_callback(self.onMidi)
        self.midiout = rtmidi.MidiOut()
        self.midiout.open_virtual_port(self.portName)

        self.mouthIsOpen = False
        self.bodyState = 0

        self.background = QPixmap("poisson.png")
        self.setEnabled(False)
        self.setWindowTitle("El Poisson Billy")
        self.setGeometry(0, 0, self.background.width(), self.background.height())
        self.setPixmap(self.background)
        self.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.btnMouth = QPushButton("Mouth (Q/Z)", self)
        self.btnMouth.clicked.connect(self.toggleMouth)
        self.btnMouth.setGeometry(10, 250, 100, 30)

        self.btnRelax = QPushButton("Head (S)", self)
        self.btnRelax.clicked.connect(lambda: self.sendNote(MainWidget.Note.HEAD))
        self.btnRelax.setGeometry(150, 250, 100, 30)

        self.btnRelax = QPushButton("Relax (D)", self)
        self.btnRelax.clicked.connect(lambda: self.sendNote(MainWidget.Note.STOP))
        self.btnRelax.setGeometry(300, 250, 100, 30)

        self.btnRelax = QPushButton("Tail (E)", self)
        self.btnRelax.clicked.connect(lambda: self.sendNote(MainWidget.Note.TAIL))
        self.btnRelax.setGeometry(450, 250, 100, 30)

        self.btnToggleCV = QPushButton("Mouth recognition off", self)
        self.btnToggleCV.setCheckable(True)
        self.btnToggleCV.clicked.connect(lambda: self.toggleCV())
        self.btnToggleCV.setGeometry(400, 350, 200, 30)

        self.image_label = QLabel(self)
        self.image_label.setGeometry(
            0, self.background.height(), self.width(), self.height()
        )

        self.agent = QBluetoothDeviceDiscoveryAgent()
        self.agent.deviceDiscovered.connect(self.onDeviceDiscovered)
        self.agent.start(QBluetoothDeviceDiscoveryAgent.DiscoveryMethod.ClassicMethod)

        self.thread = VideoThread()
        self.thread.change_pixmap_signal.connect(self.update_image)
        self.thread.mouthChanged.connect(self.updateMouth)

        self.show()

    def closeEvent(self, a0: QCloseEvent) -> None:
        self.thread.stop()
        self.thread.wait()
        return super().closeEvent(a0)

    def toggleCV(self):
        self.btnToggleCV.setText(
            f'Mouth recognition {"on" if self.btnToggleCV.isChecked() else "off"}'
        )
        if self.btnToggleCV.isChecked():
            self.setGeometry(0, 0, self.background.width(), 2 * self.background.height())
            self.thread.start()
        else:
            self.thread.stop()
            self.thread.wait()
            self.setGeometry(0, 0, self.background.width(), self.background.height())

    def keyPressEvent(self, ev: QKeyEvent):
        t = ev.text().lower()
        if t in self.keyToNote.keys():
            self.sendNote(self.keyToNote[t])

        return super().keyPressEvent(ev)

    @pyqtSlot(bool)
    def updateMouth(self, open: bool):
        self.sendNoteToRemote(MainWidget.Note.OPEN if open else MainWidget.Note.CLOSE)

    @pyqtSlot(np.ndarray)
    def update_image(self, frame):
        """Updates the image_label with a new opencv image"""
        qt_img = self.convert_cv_qt(frame)
        self.image_label.setPixmap(qt_img)

    def convert_cv_qt(self, cv_img):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(
            self.image_label.width(), self.image_label.height(), Qt.KeepAspectRatio
        )
        return QPixmap.fromImage(p)

    def close(self):
        print("Exit")
        self.socket.close()
        self.midiin.close_port()
        self.cam.release()
        del self.midiin

        super(MainWidget, self).close()

    def onSocketStateChange(self, state: QBluetoothSocket.SocketState):
        if state == QBluetoothSocket.SocketState.ConnectedState:
            s = "connected"
            self.setEnabled(True)
        elif state == QBluetoothSocket.SocketState.ClosingState:
            s = "closing"
        elif state == QBluetoothSocket.SocketState.ConnectingState:
            s = "connecting"
        elif state == QBluetoothSocket.SocketState.UnconnectedState:
            s = "not connected"
        elif state == QBluetoothSocket.SocketState.ServiceLookupState:
            s = "service lookup"
        else:
            s = "unknown: " + str(state)
        print("Socket state changed:", s)

    def onSocketError(self):
        print("Socket error:", self.socket.errorString())

    def onDeviceDiscovered(self, dev: QBluetoothDeviceInfo):
        print("Device discovered:", dev.name())
        if dev.name() == "El Poisson":
            self.agent.stop()

            self.socket = QBluetoothSocket(QBluetoothServiceInfo.Protocol.RfcommProtocol)
            self.socket.error.connect(self.onSocketError)
            self.socket.stateChanged.connect(self.onSocketStateChange)
            s = (
                1
                if sys.platform == "darwin"
                else QBluetoothUuid(QBluetoothUuid.ServiceClassUuid.SerialPort)
            )
            self.socket.connectToService(dev.address(), s)

    def onMidi(self, event, data=None):
        message, deltatime = event
        print("Received MIDI message:", message)

        # check for note on
        if message[0] == 0x90:
            note = message[1]
            if note in self.noteToCommand.keys():
                self.sendNoteToRemote(note)

    def sendNoteToRemote(self, note: Note):
        print("Sending note to remote:", note)
        if self.socket is None or not self.socket.isWritable():
            print("Cannot send command")
            return
        self.socket.write(self.noteToCommand[note].encode())

    def sendNote(self, note: Note):
        print("Sending note:", note)
        # TODO: here we want to temporarily ignore incoming midi messages in case
        #       Ableton (for example) is configured to loop back
        self.midiout.send_message([0x90, int(note), 0x7F])
        self.sendNoteToRemote(note)

    def toggleMouth(self):
        if self.mouthIsOpen:
            self.sendNote(MainWidget.Note.CLOSE)
        else:
            self.sendNote(MainWidget.Note.OPEN)
        self.mouthIsOpen = not self.mouthIsOpen
