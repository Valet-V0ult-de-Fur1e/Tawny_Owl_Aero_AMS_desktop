from datetime import datetime
import sys
import os
import requests
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QDateTime, QThread, QMutex
from PySide6.QtGui import QFont
import cv2
import platform
import subprocess
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
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
        self.flight_number = 1
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
    status_changed = Signal(str)

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
        self.number_input.setText(str(state.flight_number))
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


from PySide6.QtWidgets import *
from PySide6.QtCore import Qt, QThread, QMutex, QMutexLocker, Signal
from PySide6.QtGui import QImage, QPixmap
import cv2
import os
import numpy as np
from datetime import datetime

class ShootingControlPage(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.stop_count = 0
        self.recording_paused = False
        self.session_folder = ""
        self.window = parent
        self.camera_mode = self.window.state.camera_mode
        self.camera_ids = []
        self.workers = []
        self.video_writers = {}
        self.preview_labels = {}
        self.is_recording = False
        self.preview_mutex = QMutex()  # Мьютекс для синхронизации превью
        self.selected_point = self.window.state.flight_number
        self.count_try = 1
        self.create_session_folder(self.selected_point)
        self.init_ui()
        self.init_cameras()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        
        title = QLabel(f"Режим {'видео' if self.camera_mode == 'video' else 'фото'}")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font: bold 20px;")
        main_layout.addWidget(title)
        
        if self.camera_mode != "video":
            params_layout_point = QHBoxLayout()
            
            self.label_selected_point_count = QLabel("Выбран пролёт")
            
            self.selected_point_count_input = QLineEdit(str(self.selected_point))
            self.selected_point_count_input.textChanged.connect(self.updated_point_l)
            
            self.button_update = QPushButton("+")
            self.button_update.clicked.connect(self.updated_point_b)
            
            params_layout_point.addWidget(self.label_selected_point_count)
            params_layout_point.addWidget(self.selected_point_count_input)
            params_layout_point.addWidget(self.button_update)
            main_layout.addLayout(params_layout_point)

            params_layout_count = QHBoxLayout()

            self.count_try_label_1 = QLabel("Остановок на пролёте")
            self.count_try_label_2 = QLabel(f"{self.count_try}")

            params_layout_count.addWidget(self.count_try_label_1)
            params_layout_count.addWidget(self.count_try_label_2)

            main_layout.addLayout(params_layout_count)

        self.preview_grid = QGridLayout()
        main_layout.addLayout(self.preview_grid)
        
        self.init_control_panel(main_layout)
    
    def updated_point_l(self, text):
        print(self.selected_point_count_input.text)
        self.create_session_folder(self.selected_point)
        if str(text).isdigit():
            self.selected_point = int(text)
            self.count_try = 1
            self.count_try_label_2.setText("1")
        else:
            QMessageBox.critical(self, "Ошибка", f"Введёно не число")

    def updated_point_b(self):
        self.create_session_folder(self.selected_point)
        self.selected_point = int(self.selected_point)
        self.selected_point += 1
        self.count_try = 1
        self.count_try_label_2.setText("1")
        self.selected_point_count_input.setText(str(self.selected_point))
    
    def init_control_panel(self, main_layout):
        control_layout = QHBoxLayout()
        
        back_btn = QPushButton("Назад")
        back_btn.setFixedSize(100, 40)
        back_btn.clicked.connect(self.return_to_main)
        
        
        mode_btn_layout = QHBoxLayout()
        
        if self.camera_mode == "video":
            self.record_btn = QPushButton("Запись")
            self.pause_btn = QPushButton("Пауза")
            self.finish_btn = QPushButton("Закончить съёмку")
            
            self.record_btn.setStyleSheet("background-color: #27ae60; color: white;")
            self.pause_btn.setStyleSheet("background-color: #f1c40f; color: black;")
            self.finish_btn.setStyleSheet("background-color: #e74c3c; color: white;")
            
            self.record_btn.clicked.connect(self.start_recording)
            self.pause_btn.clicked.connect(self.toggle_pause)
            self.finish_btn.clicked.connect(self.finish_recording)
            
            mode_btn_layout.addWidget(self.record_btn)
            mode_btn_layout.addWidget(self.pause_btn)
            mode_btn_layout.addWidget(self.finish_btn)
            
            self.pause_btn.setEnabled(False)
            self.finish_btn.setEnabled(False)
            
        else: 
            self.shoot_btn = QPushButton("Сделать фото")
            self.finish_btn = QPushButton("Закончить съёмку")
            
            self.shoot_btn.setStyleSheet("background-color: #27ae60; color: white;")
            self.finish_btn.setStyleSheet("background-color: #e74c3c; color: white;")
            
            self.shoot_btn.clicked.connect(self.capture_photos)
            self.finish_btn.clicked.connect(self.finish_photo_session)
            
            mode_btn_layout.addWidget(self.shoot_btn)
            mode_btn_layout.addWidget(self.finish_btn)

        control_layout.addWidget(back_btn)
        control_layout.addStretch()
        control_layout.addLayout(mode_btn_layout)
        main_layout.addLayout(control_layout)

    def create_session_folder(self, point=1):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        folder_name = "video" if self.camera_mode == "video" else "photo"
        self.session_folder = os.path.join(folder_name, f"session_{timestamp}" if self.camera_mode == "video" else f"session_{timestamp}_point_{point}")
        os.makedirs(self.session_folder, exist_ok=True)
        return timestamp

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
            with QMutexLocker(self.preview_mutex):
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

    def start_recording(self):
        time_start = self.create_session_folder()
        self.is_recording = True
        self.recording_paused = False
        self.record_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.finish_btn.setEnabled(True)
        
        for cam_id in self.camera_ids:
            filename = os.path.join(self.session_folder, f"camera_{cam_id}.avi")
            self.video_writers[cam_id] = cv2.VideoWriter(
                filename, cv2.VideoWriter_fourcc(*'XVID'), 30.0, (1920, 1080))
            with open(os.path.join(self.session_folder, f"session_{cam_id}.json"), 'w') as f:
                json.dump({
                    "greenHouse": self.window.state.location_data['complex'],
                    "block": self.window.state.location_data['block'],
                    "gardenBed": self.window.state.location_data['tray'],
                    "gardenBedSide": self.window.state.location_data['side'],
                    "fileURL": filename,
                    "fileType": "video",
                    "task": "crowns",
                    "createDate": time_start
                }, f)

    def toggle_pause(self):
        self.recording_paused = not self.recording_paused
        self.pause_btn.setText("Продолжить" if self.recording_paused else "Пауза")

    def start_camera_stream(self, cam_id):
        worker = CameraWorker(cam_id)
        worker.frame_ready.connect(self.update_preview)
        worker.start()
        self.workers.append(worker)
    
    def update_preview(self, cam_id, qt_image, original_frame):
        locker = QMutexLocker(self.preview_mutex)  # Блокировка мьютекса
        
        if cam_id in self.preview_labels:
            preview_label = self.preview_labels[cam_id]
            # Проверка на существование виджета
            if preview_label and preview_label.parent() is not None:
                preview_label.setPixmap(
                    QPixmap.fromImage(qt_image).scaled(
                        320, 240, 
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                )
        
        if self.is_recording and self.camera_mode == "video" and not self.recording_paused:
            self.video_writers[cam_id].write(original_frame)

    def finish_recording(self):
        self.is_recording = False
        self.recording_paused = False
        for writer in self.video_writers.values():
            writer.release()
        self.video_writers.clear()
        self.record_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.finish_btn.setEnabled(False)
        self.window.navigate_to(MainPage)

    def get_worker(self, cam_id):
        """Возвращает worker для указанной камеры"""
        for worker in self.workers:
            if worker.camera_id == cam_id:
                return worker
        return None

    def capture_photos(self):
        try:
            self.count_try += 1
            self.count_try_label_2.setText(str(self.count_try))
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            for cam_id in self.camera_ids:
                worker = self.get_worker(cam_id)
                if worker and worker.last_frame is not None:
                    filename = os.path.join(self.session_folder, 
                                          f"photo_{timestamp}_num_{self.count_try}_cam{cam_id}.jpg")
                    cv2.imwrite(filename, worker.last_frame)
                    with open(os.path.join(self.session_folder, f"session_{cam_id}_try_{self.count_try}.json"), 'w') as f:
                        json.dump({
                            "greenHouse": self.window.state.location_data['complex'],
                            "block": self.window.state.location_data['block'],
                            "gardenBed": self.window.state.location_data['tray'],
                            "gardenBedSide": self.window.state.location_data['side'],
                            "gardenBedPoint": self.selected_point,
                            "fileURL": filename,
                            "fileType": "photo",
                            "task": "crowns",
                            "createDate": timestamp
                        }, f)
            
            QMessageBox.information(self, "Успех", f"Фото сохранены в папку:\n{self.session_folder}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении фото: {str(e)}")

    def finish_photo_session(self):
        self.cleanup()
        self.window.navigate_to(MainPage)

    def return_to_main(self):
        self.cleanup()
        self.window.navigate_to(MainPage)

    def cleanup(self):
        for worker in self.workers:
            worker.stop()
        with QMutexLocker(self.preview_mutex):
            self.preview_labels.clear()
        
        if self.camera_mode == "video":
            self.finish_recording()

class CameraWorker(QThread):
    frame_ready = Signal(int, QImage, np.ndarray)
    
    def __init__(self, camera_id):
        super().__init__()
        self.camera_id = camera_id
        self.running = True
        self.last_frame = None
        self.mutex = QMutex()

    def run(self):
        cap = cv2.VideoCapture(self.camera_id)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 3840)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)

        while self.running:
            with QMutexLocker(self.mutex):
                if not self.running:
                    break
                
                ret, frame = cap.read()
                if ret:
                    self.last_frame = frame.copy()
                    preview = cv2.resize(frame, (640, 480))
                    rgb_preview = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb_preview.shape
                    qt_img = QImage(rgb_preview.data, w, h, QImage.Format.Format_RGB888)
                    self.frame_ready.emit(self.camera_id, qt_img, frame)
            QThread.msleep(30)
        
        cap.release()

    def stop(self):
        with QMutexLocker(self.mutex):
            self.running = False
        self.wait()
        
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    if not os.path.exists("photo"):
        os.makedirs("photo")
    if not os.path.exists("video"):
        os.makedirs("video")
    window = MainWindow()
    sys.exit(app.exec())