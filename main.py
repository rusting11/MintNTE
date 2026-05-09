# main.py (完整最终版)
import sys, os, ctypes, atexit, shutil, tempfile

# 隐藏 PyInstaller 单文件模式的清理失败弹窗
if getattr(sys, 'frozen', False):
    def _silent_cleanup():
        try:
            temp_dir = os.path.join(tempfile.gettempdir(), f"_MEI{os.getpid()}")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass
    atexit.register(_silent_cleanup)
    try:
        ctypes.windll.user32.SetErrorMode(0x8000)  # SEM_NOGPFAULTERRORBOX
    except:
        pass

# ================= 管理员提权（ShellExecute） =================
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def elevate():
    params = " ".join([f'"{os.path.abspath(__file__)}"'] + sys.argv[1:])
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, params, None, 1
    )
    sys.exit()

if not is_admin():
    elevate()
# ==============================================

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'

from PyQt5.QtWidgets import QApplication, QWidget, QLabel
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap, QIcon
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

    app.setWindowIcon(QIcon(os.path.join(BASE_DIR, "Image", "logo", "titlelogo.ico")))
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

    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('daoqi.MintNTE')
    ctypes.windll.user32.SendMessageW(0xFFFF, 0x001A, 0, 0)

    main_window.auto_check_update()

    from UI.logViewerUI import LogViewer
    log_viewer = LogViewer("nte_bohe.log")
    log_viewer.show()
    main_window.log_viewer = log_viewer
    main_window.header.btn_log.setText("关闭日志")

    info("主界面已显示")
    sys.exit(app.exec_())