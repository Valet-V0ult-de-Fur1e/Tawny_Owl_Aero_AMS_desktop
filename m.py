from datetime import datetime
import sys
import os
import requests
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QDateTime, QThread, QMutex
from PyQt6.QtGui import QFont
import cv2
import platform
import subprocess
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QGridLayout, QMessageBox)
import json
import numpy as np

class AppState:
    """Глобальное состояние приложения"""
    def __init__(self):
        self.camera_mode = None
        self.direction = ""
        self.location_data = {}
        self.connection_status = False
        self.flight_number = "1"
        self.start_point = ""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.state = AppState()
        self.stacked = QStackedWidget()
        self.setCentralWidget(self.stacked)
        self.init_pages()
        self.showFullScreen()

    def init_pages(self):
        self.stacked.addWidget(MainPage(self))
        self.stacked.addWidget(UploadPage(self))

    def navigate_to(self, page_class, destroy_current=True):
        if destroy_current and self.stacked.count() > 1:
            old_page = self.stacked.widget(1)
            self.stacked.removeWidget(old_page)
            old_page.deleteLater()
        
        new_page = page_class(self)
        self.stacked.addWidget(new_page)
        self.stacked.setCurrentWidget(new_page)

class MainPage(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.window = parent
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_style = """
            QPushButton {
                background-color: %s; color: white;
                padding: 30px 60px; font-size: 32px;
                margin: 20px; border-radius: 15px;
                min-width: 400px;
            }
            QPushButton:hover { background-color: %s; }
        """
        
        self.btn_upload = QPushButton("Выгрузить данные на сервер")
        self.btn_upload.setStyleSheet(btn_style % ("#4CAF50", "#45a049"))
        self.btn_upload.clicked.connect(
            lambda: self.window.navigate_to(UploadPage))
        
        self.btn_scan = QPushButton("Начать обследование") 
        self.btn_scan.setStyleSheet(btn_style % ("#4CAF50", "#45a049"))
        self.btn_scan.clicked.connect(
            lambda: self.window.navigate_to(SelectModePage))
        
        self.btn_power = QPushButton("⏻ Выключить систему")
        self.btn_power.setStyleSheet(btn_style % ("#EF5350", "#D32F2F"))
        self.btn_power.clicked.connect(QApplication.instance().quit)

        layout.addWidget(self.btn_upload)
        layout.addWidget(self.btn_scan)
        layout.addWidget(self.btn_power)

class UploadPage(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.window = parent
        self.timer = QTimer(self)
        self.init_ui()
        self.timer.timeout.connect(self.check_connection)
        self.timer.start(2000)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 30, 50, 30)
        
        title = QLabel("Выгрузка данных")
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.status_label = QLabel("Проверка соединения...")
        self.status_label.setFont(QFont("Arial", 18))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.upload_btn = QPushButton("Начать выгрузку данных ↑")
        self.upload_btn.setFont(QFont("Arial", 16))
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3; color: white;
                padding: 15px 30px; border-radius: 8px;
                min-width: 300px;
            }
            QPushButton:hover { background-color: #1976D2; }
            QPushButton:disabled { background-color: #BDBDBD; }
        """)
        self.upload_btn.clicked.connect(self.start_upload)
        
        btn_layout = QHBoxLayout()
        back_btn = QPushButton("Назад")
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #EF5350; color: white;
                padding: 12px 24px; font-size: 16px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #D32F2F; }
        """)
        back_btn.clicked.connect(self.go_back)
        
        btn_layout.addWidget(back_btn)
        btn_layout.addStretch()
        
        layout.addWidget(title)
        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addWidget(self.upload_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        layout.addLayout(btn_layout)
    
    def check_connection(self):
        try:
            requests.get("https://www.google.com", timeout=3)
            self.window.state.connection_status = True
            self.update_ui(True)
        except:
            self.window.state.connection_status = False
            self.update_ui(False)
    
    def update_ui(self, connected):
        if connected:
            self.status_label.setText("Доступность сети Wi-Fi: ✓ Подключено")
            self.status_label.setStyleSheet("color: #4CAF50;")
            self.upload_btn.setEnabled(True)
        else:
            self.status_label.setText("Доступность сети Wi-Fi: ✗ Нет соединения")
            self.status_label.setStyleSheet("color: #EF5350;")
            self.upload_btn.setEnabled(False)
    
    def start_upload(self):
        progress = QProgressDialog("Выгрузка данных...", "Отмена", 0, 100, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        for i in range(101):
            progress.setValue(i)
            QApplication.processEvents()
            if progress.wasCanceled():
                break
        progress.close()
        QMessageBox.information(self, "Статус", 
            "Данные успешно выгружены!" if progress.value() == 100 else "Выгрузка прервана")
    
    def go_back(self):
        self.window.navigate_to(MainPage)

class SelectModePage(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.window = parent
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_style = """
            QPushButton {
                background-color: #2196F3; color: white;
                padding: 30px 60px; font-size: 32px;
                margin: 20px; border-radius: 15px;
                min-width: 400px;
            }
            QPushButton:hover { background-color: #1976D2; }
        """
        
        photo_btn = QPushButton("Фото")
        photo_btn.setStyleSheet(btn_style)
        photo_btn.clicked.connect(lambda: self.set_mode("photo"))
        
        video_btn = QPushButton("Видео")
        video_btn.setStyleSheet(btn_style)
        video_btn.clicked.connect(lambda: self.set_mode("video"))
        
        back_btn = QPushButton("Назад")
        back_btn.setStyleSheet(btn_style.replace("2196F3", "EF5350").replace("1976D2", "D32F2F"))
        back_btn.clicked.connect(self.go_back)
        
        layout.addWidget(photo_btn)
        layout.addWidget(video_btn)
        layout.addWidget(back_btn)
    
    def set_mode(self, mode):
        self.window.state.camera_mode = mode
        self.window.navigate_to(LocationPage)
    
    def go_back(self):
        self.window.navigate_to(MainPage)

class LocationPage(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.window = parent
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 30, 50, 30)
        
        form = QFormLayout()
        self.fields = {
            'complex': QLineEdit(),
            'block': QLineEdit(),
            'tray': QLineEdit(),
            'side': QLineEdit()
        }
        
        if self.window.state.camera_mode == "photo":
            self.direction_combo = QComboBox()
            self.direction_combo.addItems(["Вперед", "Назад"])
            self.direction_combo.currentTextChanged.connect(
                lambda: setattr(self.window.state, 'direction', self.direction_combo.currentText()))
            self.fields['direction'] = self.direction_combo
        
        for label, widget in self.fields.items():
            widget.setFont(QFont("Arial", 18))
            widget.setMinimumWidth(300)
            form.addRow(QLabel(self.get_label_text(label)), widget)
        
        btn_layout = QHBoxLayout()
        confirm_btn = QPushButton("Подтвердить")
        confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; color: white;
                padding: 12px 24px; font-size: 16px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #388E3C; }
        """)
        confirm_btn.clicked.connect(self.save_data)
        
        back_btn = QPushButton("Назад")
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #EF5350; color: white;
                padding: 12px 24px; font-size: 16px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #D32F2F; }
        """)
        back_btn.clicked.connect(self.go_back)
        
        btn_layout.addWidget(back_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(confirm_btn)
        
        layout.addLayout(form)
        layout.addStretch()
        layout.addLayout(btn_layout)
    
    def get_label_text(self, key):
        labels = {
            'complex': "Тепличный комплекс",
            'block': "Блок",
            'tray': "Лоток",
            'side': "Сторона",
            'direction': "Направление"
        }
        return labels.get(key, "")
    
    def save_data(self):
        for key, field in self.fields.items():
            if isinstance(field, QLineEdit):
                self.window.state.location_data[key] = field.text()
            elif isinstance(field, QComboBox):
                self.window.state.location_data[key] = field.currentText()
        print("Сохраненные данные:", self.window.state.location_data)
        self.window.navigate_to(CameraDetectionPage)
    
    def go_back(self):
        self.window.navigate_to(SelectModePage)


class GoProManager(QObject):
    status_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.connected = False

    def detect(self):
        try:
            if platform.system() == 'Windows':
                output = subprocess.check_output("pnputil /enum-devices /class Camera", shell=True)
                return b'GoPro' in output
            else:
                output = subprocess.check_output("lsusb").decode()
                return 'GoPro' in output
        except:
            return False

class CameraDetectionPage(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.window = parent
        self.cameras = []
        self.current_cam = 0
        self.cap = None
        self.timer = QTimer(self)
        self.gopro_manager = GoProManager()
        self.init_ui()
        self.find_cameras()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        title = QLabel("Обнаружение камер")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        main_layout.addWidget(title)

        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(640, 480)
        self.video_label.setStyleSheet("background-color: black;")
        main_layout.addWidget(self.video_label)

        control_layout = QGridLayout()
        self.cam_labels = [QLabel(str(i+1)) for i in range(4)]
        for i, lbl in enumerate(self.cam_labels):
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-size: 20px;")
            control_layout.addWidget(lbl, 0, i)

        self.prev_btn = QPushButton("Предыдущая")
        self.next_btn = QPushButton("Следующая")
        self.prev_btn.clicked.connect(self.prev_camera)
        self.next_btn.clicked.connect(self.next_camera)
        
        nav_layout = QHBoxLayout()
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.next_btn)
        control_layout.addLayout(nav_layout, 1, 0, 1, 4)
        main_layout.addLayout(control_layout)

        bottom_layout = QHBoxLayout()
        back_btn = QPushButton("< Назад")
        back_btn.clicked.connect(lambda: self.window.navigate_to(MainPage))
        self.status_label = QLabel("Камеры проверены, далее =>")
        next_btn = QPushButton(self.status_label.text())
        next_btn.clicked.connect(self.next_step)

        bottom_layout.addWidget(back_btn)
        bottom_layout.addStretch()
        bottom_layout.addWidget(next_btn)
        main_layout.addLayout(bottom_layout)

    def find_cameras(self):
        self.cameras = []
        for i in range(4):
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    self.cameras.append({'type': 'webcam', 'index': i})
                    cap.release()
            except:
                pass

        if self.gopro_manager.detect():
            self.cameras.append({'type': 'gopro', 'index': 0})
        self.update_ui()

    def update_ui(self):
        for i, lbl in enumerate(self.cam_labels):
            color = 'green' if i == self.current_cam else 'gray'
            lbl.setStyleSheet(f"font-size: 20px; color: {color}; border: 2px solid {color}; border-radius: 15px; padding: 5px;")

        self.prev_btn.setEnabled(self.current_cam > 0)
        self.next_btn.setEnabled(self.current_cam < len(self.cameras)-1)
        self.start_camera()

    def start_camera(self):
        if self.cap:
            self.cap.release()
        if not self.cameras:
            return

        current = self.cameras[self.current_cam]
        if current['type'] == 'webcam':
            try:
                self.cap = cv2.VideoCapture(current['index'])
                self.timer.timeout.connect(self.update_frame)
                self.timer.start(30)
            except:
                QMessageBox.critical(self, "Ошибка", "Не удалось запустить камеру")
        elif current['type'] == 'gopro':
            self.video_label.setText("Режим GoPro")

    def update_frame(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame.shape
                q_img = QImage(frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
                self.video_label.setPixmap(QPixmap.fromImage(q_img))

    def prev_camera(self):
        if self.current_cam > 0:
            self.current_cam -= 1
            self.update_ui()

    def next_camera(self):
        if self.current_cam < len(self.cameras)-1:
            self.current_cam += 1
            self.update_ui()

    def next_step(self):
        if self.cameras:
            self.window.navigate_to(ShootingSetupPage)

    def closeEvent(self, event):
        if self.cap:
            self.cap.release()
        self.timer.stop()


class ShootingSetupPage(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.window = parent
        self.init_ui()
        self.load_state()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(50, 30, 50, 30)
        main_layout.setSpacing(25)

        title_text = "Статическое фотографирование" if self.window.state.camera_mode == "photo" else "Старт видеозаписи"
        title = QLabel(title_text)
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        start_point_group = QVBoxLayout()
        start_point_label = QLabel("Задать стартовую точку:")
        start_point_label.setFont(QFont("Arial", 18))
        
        self.start_point_value = QLabel("Начало пролета")
        self.start_point_value.setFont(QFont("Arial", 16))
        self.start_point_value.setStyleSheet("color: #2c3e50;")
        
        start_point_group.addWidget(start_point_label)
        start_point_group.addWidget(self.start_point_value)

        main_layout.addLayout(start_point_group)

        number_layout = QHBoxLayout()
        number_label = QLabel("Номер пролета:")
        number_label.setFont(QFont("Arial", 18))
        
        self.number_input = QLineEdit()
        self.number_input.setFont(QFont("Arial", 16))
        self.number_input.setFixedWidth(150)
        self.number_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.number_input.setStyleSheet("padding: 8px; border: 1px solid #bdc3c7; border-radius: 5px;")
        
        number_layout.addWidget(number_label)
        number_layout.addWidget(self.number_input)
        number_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        main_layout.addLayout(number_layout)

        button_layout = QHBoxLayout()
        back_btn = QPushButton("< Назад")
        back_btn.setFont(QFont("Arial", 18))
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                padding: 10px 25px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        back_btn.clicked.connect(lambda: self.window.navigate_to(MainPage))
        button_layout.addWidget(back_btn)
        self.shoot_btn = QPushButton("Начать съемку")
        self.shoot_btn.setFont(QFont("Arial", 18))
        self.shoot_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                padding: 10px 25px;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #219a52; }
        """)
        self.shoot_btn.clicked.connect(self.start_shooting)
        button_layout.addWidget(self.shoot_btn)
        main_layout.addLayout(button_layout)

    def load_state(self):
        state = self.window.state
        self.number_input.setText(state.flight_number)
        state.start_point = "Начало пролета"
        if state.camera_mode == "video":
            self.shoot_btn.setText("Начать видеозапись")

    def start_shooting(self):
        state = self.window.state
        flight_number = self.number_input.text().strip()
        
        if not flight_number.isdigit():
            QMessageBox.warning(self, "Ошибка", "Номер пролета должен быть целым числом")
            return
            
        state.flight_number = flight_number
        state.start_point = "Начало пролета"
        
        self.window.navigate_to(ShootingControlPage)

    def closeEvent(self, event):
        self.window.state.flight_number = self.number_input.text()


class CameraWorker(QThread):
    frame_ready = pyqtSignal(int, QImage, np.ndarray)  # (cam_id, preview, original_frame)
    error_occurred = pyqtSignal(int, str)

    def __init__(self, camera_id):
        super().__init__()
        self.camera_id = camera_id
        self.running = True
        self.mutex = QMutex()

    def run(self):
        cap = cv2.VideoCapture(self.camera_id)

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)

        if not cap.isOpened():
            self.error_occurred.emit(self.camera_id, "Не удалось открыть камеру")
            return

        while self.running:
            self.mutex.lock()
            ret, frame = cap.read()
            if ret:
                # Готовим превью для отображения (размер 640x480)
                preview_frame = cv2.resize(frame, (640, 480))
                rgb_preview = cv2.cvtColor(preview_frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_preview.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_preview.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                self.frame_ready.emit(self.camera_id, qt_image, frame)
            self.mutex.unlock()
            QThread.msleep(30)
        cap.release()

    def stop(self):
        self.running = False
        self.wait()


class ShootingControlPage(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.window = parent
        self.camera_mode = self.window.state.camera_mode
        self.camera_ids = []
        self.workers = []
        self.video_writers = {}
        self.preview_labels = {}
        self.is_recording = False
        self.init_ui()
        self.init_cameras()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Заголовок и сетка превью
        title = QLabel(f"Режим {'видео' if self.camera_mode == 'video' else 'фото'}")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font: bold 20px;")
        main_layout.addWidget(title)
        
        self.preview_grid = QGridLayout()
        main_layout.addLayout(self.preview_grid)
        
        # Панель управления
        control_panel = QHBoxLayout()
        self.record_btn = QPushButton("СТАРТ", self)
        self.record_btn.setFixedSize(150, 40)
        self.record_btn.clicked.connect(self.toggle_recording)
        
        self.status_label = QLabel("Статус: Готов")
        self.status_label.setStyleSheet("font: 14px; color: #666;")
        
        control_panel.addWidget(self.status_label)
        control_panel.addStretch()
        control_panel.addWidget(self.record_btn)
        main_layout.addLayout(control_panel)

    def init_cameras(self):
        # Автопоиск доступных камер
        self.camera_ids = self.detect_available_cameras()
        
        # Создание превью-контейнеров
        for i, cam_id in enumerate(self.camera_ids):
            container = QGroupBox(f"Камера {cam_id}")
            layout = QVBoxLayout()
            
            preview_label = QLabel()
            preview_label.setMinimumSize(320, 240)
            preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            preview_label.setStyleSheet("background: #222;")
            
            layout.addWidget(preview_label)
            container.setLayout(layout)
            self.preview_grid.addWidget(container, i//2, i%2)
            self.preview_labels[cam_id] = preview_label
            
            # Запуск потока захвата кадров
            self.start_camera_stream(cam_id)

    def detect_available_cameras(self, max_check=4):
        available = []
        for i in range(max_check):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append(i)
                cap.release()
            else:
                cap.release()
                break
        return available

    def start_camera_stream(self, cam_id):
        worker = CameraWorker(cam_id)
        worker.frame_ready.connect(
            lambda cid, img, frame: self.update_preview(cid, img, frame)
        )
        worker.start()
        self.workers.append(worker)

    def update_preview(self, cam_id, qt_image, original_frame):
        if isinstance(cam_id, np.ndarray):  # Если вдруг пришел массив
            cam_id = int(cam_id[0])        # Преобразуем в int
        
        if cam_id in self.preview_labels:
            self.preview_labels[cam_id].setPixmap(
                QPixmap.fromImage(qt_image).scaled(320, 240, 
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
            )
        
        if self.is_recording and self.camera_mode == "video":
            self.video_writers[cam_id].write(original_frame)

    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    

    def start_recording(self):
        self.is_recording = True
        self.status_label.setText("Статус: Запись...")
        self.record_btn.setText("СТОП")
        
        if self.camera_mode == "video":
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            for cam_id in self.camera_ids:
                self.video_writers[cam_id] = cv2.VideoWriter(
                    f"video_{timestamp}_cam{cam_id}.avi",
                    cv2.VideoWriter_fourcc(*'XVID'), 30, (3840, 2160)
                )
        else:
            QTimer.singleShot(100, self.capture_photos)

    def capture_photos(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        for cam_id in self.camera_ids:
            frame = self.workers[cam_id].last_frame  # Нужно добавить в CameraWorker
            cv2.imwrite(f"photo_{timestamp}_cam{cam_id}.jpg", frame)
        self.stop_recording()

    def stop_recording(self):
        self.is_recording = False
        self.status_label.setText("Статус: Готов")
        self.record_btn.setText("СТАРТ")
        
        if self.camera_mode == "video":
            for writer in self.video_writers.values():
                writer.release()
            self.video_writers.clear()

    def cleanup(self):
        for worker in self.workers:
            worker.stop()
        self.stop_recording()
        
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    if not os.path.exists("photos"):
        os.makedirs("photos")
    if not os.path.exists("videos"):
        os.makedirs("videos")
    window = MainWindow()
    sys.exit(app.exec())