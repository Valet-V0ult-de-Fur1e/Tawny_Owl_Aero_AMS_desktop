import sys
import cv2
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, 
                              QVBoxLayout, QHBoxLayout, QLabel,
                              QTabWidget, QTextEdit, QComboBox)

def list_ports():
    non_working_ports = []
    dev_port = 0
    working_ports = []
    available_ports = []
    while len(non_working_ports) < 6:
        camera = cv2.VideoCapture(dev_port)
        if not camera.isOpened():
            non_working_ports.append(dev_port)
        else:
            is_reading, img = camera.read()
            w = camera.get(3)
            h = camera.get(4)
            if is_reading:
                working_ports.append((dev_port, h, w))
            else:
                available_ports.append(dev_port)
        dev_port +=1
        camera.release()
    return available_ports, working_ports, non_working_ports

class CameraWorker(QObject):
    image_updated = Signal(QImage)
    finished = Signal()

    def __init__(self, port):
        super().__init__()
        self.port = port
        self.running = True

    def run(self):
        cap = cv2.VideoCapture(self.port)
        while self.running:
            ret, frame = cap.read()
            if ret:
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                self.image_updated.emit(qt_image)
        cap.release()
        self.finished.emit()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Camera Viewer")
        self.setGeometry(100, 100, 800, 600)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Statistics Tab
        self.stats_tab = QWidget()
        self.stats_layout = QVBoxLayout()
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_layout.addWidget(self.stats_text)
        self.stats_tab.setLayout(self.stats_layout)

        # Camera View Tab
        self.camera_tab = QWidget()
        self.camera_layout = QVBoxLayout()
        self.camera_tab.setLayout(self.camera_layout)

        # Combo box for camera selection
        self.camera_selector = QComboBox()
        self.camera_selector.currentIndexChanged.connect(self.switch_camera)
        self.camera_layout.addWidget(self.camera_selector)

        # Label for displaying the camera feed
        self.camera_label = QLabel()
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setStyleSheet("border: 2px solid black;")
        self.camera_label.setFixedSize(640, 480)  # Фиксированный размер для отображения камеры
        self.camera_layout.addWidget(self.camera_label)

        self.tabs.addTab(self.stats_tab, "Statistics")
        self.tabs.addTab(self.camera_tab, "Camera View")

        self.camera_workers = []
        self.camera_threads = []
        self.working_ports = []

        self.show_ports_statistics()
        self.setup_cameras()

    def show_ports_statistics(self):
        available, working_ports, non_working = list_ports()
        self.working_ports = working_ports
        stats = []
        stats.append("Working ports:")
        for port, h, w in working_ports:
            stats.append(f"Port {port}: {w}x{h}")
        stats.append("\nAvailable but non-working ports:")
        stats += [f"Port {p}" for p in available]
        stats.append("\nNon-working ports:")
        stats += [f"Port {p}" for p in non_working]

        self.stats_text.setText("\n".join(stats))

    def setup_cameras(self):
        for port, h, w in self.working_ports:
            self.camera_selector.addItem(f"Camera {port} ({w}x{h})")

            worker = CameraWorker(port)
            thread = QThread()
            worker.moveToThread(thread)
            worker.image_updated.connect(self.update_image)
            thread.started.connect(worker.run)
            thread.start()
            
            self.camera_workers.append(worker)
            self.camera_threads.append(thread)

        if self.working_ports:
            self.switch_camera(-1)

    def switch_camera(self, index):
        if index < 0 or index >= len(self.camera_workers):
            return

        # Disconnect previous camera's signal
        if hasattr(self, 'current_worker'):
            self.current_worker.image_updated.disconnect()

        # Connect to the new camera's signal
        self.current_worker = self.camera_workers[index]
        self.current_worker.image_updated.connect(self.update_image)

    def update_image(self, image):
        pixmap = QPixmap.fromImage(image)
        # Масштабируем изображение под фиксированный размер QLabel
        pixmap = pixmap.scaled(
            self.camera_label.width(), self.camera_label.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.camera_label.setPixmap(pixmap)

    def closeEvent(self, event):
        for worker, thread in zip(self.camera_workers, self.camera_threads):
            worker.running = False
            thread.quit()
            thread.wait()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())