# core/Macro/macro_ui.py
import sys, os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QGroupBox, QTextEdit, QSpinBox
)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer
import win32api, win32gui

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from core.Macro.macro_core import MacroCore
from Module.Hwnd.game_hwnd import get_game_hwnd
from UI import logui

# 尝试导入 keyboard 库（全局热键必需）
try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

class MacroPanel(QWidget):
    signal_toggle_record = pyqtSignal()
    signal_toggle_macro = pyqtSignal()
    signal_save_config = pyqtSignal()
    signal_load_config = pyqtSignal()
    signal_loop_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("异环·后台宏录制/回放")
        self.setup_ui()
        self.apply_style()

        self.core = MacroCore(loop_count=self.spin_loop.value())
        self.connect_signals()

        # 定时刷新当前锁定窗口的句柄
        self.hwnd_timer = QTimer(self)
        self.hwnd_timer.timeout.connect(self.refresh_hwnd)
        self.hwnd_timer.start(1000)
        self.refresh_hwnd()

        # 延迟注册全局热键，避免阻塞启动
        self.hotkey_alt_y = None
        self.hotkey_alt_t = None
        QTimer.singleShot(1000, self._register_global_hotkeys)

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # 目标窗口状态显示
        win_grp = QGroupBox("目标窗口 (来自窗口检测)")
        win_grp.setObjectName("NeonGroup")
        win_layout = QHBoxLayout()
        self.label_hwnd = QLabel("句柄: 未锁定")
        win_layout.addWidget(self.label_hwnd)
        win_grp.setLayout(win_layout)
        layout.addWidget(win_grp)

        # 操作按钮
        btn_layout = QHBoxLayout()
        self.btn_enable = QPushButton("启用宏 (Alt+T)")
        self.btn_enable.setObjectName("NeonButton")
        self.btn_enable.clicked.connect(lambda: self.signal_toggle_macro.emit())
        self.btn_record = QPushButton("开始录制 (Alt+Y)")
        self.btn_record.setObjectName("NeonButton")
        self.btn_record.clicked.connect(lambda: self.signal_toggle_record.emit())
        btn_layout.addWidget(self.btn_enable)
        btn_layout.addWidget(self.btn_record)
        layout.addLayout(btn_layout)

        # 配置区域
        cfg_layout = QHBoxLayout()
        self.btn_save = QPushButton("保存配置")
        self.btn_load = QPushButton("加载配置")
        self.btn_save.clicked.connect(lambda: self.signal_save_config.emit())
        self.btn_load.clicked.connect(lambda: self.signal_load_config.emit())
        cfg_layout.addWidget(self.btn_save)
        cfg_layout.addWidget(self.btn_load)
        cfg_layout.addStretch()
        lbl_loop = QLabel("循环次数:")
        self.spin_loop = QSpinBox()
        self.spin_loop.setRange(1, 9999)
        self.spin_loop.setValue(99)
        self.spin_loop.valueChanged.connect(lambda val: self.signal_loop_changed.emit(val))
        cfg_layout.addWidget(lbl_loop)
        cfg_layout.addWidget(self.spin_loop)
        layout.addLayout(cfg_layout)

        # 宏指令列表
        script_grp = QGroupBox("宏指令列表")
        script_grp.setObjectName("NeonGroup")
        vbox = QVBoxLayout(script_grp)
        self.text_script = QTextEdit()
        self.text_script.setReadOnly(True)
        vbox.addWidget(self.text_script)
        layout.addWidget(script_grp)

        self.status_label = QLabel("就绪")
        layout.addWidget(self.status_label)

    def apply_style(self):
        self.setStyleSheet("""
            QWidget { background-color: #1e1e2f; color: #cccccc; font-size: 12px; }
            #NeonGroup { border: 1px solid #0ff; border-radius: 5px; margin-top: 8px; padding: 5px; }
            #NeonGroup::title { color: #0ff; font-weight: bold; }
            #NeonButton { background-color: #2a2a3a; color: #0f0; border: 1px solid #0f0; border-radius: 5px; padding: 8px; font-weight: bold; }
            #NeonButton:hover { background-color: #0f0; color: #1e1e2f; }
            QTextEdit { background-color: #15151f; color: #0ff; border: none; }
            QLineEdit, QSpinBox { background-color: #2a2a3a; color: #0f0; border: 1px solid #0f0; padding: 3px; }
        """)

    def refresh_hwnd(self):
        hwnd = get_game_hwnd()
        if hwnd:
            title = win32gui.GetWindowText(hwnd)
            self.label_hwnd.setText(f"已锁定: {title[:30]} (句柄: {hwnd})")
        else:
            self.label_hwnd.setText("句柄: 未锁定（请在窗口检测中锁定目标窗口）")

    def connect_signals(self):
        self.signal_toggle_record.connect(self.core.toggle_record)
        self.signal_toggle_macro.connect(self.core.toggle_macro)
        self.signal_save_config.connect(self.core.save_config)
        self.signal_load_config.connect(self._load_config_and_update_ui)
        self.signal_loop_changed.connect(lambda val: setattr(self.core, 'loop_count', val))

        self.core.recording_state_changed.connect(self._on_recording_state, Qt.QueuedConnection)
        self.core.running_state_changed.connect(self._on_running_state, Qt.QueuedConnection)
        self.core.hwnd_updated.connect(self.set_hwnd_label, Qt.QueuedConnection)

    def _load_config_and_update_ui(self):
        success, loop, actions = self.core.load_config()
        if success:
            self.spin_loop.setValue(loop)
            self.update_script_display(actions)

    def _on_recording_state(self, is_recording):
        self.btn_record.setText("停止录制 (Alt+Y)" if is_recording else "开始录制 (Alt+Y)")

    def _on_running_state(self, is_running):
        self.btn_enable.setText("禁用宏 (Alt+T)" if is_running else "启用宏 (Alt+T)")

    def update_script_display(self, actions):
        self.text_script.clear()
        for act in actions:
            act_type, data, is_down, delay = act
            if act_type == 'key':
                key_name = vk_to_name(data)
                direction = "↓" if is_down else "↑"
                self.text_script.append(f"按键 {key_name} {direction}  延时 {delay:.3f}s")
            else:
                direction = "↓" if is_down else "↑"
                self.text_script.append(f"鼠标 {data} {direction}  延时 {delay:.3f}s")

    def set_status(self, text):
        self.status_label.setText(text)

    def set_hwnd_label(self, text):
        self.label_hwnd.setText(text)

    # ========== 全局热键 ==========
    def _register_global_hotkeys(self):
        """延迟注册全局热键，避免启动卡顿"""
        if not HAS_KEYBOARD:
            logui.warning("keyboard 库未安装，无法注册全局热键，宏模块的快捷键将仅在程序激活时有效")
            self.status_label.setText("⚠ 全局热键不可用，请安装 keyboard 库")
            return

        try:
            # 清除可能残留的热键
            self._unregister_global_hotkeys()

            # 注册 Alt+Y 触发录制/停止
            self.hotkey_alt_y = keyboard.add_hotkey('alt+y', self._on_alt_y, suppress=False)
            # 注册 Alt+T 触发回放/停止
            self.hotkey_alt_t = keyboard.add_hotkey('alt+t', self._on_alt_t, suppress=False)

            logui.info("全局热键已注册: Alt+Y (录制/停止), Alt+T (回放/停止)")
            self.status_label.setText("全局热键已就绪: Alt+Y, Alt+T")
        except Exception as e:
            logui.error(f"注册全局热键失败: {e}")
            self.status_label.setText("全局热键注册失败，可能需要管理员权限")

    def _unregister_global_hotkeys(self):
        if self.hotkey_alt_y:
            try:
                keyboard.remove_hotkey(self.hotkey_alt_y)
            except:
                pass
            self.hotkey_alt_y = None
        if self.hotkey_alt_t:
            try:
                keyboard.remove_hotkey(self.hotkey_alt_t)
            except:
                pass
            self.hotkey_alt_t = None

    def _on_alt_y(self):
        """全局热键 Alt+Y 回调（keyboard 线程中）"""
        QTimer.singleShot(0, self.signal_toggle_record.emit)

    def _on_alt_t(self):
        """全局热键 Alt+T 回调"""
        QTimer.singleShot(0, self.signal_toggle_macro.emit)

    def closeEvent(self, event):
        self.hwnd_timer.stop()
        self._unregister_global_hotkeys()
        self.core.cleanup()
        event.accept()

def vk_to_name(vk):
    try:
        return chr(win32api.MapVirtualKey(vk, 2)) or f"VK_{vk}"
    except:
        return f"VK_{vk}"