import sys
import os
import threading
import time
import cv2
import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QCheckBox,
                             QPushButton, QLabel, QSpinBox, QGroupBox,
                             QMessageBox, QComboBox, QFileDialog)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QIcon

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from Module.Hwnd.game_hwnd import get_game_hwnd
from core.fishing.fishing_core import FishingCore
from core.fishing.fishing_roi.fishing_roi_core import FishingROICore
from UI import logui

# 图标路径
ICON_PATH = os.path.join(BASE_DIR, "Image", "logo", "titlelogo.ico")

BASE_ROI = (606, 64, 1319, 85)


class SimpleROIViewer(QWidget):
    """ROI实时显示窗口（仅显示ROI区域）"""
    def __init__(self, hwnd, roi_offset):
        super().__init__()
        self.hwnd = hwnd
        self.roi_offset = roi_offset
        self.actual_roi = (BASE_ROI[0], BASE_ROI[1] + roi_offset,
                           BASE_ROI[2], BASE_ROI[3] + roi_offset)
        self.core = FishingROICore(self.actual_roi)
        self.core.start()
        self.setWindowTitle("ROI 实时显示（仅ROI区域）")
        roi_w = self.actual_roi[2] - self.actual_roi[0]
        roi_h = self.actual_roi[3] - self.actual_roi[1]
        self.setMinimumSize(roi_w + 20, roi_h + 40)

        # 设置窗口图标
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout()
        layout.addWidget(self.image_label)
        self.setLayout(layout)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_view)
        self.timer.start(50)

    def update_view(self):
        data = self.core.get_data()
        full_img = self.core.get_full_screenshot()
        if full_img is None:
            return
        rx1, ry1, rx2, ry2 = self.actual_roi
        h, w = full_img.shape[:2]
        if rx2 > w or ry2 > h or rx1 < 0 or ry1 < 0:
            return
        roi_img = full_img[ry1:ry2, rx1:rx2].copy()
        rect_a = data['color_a']['rect']
        if rect_a:
            ax1, ay1, ax2, ay2 = rect_a
            cv2.rectangle(roi_img, (ax1, ay1), (ax2, ay2), (0, 0, 255), 2)
        rect_b = data['color_b']['rect']
        if rect_b:
            bx1, by1, bx2, by2 = rect_b
            cv2.rectangle(roi_img, (bx1, by1), (bx2, by2), (0, 255, 0), 2)
        rgb = cv2.cvtColor(roi_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qt_img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_img)
        scaled = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled)

    def closeEvent(self, event):
        self.core.stop()
        event.accept()


class FishingUI(QWidget):
    update_stats_signal = pyqtSignal(str)  # grade: 'A','B','S','escape','unknown'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fishing_stop_event = None
        self.fishing_thread = None
        self.follower = None
        self.setup_ui()
        self.update_stats_signal.connect(self.on_fish_grade)

    # ---------- 辅助：带图标的 QMessageBox ----------
    def _msg_box(self, icon, title, text):
        box = QMessageBox(icon, title, text, parent=self)
        if os.path.exists(ICON_PATH):
            box.setWindowIcon(QIcon(ICON_PATH))
        return box

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        # ---------- 鱼获统计 ----------
        stats_group = QGroupBox("鱼获统计")
        stats_group.setObjectName("NeonGroup")
        stats_layout = QHBoxLayout(stats_group)
        self.label_a = QLabel("A级鱼类: 0")
        self.label_b = QLabel("B级鱼类: 0")
        self.label_s = QLabel("S级鱼类: 0")
        self.label_total = QLabel("总钓鱼数: 0")
        for lbl in (self.label_a, self.label_b, self.label_s, self.label_total):
            lbl.setObjectName("StatLabel")
            lbl.setAlignment(Qt.AlignCenter)
            stats_layout.addWidget(lbl)
        main_layout.addWidget(stats_group)

        # ---------- 超时设置 ----------
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("钓鱼心跳(秒):"))
        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(1, 60)
        self.spin_timeout.setValue(60)
        self.spin_timeout.setSuffix(" 秒")
        timeout_layout.addWidget(self.spin_timeout)
        timeout_layout.addStretch()
        main_layout.addLayout(timeout_layout)

        # ---------- 跟随模式 ----------
        follow_layout = QVBoxLayout()
        follow_top = QHBoxLayout()
        follow_top.addWidget(QLabel("跟随模式:"))
        self.combo_follow = QComboBox()
        self.combo_follow.addItem("ROI跟随")
        self.combo_follow.addItem("A_I跟随")
        self.combo_follow.addItem("阈值跟随")
        self.combo_follow.setCurrentIndex(0)
        follow_top.addWidget(self.combo_follow)
        follow_top.addStretch()
        follow_layout.addLayout(follow_top)
        hint_label = QLabel("默认选ROI跟随即可！AI需要自己学Q-Learning！图色是之前的容易丢失！推荐默认即可100%跟随其他选项是UP自己测试用的")
        hint_label.setStyleSheet("color: #888; font-size: 12px;")
        hint_label.setWordWrap(True)
        follow_layout.addWidget(hint_label)
        main_layout.addLayout(follow_layout)

        # ---------- ROI 偏移量 ----------
        roi_offset_layout = QHBoxLayout()
        roi_offset_layout.addWidget(QLabel("ROI标题偏移:"))
        self.spin_roi_offset = QSpinBox()
        self.spin_roi_offset.setRange(0, 100)
        self.spin_roi_offset.setValue(0)
        self.spin_roi_offset.setSuffix(" px")
        roi_offset_layout.addWidget(self.spin_roi_offset)
        offset_hint = QLabel("如果ROI区域不准确,需要+标题偏移30")
        offset_hint.setStyleSheet("color: #888; font-size: 12px;")
        roi_offset_layout.addWidget(offset_hint)
        roi_offset_layout.addStretch()
        main_layout.addLayout(roi_offset_layout)

        # ---------- 选项 ----------
        opt_layout = QHBoxLayout()
        self.cb_fish = QCheckBox("自动钓鱼")
        self.cb_buy = QCheckBox("自动购买鱼饵")
        self.cb_sell = QCheckBox("自动售卖")
        self.cb_sell.stateChanged.connect(self.on_sell_check_changed)
        self.cb_fish.setChecked(True)
        self.cb_buy.setChecked(True)
        self.cb_sell.setChecked(False)

        self.combo_sell_mode = QComboBox()
        self.combo_sell_mode.addItem("鱼饵不足时自动售卖")
        self.combo_sell_mode.addItem("每日3:50时强制卖鱼")
        self.combo_sell_mode.setVisible(False)

        self.cb_debug_screenshot = QCheckBox("启用截图")
        self.cb_debug_screenshot.setChecked(False)

        opt_layout.addWidget(self.cb_fish)
        opt_layout.addWidget(self.cb_buy)
        opt_layout.addWidget(self.cb_sell)
        opt_layout.addWidget(self.combo_sell_mode)
        opt_layout.addWidget(self.cb_debug_screenshot)
        opt_layout.addStretch()
        main_layout.addLayout(opt_layout)

        # ---------- Q-Learning 模型管理 ----------
        self.model_group = QGroupBox("Q-Learning 模型管理")
        model_layout = QVBoxLayout(self.model_group)
        btn_model_layout = QHBoxLayout()
        self.btn_export_model = QPushButton("导出 Q 模型")
        self.btn_export_model.clicked.connect(self.export_q_model)
        btn_model_layout.addWidget(self.btn_export_model)
        self.btn_import_model = QPushButton("导入 Q 模型")
        self.btn_import_model.clicked.connect(self.import_q_model)
        btn_model_layout.addWidget(self.btn_import_model)
        model_layout.addLayout(btn_model_layout)
        self.label_q_stats = QLabel("当前学习程度: 未启动")
        self.label_q_stats.setStyleSheet("color: #0ff; font-size: 12px;")
        model_layout.addWidget(self.label_q_stats)
        main_layout.addWidget(self.model_group)
        self.model_group.setVisible(False)

        # ---------- 控制按钮 ----------
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("开始钓鱼")
        self.btn_start.setObjectName("BigStartButton")
        self.btn_start.setMinimumHeight(40)
        self.btn_start.clicked.connect(self.start_fishing)
        btn_layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("停止")
        self.btn_stop.setObjectName("BigStopButton")
        self.btn_stop.setMinimumHeight(40)
        self.btn_stop.clicked.connect(self.stop_fishing)
        self.btn_stop.setEnabled(False)
        btn_layout.addWidget(self.btn_stop)

        self.btn_roi_tool = QPushButton("ROI测试工具")
        self.btn_roi_tool.setObjectName("NeonButton")
        self.btn_roi_tool.clicked.connect(self.open_roi_tool)
        btn_layout.addWidget(self.btn_roi_tool)

        self.btn_show_roi = QPushButton("显示ROI区域")
        self.btn_show_roi.setObjectName("NeonButton")
        self.btn_show_roi.clicked.connect(self.show_roi_viewer)
        btn_layout.addWidget(self.btn_show_roi)

        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        # ---------- 界面提示文字 ----------
        tip_text = """
        <p style="font-size:22px; color:#00ffff;">界面提示：</p>
        <ol style="font-size:20px; color:#ff00ff;">
            <li>界面爱研究的可以去B站看视频</li>
            <li>默认选择就可以了！可以完美跟随</li>
            <li>ROI显示是调试用的</li>
            <li>如果鱼饵足够多！可以后台一直钓到没有鱼饵为止</li>
            <li>如果需要调用到鼠标时候最好不要抢鼠标.窗口会被强制置顶</li>
            <li>基于图色脚本为初衷!当前Up技术有限无法实现后台点击</li>
        </ol>
        """
        self.tip_label = QLabel(tip_text)
        self.tip_label.setWordWrap(True)
        main_layout.addWidget(self.tip_label)

        main_layout.addStretch()

        # ---------- 信号 ----------
        self.combo_follow.currentIndexChanged.connect(self.on_follow_mode_changed)

        # ---------- 样式 ----------
        self.setStyleSheet("""
        #NeonGroup {
            border: 1px solid #f0f;
            border-radius: 5px;
            margin-top: 10px;
        }
        #NeonGroup::title { color: #f0f;font-size: 16px; }
        #StatLabel { color: #0ff; font-size: 16px; font-weight: bold; }
        #BigStartButton {
            background-color: #2a2a3a; color: #0f0; border: 2px solid #0f0;
            border-radius: 8px; padding: 12px 30px; font-size: 18px; font-weight: bold;
        }
        #BigStartButton:hover { background-color: #0f0; color: #1e1e2f; }
        #BigStopButton {
            background-color: #2a2a3a; color: #f00; border: 2px solid #f00;
            border-radius: 8px; padding: 12px 30px; font-size: 18px; font-weight: bold;
        }
        #BigStopButton:hover { background-color: #f00; color: #1e1e2f; }
        #NeonButton {
            background-color: #2a2a3a; color: #0ff; border: 1px solid #0ff;
            border-radius: 5px; padding: 6px 15px;
        }
        #NeonButton:hover { background-color: #0ff; color: #1e1e2f; }
        QCheckBox { color: #0ff; font-size: 14px; spacing: 8px; }
        QCheckBox::indicator { width: 16px; height: 16px; }
        QLabel { color: #0ff; font-size: 14px; }
        QSpinBox, QComboBox {
            background-color: #2a2a3a; color: #0ff; border: 1px solid #0ff;
            border-radius: 4px; padding: 4px; font-size: 14px;
        }
        QComboBox::drop-down { border: none; }
        QGroupBox { color: #0ff; border: 1px solid #0ff; border-radius: 5px; margin-top: 10px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
        """)

    def on_sell_check_changed(self, state):
        self.combo_sell_mode.setVisible(state == Qt.Checked)

    def on_follow_mode_changed(self, idx):
        self.model_group.setVisible(idx == 1)

    def export_q_model(self):
        if not self.follower or not hasattr(self.follower, 'use_ai') or not self.follower.use_ai:
            self._msg_box(QMessageBox.Information, "提示", "请先启动钓鱼（A_I跟随模式）后再导出。").exec_()
            return
        path, _ = QFileDialog.getSaveFileName(self, "保存 Q 模型", "q_model.pkl", "Pickle Files (*.pkl)")
        if path:
            self.follower.save_model(path)
            self._msg_box(QMessageBox.Information, "成功", f"模型已保存至 {path}").exec_()

    def import_q_model(self):
        if not self.follower or not hasattr(self.follower, 'use_ai') or not self.follower.use_ai:
            self._msg_box(QMessageBox.Information, "提示", "请先启动钓鱼（A_I跟随模式）后再导入。").exec_()
            return
        path, _ = QFileDialog.getOpenFileName(self, "加载 Q 模型", "", "Pickle Files (*.pkl)")
        if path:
            self.follower.load_model(path)
            self._msg_box(QMessageBox.Information, "成功", f"模型已从 {path} 加载").exec_()
            self.update_q_stats()

    def update_q_stats(self):
        if self.follower and hasattr(self.follower, 'use_ai') and self.follower.use_ai:
            stats = self.follower.get_learning_stats()
            if stats:
                self.label_q_stats.setText(
                    f"Q表条目: {stats['q_entries']}  探索率 ε: {stats['epsilon']:.3f}  桶数: {stats['num_buckets']}"
                )
        else:
            self.label_q_stats.setText("当前学习程度: 未启动")

    def open_roi_tool(self):
        from core.fishing.fishing_roi.fishing_roi_ui import FishingROIWindow
        self.roi_win = FishingROIWindow()
        self.roi_win.setAttribute(Qt.WA_DeleteOnClose, False)
        self.roi_win.show()
        self.roi_win.raise_()

    def show_roi_viewer(self):
        hwnd = get_game_hwnd()
        if not hwnd:
            self._msg_box(QMessageBox.Warning, "错误", "未找到游戏窗口，请先锁定窗口。").exec_()
            return
        offset = self.spin_roi_offset.value()
        self.roi_viewer = SimpleROIViewer(hwnd, offset)
        self.roi_viewer.setAttribute(Qt.WA_DeleteOnClose)
        self.roi_viewer.show()
        self.roi_viewer.raise_()

    def toggle_fishing(self):
        if self.fishing_thread and self.fishing_thread.is_alive():
            self.stop_fishing()
        else:
            self.start_fishing()

    def start_fishing(self):
        hwnd = get_game_hwnd()
        if not hwnd:
            self._msg_box(QMessageBox.Warning, "错误", "未找到游戏窗口，请先锁定窗口。").exec_()
            return
        self.fishing_stop_event = threading.Event()
        timeout = self.spin_timeout.value()
        sell_mode = 0
        if self.cb_sell.isChecked():
            sell_mode = self.combo_sell_mode.currentIndex() + 1
        follow_mode = self.combo_follow.currentIndex()
        roi_offset = self.spin_roi_offset.value()
        enable_debug = self.cb_debug_screenshot.isChecked()
        self.fishing_core = FishingCore(hwnd, self.fishing_stop_event,
                                        timeout=timeout,
                                        sell_mode=sell_mode,
                                        follow_mode=follow_mode,
                                        roi_offset=roi_offset,
                                        enable_debug_screenshot=enable_debug,
                                        stats_callback=lambda grade: self.update_stats_signal.emit(grade))
        self.fishing_thread = threading.Thread(target=self.fishing_core.run, daemon=True)
        self.fishing_thread.start()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        logui.info("钓鱼已开始")

        def set_follower():
            time.sleep(0.5)
            self.follower = self.fishing_core.roi_follower
            self.update_q_stats()
        threading.Thread(target=set_follower, daemon=True).start()

    def stop_fishing(self):
        if self.fishing_stop_event:
            self.fishing_stop_event.set()
        if self.fishing_thread and self.fishing_thread.is_alive():
            self.fishing_thread.join(timeout=2)
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        logui.info("钓鱼已停止")
        self.follower = None
        self.update_q_stats()

    # ---------- 统计更新 ----------
    def on_fish_grade(self, grade):
        if grade == 'A':
            self._add_count(self.label_a)
        elif grade == 'B':
            self._add_count(self.label_b)
        elif grade == 'S':
            self._add_count(self.label_s)
        # 总钓鱼数增加（逃走不计）
        if grade in ('A', 'B', 'S', 'unknown'):
            self._add_count(self.label_total)

    def _add_count(self, label):
        text = label.text()
        try:
            prefix, num = text.rsplit(':', 1)
            new_num = int(num.strip()) + 1
            label.setText(f"{prefix}: {new_num}")
        except:
            pass

    def closeEvent(self, event):
        self.stop_fishing()
        event.accept()