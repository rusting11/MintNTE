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
    ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002)
except Exception:
    pass

# ===== 第三步：提权判断 =====
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

# 检查是否已经是提权后的进程
is_elevated = "--elevated" in sys.argv

if not is_elevated and not is_admin():
    # 需要提权，使用 pythonw.exe 启动以避免控制台窗口
    pythonw_exe = sys.executable.replace("python.exe", "pythonw.exe")
    if not os.path.exists(pythonw_exe):
        pythonw_exe = sys.executable
    
    # 构建命令：添加 --elevated 参数标识已提权
    cmd = f'"{pythonw_exe}" "{os.path.abspath(__file__)}" --elevated'
    
    # 使用 SW_SHOWNORMAL 确保提权对话框能显示
    result = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", pythonw_exe, f'"{os.path.abspath(__file__)}" --elevated', PROJECT_ROOT, 1  # 1 = SW_SHOWNORMAL
    )
    
    # ShellExecuteW 返回值 > 32 表示成功
    if result <= 32:
        # 提权失败（用户取消或其他错误）
        # 在非管理员模式下尝试继续运行
        pass
    else:
        # 提权成功，当前进程退出
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

# grab() 强制 Qt 完成一次完整绘制（布局+样式+像素），窗口仍不可见
main_window.grab()

# 此时 Qt 已缓存完整绘制结果，show() 时直接使用缓存，不会闪白
screen = app.primaryScreen().availableGeometry()
x = (screen.width() - main_window.width()) // 2
y = (screen.height() - main_window.height()) // 2
main_window.move(x, y)
main_window.show()

info("主界面已显示")
sys.exit(app.exec_())
