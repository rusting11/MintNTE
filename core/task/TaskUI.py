# core/task/TaskUI.py
import sys, os, threading
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QCheckBox,
                             QPushButton, QLabel, QMessageBox, QShortcut,
                             QDialog, QVBoxLayout as QVBoxLayoutDialog, QDialogButtonBox,
                             QKeySequenceEdit)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QKeySequence

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.task.task_core import TaskThread, simulate_mouse_click_relative
from UI import logui

class HotkeyDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("按下新的快捷键")
        self.setFixedSize(300, 100)
        layout = QVBoxLayoutDialog(self)
        self.key_edit = QKeySequenceEdit()
        layout.addWidget(self.key_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.key_edit.setFocus()

    def keySequence(self):
        return self.key_edit.keySequence().toString()

class TaskUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.stop_event = threading.Event()
        self.task_thread = None
        self.shortcut = None
        self.custom_key = "Alt+F1"
        self.setup_ui()
        self.setup_shortcut(self.custom_key)

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        hint = QLabel("不要点击自动任务哦！不然无法识别")
        hint.setStyleSheet("color: #ffaa00; font-size: 14px;")
        hint.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(hint)

        opts_layout = QHBoxLayout()
        self.cb_skip = QCheckBox("自动跳过任务")
        self.cb_skip.setChecked(True)
        self.cb_no_remind = QCheckBox("不再提示跳过")
        self.cb_no_remind.setChecked(True)
        opts_layout.addWidget(self.cb_skip)
        opts_layout.addWidget(self.cb_no_remind)
        opts_layout.addStretch()
        main_layout.addLayout(opts_layout)

        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("启用跳过任务")
        self.btn_start.clicked.connect(self.toggle_task)
        btn_layout.addWidget(self.btn_start)
        self.btn_custom = QPushButton("自定义快捷键")
        self.btn_custom.clicked.connect(self.change_hotkey)
        btn_layout.addWidget(self.btn_custom)
        main_layout.addLayout(btn_layout)

        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #0ff; font-size: 12px;")
        main_layout.addWidget(self.status_label)
        main_layout.addStretch()

        self.dialog_icon = QIcon(os.path.join(BASE_DIR, "core", "task", "Taskimages", "titlelogo.ico"))
        self.setStyleSheet("""
        QCheckBox { color: #0ff; font-size: 14px; }
        QPushButton { background-color: #2a2a3a; color: #0ff; border: 1px solid #0ff; border-radius: 5px; padding: 6px 12px; }
        QPushButton:hover { background-color: #0ff; color: #1e1e2f; }
        """)

    def setup_shortcut(self, key_seq):
        if self.shortcut:
            self.shortcut.setEnabled(False)
            self.shortcut.deleteLater()
        # 使用 WidgetWithChildrenShortcut 让快捷键仅在当前控件及其子控件中生效
        self.shortcut = QShortcut(QKeySequence(key_seq), self, context=Qt.WidgetWithChildrenShortcut)
        self.shortcut.activated.connect(self.toggle_task)

    def change_hotkey(self):
        dialog = HotkeyDialog(self)
        dialog.setWindowIcon(self.dialog_icon)
        if dialog.exec_() == QDialog.Accepted:
            key = dialog.keySequence()
            if key:
                self.custom_key = key
                self.setup_shortcut(key)
                self.status_label.setText(f"当前快捷键: {key}")

    def toggle_task(self):
        if self.task_thread and self._is_thread_running():
            self.stop_task()
        else:
            self.start_task()

    def _is_thread_running(self):
        return self.task_thread is not None and self.task_thread._thread.is_alive()

    def start_task(self):
        if not self.cb_skip.isChecked() and not self.cb_no_remind.isChecked():
            box = QMessageBox(QMessageBox.Warning, "提示", "请至少勾选一个选项！", parent=self)
            box.setWindowIcon(self.dialog_icon)
            box.exec_()
            return
        self.stop_event.clear()
        self.task_thread = TaskThread(self.stop_event, self.cb_skip.isChecked(), self.cb_no_remind.isChecked())
        self.task_thread.request_click.connect(self.on_request_click)
        self.task_thread.start()
        self.btn_start.setText("停止跳过任务")
        self.status_label.setText("运行中...")

    def on_request_click(self, hwnd, x, y):
        """在主线程安全执行点击"""
        try:
            simulate_mouse_click_relative(hwnd, x, y)
        except Exception as e:
            logui.error(f"点击失败: {e}")

    def stop_task(self):
        # 1. 通知线程退出
        self.stop_event.set()
        # 2. 等待线程完全结束
        if self.task_thread:
            try:
                self.task_thread.wait(2.0)
            except:
                pass
        # 3. 断开信号
        if self.task_thread:
            try:
                self.task_thread.request_click.disconnect()
            except:
                pass
            # 不立即删除对象，保留以便下次启动
        self.task_thread = None
        self.btn_start.setText("启用跳过任务")
        self.status_label.setText("已停止")

    def showEvent(self, event):
        super().showEvent(event)
        if self.shortcut:
            self.shortcut.setEnabled(True)
        self.status_label.setText("就绪")

    def hideEvent(self, event):
        super().hideEvent(event)
        if self.shortcut:
            self.shortcut.setEnabled(False)
        self.stop_task()

    def closeEvent(self, event):
        self.stop_task()
        event.accept()