# core/fishing/FishingUI.py
# 钓鱼功能模块 - 提供自动钓鱼功能的用户界面
# 主要功能：
#   1. 鱼获统计：显示A级、B级、S级鱼类捕获数量和总钓鱼数
#   2. 超时设置：设置钓鱼心跳时间
#   3. 跟随模式：支持ROI跟随和阈值跟随两种模式
#   4. ROI设置：调整标题偏移量
#   5. 功能选项：自动钓鱼、自动购买鱼饵、自动售卖、启用截图
#   6. 控制按钮：开始钓鱼、停止、ROI测试工具、显示ROI区域

import sys
import os
import threading
import cv2
import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QCheckBox,
    QPushButton, QLabel, QSpinBox, QGroupBox,
    QMessageBox, QComboBox, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QIcon, QFont

# 添加项目根目录到路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from Module.Hwnd.game_hwnd import get_game_hwnd
from core.fishing.fishing_core import FishingCore
from core.fishing.fishing_roi.fishing_roi_core import FishingROICore
from UI import logui
from UI.themes import get_theme


# ========== 常量定义 ==========

# 图标路径
ICON_PATH = os.path.join(BASE_DIR, "Image", "logo", "titlelogo.ico")

# 默认ROI区域（游戏窗口内的目标检测区域）
BASE_ROI = (606, 64, 1319, 85)


# ========== ROI实时查看器 ==========

class SimpleROIViewer(QWidget):
    """
    ROI实时显示窗口
    
    用于显示游戏窗口中ROI区域的实时画面，帮助用户调试和验证ROI设置。
    
    Attributes:
        hwnd: 游戏窗口句柄
        roi_offset: ROI偏移量
        actual_roi: 实际的ROI区域坐标
        core: FishingROICore实例，负责捕获和处理图像
        image_label: 显示图像的QLabel
        timer: 更新画面的定时器
    """
    
    def __init__(self, hwnd, roi_offset):
        """
        初始化ROI查看器
        
        Args:
            hwnd: 游戏窗口句柄
            roi_offset: ROI垂直偏移量（用于调整标题位置）
        """
        super().__init__()
        
        # 保存参数
        self.hwnd = hwnd
        self.roi_offset = roi_offset
        
        # 计算实际ROI区域
        self.actual_roi = (
            BASE_ROI[0], 
            BASE_ROI[1] + roi_offset,
            BASE_ROI[2], 
            BASE_ROI[3] + roi_offset
        )
        
        # 创建ROI核心处理器
        self.core = FishingROICore(self.actual_roi)
        self.core.start()
        
        # 设置窗口属性
        self.setWindowTitle("ROI 实时显示（仅ROI区域）")
        
        # 设置窗口大小（基于ROI尺寸）
        roi_w = self.actual_roi[2] - self.actual_roi[0]
        roi_h = self.actual_roi[3] - self.actual_roi[1]
        self.setMinimumSize(roi_w + 20, roi_h + 40)
        
        # 设置窗口图标
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))
        
        # 初始化UI
        self._init_ui()
    
    def _init_ui(self):
        """初始化UI布局"""
        # 图像显示标签
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        
        # 布局
        layout = QVBoxLayout()
        layout.addWidget(self.image_label)
        self.setLayout(layout)
        
        # 更新定时器（50ms间隔）
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_view)
        self.timer.start(50)
    
    def update_view(self):
        """更新ROI显示画面"""
        # 获取ROI数据和全屏截图
        data = self.core.get_data()
        full_img = self.core.get_full_screenshot()
        
        if full_img is None:
            return
        
        # 提取ROI区域
        rx1, ry1, rx2, ry2 = self.actual_roi
        h, w = full_img.shape[:2]
        
        # 边界检查
        if rx2 > w or ry2 > h or rx1 < 0 or ry1 < 0:
            return
        
        # 截取ROI图像
        roi_img = full_img[ry1:ry2, rx1:rx2].copy()
        
        # 绘制颜色A区域（红色框）
        rect_a = data['color_a']['rect']
        if rect_a:
            ax1, ay1, ax2, ay2 = rect_a
            cv2.rectangle(roi_img, (ax1, ay1), (ax2, ay2), (0, 0, 255), 2)
        
        # 绘制颜色B区域（绿色框）
        rect_b = data['color_b']['rect']
        if rect_b:
            bx1, by1, bx2, by2 = rect_b
            cv2.rectangle(roi_img, (bx1, by1), (bx2, by2), (0, 255, 0), 2)
        
        # 转换格式并显示
        rgb = cv2.cvtColor(roi_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qt_img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_img)
        scaled = pixmap.scaled(
            self.image_label.size(), 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)
    
    def closeEvent(self, event):
        """
        关闭窗口时清理资源
        
        Args:
            event: QCloseEvent - 关闭事件
        """
        self.core.stop()
        event.accept()


# ========== 钓鱼主界面 ==========

class FishingUI(QWidget):
    """
    钓鱼功能主界面
    
    提供完整的自动钓鱼功能控制界面，包括：
    - 鱼获统计显示
    - 超时设置
    - 跟随模式选择
    - ROI偏移调整
    - 功能选项开关
    - 控制按钮
    
    Signals:
        update_stats_signal: 鱼获统计更新信号，参数为鱼的等级('A', 'B', 'S', 'escape', 'unknown')
    """
    
    update_stats_signal = pyqtSignal(str)
    
    def __init__(self, parent=None):
        """
        初始化钓鱼界面
        
        Args:
            parent: 父窗口对象
        """
        super().__init__(parent)
        
        # ========== 状态变量 ==========
        self.fishing_stop_event = None  # 停止钓鱼事件
        self.fishing_thread = None      # 钓鱼线程
        self.fishing_core = None        # 钓鱼核心实例
        
        # ========== 初始化UI ==========
        self.setup_ui()
        
        # ========== 连接信号 ==========
        self.update_stats_signal.connect(self.on_fish_grade)
    
    # ========== 辅助方法 ==========
    
    def _msg_box(self, icon, title, text):
        """
        创建带图标的消息框
        
        Args:
            icon: QMessageBox图标类型
            title: 消息框标题
            text: 消息内容
        
        Returns:
            QMessageBox: 配置好的消息框对象
        """
        box = QMessageBox(icon, title, text, parent=self)
        if os.path.exists(ICON_PATH):
            box.setWindowIcon(QIcon(ICON_PATH))
        return box
    
    # ========== UI初始化 ==========
    
    def setup_ui(self):
        """设置钓鱼界面的UI布局"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(16, 16, 16, 16)
        
        # 1. 鱼获统计区域
        stats_group = self._create_stats_group()
        main_layout.addWidget(stats_group)
        
        # 2. 超时设置区域
        timeout_group = self._create_timeout_group()
        main_layout.addWidget(timeout_group)
        
        # 3. 跟随模式与ROI设置区域
        follow_roi_group = self._create_follow_roi_group()
        main_layout.addWidget(follow_roi_group)
        
        # 4. 功能选项区域
        opt_group = self._create_options_group()
        main_layout.addWidget(opt_group)
        
        # 5. 控制按钮区域
        btn_layout = self._create_button_layout()
        main_layout.addLayout(btn_layout)
        
        # 添加拉伸空间
        main_layout.addStretch()
        
        # 应用主题样式
        self._apply_styles()
    
    def _create_stats_group(self):
        """创建鱼获统计区域"""
        # 创建标题标签
        title_label = QLabel("鱼获统计")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setObjectName("InfoGroupTitle")
        title_font = QFont("Microsoft YaHei", 50, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: rgba(0, 220, 180, 0.95); font-size: 30px; font-weight: bold;")
        
        # 创建内容框架
        stats_group = QFrame()
        stats_group.setObjectName("InfoGroup")
        
        stats_layout = QHBoxLayout(stats_group)
        stats_layout.setSpacing(20)
        
        # 统计标签
        self.label_a = QLabel("A级鱼类: 0")
        self.label_b = QLabel("B级鱼类: 0")
        self.label_s = QLabel("S级鱼类: 0")
        self.label_total = QLabel("总钓鱼数: 0")
        
        # 设置标签样式
        for lbl in (self.label_a, self.label_b, self.label_s, self.label_total):
            lbl.setObjectName("StatLabel")
            lbl.setAlignment(Qt.AlignCenter)
            stats_layout.addWidget(lbl)
        
        # 创建垂直布局
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.addWidget(title_label)
        main_layout.addWidget(stats_group)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        return container
    
    def _create_timeout_group(self):
        """创建超时设置区域"""
        # 创建标题标签
        title_label = QLabel("超时设置")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("Microsoft YaHei", 50, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: rgba(0, 220, 180, 0.95); font-size: 30px; font-weight: bold; padding-bottom: 8px;")
        
        # 创建内容框架
        timeout_group = QFrame()
        timeout_group.setObjectName("InfoGroup")
        
        timeout_layout = QHBoxLayout(timeout_group)
        timeout_layout.setSpacing(12)
        
        # 标签
        timeout_layout.addWidget(QLabel("钓鱼心跳(秒):"))
        
        # 数值输入框
        self.spin_timeout = QSpinBox()
        self.spin_timeout.setObjectName("InfoField")
        self.spin_timeout.setRange(1, 60)
        self.spin_timeout.setValue(60)
        self.spin_timeout.setSuffix(" 秒")
        timeout_layout.addWidget(self.spin_timeout)
        
        # 拉伸空间
        timeout_layout.addStretch()
        
        # 创建垂直布局容器
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.addWidget(title_label)
        main_layout.addWidget(timeout_group)
        main_layout.setSpacing(4)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        return container
    
    def _create_follow_roi_group(self):
        """创建跟随模式与ROI设置区域"""
        # 创建标题标签
        title_label = QLabel("跟随与ROI设置")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("Microsoft YaHei", 50, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: rgba(0, 220, 180, 0.95); font-size: 30px; font-weight: bold; padding-bottom: 8px;")
        
        # 创建内容框架
        follow_roi_group = QFrame()
        follow_roi_group.setObjectName("InfoGroup")
        
        follow_roi_layout = QVBoxLayout(follow_roi_group)
        follow_roi_layout.setSpacing(12)
        
        # 水平布局：跟随模式与标题偏移
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(40)
        
        # 跟随模式选择
        controls_layout.addWidget(QLabel("跟随模式:"))
        self.combo_follow = QComboBox()
        self.combo_follow.setObjectName("ActionComboBox")
        self.combo_follow.addItem("ROI跟随")
        self.combo_follow.addItem("阈值跟随")
        self.combo_follow.setCurrentIndex(0)
        controls_layout.addWidget(self.combo_follow)
        
        # 标题偏移设置
        controls_layout.addWidget(QLabel("标题偏移:"))
        self.spin_roi_offset = QSpinBox()
        self.spin_roi_offset.setObjectName("InfoField")
        self.spin_roi_offset.setRange(0, 100)
        self.spin_roi_offset.setValue(0)
        self.spin_roi_offset.setSuffix(" px")
        controls_layout.addWidget(self.spin_roi_offset)
        
        # 拉伸空间
        controls_layout.addStretch()
        follow_roi_layout.addLayout(controls_layout)
        
        # 提示信息
        hint_label = QLabel(
            "默认选ROI跟随即可！图色是之前的容易丢失！推荐默认即可100%跟随。"
            "如果ROI区域不准确,需要+标题偏移30"
        )
        hint_label.setStyleSheet("color: rgba(160, 190, 220, 0.6); font-size: 12px;")
        hint_label.setWordWrap(True)
        follow_roi_layout.addWidget(hint_label)
        
        # 创建垂直布局容器
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.addWidget(title_label)
        main_layout.addWidget(follow_roi_group)
        main_layout.setSpacing(4)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        return container
    
    def _create_options_group(self):
        """创建功能选项区域"""
        # 创建标题标签
        title_label = QLabel("功能选项")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont("Microsoft YaHei", 50, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: rgba(0, 220, 180, 0.95); font-size: 30px; font-weight: bold; padding-bottom: 8px;")
        
        # 创建内容框架
        opt_group = QFrame()
        opt_group.setObjectName("InfoGroup")
        
        opt_layout = QHBoxLayout(opt_group)
        opt_layout.setSpacing(20)
        
        # 自动钓鱼
        self.cb_fish = QCheckBox("自动钓鱼")
        self.cb_fish.setChecked(True)
        
        # 自动购买鱼饵
        self.cb_buy = QCheckBox("自动购买鱼饵")
        self.cb_buy.setChecked(True)
        
        # 鱼饵不足时自动售卖
        self.cb_sell = QCheckBox("鱼饵不足时自动售卖")
        self.cb_sell.setChecked(False)
        
        # 启用截图（调试用）
        self.cb_debug_screenshot = QCheckBox("启用截图")
        self.cb_debug_screenshot.setChecked(False)
        
        # 添加到布局
        opt_layout.addWidget(self.cb_fish)
        opt_layout.addWidget(self.cb_buy)
        opt_layout.addWidget(self.cb_sell)
        opt_layout.addWidget(self.cb_debug_screenshot)
        opt_layout.addStretch()
        
        # 创建垂直布局容器
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.addWidget(title_label)
        main_layout.addWidget(opt_group)
        main_layout.setSpacing(4)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        return container
    
    def _create_button_layout(self):
        """创建控制按钮布局"""
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        # 开始钓鱼按钮
        self.btn_start = QPushButton("开始钓鱼")
        self.btn_start.setObjectName("ActionButton")
        self.btn_start.setMinimumHeight(50)
        self.btn_start.clicked.connect(self.start_fishing)
        btn_layout.addWidget(self.btn_start)
        
        # 停止按钮
        self.btn_stop = QPushButton("停止")
        self.btn_stop.setObjectName("ActionButton")
        self.btn_stop.setMinimumHeight(50)
        self.btn_stop.clicked.connect(self.stop_fishing)
        self.btn_stop.setEnabled(False)
        btn_layout.addWidget(self.btn_stop)
        
        # ROI测试工具按钮
        self.btn_roi_tool = QPushButton("ROI测试工具")
        self.btn_roi_tool.setObjectName("ActionButton")
        self.btn_roi_tool.setMinimumHeight(50)
        self.btn_roi_tool.clicked.connect(self.open_roi_tool)
        btn_layout.addWidget(self.btn_roi_tool)
        
        # 显示ROI区域按钮
        self.btn_show_roi = QPushButton("显示ROI区域")
        self.btn_show_roi.setObjectName("ActionButton")
        self.btn_show_roi.setMinimumHeight(50)
        self.btn_show_roi.clicked.connect(self.show_roi_viewer)
        btn_layout.addWidget(self.btn_show_roi)
        
        # 拉伸空间
        btn_layout.addStretch()
        
        return btn_layout
    
    def _apply_styles(self):
        """应用界面样式"""
        # 应用全局主题
        self.setStyleSheet(get_theme())
        
        # 添加自定义样式
        custom_style = """
            /* 统计标签样式 */
            #StatLabel {
                color: rgba(0, 220, 180, 0.95);
                font-size: 22px;
                font-weight: bold;
                font-family: "Microsoft YaHei", "SimHei", sans-serif;
            }
            
            /* 普通标签样式 */
            QLabel {
                color: rgba(180, 210, 240, 0.9);
                font-size: 16px;
                font-family: "Microsoft YaHei", "SimHei", sans-serif;
            }
            
            /* 数字输入框样式 */
            QSpinBox#InfoField {
                font-size: 16px;
                min-width: 100px;
                padding: 6px 10px;
                font-family: "Microsoft YaHei", "SimHei", sans-serif;
            }
            
            /* 按钮样式 */
            QPushButton#ActionButton {
                min-height: 46px;
                font-size: 20px;
                font-weight: bold;
                font-family: "Microsoft YaHei", "SimHei", sans-serif;
            }
            
            /* 分组框标题样式 */
            QGroupBox#InfoGroup::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                font-size: 28px;
                font-weight: bold;
                font-family: "Microsoft YaHei", "SimHei", sans-serif;
                color: rgba(0, 220, 180, 0.95);
            }
        """
        
        self.setStyleSheet(self.styleSheet() + custom_style)
    
    # ========== 功能方法 ==========
    
    def open_roi_tool(self):
        """打开ROI测试工具窗口"""
        from core.fishing.fishing_roi.fishing_roi_ui import FishingROIWindow
        self.roi_win = FishingROIWindow()
        self.roi_win.setAttribute(Qt.WA_DeleteOnClose, False)
        self.roi_win.show()
        self.roi_win.raise_()
    
    def show_roi_viewer(self):
        """显示ROI实时查看器"""
        hwnd = get_game_hwnd()
        
        if not hwnd:
            self._msg_box(
                QMessageBox.Warning, 
                "错误", 
                "未找到游戏窗口，请先锁定窗口。"
            ).exec_()
            return
        
        # 获取当前ROI偏移量
        offset = self.spin_roi_offset.value()
        
        # 创建并显示ROI查看器
        self.roi_viewer = SimpleROIViewer(hwnd, offset)
        self.roi_viewer.setAttribute(Qt.WA_DeleteOnClose)
        self.roi_viewer.show()
        self.roi_viewer.raise_()
    
    def toggle_fishing(self):
        """切换钓鱼状态（开始/停止）"""
        if self.fishing_thread and self.fishing_thread.is_alive():
            self.stop_fishing()
        else:
            self.start_fishing()
    
    def start_fishing(self):
        """开始钓鱼"""
        # 检查游戏窗口
        hwnd = get_game_hwnd()
        if not hwnd:
            self._msg_box(
                QMessageBox.Warning, 
                "错误", 
                "未找到游戏窗口，请先锁定窗口。"
            ).exec_()
            return
        
        # 创建停止事件
        self.fishing_stop_event = threading.Event()
        
        # 获取配置参数
        timeout = self.spin_timeout.value()
        sell_mode = 1 if self.cb_sell.isChecked() else 0
        follow_mode = self.combo_follow.currentIndex()
        roi_offset = self.spin_roi_offset.value()
        enable_debug = self.cb_debug_screenshot.isChecked()
        
        # 创建钓鱼核心实例
        self.fishing_core = FishingCore(
            hwnd, 
            self.fishing_stop_event,
            timeout=timeout,
            sell_mode=sell_mode,
            follow_mode=follow_mode,
            roi_offset=roi_offset,
            enable_debug_screenshot=enable_debug,
            stats_callback=lambda grade: self.update_stats_signal.emit(grade)
        )
        
        # 启动钓鱼线程
        self.fishing_thread = threading.Thread(
            target=self.fishing_core.run, 
            daemon=True
        )
        self.fishing_thread.start()
        
        # 更新UI状态
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        
        # 记录日志
        logui.info("钓鱼已开始")
    
    def stop_fishing(self):
        """停止钓鱼"""
        # 设置停止事件
        if self.fishing_stop_event:
            self.fishing_stop_event.set()
        
        # 等待线程结束
        if self.fishing_thread and self.fishing_thread.is_alive():
            self.fishing_thread.join(timeout=2)
        
        # 更新UI状态
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        
        # 记录日志
        logui.info("钓鱼已停止")
    
    # ========== 统计更新方法 ==========
    
    def on_fish_grade(self, grade):
        """
        处理鱼获统计更新
        
        Args:
            grade: 鱼的等级 ('A', 'B', 'S', 'escape', 'unknown')
        """
        if grade == 'A':
            self._add_count(self.label_a)
        elif grade == 'B':
            self._add_count(self.label_b)
        elif grade == 'S':
            self._add_count(self.label_s)
        
        # 总钓鱼数增加（逃走不计入）
        if grade in ('A', 'B', 'S', 'unknown'):
            self._add_count(self.label_total)
    
    def _add_count(self, label):
        """
        增加标签显示的数值
        
        Args:
            label: QLabel对象，格式为 "前缀: 数值"
        """
        text = label.text()
        try:
            # 分割前缀和数值
            prefix, num = text.rsplit(':', 1)
            new_num = int(num.strip()) + 1
            label.setText(f"{prefix}: {new_num}")
        except Exception:
            pass
    
    # ========== 窗口生命周期 ==========
    
    def closeEvent(self, event):
        """
        关闭窗口时停止钓鱼
        
        Args:
            event: QCloseEvent - 关闭事件
        """
        self.stop_fishing()
        event.accept()