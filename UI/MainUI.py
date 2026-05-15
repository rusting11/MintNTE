# UI/MainUI.py
# 主界面模块 - 应用程序主窗口，负责管理各功能模块的加载和切换
# 主要功能：
#   1. 主窗口布局管理
#   2. 标签页懒加载（按需加载各功能模块）
#   3. 全局快捷键管理
#   4. 主题样式应用
#   5. 日志查看器管理
#   6. 自动更新检查

import sys
import os
import ctypes
from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QVBoxLayout, QWidget,
    QLabel, QHBoxLayout, QPushButton, QProgressBar,
    QShortcut, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QKeySequence, QFont

# 添加项目根目录到路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from UI.HeaderUI import HeaderUI
from UI.themes import get_theme


class MainUI(QMainWindow):
    """
    应用程序主窗口
    
    负责管理所有功能模块的加载、切换和生命周期。
    
    Attributes:
        tab_widget: QTabWidget - 标签页容器
        window_detect: WindowDetectUI - 窗口检测模块（默认加载）
        _lazy_tabs: dict - 懒加载的标签页缓存
        log_viewer: LogViewer - 日志查看器窗口
        fortissimo_win: QWidget - 超强音功能窗口
        updater: Updater - 自动更新器
        update_status: QLabel - 更新状态标签
        update_progress: QProgressBar - 更新进度条
    """
    
    def __init__(self):
        """初始化主窗口"""
        super().__init__()
        
        # ========== 窗口基础设置 ==========
        self.setWindowTitle("MintNTE")
        self.resize(1200, 900)
        self.setMinimumSize(1000, 600)
        
        # 设置窗口图标
        self._set_window_icon()
        
        # 设置任务栏图标（Windows）
        self._set_taskbar_icon()
        
        # ========== 初始化UI布局 ==========
        self._init_layout()
        
        # ========== 初始化标签页 ==========
        self._init_tabs()
        
        # ========== 初始化更新器 ==========
        self._init_updater()
        
        # ========== 初始化全局快捷键 ==========
        self._init_shortcuts()
        
        # ========== 应用主题样式 ==========
        self.apply_theme()
    
    def _set_window_icon(self):
        """设置窗口图标"""
        icon_path = os.path.join(BASE_DIR, "Image", "logo", "titlelogo.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
    
    def _set_taskbar_icon(self):
        """设置任务栏图标（仅Windows）"""
        if hasattr(ctypes, 'windll'):
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('daoqi.MintNTE')
    
    def _init_layout(self):
        """初始化主布局"""
        # 中央控件
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        
        # 主布局
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 添加头部
        self.header = HeaderUI()
        layout.addWidget(self.header)
        
        # 头部与标签页之间的间距
        layout.addSpacing(10)
        
        # 标签页容器
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("MainTabWidget")
        layout.addWidget(self.tab_widget)
        
        # 更新状态区域
        self._init_update_status(layout)
    
    def _init_update_status(self, parent_layout):
        """初始化更新状态显示"""
        # 更新状态标签
        self.update_status = QLabel("")
        self.update_status.setStyleSheet("color:#00ffff; font-size:12px;")
        self.update_status.setVisible(False)
        parent_layout.addWidget(self.update_status)
        
        # 更新进度条
        self.update_progress = QProgressBar()
        self.update_progress.setMaximum(100)
        self.update_progress.setVisible(False)
        parent_layout.addWidget(self.update_progress)
    
    def _init_tabs(self):
        """初始化标签页（懒加载模式）"""
        # 懒加载缓存字典
        self._lazy_tabs = {}
        
        # 1. 窗口检测（默认立即加载）
        from core.window_detect.window_detect_ui import WindowDetectUI
        self.window_detect = WindowDetectUI()
        self.tab_widget.addTab(self.window_detect, "👁️ 窗口检测")
        self.window_detect.show_log_signal.connect(self.toggle_log)
        
        # 2. 其他标签页（懒加载）
        lazy_tab_config = [
            (1, "🎮 键鼠宏", "键鼠宏"),
            (2, "🎣 钓鱼", "钓鱼"),
            (3, "🎁 兑换码", "兑换码"),
            (4, "📋 任务交互", "任务交互"),
            (5, "🎵 超强音", "超强音")
        ]
        
        for _, display_name, _ in lazy_tab_config:
            self.tab_widget.addTab(QWidget(), display_name)
        
        # 连接标签页切换信号
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
    
    def _init_updater(self):
        """初始化自动更新器"""
        from updater.updater import Updater
        self.updater = Updater(parent=self)
        
        # 连接更新器信号
        self.updater.checkResult.connect(self.on_check_result)
        self.updater.progress.connect(self.update_progress.setValue)
        self.updater.status.connect(self.update_status.setText)
    
    def _init_shortcuts(self):
        """初始化全局快捷键"""
        self.log_viewer = None
        self.fortissimo_win = None
        
        # Alt+F1 快捷键（预留）
        self.shortcut = QShortcut(QKeySequence("Alt+F1"), self)
        self.shortcut.activated.connect(self._global_hotkey)
    
    # ========== 标签页懒加载 ==========
    
    def _on_tab_changed(self, index):
        """
        标签页切换处理函数
        
        当用户切换到未加载的标签页时，动态加载对应的功能模块。
        
        Args:
            index: int - 当前选中的标签页索引
        """
        # 跳过窗口检测（已加载）和无效索引
        if index <= 0:
            return
        
        # 获取标签页配置
        tab_info = self._get_tab_info(index)
        if not tab_info:
            return
        
        tab_name, display_name = tab_info
        
        # 如果已加载，直接返回
        if tab_name in self._lazy_tabs:
            return
        
        # 动态加载模块
        widget = self._load_module_widget(tab_name)
        if widget:
            self._lazy_tabs[tab_name] = widget
            self._replace_tab(index, widget, display_name)
    
    def _get_tab_info(self, index):
        """
        根据索引获取标签页信息
        
        Args:
            index: int - 标签页索引
        
        Returns:
            tuple: (tab_name, display_name) 或 None
        """
        tab_map = {
            1: ("键鼠宏", "🎮 键鼠宏"),
            2: ("钓鱼", "🎣 钓鱼"),
            3: ("兑换码", "🎁 兑换码"),
            4: ("任务交互", "📋 任务交互"),
            5: ("超强音", "🎵 超强音")
        }
        return tab_map.get(index, None)
    
    def _load_module_widget(self, tab_name):
        """
        根据模块名称加载对应的UI组件
        
        Args:
            tab_name: str - 模块名称
        
        Returns:
            QWidget: 加载的UI组件，加载失败返回None
        """
        try:
            if tab_name == "键鼠宏":
                from core.Macro.macro_ui import MacroPanel
                return MacroPanel()
            
            elif tab_name == "钓鱼":
                from core.fishing.FishingUI import FishingUI
                return FishingUI()
            
            elif tab_name == "任务交互":
                from core.task.TaskUI import TaskUI
                return TaskUI()
            
            elif tab_name == "超强音":
                return self._create_fortissimo_tab()
            
            elif tab_name == "兑换码":
                return self._create_redeem_tab()
            
        except Exception as e:
            QMessageBox.critical(self, f"加载失败 - {tab_name}", str(e))
            return None
        
        return None
    
    def _replace_tab(self, index, widget, display_name):
        """
        替换标签页内容
        
        Args:
            index: int - 标签页索引
            widget: QWidget - 新的UI组件
            display_name: str - 显示名称
        """
        self.tab_widget.removeTab(index)
        self.tab_widget.insertTab(index, widget, display_name)
        self.tab_widget.setCurrentIndex(index)
    
    def _create_fortissimo_tab(self):
        """创建超强音功能标签页"""
        try:
            w = QWidget()
            layout = QVBoxLayout(w)
            layout.setAlignment(Qt.AlignCenter)
            layout.setContentsMargins(40, 40, 40, 40)
            layout.setSpacing(20)
            
            # 标题
            title = QLabel("Fortissimo 自动演奏")
            title.setFont(QFont("Microsoft YaHei", 22, QFont.Bold))
            title.setAlignment(Qt.AlignCenter)
            title.setStyleSheet("color: #ffffff; background: transparent;")
            layout.addWidget(title)
            
            # 描述文本
            desc_style = """
                QLabel {
                    color: rgba(180, 220, 255, 0.7);
                    font-size: 16px;
                    font-family: 'Microsoft YaHei';
                    background: transparent;
                }
            """
            layout.addWidget(
                QLabel("前台模式命中率高达 98% 以上 · 游戏窗口自动置顶", 
                       alignment=Qt.AlignCenter, styleSheet=desc_style)
            )
            layout.addWidget(
                QLabel("后台模式命中率可达 80% 以上 · 无额外限制", 
                       alignment=Qt.AlignCenter, styleSheet=desc_style)
            )
            
            layout.addSpacing(25)
            
            # 按钮布局
            btn_layout = QHBoxLayout()
            btn_layout.setSpacing(40)
            btn_layout.setAlignment(Qt.AlignCenter)
            
            # 前台模式按钮
            b1 = QPushButton("⚡ 前台模式")
            b1.setStyleSheet(self._get_fortissimo_btn_style(primary=True))
            b1.clicked.connect(lambda: self._launch_fortissimo('foreground'))
            
            # 后台模式按钮
            b2 = QPushButton("🔒 后台模式")
            b2.setStyleSheet(self._get_fortissimo_btn_style(primary=False))
            b2.clicked.connect(lambda: self._launch_fortissimo('background'))
            
            btn_layout.addWidget(b1)
            btn_layout.addWidget(b2)
            layout.addLayout(btn_layout)
            
            # 提示信息
            note_style = """
                QLabel {
                    color: rgba(150, 170, 190, 0.6);
                    font-size: 12px;
                    font-family: 'Microsoft YaHei';
                    background: transparent;
                    margin-top: 20px;
                }
            """
            layout.addWidget(
                QLabel("※ 前台模式会自动保持游戏窗口置顶，确保按键精准。", 
                       alignment=Qt.AlignCenter, styleSheet=note_style)
            )
            
            return w
        
        except Exception as e:
            QMessageBox.critical(self, "超强音错误", str(e))
            return None
    
    def _get_fortissimo_btn_style(self, primary=True):
        """获取超强音按钮样式"""
        if primary:
            return """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(0, 180, 220, 0.35),
                        stop:1 rgba(0, 200, 160, 0.25));
                    color: #e0f8ff;
                    border: 2px solid rgba(0, 255, 200, 0.5);
                    border-radius: 14px;
                    padding: 14px 40px;
                    font-size: 15px;
                    font-weight: bold;
                    font-family: 'Microsoft YaHei';
                    min-width: 160px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(0, 200, 240, 0.55),
                        stop:1 rgba(0, 255, 200, 0.45));
                    border: 2px solid rgba(0, 255, 200, 0.8);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(0, 140, 180, 0.6),
                        stop:1 rgba(0, 180, 140, 0.5));
                }
            """
        else:
            return """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(255, 170, 0, 0.3),
                        stop:1 rgba(255, 140, 0, 0.2));
                    color: #fff4e0;
                    border: 2px solid rgba(255, 180, 0, 0.5);
                    border-radius: 14px;
                    padding: 14px 40px;
                    font-size: 15px;
                    font-weight: bold;
                    font-family: 'Microsoft YaHei';
                    min-width: 160px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(255, 190, 0, 0.5),
                        stop:1 rgba(255, 160, 0, 0.4));
                    border: 2px solid rgba(255, 200, 0, 0.8);
                }
                QPushButton:pressed {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(200, 130, 0, 0.5),
                        stop:1 rgba(220, 110, 0, 0.4));
                }
            """
    
    def _create_redeem_tab(self):
        """创建兑换码功能标签页（占位）"""
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignCenter)
        
        label = QLabel("兑换码功能开发中")
        label.setStyleSheet("color: rgba(180, 210, 240, 0.6); font-size: 18px;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        
        return w
    
    def _launch_fortissimo(self, mode):
        """
        启动超强音功能
        
        Args:
            mode: str - 'foreground' 或 'background'
        """
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
        """全局快捷键处理（预留）"""
        pass
    
    # ========== 更新相关方法 ==========
    
    def manual_check_update(self):
        """手动检查更新"""
        self.update_status.setVisible(True)
        self.update_progress.setVisible(True)
        self.update_progress.setValue(0)
        self.update_status.setText("正在检查更新...")
        self.updater.check_for_update()
    
    def auto_check_update(self):
        """自动检查更新（预留）"""
        pass
    
    def on_check_result(self, status, info):
        """
        处理更新检查结果
        
        Args:
            status: int - 更新状态 (-1: 失败, 0: 已是最新, 1: 有新版本)
            info: str - 额外信息（版本号或错误信息）
        """
        if status == -1:
            QMessageBox.warning(self, "检查更新失败", info)
        
        elif status == 1:
            # 有新版本
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
        
        # 隐藏更新状态
        self.update_status.setVisible(False)
        self.update_progress.setVisible(False)
    
    # ========== 主题应用 ==========
    
    def apply_theme(self):
        """应用主题样式"""
        try:
            self.setStyleSheet(get_theme())
        except Exception as e:
            print(f"Theme error: {e}")
    
    # ========== 日志查看器 ==========
    
    def toggle_log(self):
        """切换日志查看器显示/隐藏"""
        try:
            if self.log_viewer is None:
                from UI.logViewerUI import LogViewer
                self.log_viewer = LogViewer("nte_bohe.log")
                self.log_viewer.show()
                self.window_detect.btn_log.setText("关闭日志")
            else:
                self.log_viewer.close()
                self.log_viewer = None
                self.window_detect.btn_log.setText("显示日志")
        except Exception as e:
            QMessageBox.warning(self, "日志错误", str(e))
    
    # ========== 窗口生命周期 ==========
    
    def closeEvent(self, event):
        """
        关闭窗口时清理资源
        
        Args:
            event: QCloseEvent - 关闭事件
        """
        # 关闭日志查看器
        if self.log_viewer:
            self.log_viewer.close()
        
        # 关闭超强音窗口
        if self.fortissimo_win:
            self.fortissimo_win.close()
        
        # 取消更新
        self.updater.cancel()
        
        # 接受关闭事件
        event.accept()