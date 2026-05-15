# core/task/TaskUI.py
# 任务交互模块 - 提供自动跳过任务功能的用户界面
# 主要功能：
#   1. 自动跳过任务：自动识别并跳过游戏任务对话
#   2. 今日不再提示跳过：跳过"今日不再提示"弹窗
#   3. 自定义快捷键：支持自定义启用/停止的快捷键
#   4. 状态显示：显示当前运行状态

import sys
import os
import threading
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QCheckBox,
    QPushButton, QLabel, QMessageBox, QShortcut,
    QDialog, QVBoxLayout as QVBoxLayoutDialog, QDialogButtonBox,
    QKeySequenceEdit
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QKeySequence

# 添加项目根目录到路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.task.task_core import TaskThread, simulate_mouse_click_relative
from UI import logui
from UI.themes import get_theme


# ========== 快捷键设置对话框 ==========

class HotkeyDialog(QDialog):
    """
    快捷键设置对话框
    
    用于让用户自定义任务跳过功能的快捷键。
    
    Attributes:
        key_edit: QKeySequenceEdit - 快捷键输入控件
    """
    
    def __init__(self, parent=None):
        """
        初始化快捷键对话框
        
        Args:
            parent: 父窗口对象
        """
        super().__init__(parent)
        
        # 设置窗口属性
        self.setWindowTitle("按下新的快捷键")
        self.setFixedSize(300, 100)
        
        # 布局
        layout = QVBoxLayoutDialog(self)
        
        # 快捷键输入控件
        self.key_edit = QKeySequenceEdit()
        layout.addWidget(self.key_edit)
        
        # 按钮框
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # 设置焦点到输入框
        self.key_edit.setFocus()
    
    def keySequence(self):
        """
        获取用户输入的快捷键序列
        
        Returns:
            str: 快捷键字符串（如 "Alt+F1"）
        """
        return self.key_edit.keySequence().toString()


# ========== 任务交互主界面 ==========

class TaskUI(QWidget):
    """
    任务交互主界面
    
    提供任务自动跳过功能的控制界面，包括：
    - 自动跳过任务选项
    - 今日不再提示跳过选项
    - 启用/停止控制按钮
    - 自定义快捷键功能
    
    Attributes:
        stop_event: threading.Event - 线程停止事件
        task_thread: TaskThread - 任务线程实例
        shortcut: QShortcut - 快捷键对象
        custom_key: str - 当前自定义快捷键
    """
    
    def __init__(self, parent=None):
        """
        初始化任务交互界面
        
        Args:
            parent: 父窗口对象
        """
        super().__init__(parent)
        
        # ========== 状态变量 ==========
        self.stop_event = threading.Event()  # 线程停止事件
        self.task_thread = None              # 任务线程实例
        self.shortcut = None                 # 快捷键对象
        self.custom_key = "Alt+F1"           # 默认快捷键
        
        # ========== 初始化UI ==========
        self.setup_ui()
        
        # ========== 设置快捷键 ==========
        self.setup_shortcut(self.custom_key)
    
    # ========== UI初始化 ==========
    
    def setup_ui(self):
        """设置任务交互界面的UI布局"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(16, 16, 16, 16)
        
        # 1. 提示信息
        hint = QLabel("游戏内不要点击自动对话！不然无法识别")
        hint.setStyleSheet("color: rgba(255, 170, 0, 0.8); font-size: 14px;")
        hint.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(hint)
        
        # 2. 功能选项
        opts_layout = self._create_options_layout()
        main_layout.addLayout(opts_layout)
        
        # 3. 控制按钮
        btn_layout = self._create_button_layout()
        main_layout.addLayout(btn_layout)
        
        # 4. 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("StatusLabel")
        main_layout.addWidget(self.status_label)
        
        # 添加拉伸空间
        main_layout.addStretch()
        
        # 应用主题样式
        self.setStyleSheet(get_theme())
        
        # 设置对话框图标
        self.dialog_icon = QIcon(os.path.join(
            BASE_DIR, "core", "task", "Taskimages", "titlelogo.ico"
        ))
        
    def _create_options_layout(self):
        """创建功能选项布局"""
        opts_layout = QHBoxLayout()
        opts_layout.setSpacing(20)
        
        # 自动跳过任务选项
        self.cb_skip = QCheckBox("自动跳过任务")
        self.cb_skip.setChecked(True)
        self.cb_skip.setObjectName("ActionCheckBox")
        opts_layout.addWidget(self.cb_skip)
        
        # 今日不再提示跳过选项
        self.cb_no_remind = QCheckBox("今日不再提示跳过")
        self.cb_no_remind.setChecked(True)
        self.cb_no_remind.setObjectName("ActionCheckBox")
        opts_layout.addWidget(self.cb_no_remind)
        
        # 拉伸空间
        opts_layout.addStretch()
        
        return opts_layout
    
    def _create_button_layout(self):
        """创建控制按钮布局"""
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        # 启用/停止按钮
        self.btn_start = QPushButton("启用跳过任务")
        self.btn_start.setObjectName("ActionButton")
        self.btn_start.setMinimumHeight(50)
        self.btn_start.clicked.connect(self.toggle_task)
        btn_layout.addWidget(self.btn_start)
        
        # 自定义快捷键按钮
        self.btn_custom = QPushButton("自定义快捷键")
        self.btn_custom.setObjectName("ActionButton")
        self.btn_custom.setMinimumHeight(50)
        self.btn_custom.clicked.connect(self.change_hotkey)
        btn_layout.addWidget(self.btn_custom)
        
        # 拉伸空间
        btn_layout.addStretch()
        
        return btn_layout
    
    # ========== 快捷键管理 ==========
    
    def setup_shortcut(self, key_seq):
        """
        设置快捷键
        
        Args:
            key_seq: str - 快捷键序列（如 "Alt+F1"）
        """
        # 如果已有快捷键，先禁用并删除
        if self.shortcut:
            self.shortcut.setEnabled(False)
            self.shortcut.deleteLater()
        
        # 创建新的快捷键，使用 WidgetWithChildrenShortcut 让快捷键仅在当前控件及其子控件中生效
        self.shortcut = QShortcut(
            QKeySequence(key_seq), 
            self, 
            context=Qt.WidgetWithChildrenShortcut
        )
        self.shortcut.activated.connect(self.toggle_task)
    
    def change_hotkey(self):
        """打开快捷键设置对话框并更新快捷键"""
        dialog = HotkeyDialog(self)
        dialog.setWindowIcon(self.dialog_icon)
        
        if dialog.exec_() == QDialog.Accepted:
            key = dialog.keySequence()
            if key:
                self.custom_key = key
                self.setup_shortcut(key)
                self.status_label.setText(f"当前快捷键: {key}")
                logui.info(f"任务模块快捷键已更新为: {key}")
    
    # ========== 任务控制 ==========
    
    def toggle_task(self):
        """切换任务跳过状态（启用/停止）"""
        if self.task_thread and self._is_thread_running():
            self.stop_task()
        else:
            self.start_task()
    
    def _is_thread_running(self):
        """
        检查任务线程是否正在运行
        
        Returns:
            bool: True 表示线程正在运行，False 表示已停止
        """
        return self.task_thread is not None and self.task_thread._thread.is_alive()
    
    def start_task(self):
        """启动任务跳过功能"""
        # 检查选项是否至少勾选一个
        if not self.cb_skip.isChecked() and not self.cb_no_remind.isChecked():
            box = QMessageBox(
                QMessageBox.Warning, 
                "提示", 
                "请至少勾选一个选项！", 
                parent=self
            )
            box.setWindowIcon(self.dialog_icon)
            box.exec_()
            return
        
        # 重置停止事件
        self.stop_event.clear()
        
        # 创建任务线程
        self.task_thread = TaskThread(
            self.stop_event, 
            self.cb_skip.isChecked(), 
            self.cb_no_remind.isChecked()
        )
        
        # 连接信号
        self.task_thread.request_click.connect(self.on_request_click)
        
        # 启动线程
        self.task_thread.start()
        
        # 更新UI状态
        self.btn_start.setText("停止跳过任务")
        self.status_label.setText("运行中...")
        
        # 记录日志
        logui.info("任务跳过功能已启动")
    
    def on_request_click(self, hwnd, x, y):
        """
        处理线程请求的点击操作（在主线程安全执行）
        
        Args:
            hwnd: int - 目标窗口句柄
            x: int - 相对X坐标
            y: int - 相对Y坐标
        """
        try:
            simulate_mouse_click_relative(hwnd, x, y)
        except Exception as e:
            logui.error(f"任务模块点击失败: {e}")
    
    def stop_task(self):
        """停止任务跳过功能"""
        # 1. 通知线程退出
        self.stop_event.set()
        
        # 2. 等待线程完全结束
        if self.task_thread:
            try:
                self.task_thread.wait(2.0)
            except Exception:
                pass
        
        # 3. 断开信号
        if self.task_thread:
            try:
                self.task_thread.request_click.disconnect()
            except Exception:
                pass
        
        # 4. 清空线程引用
        self.task_thread = None
        
        # 5. 更新UI状态
        self.btn_start.setText("启用跳过任务")
        self.status_label.setText("已停止")
        
        # 记录日志
        logui.info("任务跳过功能已停止")
    
    # ========== 窗口生命周期 ==========
    
    def showEvent(self, event):
        """
        窗口显示时的处理
        
        Args:
            event: QShowEvent - 显示事件
        """
        super().showEvent(event)
        
        # 启用快捷键
        if self.shortcut:
            self.shortcut.setEnabled(True)
        
        # 更新状态
        self.status_label.setText("就绪")
    
    def hideEvent(self, event):
        """
        窗口隐藏时的处理
        
        Args:
            event: QHideEvent - 隐藏事件
        """
        super().hideEvent(event)
        
        # 禁用快捷键
        if self.shortcut:
            self.shortcut.setEnabled(False)
        
        # 停止任务
        self.stop_task()
    
    def closeEvent(self, event):
        """
        关闭窗口时的处理
        
        Args:
            event: QCloseEvent - 关闭事件
        """
        # 停止任务
        self.stop_task()
        
        # 接受关闭事件
        event.accept()