import faulthandler, os, sys
faulthandler.enable()
# 禁用 Windows 错误弹窗
import ctypes
ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002)

# 确保项目根目录在搜索路径
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 管理员提权（自动请求管理员权限）
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False
if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, f'"{__file__}"', PROJECT_ROOT, 1
    )
    sys.exit()

from PyQt5.QtWidgets import QApplication
from UI.logui import setup_logging, info

setup_logging("nte_bohe.log")
info("程序启动")

app = QApplication(sys.argv)

from UI.MainUI import MainUI
main_window = MainUI()
main_window.show()

info("主界面已显示")
sys.exit(app.exec_())