# core/Macro/macro_ui.py
# 键鼠宏模块 - 提供后台宏录制/回放功能的用户界面
# 主要功能：
#   1. 宏录制：记录键盘和鼠标操作
#   2. 宏回放：在目标窗口后台执行录制的宏
#   3. 配置管理：保存/加载宏配置
#   4. 全局热键：支持 Alt+Y 录制/停止，Alt+T 回放/停止
#   5. 循环设置：设置宏执行的循环次数

import sys
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QGroupBox, QTextEdit, QSpinBox, QFrame
)
from PyQt5.QtCore import pyqtSignal, Qt, QTimer
import win32api
import win32gui

# 添加项目根目录到路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.Macro.macro_core import MacroCore
from Module.Hwnd.game_hwnd import get_game_hwnd
from UI import logui
from UI.themes import get_theme


# ========== 全局热键支持检测 ==========

# 尝试导入 keyboard 库（全局热键必需）
try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False


# ========== 键鼠宏主界面 ==========

class MacroPanel(QWidget):
    """
    键鼠宏控制面板
    
    提供宏录制、回放、配置管理等功能的用户界面。
    
    Signals:
        signal_toggle_record: 切换录制状态信号
        signal_toggle_macro: 切换宏执行状态信号
        signal_save_config: 保存配置信号
        signal_load_config: 加载配置信号
        signal_loop_changed: 循环次数改变信号，参数为新的循环次数
    """
    
    signal_toggle_record = pyqtSignal()
    signal_toggle_macro = pyqtSignal()
    signal_save_config = pyqtSignal()
    signal_load_config = pyqtSignal()
    signal_loop_changed = pyqtSignal(int)
    
    def __init__(self, parent=None):
        """
        初始化宏控制面板
        
        Args:
            parent: 父窗口对象
        """
        super().__init__(parent)
        
        # 设置窗口标题
        self.setWindowTitle("异环·后台宏录制/回放")
        
        # ========== 状态变量 ==========
        self.hwnd_timer = None           # 句柄刷新定时器
        self.hotkey_alt_y = None         # Alt+Y 热键对象
        self.hotkey_alt_t = None         # Alt+T 热键对象
        
        # ========== 初始化UI ==========
        self.setup_ui()
        
        # ========== 创建宏核心实例 ==========
        self.core = MacroCore(loop_count=self.spin_loop.value())
        
        # ========== 连接信号 ==========
        self.connect_signals()
        
        # ========== 定时刷新当前锁定窗口的句柄 ==========
        self.hwnd_timer = QTimer(self)
        self.hwnd_timer.timeout.connect(self.refresh_hwnd)
        self.hwnd_timer.start(1000)
        self.refresh_hwnd()
        
        # ========== 延迟注册全局热键，避免阻塞启动 ==========
        QTimer.singleShot(1000, self._register_global_hotkeys)
    
    # ========== UI初始化 ==========
    
    def setup_ui(self):
        """设置宏控制面板的UI布局"""
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # 1. 目标窗口状态显示区域
        win_grp = self._create_window_status_group()
        layout.addWidget(win_grp)
        
        # 2. 操作按钮区域
        btn_layout = self._create_action_button_layout()
        layout.addLayout(btn_layout)
        
        # 3. 配置区域（保存/加载 + 循环次数）
        cfg_layout = self._create_config_layout()
        layout.addLayout(cfg_layout)
        
        # 4. 宏指令列表显示区域
        script_grp = self._create_script_display_group()
        layout.addWidget(script_grp)
        
        # 5. 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("StatusLabel")
        layout.addWidget(self.status_label)
        
        # 应用主题样式
        self.setStyleSheet(get_theme())
    
    def _create_window_status_group(self):
        """创建目标窗口状态显示区域"""
        win_grp = QFrame()
        win_grp.setObjectName("InfoGroup")
        
        win_layout = QVBoxLayout(win_grp)
        win_layout.setContentsMargins(16, 16, 16, 16)
        win_layout.setSpacing(12)
        
        # 标题
        title_label = QLabel("目标窗口")
        title_label.setObjectName("InfoGroupTitle")
        win_layout.addWidget(title_label)
        
        # 句柄显示标签
        self.label_hwnd = QLabel("句柄: 未锁定（请在窗口检测中锁定目标窗口）")
        self.label_hwnd.setObjectName("InfoLabel")
        win_layout.addWidget(self.label_hwnd)
        
        return win_grp
    
    def _create_action_button_layout(self):
        """创建操作按钮布局"""
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        # 启用宏按钮
        self.btn_enable = QPushButton("启用宏 (Alt+T)")
        self.btn_enable.setObjectName("ActionButton")
        self.btn_enable.setMinimumHeight(50)
        self.btn_enable.clicked.connect(lambda: self.signal_toggle_macro.emit())
        btn_layout.addWidget(self.btn_enable)
        
        # 开始录制按钮
        self.btn_record = QPushButton("开始录制 (Alt+Y)")
        self.btn_record.setObjectName("ActionButton")
        self.btn_record.setMinimumHeight(50)
        self.btn_record.clicked.connect(lambda: self.signal_toggle_record.emit())
        btn_layout.addWidget(self.btn_record)
        
        # 拉伸空间
        btn_layout.addStretch()
        
        return btn_layout
    
    def _create_config_layout(self):
        """创建配置区域布局"""
        cfg_layout = QHBoxLayout()
        cfg_layout.setSpacing(12)
        
        # 保存/加载按钮
        self.btn_save = QPushButton("保存配置")
        self.btn_save.setObjectName("ActionButton")
        self.btn_save.clicked.connect(lambda: self.signal_save_config.emit())
        
        self.btn_load = QPushButton("加载配置")
        self.btn_load.setObjectName("ActionButton")
        self.btn_load.clicked.connect(lambda: self.signal_load_config.emit())
        
        cfg_layout.addWidget(self.btn_save)
        cfg_layout.addWidget(self.btn_load)
        
        # 拉伸空间
        cfg_layout.addStretch()
        
        # 循环次数设置
        loop_container = QHBoxLayout()
        loop_container.setSpacing(8)
        
        lbl_loop = QLabel("循环次数:")
        lbl_loop.setObjectName("InfoLabel")
        
        self.spin_loop = QSpinBox()
        self.spin_loop.setRange(1, 9999)
        self.spin_loop.setValue(99)
        self.spin_loop.setObjectName("InfoField")
        self.spin_loop.setFixedWidth(70)
        self.spin_loop.valueChanged.connect(lambda val: self.signal_loop_changed.emit(val))
        
        loop_container.addWidget(lbl_loop)
        loop_container.addWidget(self.spin_loop)
        cfg_layout.addLayout(loop_container)
        
        return cfg_layout
    
    def _create_script_display_group(self):
        """创建宏指令列表显示区域"""
        script_grp = QFrame()
        script_grp.setObjectName("InfoGroup")
        
        vbox = QVBoxLayout(script_grp)
        vbox.setContentsMargins(16, 16, 16, 16)
        vbox.setSpacing(12)
        
        # 标题
        title_label = QLabel("宏指令列表")
        title_label.setObjectName("InfoGroupTitle")
        vbox.addWidget(title_label)
        
        # 脚本显示文本框
        self.text_script = QTextEdit()
        self.text_script.setReadOnly(True)
        self.text_script.setObjectName("InfoText")
        self.text_script.setMinimumHeight(150)
        vbox.addWidget(self.text_script)
        
        return script_grp
    
    # ========== 状态刷新方法 ==========
    
    def refresh_hwnd(self):
        """刷新目标窗口句柄显示"""
        hwnd = get_game_hwnd()
        if hwnd:
            title = win32gui.GetWindowText(hwnd)
            self.label_hwnd.setText(f"已锁定: {title[:30]} (句柄: {hwnd})")
        else:
            self.label_hwnd.setText("句柄: 未锁定（请在窗口检测中锁定目标窗口）")
    
    # ========== 信号连接 ==========
    
    def connect_signals(self):
        """连接UI信号与核心模块"""
        # UI信号连接到核心模块
        self.signal_toggle_record.connect(self.core.toggle_record)
        self.signal_toggle_macro.connect(self.core.toggle_macro)
        self.signal_save_config.connect(self.core.save_config)
        self.signal_load_config.connect(self._load_config_and_update_ui)
        self.signal_loop_changed.connect(lambda val: setattr(self.core, 'loop_count', val))
        
        # 核心模块信号连接到UI更新
        self.core.recording_state_changed.connect(
            self._on_recording_state, 
            Qt.QueuedConnection
        )
        self.core.running_state_changed.connect(
            self._on_running_state, 
            Qt.QueuedConnection
        )
        self.core.hwnd_updated.connect(
            self.set_hwnd_label, 
            Qt.QueuedConnection
        )
        
        # 宏指令更新信号
        self.core.script_updated.connect(
            self.update_script_display,
            Qt.QueuedConnection
        )
    
    # ========== UI更新方法 ==========
    
    def _load_config_and_update_ui(self):
        """加载配置并更新UI显示"""
        success, loop, actions = self.core.load_config()
        if success:
            self.spin_loop.setValue(loop)
            self.update_script_display(actions)
    
    def _on_recording_state(self, is_recording):
        """
        录制状态改变时更新按钮文本
        
        Args:
            is_recording: 当前是否正在录制
        """
        self.btn_record.setText("停止录制 (Alt+Y)" if is_recording else "开始录制 (Alt+Y)")
    
    def _on_running_state(self, is_running):
        """
        宏执行状态改变时更新按钮文本
        
        Args:
            is_running: 当前是否正在执行宏
        """
        self.btn_enable.setText("禁用宏 (Alt+T)" if is_running else "启用宏 (Alt+T)")
    
    def update_script_display(self, actions):
        """
        更新宏指令列表显示
        
        Args:
            actions: 宏指令列表，每个元素为 (act_type, data, is_down, delay)
                     - act_type: 'key' 或 'mouse'
                     - data: 按键码或鼠标按钮
                     - is_down: True表示按下，False表示释放
                     - delay: 延迟时间（秒）
        """
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
        """
        设置状态栏文本
        
        Args:
            text: 状态文本
        """
        self.status_label.setText(text)
    
    def set_hwnd_label(self, text):
        """
        设置句柄标签文本
        
        Args:
            text: 句柄显示文本
        """
        self.label_hwnd.setText(text)
    
    # ========== 全局热键管理 ==========
    
    def _register_global_hotkeys(self):
        """延迟注册全局热键，避免启动卡顿"""
        if not HAS_KEYBOARD:
            logui.warning(
                "keyboard 库未安装，无法注册全局热键，"
                "宏模块的快捷键将仅在程序激活时有效"
            )
            self.status_label.setText("⚠ 全局热键不可用，请安装 keyboard 库")
            return
        
        try:
            # 清除可能残留的热键
            self._unregister_global_hotkeys()
            
            # 注册 Alt+Y 触发录制/停止
            self.hotkey_alt_y = keyboard.add_hotkey(
                'alt+y', 
                self._on_alt_y, 
                suppress=False
            )
            
            # 注册 Alt+T 触发回放/停止
            self.hotkey_alt_t = keyboard.add_hotkey(
                'alt+t', 
                self._on_alt_t, 
                suppress=False
            )
            
            logui.info("全局热键已注册: Alt+Y (录制/停止), Alt+T (回放/停止)")
            self.status_label.setText("全局热键已就绪: Alt+Y, Alt+T")
            
        except Exception as e:
            logui.error(f"注册全局热键失败: {e}")
            self.status_label.setText("全局热键注册失败，可能需要管理员权限")
    
    def _unregister_global_hotkeys(self):
        """注销所有已注册的全局热键"""
        if self.hotkey_alt_y:
            try:
                keyboard.remove_hotkey(self.hotkey_alt_y)
            except Exception:
                pass
            self.hotkey_alt_y = None
        
        if self.hotkey_alt_t:
            try:
                keyboard.remove_hotkey(self.hotkey_alt_t)
            except Exception:
                pass
            self.hotkey_alt_t = None
    
    def _on_alt_y(self):
        """全局热键 Alt+Y 回调（在keyboard线程中执行）"""
        # 使用 QTimer.singleShot 确保在主线程中执行
        QTimer.singleShot(0, self.signal_toggle_record.emit)
    
    def _on_alt_t(self):
        """全局热键 Alt+T 回调（在keyboard线程中执行）"""
        # 使用 QTimer.singleShot 确保在主线程中执行
        QTimer.singleShot(0, self.signal_toggle_macro.emit)
    
    # ========== 窗口生命周期 ==========
    
    def closeEvent(self, event):
        """
        关闭窗口时清理资源
        
        Args:
            event: QCloseEvent - 关闭事件
        """
        # 停止句柄刷新定时器
        if self.hwnd_timer:
            self.hwnd_timer.stop()
        
        # 注销全局热键
        self._unregister_global_hotkeys()
        
        # 清理宏核心资源
        self.core.cleanup()
        
        # 接受关闭事件
        event.accept()


# ========== 辅助函数 ==========

def vk_to_name(vk):
    """
    将虚拟键码转换为可读的键名
    
    Args:
        vk: 虚拟键码
        
    Returns:
        str: 键名，如果转换失败则返回 "VK_{vk}"
    """
    try:
        return chr(win32api.MapVirtualKey(vk, 2)) or f"VK_{vk}"
    except Exception:
        return f"VK_{vk}"