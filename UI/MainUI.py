import sys, os
from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QVBoxLayout, QWidget,
                             QLabel, QComboBox, QHBoxLayout, QPushButton,
                             QProgressBar, QShortcut, QMessageBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QKeySequence, QFont   # QFont 正确放在这里
import ctypes

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from UI.HeaderUI import HeaderUI
from UI.themes import THEMES

class MainUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MintNTE")
        self.resize(1200, 800)
        self.setMinimumSize(1000, 600)

        icon_path = os.path.join(BASE_DIR, "Image", "logo", "titlelogo.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        if hasattr(ctypes, 'windll'):
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('daoqi.MintNTE')

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        self.header = HeaderUI()
        self.header.checkUpdate_signal.connect(self.manual_check_update)
        self.header.toggle_log_signal.connect(self.toggle_log)
        layout.addWidget(self.header)

        # 主题栏（延迟添加）
        QTimer.singleShot(0, self._add_theme_bar)

        # 标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("MainTabWidget")
        from core.window_detect.window_detect_ui import WindowDetectUI
        self.window_detect = WindowDetectUI()
        self.tab_widget.addTab(self.window_detect, "窗口检测")

        self._lazy_tabs = {}
        tab_names = ["键鼠宏", "钓鱼", "兑奖码", "任务交互", "超强音", "加入我们"]
        for name in tab_names:
            self.tab_widget.addTab(QWidget(), name)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tab_widget)

        # 更新控件
        self.update_status = QLabel("")
        self.update_status.setStyleSheet("color:#00ffff; font-size:12px;")
        self.update_status.setVisible(False)
        self.update_progress = QProgressBar()
        self.update_progress.setMaximum(100)
        self.update_progress.setVisible(False)
        layout.addWidget(self.update_status)
        layout.addWidget(self.update_progress)

        # Updater
        from updater.updater import Updater
        self.updater = Updater(parent=self)
        self.updater.checkResult.connect(self.on_check_result)
        self.updater.progress.connect(self.update_progress.setValue)
        self.updater.status.connect(self.update_status.setText)

        self.log_viewer = None
        self.fortissimo_win = None

        self.shortcut = QShortcut(QKeySequence("Alt+F1"), self)
        self.shortcut.activated.connect(self._global_hotkey)

        self.apply_theme("薄荷风格")

    def _add_theme_bar(self):
        central = self.centralWidget()
        layout = central.layout()
        theme_layout = QHBoxLayout()
        theme_label = QLabel("切换主题:")
        theme_label.setStyleSheet("color: #00ffff; font-size: 14px; font-weight: bold;")
        theme_layout.addWidget(theme_label)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES.keys()))
        self.theme_combo.setCurrentText("薄荷风格")
        self.theme_combo.currentTextChanged.connect(self.apply_theme)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        layout.insertLayout(1, theme_layout)

    def _on_tab_changed(self, index):
        if index <= 0:
            return
        tab_name = {1: "键鼠宏", 2: "钓鱼", 3: "兑奖码", 4: "任务交互", 5: "超强音", 6: "加入我们"}.get(index, None)
        if not tab_name or tab_name in self._lazy_tabs:
            return

        widget = None
        try:
            if tab_name == "键鼠宏":
                from core.Macro.macro_ui import MacroPanel
                widget = MacroPanel()
            elif tab_name == "钓鱼":
                from core.fishing.FishingUI import FishingUI
                widget = FishingUI()
            elif tab_name == "麻将":
                from core.Mahjong.MahjongUI import MahjongUI
                widget = MahjongUI()
            elif tab_name == "任务":
                from core.task.TaskUI import TaskUI
                widget = TaskUI()
            elif tab_name == "超强音":
                widget = self._fortissimo_tab()
                if widget is None:
                    return
            elif tab_name == "加入我们":
                from core.JoinUs.JoinUsUI import JoinUsUI
                widget = JoinUsUI()
        except Exception as e:
            QMessageBox.critical(self, f"加载失败 - {tab_name}", str(e))
            return

        if widget:
            self._lazy_tabs[tab_name] = widget
            self.tab_widget.removeTab(index)
            self.tab_widget.insertTab(index, widget, tab_name)
            self.tab_widget.setCurrentIndex(index)

    def _fortissimo_tab(self):
        try:
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
            b1.setMinimumSize(60, 35)
            b1.setStyleSheet("QPushButton{background:#0a0a2a; border:2px solid #00ffff; border-radius:10px; color:#00ffff;} QPushButton:hover{background:#00ffff; color:#050510;}")
            b2 = QPushButton("后台模式")
            b2.setMinimumSize(60, 35)
            b2.setStyleSheet("QPushButton{background:#0a0a2a; border:2px solid #ffaa00; border-radius:10px; color:#ffaa00;} QPushButton:hover{background:#ffaa00; color:#050510;}")
            b1.clicked.connect(lambda: self._launch_fortissimo('foreground'))
            b2.clicked.connect(lambda: self._launch_fortissimo('background'))
            btn_layout.addWidget(b1)
            btn_layout.addWidget(b2)
            l.addLayout(btn_layout)
            l.addWidget(QLabel("※ 前台模式会自动保持游戏窗口置顶，确保按键精准。", alignment=Qt.AlignCenter, styleSheet="color:#888888; font-size:11px; margin-top:15px;"))
            return w
        except Exception as e:
            QMessageBox.critical(self, "超强音错误", str(e))
            return None

    def _launch_fortissimo(self, mode):
        try:
            if mode == 'foreground':
                from core.Fortissimo.foreground.foreground_ui import ForegroundWindow
                self.fortissimo_win = ForegroundWindow(mode='foreground')
            else:
                from core.Fortissimo.background.background_ui import BackgroundWindow
                self.fortissimo_win = BackgroundWindow()
            self.fortissimo_win.show()
        except Exception as e:
            QMessageBox.critical(self, "Fortissimo 启动失败", str(e))

    def _global_hotkey(self):
        pass

    def manual_check_update(self):
        self.update_status.setVisible(True)
        self.update_progress.setVisible(True)
        self.update_progress.setValue(0)
        self.update_status.setText("正在检查更新...")
        self.updater.check_for_update()

    def auto_check_update(self):
        pass

    def on_check_result(self, status, info):
        if status == -1:
            QMessageBox.warning(self, "检查更新失败", info)
        elif status == 1:
            local = self.updater.get_local_version()
            box = QMessageBox(self)
            box.setWindowTitle("发现新版本")
            box.setText(f"当前版本: {local}\n最新版本: {info}\n是否立即更新？")
            btn_update = box.addButton("立即更新", QMessageBox.YesRole)
            btn_skip = box.addButton(f"跳过此版本({info})", QMessageBox.NoRole)
            btn_no = box.addButton("暂不更新", QMessageBox.RejectRole)
            box.exec_()
            if box.clickedButton() == btn_update:
                self.updater.perform_update()
            elif box.clickedButton() == btn_skip:
                self.updater.skip_this_version(info)
        else:
            QMessageBox.information(self, "检查更新", "当前已是最新版本。")
        self.update_status.setVisible(False)
        self.update_progress.setVisible(False)

    def apply_theme(self, theme_name):
        try:
            from UI.themes import get_theme
            self.setStyleSheet(get_theme(theme_name))
        except Exception as e:
            print(f"Theme error: {e}")

    def toggle_log(self):
        try:
            if self.log_viewer is None:
                from UI.logViewerUI import LogViewer
                self.log_viewer = LogViewer("nte_bohe.log")
                self.log_viewer.show()
                self.header.btn_log.setText("关闭日志")
            else:
                self.log_viewer.close()
                self.log_viewer = None
                self.header.btn_log.setText("显示日志")
        except Exception as e:
            QMessageBox.warning(self, "日志错误", str(e))

    def closeEvent(self, event):
        if self.log_viewer:
            self.log_viewer.close()
        if self.fortissimo_win:
            self.fortissimo_win.close()
        self.updater.cancel()
        event.accept()