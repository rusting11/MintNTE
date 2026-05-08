# core/fishing/fishing_utils.py
# =================== 后台截图函数 ===================
# 功能：获取指定窗口的客户区画面（BGR格式），完全后台操作。
#
# 工作原理：
#   - 通过 GetWindowDC 获取窗口的设备上下文（DC）
#   - 使用 PrintWindow 将窗口内容渲染到内存位图
#   - 将位图转换为 OpenCV 可用的 numpy 数组
#
# 关键特性：
#   - 窗口被其他窗口遮挡 / 最小化 / 隐藏时，仍然能截取到正确的游戏画面
#   - 不需要将窗口激活或置顶，不会抢鼠标，不影响用户正常操作电脑
#   - 只要游戏是“窗口化”或“无边框窗口”，就可以正确截取
#
# 注意事项：
#   - 如果游戏处于“全屏独占模式”(Full-Screen Exclusive)，PrintWindow 可能失效，
#     截图会全黑或只显示桌面，此时请将游戏改为窗口化或无边框窗口
#   - 函数内部已经包含 GDI 资源释放与异常保护，调用者无需关心清理
# ==================================================
import cv2
import numpy as np
import win32gui
import win32ui
import ctypes
from PIL import Image
import time

def capture_window_to_cv(hwnd):
    """后台截图：使用 PrintWindow 获取窗口客户区，返回 BGR 格式的 numpy 数组。
    增加完备的错误处理，防止 GDI 资源泄漏和崩溃。
    """
    if not win32gui.IsWindow(hwnd):
        return None
    rect = win32gui.GetClientRect(hwnd)
    left, top, right, bottom = rect
    width = right - left
    height = bottom - top
    if width <= 0 or height <= 0:
        return None

    # 获取窗口 DC
    hwnd_dc = win32gui.GetWindowDC(hwnd)
    if not hwnd_dc:                     # 关键：检查 DC 是否有效
        return None

    try:
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()
        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
        save_dc.SelectObject(bitmap)

        success = ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 3)
        if not success:
            return None

        bitmap_bits = bitmap.GetBitmapBits(True)
        img = Image.frombuffer("RGB", (width, height), bitmap_bits, "raw", "BGRX", 0, 1)
        opencv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        return opencv_img
    except Exception:
        return None
    finally:
        # 无论成功与否，都要释放 GDI 资源
        try:
            win32gui.DeleteObject(bitmap.GetHandle())
        except:
            pass
        try:
            save_dc.DeleteDC()
        except:
            pass
        try:
            mfc_dc.DeleteDC()
        except:
            pass
        try:
            win32gui.ReleaseDC(hwnd, hwnd_dc)
        except:
            pass