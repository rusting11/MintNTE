# core/window_detect/window_detect_ui.py
# 窗口检测模块 - 提供窗口拾取、锁定和信息显示功能
# 主要功能：
#   1. 窗口拾取：通过拖动靶心图标获取目标窗口
#   2. 窗口锁定：锁定目标窗口供其他功能使用
#   3. 信息显示：显示窗口句柄、标题、类名、位置、尺寸等信息
#   4. 实时预览：显示目标窗口的实时截图

import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QPushButton
)
from PyQt5.QtCore import Qt, QTimer, QPoint, QEvent, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage, QCursor
import win32gui
import win32con
import win32process
import win32ui
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


class WindowDetectUI(QWidget):
    """
    窗口检测界面类
    
    提供窗口拾取、锁定和信息展示功能，是整个应用的核心模块之一。
    其他功能模块（如钓鱼、键鼠宏等）依赖此模块锁定的窗口句柄进行操作。
    
    Signals:
        show_log_signal: 请求显示日志窗口的信号
    """
    
    show_log_signal = pyqtSignal()
    
    def __init__(self, parent=None):
        """
        初始化窗口检测界面
        
        Args:
            parent: 父窗口对象
        """
        super().__init__(parent)
        
        # ========== 状态变量 ==========
        self.target_hwnd = None          # 当前拾取到的窗口句柄
        self.locked_hwnd = None          # 当前锁定的窗口句柄
        
        # ========== UI资源 ==========
        self.spy_cursor = None           # 自定义拾取光标
        self._init_spy_cursor()
        
        # ========== 动态跟踪窗口 ==========
        self.tracker = None              # 跟踪窗口
        self.drag_active = False         # 是否正在拖动
        
        # ========== 预览相关 ==========
        self.preview_timer = QTimer()    # 预览定时器（新增）
        self.preview_timer.timeout.connect(self.update_preview)
        self.show_preview = True         # 是否显示预览
        
        # ========== 初始化UI ==========
        self.init_ui()
    
    def _init_spy_cursor(self):
        """初始化拾取光标"""
        image_dir = os.path.join(BASE_DIR, "Image", "logo")
        spy_path = os.path.join(image_dir, "Window_Spy.png")
        
        if os.path.exists(spy_path):
            self.spy_cursor = QCursor(
                QPixmap(spy_path).scaled(
                    17, 17, 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
            )
    
    def init_ui(self):
        """初始化界面布局"""
        h_main_layout = QHBoxLayout(self)
        h_main_layout.setContentsMargins(16, 16, 16, 16)
        h_main_layout.setSpacing(20)
        
        left_widget = self._create_left_panel()
        right_widget = self._create_right_panel()
        
        h_main_layout.addWidget(left_widget, stretch=3)
        h_main_layout.addWidget(right_widget, stretch=2)
    
    def _create_left_panel(self):
        """创建左侧面板 - 包含操作指引、锁定控制和窗口信息"""
        left_widget = QFrame(self)
        left_widget.setObjectName("LeftPanel")
        
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(16, 16, 16, 16)
        left_layout.setSpacing(20)
        
        guide_card = self._create_guide_card()
        left_layout.addWidget(guide_card)
        
        lock_card = self._create_lock_card()
        left_layout.addWidget(lock_card)
        
        info_panel = self._create_info_panel()
        left_layout.addWidget(info_panel)
        
        return left_widget
    
    def _create_guide_card(self):
        """创建操作指引卡片"""
        guide_container = QFrame()
        guide_container.setObjectName("GuideCard")
        
        guide_layout = QVBoxLayout(guide_container)
        guide_layout.setContentsMargins(16, 16, 16, 16)
        guide_layout.setSpacing(16)
        
        self.icon_frame = QFrame()
        self.icon_frame.setFixedSize(180, 100)
        
        image_dir = os.path.join(BASE_DIR, "Image", "logo")
        bg_path = os.path.join(image_dir, "Window_Picker.png")
        
        self.bg_label = QLabel(self.icon_frame)
        if os.path.exists(bg_path):
            self.bg_label.setPixmap(
                QPixmap(bg_path).scaled(
                    40, 40, 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
            )
        self.bg_label.setGeometry(70, 30, 40, 40)
        
        spy_path = os.path.join(image_dir, "Window_Spy.png")
        self.spy_static = QLabel(self.icon_frame)
        
        if os.path.exists(spy_path):
            self.spy_static.setPixmap(
                QPixmap(spy_path).scaled(
                    20, 20, 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
            )
        else:
            self.spy_static.setText("+")
        
        self.spy_static.setGeometry(80, 40, 20, 20)
        self.spy_static.setCursor(Qt.CrossCursor)
        self.spy_static.mousePressEvent = self.on_spy_press
        self.spy_static.setMouseTracking(True)
        
        guide_layout.addWidget(self.icon_frame, alignment=Qt.AlignCenter)
        
        hint_text = (
            "<span style='color: rgba(0, 220, 180, 0.9); font-size: 15px; font-weight: 600;'>"
            "🎯 窗口检测操作指引</span>\n\n"
            "<span style='color: rgba(180, 210, 240, 0.8); font-size: 13px;'>"
            "① 按住右侧“靶心”拖到游戏窗口\n"
            "② 松开后自动获取窗口信息与截图\n"
            "③ 点击“锁定窗口”按钮即可开始\n\n"
            "<span style='color: rgba(255, 180, 100, 0.7);'>"
            "🧣 锁定后钓鱼、宏等功能可后台操作</span></span>"
        )
        
        hint_label = QLabel(hint_text)
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setWordWrap(True)
        guide_layout.addWidget(hint_label)
        
        return guide_container
    
    def _create_lock_card(self):
        """创建锁定控制卡片"""
        lock_container = QFrame()
        lock_container.setObjectName("LockCard")
        
        lock_layout = QHBoxLayout(lock_container)
        lock_layout.setContentsMargins(16, 12, 16, 12)
        lock_layout.setSpacing(16)
        
        status_layout = QVBoxLayout()
        
        status_label = QLabel("锁定状态")
        status_label.setObjectName("StatusLabel")
        
        self.lock_status_label = QLabel("未锁定")
        self.lock_status_label.setObjectName("LockStatus")
        
        status_layout.addWidget(status_label)
        status_layout.addWidget(self.lock_status_label)
        lock_layout.addLayout(status_layout)
        
        lock_layout.addStretch()
        
        self.btn_lock = QPushButton("锁定窗口")
        self.btn_lock.clicked.connect(self.toggle_lock)
        lock_layout.addWidget(self.btn_lock)
        
        self.btn_log = QPushButton("显示日志")
        self.btn_log.setObjectName("LogButton")
        self.btn_log.clicked.connect(self.show_log_signal.emit)
        lock_layout.addWidget(self.btn_log)
        
        return lock_container
    
    def _create_info_panel(self):
        """创建窗口信息面板（双列布局）"""
        info_group = QFrame()
        info_group.setObjectName("InfoGroup")
        
        group_layout = QVBoxLayout(info_group)
        group_layout.setContentsMargins(16, 16, 16, 16)
        group_layout.setSpacing(16)
        
        title_label = QLabel("窗口信息")
        title_label.setObjectName("InfoGroupTitle")
        group_layout.addWidget(title_label)
        
        grid_layout = QGridLayout()
        grid_layout.setHorizontalSpacing(12)
        grid_layout.setVerticalSpacing(24)
        grid_layout.setColumnMinimumWidth(0, 70)
        grid_layout.setColumnMinimumWidth(1, 160)
        grid_layout.setColumnMinimumWidth(2, 70)
        grid_layout.setColumnMinimumWidth(3, 160)
        
        self.fields = {}
        field_list = [
            ("句柄", "handle"),
            ("标题", "title"),
            ("类名", "class_name"),
            ("位置X", "pos_x"),
            ("位置Y", "pos_y"),
            ("宽度", "width"),
            ("高度", "height"),
            ("进程ID", "pid"),
            ("进程名", "process_name"),
            ("风格", "style"),
            ("扩展风格", "ex_style"),
        ]
        
        for i, (label_text, field_key) in enumerate(field_list):
            row = i // 2
            col = i % 2
            
            label_widget = QLabel(f"{label_text}:")
            label_widget.setObjectName("InfoLabel")
            
            field_edit = QLineEdit()
            field_edit.setReadOnly(True)
            field_edit.setObjectName("InfoField")
            field_edit.setFixedHeight(30)
            
            self.fields[field_key] = field_edit
            
            grid_layout.addWidget(label_widget, row, col * 2)
            grid_layout.addWidget(field_edit, row, col * 2 + 1)
        
        group_layout.addLayout(grid_layout)
        
        return info_group
    
    def _create_right_panel(self):
        """创建右侧面板 - 包含窗口预览"""
        right_widget = QFrame(self)
        right_widget.setObjectName("RightPanel")
        
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(16, 16, 16, 16)
        right_layout.setSpacing(16)
        
        preview_card = QFrame()
        preview_card.setObjectName("PreviewCard")
        
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        
        self.preview_label = QLabel()
        self.preview_label.setMinimumSize(300, 200)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setObjectName("PreviewLabel")
        preview_layout.addWidget(self.preview_label)
        
        right_layout.addWidget(preview_card)
        
        # 保留用户的按钮
        self.btn_capture = QPushButton("点击获取最新游戏界面")
        self.btn_capture.clicked.connect(self.capture_single_frame)
        right_layout.addWidget(self.btn_capture, alignment=Qt.AlignCenter)
        
        return right_widget
    
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
        spy_path = os.path.join(BASE_DIR, "Image", "logo", "Window_Spy.png")
        
        if os.path.exists(spy_path):
            label.setPixmap(
                QPixmap(spy_path).scaled(
                    17, 17, 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
            )
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
        if not self.drag_active:
            return super().eventFilter(obj, event)
        
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
                self.start_preview()  # 启动实时预览（修改这里）
                logui.info(f"拾取窗口: {win32gui.GetWindowText(self.target_hwnd)}")
            else:
                self.stop_preview()
            
            return True
        
        return super().eventFilter(obj, event)
    
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
                except Exception:
                    pname = "N/A"
            else:
                pname = "(需安装psutil)"
            
            self.fields["process_name"].setText(pname)
            
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            self.fields["style"].setText(f"0x{style:08X}")
            self.fields["ex_style"].setText(f"0x{ex_style:08X}")
        
        except Exception as e:
            logui.error(f"更新窗口信息失败: {e}")
    
    # ========== 预览功能（修改部分） ==========
    
    def capture_single_frame(self):
        """捕获单帧截图（保留用户的按钮功能）"""
        self.update_preview()
    
    def start_preview(self):
        """启动实时预览（新增）"""
        if not self.preview_timer.isActive() and self.show_preview:
            self.preview_timer.start(100)  # 100ms间隔更新
    
    def stop_preview(self):
        """停止实时预览（新增）"""
        self.preview_timer.stop()
        self.preview_label.clear()
    
    def update_preview(self):
        """更新预览画面"""
        if not self.target_hwnd or not win32gui.IsWindow(self.target_hwnd):
            self.preview_label.setText("窗口已关闭")
            self.stop_preview()
            return
        try:
            rect = win32gui.GetClientRect(self.target_hwnd)
            left, top, right, bottom = rect
            width = right - left
            height = bottom - top
            if width <= 0 or height <= 0:
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
                    img = img.resize((nw, nh), Image.Resampling.LANCZOS);
                    qim = QImage(img.tobytes(), nw, nh, QImage.Format_RGB888)
                    self.preview_label.setPixmap(QPixmap.fromImage(qim))
            else:
                self.preview_label.setText("截图失败（窗口可能最小化）")
            win32gui.DeleteObject(bitmap.GetHandle())
            save_dc.DeleteDC()
            mfc_dc.DeleteDC()
            win32gui.ReleaseDC(self.target_hwnd, hwnd_dc)
        except Exception as e:
            self.preview_label.setText(f"预览异常: {e}")
    
    def closeEvent(self, event):
        if self.drag_active:
            QApplication.instance().removeEventFilter(self)
            if self.tracker:
                self.tracker.close()
            
            while QApplication.overrideCursor() is not None:
                QApplication.restoreOverrideCursor()
        
        self.preview_timer.stop()
        
        event.accept()
