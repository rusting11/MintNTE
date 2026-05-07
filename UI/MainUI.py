# MainUI.py
import sys
import os
import warnings
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QVBoxLayout,
                             QWidget, QLabel, QMessageBox, QShortcut, QProgressBar,
                             QPushButton, QHBoxLayout)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QKeySequence, QFont

# 项目根目录（MainUI.py 在 UI/ 下，往上两层是根目录）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

warnings.filterwarnings("ignore", category=DeprecationWarning)

# ---------- 导入各模块 UI ----------
from UI.HeaderUI import HeaderUI
from core.fishing.FishingUI import FishingUI
from core.Mahjong.MahjongUI import MahjongUI
from core.task.TaskUI import TaskUI
from core.JoinUs.JoinUsUI import JoinUsUI
from core.Macro.macro_ui import MacroPanel
from core.window_detect.window_detect_ui import WindowDetectUI

from UI.logui import setup_logging, info
from UI.logViewerUI import LogViewer

# 导入更新模块
from updater.updater import Updater


class MainUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MintNTE")
        self.resize(1200, 800)
        self.setMinimumSize(1000, 600)

        # 窗口图标
        icon_path = os.path.join(BASE_DIR, "Image", "logo", "titlelogo.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部 Header
        self.header = HeaderUI()
        self.header.checkUpdate_signal.connect(self.manual_check_update)
        self.header.toggle_log_signal.connect(self.toggle_log)
        main_layout.addWidget(self.header)

        # 标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("MainTabWidget")
        self.tab_widget.addTab(WindowDetectUI(), "窗口检测")
        self.tab_widget.addTab(MacroPanel(), "键鼠宏")
        self.tab_widget.addTab(FishingUI(), "钓鱼")
        self.tab_widget.addTab(MahjongUI(), "麻将")
        self.tab_widget.addTab(TaskUI(), "任务")

        # ========== 超强音标签页 ==========
        self.fortissimo_tab = self.create_fortissimo_tab()
        self.tab_widget.addTab(self.fortissimo_tab, "超强音")
        # ==================================

        self.tab_widget.addTab(JoinUsUI(), "加入我们")
        main_layout.addWidget(self.tab_widget)

        # ───── 底部更新状态栏 ─────
        self.update_status_label = QLabel("")
        self.update_status_label.setStyleSheet("color: #00ffff; font-size: 12px;")
        self.update_status_label.setVisible(False)
        self.update_progress_bar = QProgressBar()
        self.update_progress_bar.setMaximum(100)
        self.update_progress_bar.setVisible(False)

        main_layout.addWidget(self.update_status_label)
        main_layout.addWidget(self.update_progress_bar)

        # 创建更新管理器
        self.updater = Updater()
        self.updater.progress.connect(self.update_progress_bar.setValue)
        self.updater.status.connect(self.update_status_label.setText)
        self.updater.finished.connect(self.on_check_finished)

        self.apply_global_style()
        self.log_viewer = None

        # 全局热键 Alt+F1
        self.shortcut_global = QShortcut(QKeySequence("Alt+F1"), self)
        self.shortcut_global.activated.connect(self.on_global_hotkey)

    def create_fortissimo_tab(self):
        """返回包含两个模式按钮的标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Fortissimo 自动演奏")
        title.setFont(QFont("Microsoft YaHei", 20, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #00ffff; margin: 15px;")
        layout.addWidget(title)

        tip_fg = QLabel("前台模式命中率高达 98% 以上 · 游戏窗口自动置顶")
        tip_fg.setAlignment(Qt.AlignCenter)
        tip_fg.setStyleSheet("color: #00ff88; font-size: 13px;")
        layout.addWidget(tip_fg)

        tip_bg = QLabel("后台模式命中率可达 80% 以上 · 无额外限制")
        tip_bg.setAlignment(Qt.AlignCenter)
        tip_bg.setStyleSheet("color: #ffaa00; font-size: 13px;")
        layout.addWidget(tip_bg)

        layout.addSpacing(20)

        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignCenter)

        self.btn_foreground = QPushButton("前台模式")
        self.btn_foreground.setMinimumSize(150, 60)
        self.btn_foreground.setFont(QFont("Microsoft YaHei", 13))
        self.btn_foreground.setStyleSheet("""
            QPushButton {
                background-color: #0a0a2a; border: 2px solid #00ffff;
                border-radius: 10px; color: #00ffff;
            }
            QPushButton:hover { background-color: #00ffff; color: #050510; }
        """)
        btn_layout.addWidget(self.btn_foreground)

        self.btn_background = QPushButton("后台模式")
        self.btn_background.setMinimumSize(150, 60)
        self.btn_background.setFont(QFont("Microsoft YaHei", 13))
        self.btn_background.setStyleSheet("""
            QPushButton {
                background-color: #0a0a2a; border: 2px solid #ffaa00;
                border-radius: 10px; color: #ffaa00;
            }
            QPushButton:hover { background-color: #ffaa00; color: #050510; }
        """)
        btn_layout.addWidget(self.btn_background)

        layout.addLayout(btn_layout)

        note = QLabel("※ 前台模式会自动保持游戏窗口置顶，确保按键精准。后台模式使用后台截图，无需置顶。")
        note.setAlignment(Qt.AlignCenter)
        note.setStyleSheet("color: #888888; font-size: 11px; margin-top: 15px;")
        layout.addWidget(note)

        # 连接信号
        self.btn_foreground.clicked.connect(lambda: self.launch_fortissimo('foreground'))
        self.btn_background.clicked.connect(self.launch_background)
        return tab

    def launch_fortissimo(self, mode):
        """弹窗打开前台演奏控制界面"""
        try:
            from core.Fortissimo.foreground.foreground_ui import ForegroundWindow
            self.fortissimo_window = ForegroundWindow(mode=mode)
            self.fortissimo_window.show()
        except Exception as e:
            QMessageBox.critical(self, "启动失败", f"无法启动超强音模块：{str(e)}")

    def launch_background(self):
        """弹窗打开后台演奏控制界面"""
        try:
            from core.Fortissimo.background.background_ui import BackgroundWindow
            self.background_window = BackgroundWindow()
            self.background_window.show()
        except Exception as e:
            QMessageBox.critical(self, "启动失败", f"无法启动后台模块：{str(e)}")

    def on_global_hotkey(self):
        current = self.tab_widget.currentWidget()
        if hasattr(current, 'toggle_fishing'):
            current.toggle_fishing()
        elif hasattr(current, 'toggle_run'):
            current.toggle_run()

    def apply_global_style(self):
        self.setStyleSheet("""
        QMainWindow {
            background-color: #1e1e2f;
        }
        #MainTabWidget::pane {
            border: 1px solid #0ff;
            background-color: #1e1e2f;
        }
        #MainTabWidget::tab-bar {
            alignment: center;
        }
        QTabBar::tab {
            background-color: #2a2a3a;
            color: #0ff;
            padding: 8px 20px;
            margin: 2px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
        }
        QTabBar::tab:selected {
            background-color: #0ff;
            color: #1e1e2f;
        }
        QTabBar::tab:hover {
            background-color: #3a3a4a;
        }
        """)

    def manual_check_update(self):
        self.update_status_label.setVisible(True)
        self.update_progress_bar.setVisible(True)
        self.update_progress_bar.setValue(0)
        self.update_status_label.setText("正在检查更新...")
        self.updater.check_for_update()

    def auto_check_update(self):
        self.manual_check_update()

    def on_check_finished(self, needs_update, remote_version):
        if needs_update:
            local = self.updater.get_local_version()
            reply = QMessageBox.question(
                self, "发现新版本",
                f"当前版本: {local}\n最新版本: {remote_version}\n是否立即更新？\n\n（更新将自动重启程序）",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.update_progress_bar.setVisible(True)
                self.update_status_label.setVisible(True)
                self.updater.perform_update()
            else:
                self._hide_update_ui()
        else:
            QMessageBox.information(self, "检查更新", "当前已是最新版本")
            self._hide_update_ui()

    def _hide_update_ui(self):
        self.update_status_label.setVisible(False)
        self.update_progress_bar.setVisible(False)

    def toggle_log(self):
        if self.log_viewer is None:
            from UI.logViewerUI import LogViewer
            self.log_viewer = LogViewer()
            self.log_viewer.show()
            self.log_viewer.refresh_log()
            self.header.btn_log.setText("关闭日志")
            return
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
        if self.log_viewer is not None:
            try:
                self.log_viewer.close()
            except:
                pass
        event.accept()