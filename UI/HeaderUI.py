# UI/HeaderUI.py
import os
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QDialog, QVBoxLayout, QScrollArea, QMessageBox
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QPixmap


class HeaderUI(QWidget):
    checkUpdate_signal = pyqtSignal()
    toggle_log_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self.setObjectName("HeaderWidget")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)

        self.title_label = QLabel("MintNTE")
        self.title_label.setObjectName("TitleLabel")
        layout.addWidget(self.title_label)

        layout.addStretch()

        self.btn_update = QPushButton("自动更新")
        self.btn_update.setObjectName("HeaderButton")
        self.btn_update.clicked.connect(self.checkUpdate_signal.emit)
        layout.addWidget(self.btn_update)

        self.btn_log = QPushButton("显示日志")
        self.btn_log.setObjectName("HeaderButton")
        self.btn_log.clicked.connect(self.toggle_log_signal.emit)
        layout.addWidget(self.btn_log)

        self.btn_help = QPushButton("设置教程")
        self.btn_help.setObjectName("HeaderButton")
        self.btn_help.clicked.connect(self.show_tutorial)
        layout.addWidget(self.btn_help)

        self.setStyleSheet("""
        #HeaderWidget {
            background-color: #1e1e2f;
            border-bottom: 2px solid #0ff;
        }
        #TitleLabel {
            color: #0ff;
            font-size: 18px;
            font-weight: bold;
        }
        #HeaderButton {
            background-color: #2a2a3a;
            color: #0ff;
            border: 1px solid #0ff;
            border-radius: 5px;
            padding: 5px 10px;
            min-width: 80px;
        }
        #HeaderButton:hover {
            background-color: #0ff;
            color: #1e1e2f;
        }
        """)

    def show_tutorial(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        image_path = os.path.join(base_dir, "Image", "logo", "Tutorial.png")

        if not os.path.exists(image_path):
            QMessageBox.warning(self, "提示", f"教程图片未找到:\n{image_path}")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("帮助 - 游戏设置教程")
        dialog.setModal(True)
        layout = QVBoxLayout(dialog)

        # 使用滚动区域，100%显示原始图片
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        label = QLabel()
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            QMessageBox.warning(self, "错误", "图片加载失败")
            return
        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignCenter)
        scroll.setWidget(label)
        layout.addWidget(scroll)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)

        dialog.resize(800, 600)
        dialog.exec_()