import sys
import cv2
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget
import time

class GoProWebcamApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GoPro Webcam & Recorder")
        self.setGeometry(100, 100, 800, 600)

        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.record_btn = QPushButton("Начать запись", self)
        self.record_btn.clicked.connect(self.toggle_recording)
        
        self.snap_btn = QPushButton("Сделать фото", self)
        self.snap_btn.clicked.connect(self.take_snapshot)

        layout = QVBoxLayout()
        layout.addWidget(self.video_label)
        layout.addWidget(self.record_btn)
        layout.addWidget(self.snap_btn)
        
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.cap = cv2.VideoCapture(1)
        if not self.cap.isOpened():
            print("Ошибка: Камера не найдена!")
            sys.exit(1)

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)
        
        self.recording = False
        self.video_writer = None
        self.frame_size = (1920, 1080)

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            self.video_label.setPixmap(QPixmap.fromImage(q_img).scaled(
                self.video_label.width(), self.video_label.height(), Qt.AspectRatioMode.KeepAspectRatio))
            
            if self.recording and self.video_writer is not None:
                self.video_writer.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

    def toggle_recording(self):
        if not self.recording:
            self.video_writer = cv2.VideoWriter(
                f"recording_{time.strftime('%Y%m%d_%H%M%S')}.avi",
                cv2.VideoWriter_fourcc(*'XVID'),
                30, self.frame_size)
            self.recording = True
            self.record_btn.setText("Остановить запись")
        else:
            self.recording = False
            if self.video_writer is not None:
                self.video_writer.release()
                self.video_writer = None
            self.record_btn.setText("Начать запись")

    def take_snapshot(self):
        ret, frame = self.cap.read()
        if ret:
            cv2.imwrite(f"photo_{time.strftime('%Y%m%d_%H%M%S')}.jpg", cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

    def closeEvent(self, event):
        self.cap.release()
        if self.video_writer is not None:
            self.video_writer.release()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GoProWebcamApp()
    window.show()
    sys.exit(app.exec())