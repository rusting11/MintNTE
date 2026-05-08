import sys
import os
import warnings
import ctypes
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QVBoxLayout,
                             QWidget, QLabel, QMessageBox, QShortcut, QProgressBar,
                             QPushButton, QHBoxLayout)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QKeySequence, QFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

warnings.filterwarnings("ignore", category=DeprecationWarning)

from UI.HeaderUI import HeaderUI
from core.fishing.FishingUI import FishingUI
from core.Mahjong.MahjongUI import MahjongUI
from core.task.TaskUI import TaskUI
from core.JoinUs.JoinUsUI import JoinUsUI
from core.Macro.macro_ui import MacroPanel
from core.window_detect.window_detect_ui import WindowDetectUI
from core.Fortissimo.foreground.foreground_ui import ForegroundWindow
from core.Fortissimo.background.background_ui import BackgroundWindow
from UI.logui import setup_logging, info
from UI.logViewerUI import LogViewer
from updater.updater import Updater


class MainUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MintNTE")
        self.resize(1200, 800)
        self.setMinimumSize(1000, 600)

        # 窗口图标（标题栏）
        icon_path = os.path.join(BASE_DIR, "Image", "logo", "titlelogo.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        # 关键：锁定任务栏图标，弹窗后不会消失
        if hasattr(ctypes, 'windll'):
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('daoqi.MintNTE')

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = HeaderUI()
        self.header.checkUpdate_signal.connect(self.manual_check_update)
        self.header.toggle_log_signal.connect(self.toggle_log)
        layout.addWidget(self.header)

        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("MainTabWidget")
        self.tab_widget.addTab(WindowDetectUI(), "窗口检测")
        self.tab_widget.addTab(MacroPanel(), "键鼠宏")
        self.tab_widget.addTab(FishingUI(), "钓鱼")
        self.tab_widget.addTab(MahjongUI(), "麻将")
        self.tab_widget.addTab(TaskUI(), "任务")
        self.tab_widget.addTab(self._fortissimo_tab(), "超强音")
        self.tab_widget.addTab(JoinUsUI(), "加入我们")
        layout.addWidget(self.tab_widget)

        self.update_status = QLabel("")
        self.update_status.setStyleSheet("color:#00ffff; font-size:12px;")
        self.update_status.setVisible(False)
        self.update_progress = QProgressBar()
        self.update_progress.setMaximum(100)
        self.update_progress.setVisible(False)
        layout.addWidget(self.update_status)
        layout.addWidget(self.update_progress)

        self.updater = Updater(parent=self)
        self.updater.progress.connect(self.update_progress.setValue)
        self.updater.status.connect(self.update_status.setText)
        self.updater.finished.connect(self.on_check_finished)

        self.setStyleSheet("""
        QMainWindow { background-color: #1e1e2f; }
        #MainTabWidget::pane { border: 1px solid #0ff; background-color: #1e1e2f; }
        QTabBar::tab { background-color: #2a2a3a; color: #0ff; padding: 8px 20px; margin: 2px; border-top-left-radius: 5px; border-top-right-radius: 5px; }
        QTabBar::tab:selected { background-color: #0ff; color: #1e1e2f; }
        QTabBar::tab:hover { background-color: #3a3a4a; }
        """)

        self.log_viewer = None
        self.fortissimo_win = None

        self.shortcut = QShortcut(QKeySequence("Alt+F1"), self)
        self.shortcut.activated.connect(self._global_hotkey)


    def _fortissimo_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setAlignment(Qt.AlignCenter)
        title = QLabel("Fortissimo 自动演奏")
        title.setFont(QFont("Microsoft YaHei", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #00ffff; margin: 15px;")
        l.addWidget(title)
        l.addWidget(QLabel("前台模式命中率高达 98% 以上 · 游戏窗口自动置顶", alignment=Qt.AlignCenter, styleSheet="color:#00ff88; font-size:13px;"))
        l.addWidget(QLabel("后台模式命中率可达 80% 以上 · 无额外限制", alignment=Qt.AlignCenter, styleSheet="color:#ffaa00; font-size:13px;"))
        l.addSpacing(20)
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)
        b1 = QPushButton("前台模式")
        b1.setMinimumSize(150, 60)
        b1.setFont(QFont("Microsoft YaHei", 13))
        b1.setStyleSheet("QPushButton{background:#0a0a2a; border:2px solid #00ffff; border-radius:10px; color:#00ffff;} QPushButton:hover{background:#00ffff; color:#050510;}")
        b2 = QPushButton("后台模式")
        b2.setMinimumSize(150, 60)
        b2.setFont(QFont("Microsoft YaHei", 13))
        b2.setStyleSheet("QPushButton{background:#0a0a2a; border:2px solid #ffaa00; border-radius:10px; color:#ffaa00;} QPushButton:hover{background:#ffaa00; color:#050510;}")
        btn_layout.addWidget(b1)
        btn_layout.addWidget(b2)
        l.addLayout(btn_layout)
        l.addWidget(QLabel("※ 前台模式会自动保持游戏窗口置顶，确保按键精准。", alignment=Qt.AlignCenter, styleSheet="color:#888888; font-size:11px; margin-top:15px;"))
        b1.clicked.connect(lambda: self._launch_fortissimo('foreground'))
        b2.clicked.connect(lambda: self._launch_fortissimo('background'))
        return w

    def _launch_fortissimo(self, mode):
        try:
            if mode == 'foreground':
                self.fortissimo_win = ForegroundWindow(mode='foreground')
            else:
                self.fortissimo_win = BackgroundWindow()
            self.fortissimo_win.show()
        except Exception as e:
            QMessageBox.critical(self, "启动失败", f"无法启动超强音模块：{str(e)}")

    def _global_hotkey(self):
        cur = self.tab_widget.currentWidget()
        if hasattr(cur, 'toggle_fishing'):
            cur.toggle_fishing()
        elif hasattr(cur, 'toggle_run'):
            cur.toggle_run()

    def manual_check_update(self):
        self.update_status.setVisible(True)
        self.update_progress.setVisible(True)
        self.update_progress.setValue(0)
        self.update_status.setText("正在检查更新...")
        self.updater.check_for_update()

    def auto_check_update(self):
        self.manual_check_update()

    def on_check_finished(self, needs_update, remote_version):
        if needs_update:
            local = self.updater.get_local_version()
            reply = QMessageBox.question(self, "发现新版本",
                                         f"当前版本: {local}\n最新版本: {remote_version}\n是否立即更新？",
                                         QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.update_progress.setVisible(True)
                self.update_status.setVisible(True)
                self.updater.perform_update()
            else:
                self._hide_update_ui()
        else:
            box = QMessageBox(QMessageBox.Information, "检查更新", "当前已是最新版本", QMessageBox.NoButton, self)
            box.setAttribute(Qt.WA_DeleteOnClose)
            box.show()
            QTimer.singleShot(3000, box.close)
            self._hide_update_ui()

    def _hide_update_ui(self):
        self.update_status.setVisible(False)
        self.update_progress.setVisible(False)

    def toggle_log(self):
        if self.log_viewer is None:
            self.log_viewer = LogViewer()
            self.log_viewer.show()
            self.log_viewer.refresh_log()
            self.header.btn_log.setText("关闭日志")
        else:
            try:
                if self.log_viewer.isVisible():
                    self.log_viewer.hide()
                    self.header.btn_log.setText("显示日志")
                else:
                    self.log_viewer.show()
                    self.log_viewer.refresh_log()
                    self.header.btn_log.setText("关闭日志")
            except RuntimeError:
                self.log_viewer = LogViewer()
                self.log_viewer.show()
                self.log_viewer.refresh_log()
                self.header.btn_log.setText("关闭日志")

    def closeEvent(self, event):
        self.updater.cancel()
        if self.fortissimo_win is not None:
            try:
                self.fortissimo_win.close()
            except:
                pass
        if self.log_viewer:
            try:
                self.log_viewer.close()
            except:
                pass
        event.accept()