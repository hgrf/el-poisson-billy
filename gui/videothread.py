import cv2
import dlib
import imutils
import numpy as np

from imutils import face_utils
from scipy.spatial import distance as dist

from PyQt5.QtCore import pyqtSignal, QThread


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
    marUpdate = pyqtSignal(float)

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

                mar = mouth_aspect_ratio(mouth)
                self.marUpdate.emit(mar)
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
