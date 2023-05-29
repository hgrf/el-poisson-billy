import cv2
import numpy as np
import rtmidi

from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QThread
from PyQt5.QtGui import QPixmap, QKeyEvent, QImage
from PyQt5.QtWidgets import QApplication, QLabel, QPushButton
from PyQt5.QtBluetooth import (
    QBluetoothServiceInfo, QBluetoothSocket, QBluetoothDeviceDiscoveryAgent,
    QBluetoothDeviceInfo, QBluetoothUuid
)

from enum import IntEnum


class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)

    def run(self):
        # capture from web cam
        cap = cv2.VideoCapture(0)
        while True:
            ret, cv_img = cap.read()
            if ret:
                self.change_pixmap_signal.emit(cv_img)


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

        self.cam = cv2.VideoCapture()

        # Load the cascade
        self.face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
        self.mouth_cascade = cv2.CascadeClassifier("haarcascade_mcs_mouth.xml")

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
        self.setGeometry(0, 0, 900, 400)
        self.setPixmap(self.background)

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

        self.image_label = QLabel(self)
        self.image_label.setGeometry(self.background.width(), 0, self.width() - self.background.width(), 400)

        self.agent = QBluetoothDeviceDiscoveryAgent()
        self.agent.deviceDiscovered.connect(self.onDeviceDiscovered)
        self.agent.start(QBluetoothDeviceDiscoveryAgent.DiscoveryMethod.ClassicMethod)

        self.thread = VideoThread()
        self.thread.change_pixmap_signal.connect(self.update_image)
        self.thread.start()

        self.show()

    def keyPressEvent(self, ev: QKeyEvent):
        t = ev.text().lower()
        if t in self.keyToNote.keys():
            self.sendNote(self.keyToNote[t])

        return super().keyPressEvent(ev)

    @pyqtSlot(np.ndarray)
    def update_image(self, frame):
        """Updates the image_label with a new opencv image"""

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

            # roi = (0, 0, gray.shape[1], gray.shape[0])
            roi = (x, y, x + w, y + h)
            roi_img = gray[roi[0]:roi[2], roi[1]:roi[3]]

            mouths = self.mouth_cascade.detectMultiScale(roi_img, 2, 11)   # 1.5, 11
            smallest_mouth = (0, 0, 1000, 1000)
            for (xm, ym, wm, hm) in mouths:
                smallest_mouth = (
                    (xm, ym, wm, hm)
                    if wm * hm < smallest_mouth[2] * smallest_mouth[3]
                    else smallest_mouth
                )
            (xm, ym, wm, hm) = smallest_mouth
            if wm * hm < 1000000:
                cv2.rectangle(frame,
                    (roi[0] + xm, roi[1] + ym),
                    (roi[0] + xm + wm, roi[1] + ym + hm),
                    (255, 0, 0), 2
                )
                print("Mouth size", wm * hm)

        qt_img = self.convert_cv_qt(frame)
        self.image_label.setPixmap(qt_img)

    def convert_cv_qt(self, cv_img):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.image_label.width(), self.image_label.height(), Qt.KeepAspectRatio)
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
            
            self.socket = QBluetoothSocket(
                QBluetoothServiceInfo.Protocol.RfcommProtocol
            )
            self.socket.error.connect(self.onSocketError)
            self.socket.stateChanged.connect(self.onSocketStateChange)
            self.socket.connectToService(
                dev.address(),
                1 # QBluetoothUuid(QBluetoothUuid.ServiceClassUuid.SerialPort)
            )

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
        self.midiout.send_message([0x90, int(note), 0x7f])
        self.sendNoteToRemote(note)

    def toggleMouth(self):
        if self.mouthIsOpen:
            self.sendNote(MainWidget.Note.CLOSE)
        else:
            self.sendNote(MainWidget.Note.OPEN)
        self.mouthIsOpen = not self.mouthIsOpen        


if __name__ == "__main__":
    app = QApplication([])
    w = MainWidget()
    app.exec()
