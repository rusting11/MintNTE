# core/fishing/fishing_core.py
import os
import sys
import time
import threading
import random
import traceback
import datetime
import win32gui
import win32con
import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from UI import logui
from Module.click.NET_click import (
    send_key_down, send_key_up,
    simulate_mouse_click_relative
)
from core.fishing.auto_buy_bait import auto_buy_bait
from core.fishing.auto_sell_fish import sell_fish
from core.fishing.fishing_follow import start_follow
from core.fishing.fishing_utils import capture_window_to_cv
from Module.Hwnd.game_hwnd import set_locked_hwnd
from core.auto_reconnect.auto_reconnect import (
    check_and_click_enter_game,
    find_image_on_window
)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

IMG_DIR = "fishingimages"
PATH_DIAOYU = resource_path(os.path.join(IMG_DIR, "diaoyu.png"))
PATH_KAISHIDIAOYU = resource_path(os.path.join(IMG_DIR, "kaishidiaoyu.png"))
PATH_DIANJIKONGBAI = resource_path(os.path.join(IMG_DIR, "dianjikongbai.png"))
PATH_PANDUANDIAOYU = resource_path(os.path.join(IMG_DIR, "panduandiaoyu.png"))
PATH_YU1 = resource_path(os.path.join(IMG_DIR, "yu1.png"))
PATH_YU = resource_path(os.path.join(IMG_DIR, "yu.png"))
PATH_YUER = resource_path(os.path.join(IMG_DIR, "yuer.png"))
PATH_RECONNECT_ON_DISCONNECT = resource_path(os.path.join(IMG_DIR, "reconnect_on_disconnect.png"))
MATCH_THRESH = 0.7
RECONNECT_REGION = (42, 50, 147, 180)
DEBUG_SCREENSHOT_PATH = os.path.join(BASE_DIR, "debug_screenshot.png")

WM_ACTIVATE = 0x0006
WA_ACTIVE = 1

def fake_activate(hwnd):
    try:
        win32gui.SendMessage(hwnd, WM_ACTIVATE, WA_ACTIVE, 0)
    except:
        pass

def send_key(hwnd, vk_code, down=True):
    fake_activate(hwnd)
    if down:
        send_key_down(hwnd, vk_code)
    else:
        send_key_up(hwnd, vk_code)

def press_key(hwnd, vk_code, duration=0.05):
    send_key(hwnd, vk_code, down=True)
    time.sleep(duration)
    send_key(hwnd, vk_code, down=False)

def find_image_in_window(template_path, hwnd, timeout=0, interval=0.2, save_debug=False):
    if not hwnd or not win32gui.IsWindow(hwnd):
        return None
    start = time.time()
    while timeout <= 0 or (time.time() - start) < timeout:
        try:
            img = capture_window_to_cv(hwnd)
            if img is None:
                time.sleep(interval)
                continue
            if save_debug:
                try:
                    cv2.imwrite(DEBUG_SCREENSHOT_PATH, img)
                except:
                    pass
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
            if template is None:
                return None
            res = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            if max_val >= MATCH_THRESH:
                h, w = template.shape
                return (max_loc[0] + w // 2, max_loc[1] + h // 2)
        except:
            pass
        if timeout == 0:
            break
        time.sleep(interval)
    return None

class FishingCore:
    def __init__(self, hwnd, stop_event, timeout=20, sell_mode=0, follow_mode=0, roi_offset=0, enable_debug_screenshot=False):
        self.hwnd = hwnd
        self.stop_event = stop_event
        self.fish_count = 0
        self.timeout = timeout
        self.sell_mode = sell_mode
        self.follow_mode = follow_mode
        self.roi_offset = roi_offset
        self.today_forced_sell = False
        self.last_sell_date = ""
        self.enable_debug_screenshot = enable_debug_screenshot
        self.enable_follow = False
        self.roi_follower = None

    def fish_logic(self):
        self.enable_follow = False
        dbg = self.enable_debug_screenshot
        today_str = datetime.date.today().isoformat()
        if today_str != self.last_sell_date:
            self.today_forced_sell = False
            self.last_sell_date = today_str

        try:
            logui.info("开始监测图像...")
            last_prompt = time.time()
            last_reconnect_check = time.time()
            while not self.stop_event.is_set():
                if time.time() - last_reconnect_check > 5:
                    last_reconnect_check = time.time()
                    reconnect_found, _ = find_image_on_window(
                        self.hwnd,
                        PATH_RECONNECT_ON_DISCONNECT,
                        region=RECONNECT_REGION,
                        threshold=0.8
                    )
                    if reconnect_found:
                        logui.warning("检测到被踢出钓鱼准备进入游戏 (后台重连)")
                        check_and_click_enter_game()
                        time.sleep(3)
                        return False

                pos = find_image_in_window(PATH_DIAOYU, self.hwnd, save_debug=dbg)
                if pos:
                    logui.info("当前没有进入钓鱼界面 需要强制调用鼠标 (前台点击)")
                    simulate_mouse_click_relative(self.hwnd, pos[0], pos[1])
                    continue

                pos = find_image_in_window(PATH_KAISHIDIAOYU, self.hwnd, save_debug=dbg)
                if pos:
                    logui.info("开始钓鱼 (前台点击)")
                    simulate_mouse_click_relative(self.hwnd, pos[0], pos[1])
                    continue

                pos = find_image_in_window(PATH_DIANJIKONGBAI, self.hwnd, save_debug=dbg)
                if pos:
                    logui.info("点击空白区域关闭界面优先后台ESC (后台ESC)")
                    press_key(self.hwnd, 0x1B)
                    continue

                pos = find_image_in_window(PATH_PANDUANDIAOYU, self.hwnd, save_debug=dbg)
                if pos:
                    self.enable_follow = True
                    if self.sell_mode == 2:
                        now = time.localtime()
                        if now.tm_hour == 3 and 50 <= now.tm_min <= 59 and not self.today_forced_sell:
                            logui.info("每日3:50-3:59，执行强制卖鱼")
                            sell_fish(self.hwnd)
                            self.today_forced_sell = True

                    logui.info("当前符合抛竿 (后台按键)")
                    bait_bought = False
                    while not self.stop_event.is_set():
                        still = find_image_in_window(PATH_PANDUANDIAOYU, self.hwnd, timeout=0, save_debug=dbg)
                        if not still:
                            logui.info("抛竿结束 (后台按键)")
                            press_key(self.hwnd, 0x46)
                            break
                        if not bait_bought:
                            yuer = find_image_in_window(PATH_YUER, self.hwnd, timeout=0, save_debug=dbg)
                            if yuer:
                                logui.info("缺少鱼饵,准备购买鱼饵")
                                if self.sell_mode == 1:
                                    logui.info("鱼饵不足，先自动售卖鱼获")
                                    sell_fish(self.hwnd)
                                auto_buy_bait()
                                bait_bought = True
                        press_key(self.hwnd, 0x46)
                        time.sleep(0.3)
                    break

                if time.time() - last_prompt > 3:
                    logui.info("监测中...")
                    last_prompt = time.time()
                time.sleep(0.02)

            logui.info("等待鱼上钩...")
            f1 = f2 = False
            last_reconnect_check2 = time.time()
            while (not f1 or not f2) and not self.stop_event.is_set():
                if time.time() - last_reconnect_check2 > 2:
                    last_reconnect_check2 = time.time()
                    reconnect_found, _ = find_image_on_window(
                        self.hwnd,
                        PATH_RECONNECT_ON_DISCONNECT,
                        region=RECONNECT_REGION,
                        threshold=0.8
                    )
                    if reconnect_found:
                        logui.warning("检测到被踢出钓鱼准备进入游戏 (后台重连)")
                        check_and_click_enter_game()
                        time.sleep(3)
                        return False

                if not f1:
                    p = find_image_in_window(PATH_YU1, self.hwnd, save_debug=dbg)
                    if p:
                        logui.info("鱼饵上钩按F起钩 (后台按键)")
                        press_key(self.hwnd, 0x46)
                        f1 = True
                if not f2:
                    p = find_image_in_window(PATH_YU, self.hwnd, save_debug=dbg)
                    if p:
                        logui.info("鱼饵上钩按F起钩 (后台按键)")
                        press_key(self.hwnd, 0x46)
                        f2 = True
                time.sleep(0.05)

            if not (f1 and f2):
                logui.error("未检测到鱼上钩")
                self.enable_follow = False
                return False

            logui.info("启动跟随")
            follow_stop = threading.Event()
            follow_started = False

            if self.enable_follow:
                try:
                    if self.follow_mode == 0:
                        from core.fishing.fishing_roi.RoiFollow import FishingFollower
                        self.roi_follower = FishingFollower(offset=self.roi_offset)
                        self.roi_follower.start()
                        follow_started = True
                    elif self.follow_mode == 1:
                        from core.fishing.fishing_roi.AI_RoiFollow import FishingFollower as AIFollower
                        self.roi_follower = AIFollower(offset=self.roi_offset)
                        self.roi_follower.start()
                        follow_started = True
                    else:
                        if start_follow(follow_stop, target_hwnd=self.hwnd):
                            follow_started = True
                except Exception as e:
                    logui.error(f"跟随启动异常: {e}")
            else:
                logui.info("跟随功能已关闭")

            if not follow_started:
                logui.error("跟随启动失败，放弃本次钓鱼")
                self.enable_follow = False
                return False

            logui.info("等待结果...")
            start_wait = time.time()
            result = None
            while not self.stop_event.is_set():
                p = find_image_in_window(PATH_DIANJIKONGBAI, self.hwnd, save_debug=dbg)
                if p:
                    result = 'success'
                    break
                p = find_image_in_window(PATH_PANDUANDIAOYU, self.hwnd, save_debug=dbg)
                if p:
                    result = 'escape'
                    break
                if time.time() - start_wait > self.timeout:
                    logui.warning(f"等待超时({self.timeout}秒)，按逃走处理")
                    result = 'escape'
                    break
                time.sleep(0.05)

            if self.follow_mode == 0 or self.follow_mode == 1:
                if self.roi_follower:
                    self.roi_follower.stop()
            else:
                follow_stop.set()

            self.enable_follow = False

            if result == 'success':
                logui.info("点击空白区域关闭界面优先后台ESC (后台ESC)")
                press_key(self.hwnd, 0x1B)
                self.fish_count += 1
                return True
            else:
                logui.info("鱼逃走了")
                return False

        except Exception as e:
            logui.error(f"逻辑异常: {e}\n{traceback.format_exc()}")
            self.enable_follow = False
            return False

    def run(self):
        if self.hwnd and win32gui.IsWindow(self.hwnd):
            set_locked_hwnd(self.hwnd)
        logui.info("开始循环钓鱼")
        try:
            while not self.stop_event.is_set():
                if self.fish_logic():
                    self._smart_sleep(1)
                else:
                    self._smart_sleep(3)
        finally:
            for vk in [0x41,0x44,0x46,0x52,0x45,0x1B]:
                send_key_up(self.hwnd, vk)
            logui.info(f"结束，共钓鱼 {self.fish_count} 条")

    def _smart_sleep(self, seconds, interval=0.05):
        elapsed = 0
        while elapsed < seconds and not self.stop_event.is_set():
            time.sleep(min(interval, seconds - elapsed))
            elapsed += interval