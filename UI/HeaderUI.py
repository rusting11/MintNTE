# UI/HeaderUI.py
import os
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap


class HeaderUI(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(56)
        self.setObjectName("HeaderWidget")
        self.setAttribute(Qt.WA_StyledBackground)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        logo_path = os.path.join(base_dir, "Image", "logo", "titlelogo.ico")

        self.logo_label = QLabel()
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            self.logo_label.setPixmap(pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.logo_label.setFixedSize(36, 36)
        self.logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.logo_label)

        title_layout = QVBoxLayout()
        self.title_label = QLabel("MintNTE")
        self.title_label.setObjectName("TitleLabel")
        title_layout.addWidget(self.title_label, alignment=Qt.AlignLeft)

        subtitle = QLabel("异环自动化助手")
        subtitle.setObjectName("SubtitleLabel")
        title_layout.addWidget(subtitle, alignment=Qt.AlignLeft)
        title_layout.setSpacing(0)
        title_layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(title_layout)

        layout.addStretch()

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