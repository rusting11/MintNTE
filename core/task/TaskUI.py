from PyQt5.QtWidgets import QWidget, QVBoxLayout, QListWidget, QPushButton
from UI import logui

logui.info("任务界面加载")
logui.error("任务功能开发中")

class TaskUI(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.list = QListWidget()
        self.list.addItem("更新中: 0/50")
        self.list.addItem("更新中: 0/10")
        self.list.addItem("更新中")
        layout.addWidget(self.list)
        btn = QPushButton("刷新任务")
        btn.setObjectName("NeonButton")
        layout.addWidget(btn)
        self.setStyleSheet("""
        QListWidget {
            background-color: #15151f;
            color: #0ff;
        }
        #NeonButton {
            background-color: #2a2a3a;
            color: #0ff;
            border: 1px solid #0ff;
        }
        """)