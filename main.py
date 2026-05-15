# -*- coding: utf-8 -*-
# main.py — MintNTE 入口（彻底禁用控制台黑框）

# ===== 第一步：在一切其他 import 之前分离控制台 =====
import ctypes, sys, os

def detach_console():
    """
    彻底从进程层面分离控制台，使控制台窗口无法再出现。
    1. FreeConsole()            解除绑定
    2. ShowWindow(GetConsoleWindow(), SW_HIDE)  兜底隐藏
    """
    try:
        # 彻底解除进程与主控制台的绑定
        ctypes.windll.kernel32.FreeConsole()
    except Exception:
        pass
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)  # SW_HIDE
            ctypes.windll.kernel32.CloseHandle(hwnd)
    except Exception:
        pass

detach_console()

# ===== 第二步：抑制 Windows 系统错误对话框 =====
try:
    ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002)  # SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX
except Exception:
    pass

# ===== 第三步：提权判断（提权后的新进程也不再显示控制台） =====
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

if not is_admin():
    # 用 SW_HIDE (1) 隐藏提权时弹出的命令行窗口
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, f'"{os.path.abspath(__file__)}"', PROJECT_ROOT, 1  # 1 = SW_HIDE
    )
    sys.exit()

# 提权后再次分离（新进程也可能携带控制台）
detach_console()

# ===== 第四步：正常加载应用 =====
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
