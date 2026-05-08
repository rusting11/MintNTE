# main.py (完整最终版)
import sys
import os
import ctypes
from PyQt5.QtGui import QIcon
# ================= 管理员提权（ShellExecute） =================
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def elevate():
    """使用 Windows ShellExecute 提权重启自身，无额外控制台窗口"""
    # 将当前脚本路径和参数拼成命令行
    params = " ".join([f'"{os.path.abspath(__file__)}"'] + sys.argv[1:])
    ctypes.windll.shell32.ShellExecuteW(
        None,               # 父窗口句柄
        "runas",            # 以管理员身份运行
        sys.executable,     # Python 解释器
        params,             # 参数
        None,               # 工作目录
        1                   # SW_SHOWNORMAL
    )
    sys.exit()

if not is_admin():
    elevate()
# ==============================================

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

from PyQt5.QtWidgets import QApplication, QWidget, QLabel
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap
import pygame

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class SplashScreen(QWidget):
    def __init__(self, image_path, duration=5000):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            print(f"错误：无法加载图片 {image_path}")
            sys.exit(1)

        self.setFixedSize(pixmap.width(), pixmap.height())
        label = QLabel(self)
        label.setPixmap(pixmap)
        label.setScaledContents(True)
        label.resize(self.size())

        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)

        self.show()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.close)
        self.timer.start(duration)

    def mousePressEvent(self, event):
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    import ctypes
    app.setWindowIcon(QIcon(os.path.join(BASE_DIR, "Image", "logo", "titlelogo.ico")))
    # 关键：让 Windows 任务栏能正确识别图标
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('daoqi.MintNTE')

    from UI.logui import setup_logging, info
    setup_logging("nte_bohe.log")
    info("程序启动")

    try:
        pygame.mixer.init()
        music_path = os.path.join(BASE_DIR, "Image", "logo", "boheai.mp3")
        if os.path.exists(music_path):
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.play(0)
        else:
            info(f"音乐文件不存在: {music_path}")
    except Exception as e:
        info(f"音乐初始化失败: {e}")

    splash_image = os.path.join(BASE_DIR, "Image", "logo", "boheAI.png")
    if os.path.exists(splash_image):
        splash = SplashScreen(splash_image, duration=5000)
    else:
        info(f"启动图片不存在: {splash_image}")

    from UI.MainUI import MainUI
    main_window = MainUI()
    main_window.show()
    main_window.auto_check_update()

    from UI.logViewerUI import LogViewer
    log_viewer = LogViewer("nte_bohe.log")
    log_viewer.show()
    main_window.log_viewer = log_viewer
    main_window.header.btn_log.setText("关闭日志")

    info("主界面已显示")
    sys.exit(app.exec_())