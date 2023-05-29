import rtmidi

from PyQt5.QtGui import QPixmap, QKeyEvent
from PyQt5.QtWidgets import QApplication, QLabel, QPushButton
from PyQt5.QtBluetooth import (
    QBluetoothServiceInfo, QBluetoothSocket, QBluetoothDeviceDiscoveryAgent,
    QBluetoothDeviceInfo
)

from enum import IntEnum

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

        self.setEnabled(False)
        self.setWindowTitle("El Poisson Billy")
        self.setPixmap(QPixmap("poisson.png"))

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

        self.agent = QBluetoothDeviceDiscoveryAgent()
        self.agent.deviceDiscovered.connect(self.onDeviceDiscovered)
        self.agent.start(QBluetoothDeviceDiscoveryAgent.DiscoveryMethod.ClassicMethod)

        self.show()

    def keyPressEvent(self, ev: QKeyEvent):
        t = ev.text().lower()
        if t in self.keyToNote.keys():
            self.sendNote(self.keyToNote[t])

        return super().keyPressEvent(ev)

    def close(self):
        print("Exit")
        self.socket.close()
        self.midiin.close_port()
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
