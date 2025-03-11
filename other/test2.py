import sys
import cv2
import numpy as np
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget
import time

class VideoThread(QThread):
    frame_ready = pyqtSignal(np.ndarray)

    def __init__(self, stream_url):
        super().__init__()
        self.stream_url = stream_url
        self.running = True

    def run(self):
        cap = cv2.VideoCapture(self.stream_url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)  # Уменьшаем буфер для снижения задержки

        while self.running:
            ret, frame = cap.read()
            if ret:
                self.frame_ready.emit(frame)
            else:
                print("Ошибка получения кадра")
                break
        cap.release()

    def stop(self):
        self.running = False

class GoPro4KApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GoPro 4K Stream & Recorder")
        self.setGeometry(100, 100, 1280, 720)  # Окно предпросмотра (4K может не поместиться на экране)

        # Виджеты
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.record_btn = QPushButton("Начать запись", self)
        self.record_btn.clicked.connect(self.toggle_recording)
        
        self.snap_btn = QPushButton("Сделать фото", self)
        self.snap_btn.clicked.connect(self.take_snapshot)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.video_label)
        layout.addWidget(self.record_btn)
        layout.addWidget(self.snap_btn)
        
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Поток для обработки видео (4K требует отдельного потока)
        self.stream_url = "udp://@10.5.5.100:8554"  # URL для 4K потока
        self.video_thread = VideoThread(self.stream_url)
        self.video_thread.frame_ready.connect(self.update_frame)
        self.video_thread.start()

        # Переменные записи
        self.recording = False
        self.video_writer = None
        self.frame_size = (3840, 2160)  # 4K разрешение
        self.fps = 30  # Частота кадров

    def update_frame(self, frame):
        # Масштабирование для предпросмотра (4K -> 720p)
        preview_frame = cv2.resize(frame, (1280, 720))
        rgb_frame = cv2.cvtColor(preview_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(q_img))

        # Запись исходного 4K кадра
        if self.recording and self.video_writer is not None:
            self.video_writer.write(frame)

    def toggle_recording(self):
        if not self.recording:
            # Настройки кодека (H.265 для 4K)
            self.video_writer = cv2.VideoWriter(
                f"4k_recording_{time.strftime('%Y%m%d_%H%M%S')}.mp4",
                cv2.VideoWriter_fourcc(*'hev1'),  # Кодек H.265
                self.fps,
                self.frame_size
            )
            self.recording = True
            self.record_btn.setText("Остановить запись")
        else:
            self.recording = False
            if self.video_writer is not None:
                self.video_writer.release()
                self.video_writer = None
            self.record_btn.setText("Начать запись")

    def take_snapshot(self):
        # Получаем последний кадр из потока (в 4K)
        self.video_thread.frame_ready.disconnect()
        ret, frame = cv2.VideoCapture(self.stream_url).read()
        if ret:
            cv2.imwrite(f"4k_photo_{time.strftime('%Y%m%d_%H%M%S')}.jpg", frame)
        self.video_thread.frame_ready.connect(self.update_frame)

    def closeEvent(self, event):
        self.video_thread.stop()
        if self.video_writer is not None:
            self.video_writer.release()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GoPro4KApp()
    window.show()
    sys.exit(app.exec())