import sys
import cv2
import requests
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QLabel, 
                            QPushButton, QLineEdit, QVBoxLayout, QHBoxLayout,
                            QMessageBox)

class VideoStreamThread(QThread):
    new_frame = pyqtSignal(object)
    connection_status = pyqtSignal(bool)

    def __init__(self, stream_url):
        super().__init__()
        self.stream_url = stream_url
        self.running = True

    def run(self):
        cap = cv2.VideoCapture(self.stream_url)
        if not cap.isOpened():
            self.connection_status.emit(False)
            return

        self.connection_status.emit(True)
        while self.running:
            ret, frame = cap.read()
            if ret:
                self.new_frame.emit(frame)
            else:
                self.connection_status.emit(False)
                break
        cap.release()

    def stop(self):
        self.running = False

class GoProController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GoPro Network Controller")
        self.setGeometry(100, 100, 1280, 720)
        self.stream_thread = None
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        # Основные виджеты
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.url_input = QLineEdit("udp://@10.5.5.100:8554")
        self.connect_btn = QPushButton("Подключиться")
        self.record_btn = QPushButton("Начать запись")
        self.snapshot_btn = QPushButton("Сделать фото")
        self.status_label = QLabel("Статус: Отключено")

        # Макеты
        control_layout = QHBoxLayout()
        control_layout.addWidget(self.url_input)
        control_layout.addWidget(self.connect_btn)
        control_layout.addWidget(self.status_label)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.record_btn)
        button_layout.addWidget(self.snapshot_btn)

        main_layout = QVBoxLayout()
        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.video_label)
        main_layout.addLayout(button_layout)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Настройка кнопок
        self.record_btn.setEnabled(False)
        self.snapshot_btn.setEnabled(False)
        self.record_btn.setStyleSheet("background-color: #ff4444; color: white;")

    def setup_connections(self):
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.record_btn.clicked.connect(self.toggle_recording)
        self.snapshot_btn.clicked.connect(self.take_snapshot)

    def toggle_connection(self):
        if self.stream_thread and self.stream_thread.isRunning():
            self.disconnect_camera()
        else:
            self.connect_to_camera()

    def connect_to_camera(self):
        url = self.url_input.text()
        if not url:
            QMessageBox.warning(self, "Ошибка", "Введите URL потока!")
            return

        self.stream_thread = VideoStreamThread(url)
        self.stream_thread.new_frame.connect(self.update_video)
        self.stream_thread.connection_status.connect(self.handle_connection_status)
        self.stream_thread.start()

        self.connect_btn.setText("Отключиться")
        self.url_input.setEnabled(False)

    def disconnect_camera(self):
        if self.stream_thread:
            self.stream_thread.stop()
            self.stream_thread.quit()
            self.stream_thread.wait()
        
        self.connect_btn.setText("Подключиться")
        self.url_input.setEnabled(True)
        self.record_btn.setEnabled(False)
        self.snapshot_btn.setEnabled(False)
        self.status_label.setText("Статус: Отключено")
        self.video_label.clear()

    def handle_connection_status(self, connected):
        if connected:
            self.status_label.setText("Статус: Подключено")
            self.record_btn.setEnabled(True)
            self.snapshot_btn.setEnabled(True)
        else:
            self.status_label.setText("Статус: Ошибка подключения")
            self.disconnect_camera()

    def update_video(self, frame):
        try:
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            self.video_label.setPixmap(QPixmap.fromImage(qt_image).scaled(
                self.video_label.size(), Qt.AspectRatioMode.KeepAspectRatio))
        except Exception as e:
            print(f"Ошибка обработки кадра: {e}")

    def toggle_recording(self):
        # Реализация управления записью через HTTP-API
        try:
            if self.record_btn.text() == "Начать запись":
                response = requests.get("http://10.5.5.9/gp/gpControl/command/shutter?p=1")
                if response.status_code == 200:
                    self.record_btn.setText("Остановить запись")
                    self.record_btn.setStyleSheet("background-color: #44ff44; color: black;")
            else:
                response = requests.get("http://10.5.5.9/gp/gpControl/command/shutter?p=0")
                if response.status_code == 200:
                    self.record_btn.setText("Начать запись")
                    self.record_btn.setStyleSheet("background-color: #ff4444; color: white;")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось управлять записью: {str(e)}")

    def take_snapshot(self):
        if self.stream_thread and self.stream_thread.isRunning():
            try:
                response = requests.get("http://10.5.5.9/gp/gpControl/command/shutter?p=1")
                if response.status_code == 200:
                    QTimer.singleShot(500, lambda: requests.get("http://10.5.5.9/gp/gpControl/command/shutter?p=0"))
                    QMessageBox.information(self, "Фото", "Снимок сделан!")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сделать фото: {str(e)}")

    def closeEvent(self, event):
        self.disconnect_camera()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GoProController()
    window.show()
    sys.exit(app.exec())