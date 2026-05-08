import sys
from PySide2.QtWidgets import QApplication, QWidget, QPushButton, QLabel

app = QApplication(sys.argv)

win = QWidget()
win.setWindowTitle("我是 PySide2 UI")
win.resize(300, 180)

label = QLabel("PySide2 界面", win)
label.move(100, 50)

btn = QPushButton("点我", win)
btn.move(100, 100)
btn.clicked.connect(lambda: print("PySide2 按钮被点击"))

win.show()
sys.exit(app.exec_())