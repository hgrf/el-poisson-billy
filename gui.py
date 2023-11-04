import cv2
import dlib
import imutils
import numpy as np
import rtmidi

from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QThread
from PyQt5.QtGui import QCloseEvent, QKeyEvent, QImage, QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QPushButton
from PyQt5.QtBluetooth import (
    QBluetoothServiceInfo,
    QBluetoothSocket,
    QBluetoothDeviceDiscoveryAgent,
    QBluetoothDeviceInfo,
    QBluetoothUuid,
)

from enum import IntEnum
from imutils import face_utils
from scipy.spatial import distance as dist


def mouth_aspect_ratio(mouth):
    # compute the euclidean distances between the two sets of
    # vertical mouth landmarks (x, y)-coordinates
    A = dist.euclidean(mouth[2], mouth[10])  # 51, 59
    B = dist.euclidean(mouth[4], mouth[8])  # 53, 57

    # compute the euclidean distance between the horizontal
    # mouth landmark (x, y)-coordinates
    C = dist.euclidean(mouth[0], mouth[6])  # 49, 55

    # compute the mouth aspect ratio
    mar = (A + B) / (2.0 * C)

    # return the mouth aspect ratio
    return mar


class VideoThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)
    mouthChanged = pyqtSignal(bool)

    def run(self):
        detector = dlib.get_frontal_face_detector()
        predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")
        # grab the indexes of the facial landmarks for the mouth
        (mStart, mEnd) = (49, 68)
        # define one constants, for mouth aspect ratio to indicate open mouth
        MOUTH_AR_THRESH = 0.69  # 0.79

        mouthOpen = False
        frame = None

        self.isRunning = True

        # capture from web cam
        cap = cv2.VideoCapture(0)
        while self.isRunning:
            ret, frame = cap.read()
            frame = imutils.resize(frame, width=640)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # detect faces in the grayscale frame
            rects = detector(gray, 0)
            if len(rects) == 0:
                cv2.putText(
                        frame,
                        "No face detected!",
                        (30, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 0, 255),
                        2,
                    )
            # loop over the face detections
            for rect in rects:
                # determine the facial landmarks for the face region, then
                # convert the facial landmark (x, y)-coordinates to a NumPy
                # array
                shape = predictor(gray, rect)
                shape = face_utils.shape_to_np(shape)

                # extract the mouth coordinates, then use the
                # coordinates to compute the mouth aspect ratio
                mouth = shape[mStart:mEnd]

                mouthMAR = mouth_aspect_ratio(mouth)
                mar = mouthMAR
                # compute the convex hull for the mouth, then
                # visualize the mouth
                mouthHull = cv2.convexHull(mouth)

                cv2.drawContours(frame, [mouthHull], -1, (0, 255, 0), 1)
                cv2.putText(
                    frame,
                    "MAR: {:.2f}".format(mar),
                    (30, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2,
                )

                # Draw text if mouth is open
                if mar > MOUTH_AR_THRESH:
                    cv2.putText(
                        frame,
                        "Mouth is Open!",
                        (30, 60),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 0, 255),
                        2,
                    )

                    if not mouthOpen:
                        mouthOpen = True
                        self.mouthChanged.emit(True)
                else:
                    if mouthOpen:
                        mouthOpen = False
                        self.mouthChanged.emit(False)

            if ret:
                self.change_pixmap_signal.emit(frame)

        if frame is not None:
            frame.fill(0)
            self.change_pixmap_signal.emit(frame)

    def stop(self):
        self.isRunning = False


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

        self.btnToggleCV = QPushButton("Mouth recognition off", self)
        self.btnToggleCV.setCheckable(True)
        self.btnToggleCV.clicked.connect(lambda: self.toggleCV())
        self.btnToggleCV.setGeometry(400, 350, 200, 30)

        self.image_label = QLabel(self)
        self.image_label.setGeometry(
            self.background.width(), 0, self.width() - self.background.width(), 400
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
            self.thread.start()
        else:
            self.thread.stop()
            self.thread.wait()

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
            self.socket.connectToService(
                dev.address(), 1  # QBluetoothUuid(QBluetoothUuid.ServiceClassUuid.SerialPort)
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
        self.midiout.send_message([0x90, int(note), 0x7F])
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
