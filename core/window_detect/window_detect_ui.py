# core/window_detect/window_detect_ui.py
import sys, os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QGroupBox, QLineEdit,
    QVBoxLayout, QHBoxLayout, QFormLayout, QFrame, QPushButton
)
from PyQt5.QtCore import Qt, QTimer, QPoint, QEvent
from PyQt5.QtGui import QPixmap, QImage, QCursor
import win32gui, win32con, win32process, win32ui
from ctypes import windll
from PIL import Image

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from UI import logui
from Module.Hwnd.game_hwnd import set_locked_hwnd, clear_locked_hwnd

IMAGE_DIR = os.path.join(BASE_DIR, "Image", "logo")
BG_PATH = os.path.join(IMAGE_DIR, "Window_Picker.png")
SPY_PATH = os.path.join(IMAGE_DIR, "Window_Spy.png")

class WindowDetectUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.target_hwnd = None          # 当前拾取到的窗口句柄
        self.locked_hwnd = None          # 当前锁定的句柄

        self.spy_cursor = None
        if os.path.exists(SPY_PATH):
            self.spy_cursor = QCursor(
                QPixmap(SPY_PATH).scaled(17, 17, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

        # 动态跟踪窗口（仅在拖动期间存在）
        self.tracker = None
        self.drag_active = False

        self.init_ui()

    def init_ui(self):
        h_main_layout = QHBoxLayout(self)
        h_main_layout.setContentsMargins(5, 5, 5, 5)

        # ========== 左侧：靶心区域 + 锁定 + 信息 ==========
        left_widget = QFrame(self)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(10, 10, 10, 10)

        # 图标 + 指引
        self.icon_frame = QFrame()
        self.icon_frame.setFixedSize(200, 120)
        self.icon_frame.setStyleSheet("background: transparent;")

        # 背景图（白底）
        self.bg_label = QLabel(self.icon_frame)
        if os.path.exists(BG_PATH):
            self.bg_label.setPixmap(QPixmap(BG_PATH).scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.bg_label.setStyleSheet("background: white; border: 1px solid gray;")
        self.bg_label.setGeometry(84, 44, 32, 32)
        self.bg_label.setStyleSheet("background: white;")

        # 静态靶心（可拖动）
        self.spy_static = QLabel(self.icon_frame)
        if os.path.exists(SPY_PATH):
            self.spy_static.setPixmap(QPixmap(SPY_PATH).scaled(17, 17, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.spy_static.setText("+")
            self.spy_static.setStyleSheet("color: red; font-weight: bold;")
        self.spy_static.setGeometry(91, 51, 17, 17)
        self.spy_static.setCursor(Qt.CrossCursor)
        self.spy_static.mousePressEvent = self.on_spy_press
        self.spy_static.setMouseTracking(True)

        icon_container = QVBoxLayout()
        icon_container.addWidget(self.icon_frame, alignment=Qt.AlignCenter)

        hint = QLabel(
            "🎯 窗口检测操作指引⬆️\n\n"
            "① 按住右侧“靶心”拖到游戏窗口\n"
            "② 松开后自动获取窗口信息与截图\n"
            "③ 点击“锁定窗口”按钮即可开始\n\n"
            "🧣 锁定后钓鱼、宏等功能可后台操作"
        )
        hint.setAlignment(Qt.AlignCenter)
        hint.setStyleSheet(
            "color: #00ffcc; font-size: 13pt; "
            "font-family: 'Microsoft YaHei'; "
            "background: transparent; padding: 10px;"
        )
        icon_container.addWidget(hint)
        left_layout.addLayout(icon_container)

        # 锁定控制区
        lock_layout = QHBoxLayout()
        self.lock_status_label = QLabel("未锁定")
        self.lock_status_label.setStyleSheet("color: #ff8800; font-weight: bold;")
        lock_layout.addWidget(self.lock_status_label)

        self.btn_lock = QPushButton("锁定窗口")
        self.btn_lock.setObjectName("NeonButton")
        self.btn_lock.clicked.connect(self.toggle_lock)
        lock_layout.addWidget(self.btn_lock)
        lock_layout.addStretch()
        left_layout.addLayout(lock_layout)

        # 窗口信息面板
        info_group = QGroupBox(" 窗口信息 ")
        info_group.setObjectName("infoGroup")
        form = QFormLayout()
        form.setSpacing(2)
        self.fields = {}
        field_list = [
            ("句柄", "handle"), ("标题", "title"), ("类名", "class_name"),
            ("位置X", "pos_x"), ("位置Y", "pos_y"), ("宽度", "width"),
            ("高度", "height"), ("进程ID", "pid"), ("进程名", "process_name"),
            ("风格", "style"), ("扩展风格", "ex_style"),
        ]
        for label, key in field_list:
            ledit = QLineEdit()
            ledit.setReadOnly(True)
            ledit.setStyleSheet("background: #0a0a1a; color: #00ffcc; border: 1px solid #00ccff; padding: 2px;")
            self.fields[key] = ledit
            form.addRow(QLabel(f"{label}:"), ledit)
        info_group.setLayout(form)
        left_layout.addWidget(info_group)

        # ========== 右侧预览 ==========
        right_widget = QFrame(self)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 10, 10, 10)
        self.preview_label = QLabel()
        self.preview_label.setMinimumSize(200, 150)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("background-color: #000; border: 1px solid #0ff;")
        right_layout.addWidget(self.preview_label)

        # 实时画面显示
        self.btn_capture = QPushButton("点击获取最新游戏界面")
        self.btn_capture.setObjectName("NeonButton")
        self.btn_capture.clicked.connect(self.capture_single_frame)
        right_layout.addWidget(self.btn_capture, alignment=Qt.AlignCenter)

        h_main_layout.addWidget(left_widget, stretch=3)
        h_main_layout.addWidget(right_widget, stretch=2)

        self.setStyleSheet("""
            QWidget { background: transparent; font-family: "Microsoft YaHei", "Segoe UI"; }
            QGroupBox {
                color: #00ddff; font-weight: bold; border: 1px solid #00aaff;
                border-radius: 6px; margin-top: 10px; padding-top: 10px;
                background: rgba(0,0,30,255);
            }
            QGroupBox::title {
                subcontrol-origin: margin; subcontrol-position: top left;
                padding: 0 8px; color: #00ffff;
            }
            QLabel { color: #ccddff; background: transparent; }
            QLineEdit {
                background: #0a0a1a; color: #00ffcc;
                border: 1px solid #00ccff; border-radius: 3px; padding: 2px 4px;
            }
            #NeonButton {
                background-color: #2a2a3a; color: #0ff;
                border: 1px solid #0ff; padding: 6px 15px; border-radius: 4px;
            }
            #NeonButton:hover { background-color: #0ff; color: #1e1e2f; }
        """)

    # ---------- 拖动拾取核心 ----------
    def on_spy_press(self, event):
        if event.button() != Qt.LeftButton:
            return

        self.tracker = QWidget()
        self.tracker.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.tracker.setAttribute(Qt.WA_TranslucentBackground)
        self.tracker.setFixedSize(17, 17)

        label = QLabel(self.tracker)
        if os.path.exists(SPY_PATH):
            label.setPixmap(QPixmap(SPY_PATH).scaled(17, 17, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            label.setText("+")
            label.setStyleSheet("color: red; font-weight: bold; background: transparent;")
        label.setGeometry(0, 0, 17, 17)

        global_pos = QCursor.pos()
        self.tracker.move(global_pos.x() - 8, global_pos.y() - 8)
        self.tracker.show()

        if self.spy_cursor:
            QApplication.setOverrideCursor(self.spy_cursor)

        self.drag_active = True
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        if self.drag_active:
            if event.type() == QEvent.MouseMove:
                global_pos = QCursor.pos()
                if self.tracker:
                    self.tracker.move(global_pos.x() - 8, global_pos.y() - 8)
                return True
            elif event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                self.drag_active = False
                QApplication.instance().removeEventFilter(self)

                if self.tracker:
                    self.tracker.close()
                    self.tracker = None

                while QApplication.overrideCursor() is not None:
                    QApplication.restoreOverrideCursor()

                pt = win32gui.GetCursorPos()
                hwnd = win32gui.WindowFromPoint(pt)
                if hwnd == int(self.winId()):
                    hwnd = None
                self.target_hwnd = hwnd
                self.update_info()

                if self.target_hwnd and win32gui.IsWindow(self.target_hwnd):
                    self.capture_single_frame()          # 只截一帧
                    logui.info(f"拾取窗口: {win32gui.GetWindowText(self.target_hwnd)}")
                else:
                    self.preview_label.clear()
                return True
        return super().eventFilter(obj, event)

    # ---------- 锁定/解除绑定 ----------
    def toggle_lock(self):
        if self.locked_hwnd is None:
            if not self.target_hwnd or not win32gui.IsWindow(self.target_hwnd):
                logui.warning("没有可锁定的窗口，请先拾取一个窗口")
                return
            self.locked_hwnd = self.target_hwnd
            set_locked_hwnd(self.target_hwnd)
            title = win32gui.GetWindowText(self.target_hwnd)
            logui.info(f"锁定窗口: {title} (句柄: {self.target_hwnd})")
            self.lock_status_label.setText(f"已锁定: {title[:20]}")
            self.lock_status_label.setStyleSheet("color: #00ff00; font-weight: bold;")
            self.btn_lock.setText("解除锁定")
        else:
            clear_locked_hwnd()
            logui.info("已解除窗口锁定")
            self.locked_hwnd = None
            self.lock_status_label.setText("未锁定")
            self.lock_status_label.setStyleSheet("color: #ff8800; font-weight: bold;")
            self.btn_lock.setText("锁定窗口")

    # ---------- 窗口信息更新 ----------
    def update_info(self):
        hwnd = self.target_hwnd
        if not hwnd or not win32gui.IsWindow(hwnd):
            return
        try:
            self.fields["handle"].setText(f"0x{hwnd:08X} ({hwnd})")
            title = win32gui.GetWindowText(hwnd)
            self.fields["title"].setText(title)
            cls = win32gui.GetClassName(hwnd)
            self.fields["class_name"].setText(cls)
            x, y, r, b = win32gui.GetWindowRect(hwnd)
            self.fields["pos_x"].setText(str(x))
            self.fields["pos_y"].setText(str(y))
            self.fields["width"].setText(str(r - x))
            self.fields["height"].setText(str(b - y))
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            self.fields["pid"].setText(str(pid))
            if HAS_PSUTIL:
                try:
                    pname = psutil.Process(pid).name()
                except:
                    pname = "N/A"
            else:
                pname = "(需安装psutil)"
            self.fields["process_name"].setText(pname)
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            self.fields["style"].setText(f"0x{style:08X}")
            self.fields["ex_style"].setText(f"0x{ex:08X}")
        except Exception as e:
            logui.error(f"更新窗口信息失败: {e}")

    # ---------- 静态截图（只拍一张） ----------
    def capture_single_frame(self):
        """捕获一张窗口截图并显示在预览区，不启动任何定时器"""
        if not self.target_hwnd or not win32gui.IsWindow(self.target_hwnd):
            self.preview_label.setText("请前往窗口检测→标靶→选择异环→拖动靶心→锁定")
            return
        try:
            rect = win32gui.GetClientRect(self.target_hwnd)
            left, top, right, bottom = rect
            width = right - left
            height = bottom - top
            if width <= 0 or height <= 0:
                self.preview_label.setText("窗口尺寸无效")
                return
            hwnd_dc = win32gui.GetWindowDC(self.target_hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
            save_dc = mfc_dc.CreateCompatibleDC()
            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(bitmap)
            success = windll.user32.PrintWindow(self.target_hwnd, save_dc.GetSafeHdc(), 3)
            if success:
                bi = bitmap.GetInfo()
                buf = bitmap.GetBitmapBits(True)
                img = Image.frombuffer('RGB', (bi['bmWidth'], bi['bmHeight']), buf, 'raw', 'BGRX', 0, 1)
                nw, nh = int(width * 0.3), int(height * 0.3)
                if nw > 0 and nh > 0:
                    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
                    qim = QImage(img.tobytes(), nw, nh, QImage.Format_RGB888)
                    self.preview_label.setPixmap(QPixmap.fromImage(qim))
            else:
                self.preview_label.setText("截图失败（窗口可能最小化）")
            win32gui.DeleteObject(bitmap.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(self.target_hwnd, hwnd_dc)
        except Exception as e:
            self.preview_label.setText(f"截图异常: {e}")

    # 以下方法保留空壳，保持接口兼容
    def start_preview(self):
        pass

    def stop_preview(self):
        pass

    def toggle_preview(self):
        pass

    def update_preview(self):
        pass

    def closeEvent(self, event):
        if self.drag_active:
            QApplication.instance().removeEventFilter(self)
            if self.tracker:
                self.tracker.close()
            while QApplication.overrideCursor() is not None:
                QApplication.restoreOverrideCursor()
        event.accept()