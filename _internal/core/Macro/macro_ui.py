import sys
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QGroupBox, QTextEdit, QSpinBox, QLineEdit
)
from PyQt5.QtCore import pyqtSignal, Qt, QMetaObject, Q_ARG
import win32api

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from core.Macro.macro_core import MacroCore
from UI import logui

class MacroPanel(QWidget):
    signal_toggle_record = pyqtSignal()
    signal_toggle_macro = pyqtSignal()
    signal_save_config = pyqtSignal()
    signal_load_config = pyqtSignal()
    signal_find_window = pyqtSignal()
    signal_title_changed = pyqtSignal(str)
    signal_loop_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("异环·后台宏录制/回放")
        self.setup_ui()
        self.apply_style()

        self.core = MacroCore(loop_count=self.spin_loop.value(), target_title=self.edit_title.text())
        self.connect_signals()
        self.core.register_hotkeys()
        self.core.find_window()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        win_grp = QGroupBox("目标窗口 (支持后台)")
        win_grp.setObjectName("NeonGroup")
        win_layout = QHBoxLayout()
        self.edit_title = QLineEdit("异环")
        self.edit_title.textChanged.connect(lambda text: self.signal_title_changed.emit(text))
        win_layout.addWidget(QLabel("标题:"))
        win_layout.addWidget(self.edit_title)
        self.btn_grab = QPushButton("自动查找")
        self.btn_grab.clicked.connect(lambda: self.signal_find_window.emit())
        win_layout.addWidget(self.btn_grab)
        self.label_hwnd = QLabel("句柄: 未绑定")
        win_layout.addWidget(self.label_hwnd)
        win_grp.setLayout(win_layout)
        layout.addWidget(win_grp)

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

    def connect_signals(self):
        self.signal_toggle_record.connect(self.core.toggle_record)
        self.signal_toggle_macro.connect(self.core.toggle_macro)
        self.signal_save_config.connect(self.core.save_config)
        self.signal_load_config.connect(self._load_config_and_update_ui)
        self.signal_find_window.connect(lambda: self.core.find_window(self.edit_title.text()))
        self.signal_title_changed.connect(lambda title: setattr(self.core, 'target_title', title))
        self.signal_loop_changed.connect(lambda val: setattr(self.core, 'loop_count', val))

        self.core.recording_state_changed.connect(self._on_recording_state, Qt.QueuedConnection)
        self.core.running_state_changed.connect(self._on_running_state, Qt.QueuedConnection)
        self.core.hwnd_updated.connect(self.set_hwnd_label, Qt.QueuedConnection)

    def _load_config_and_update_ui(self):
        success, title, loop, actions = self.core.load_config()
        if success:
            self.edit_title.setText(title)
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

    def closeEvent(self, event):
        self.core.cleanup()
        event.accept()

def vk_to_name(vk):
    try:
        return chr(win32api.MapVirtualKey(vk, 2)) or f"VK_{vk}"
    except:
        return f"VK_{vk}"