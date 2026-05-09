# core/task/task_core.py
import os
import sys
import time
import threading
import cv2
import numpy as np
import win32gui
import win32con
from PyQt5.QtCore import QObject, pyqtSignal

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from Module.click.NET_click import (
    send_key_down, send_key_up,
    simulate_mouse_click_relative
)
from core.fishing.fishing_utils import capture_window_to_cv
from Module.Hwnd.game_hwnd import get_game_hwnd
from UI import logui

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

TASK_IMG_DIR = "Taskimages"
PATH_AUTO_PLAY       = resource_path(os.path.join(TASK_IMG_DIR, "taks_auto_play.bmp"))
PATH_SKIP_BTN        = resource_path(os.path.join(TASK_IMG_DIR, "skip_btn.bmp"))
PATH_CONFIRM         = resource_path(os.path.join(TASK_IMG_DIR, "confirm.bmp"))
PATH_DISABLE_SKIP    = resource_path(os.path.join(TASK_IMG_DIR, "disable_skip.bmp"))
PATH_DISABLE_SKIP_1  = resource_path(os.path.join(TASK_IMG_DIR, "disable_skip_1.bmp"))
PATH_AUTO_PLAY_1     = resource_path(os.path.join(TASK_IMG_DIR, "taks_auto_play_1.bmp"))
PATH_GO_TIMES        = resource_path(os.path.join(TASK_IMG_DIR, "go_times.bmp"))
PATH_YES             = resource_path(os.path.join(TASK_IMG_DIR, "yes.bmp"))

MATCH_THRESH = 0.7

ROI_AUTO_PLAY        = (1609, 31, 1662, 90)
ROI_AUTO_PLAY_1      = (1800, 31, 1850, 90)
ROI_SKIP_BTN         = (1824, 31, 1885, 87)
ROI_CONFIRM          = (1203, 652, 1255, 678)
ROI_DISABLE_SKIP     = (1823, 38, 1874, 89)
ROI_DISABLE_SKIP_1   = (1823, 40, 1869, 89)
ROI_GO_TIMES         = (76, 318, 193, 341)
ROI_YES              = (1119, 687, 1197, 730)

WM_ACTIVATE = 0x0006
WA_ACTIVE = 1

def fake_activate(hwnd):
    try:
        win32gui.SendMessage(hwnd, WM_ACTIVATE, WA_ACTIVE, 0)
    except:
        pass

def press_key(hwnd, vk_code, duration=0.05):
    fake_activate(hwnd)
    send_key_down(hwnd, vk_code)
    time.sleep(duration)
    send_key_up(hwnd, vk_code)

def match_region(frame, tpl_path, roi):
    """返回 (中心坐标, 最高匹配度) 或 (None, 匹配度)"""
    left, top, right, bottom = roi
    h, w = frame.shape[:2]
    x1 = max(0, min(left, w-1))
    y1 = max(0, min(top, h-1))
    x2 = max(x1+1, min(right, w))
    y2 = max(y1+1, min(bottom, h))
    if x2 - x1 < 10 or y2 - y1 < 10:
        return None, 0.0
    roi_img = frame[y1:y2, x1:x2]
    tpl = cv2.imread(tpl_path, cv2.IMREAD_GRAYSCALE)
    if tpl is None:
        return None, 0.0
    roi_gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
    res = cv2.matchTemplate(roi_gray, tpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    if max_val >= MATCH_THRESH:
        th, tw = tpl.shape
        cx = max_loc[0] + tw//2 + x1
        cy = max_loc[1] + th//2 + y1
        return (cx, cy), max_val
    return None, max_val

class TaskThread(QObject):
    request_click = pyqtSignal(int, int, int)

    def __init__(self, stop_event, skip_enabled, no_remind_enabled):
        super().__init__()
        self.stop_event = stop_event
        self.skip_enabled = skip_enabled
        self.no_remind_enabled = no_remind_enabled
        self._thread = threading.Thread(target=self.run, daemon=True)

    def start(self):
        self._thread.start()

    def run(self):
        logui.info("任务自动跳过已启动")
        while not self.stop_event.is_set():
            hwnd = get_game_hwnd()
            if not hwnd or not win32gui.IsWindow(hwnd):
                time.sleep(0.5)
                continue
            frame = capture_window_to_cv(hwnd)
            if frame is None:
                time.sleep(0.1)
                continue

            # 检测对话图标
            found_auto, _ = match_region(frame, PATH_AUTO_PLAY, ROI_AUTO_PLAY)
            found_auto1, _ = match_region(frame, PATH_AUTO_PLAY_1, ROI_AUTO_PLAY_1)
            if found_auto or found_auto1:
                logui.info("当前任务对话中")

                # ---------- 调试输出：go_times / yes 匹配度 ----------
                _, go_match = match_region(frame, PATH_GO_TIMES, ROI_GO_TIMES)
                logui.info(f"[调试] go_times.bmp 匹配度={go_match:.3f}")
                if go_match >= MATCH_THRESH:
                    logui.info("按V进入时间界面")
                    press_key(hwnd, 0x56)           # V 键
                    time.sleep(0.3)

                _, yes_match = match_region(frame, PATH_YES, ROI_YES)
                logui.info(f"[调试] yes.bmp 匹配度={yes_match:.3f}")
                if yes_match >= MATCH_THRESH:
                    logui.info("点击确认")
                    self.request_click.emit(hwnd, 1164, 708)
                    time.sleep(0.5)
                # ------------------------------------------------

                # 跳过剧情
                if self.skip_enabled and match_region(frame, PATH_SKIP_BTN, ROI_SKIP_BTN)[0]:
                    logui.info("跳过剧情")
                    press_key(hwnd, win32con.VK_ESCAPE, duration=0.05)
                    time.sleep(1.0)
                    frame2 = capture_window_to_cv(hwnd)
                    if frame2 is not None:
                        confirm_pos, _ = match_region(frame2, PATH_CONFIRM, ROI_CONFIRM)
                        if confirm_pos:
                            logui.info("请求点击确认按钮")
                            self.request_click.emit(hwnd, confirm_pos[0], confirm_pos[1])
                            if self.no_remind_enabled:
                                logui.info("请求点击「今日不再提示」")
                                self.request_click.emit(hwnd, 862, 557)
                                time.sleep(0.5)
                                self.request_click.emit(hwnd, 1227, 667)
                                time.sleep(1.0)
                # 不可跳过按钮
                elif self.skip_enabled and (
                    match_region(frame, PATH_DISABLE_SKIP, ROI_DISABLE_SKIP)[0] or
                    match_region(frame, PATH_DISABLE_SKIP_1, ROI_DISABLE_SKIP_1)[0]
                ):
                    logui.info("当前剧情不可跳  按F")
                    press_key(hwnd, 0x46)
                    time.sleep(0.5)

            time.sleep(0.2)
        logui.info("任务自动跳过已停止")