import cv2
import numpy as np
import win32gui
import win32ui
import ctypes
from PIL import Image

def capture_window_to_cv(hwnd):
    rect = win32gui.GetClientRect(hwnd)
    left, top, right, bottom = rect
    width = right - left
    height = bottom - top
    if width == 0 or height == 0:
        return None
    hdc = win32gui.GetWindowDC(hwnd)
    mfc_dc = win32ui.CreateDCFromHandle(hdc)
    save_dc = mfc_dc.CreateCompatibleDC()
    bitmap = win32ui.CreateBitmap()
    bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
    save_dc.SelectObject(bitmap)
    success = ctypes.windll.user32.PrintWindow(hwnd, save_dc.GetSafeHdc(), 3)
    if not success:
        win32gui.DeleteObject(bitmap.GetHandle())
        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(hwnd, hdc)
        return None
    bitmap_bits = bitmap.GetBitmapBits(True)
    img = Image.frombuffer("RGB", (width, height), bitmap_bits, "raw", "BGRX", 0, 1)
    opencv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    win32gui.DeleteObject(bitmap.GetHandle())
    save_dc.DeleteDC()
    mfc_dc.DeleteDC()
    win32gui.ReleaseDC(hwnd, hdc)
    return opencv_img