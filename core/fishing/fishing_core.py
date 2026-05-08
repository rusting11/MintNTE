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
PATH_YUER = resource_path(os.path.join(IMG_DIR, "yuer.png"))
PATH_RECONNECT_ON_DISCONNECT = resource_path(os.path.join(IMG_DIR, "reconnect_on_disconnect.png"))

# 鱼获判定图片
PATH_FISH_GONE = resource_path(os.path.join(IMG_DIR, "rank_fish", "fish_gone.bmp"))
PATH_RANK_A = resource_path(os.path.join(IMG_DIR, "rank_fish", "rank_a_fish.bmp"))
PATH_RANK_B = resource_path(os.path.join(IMG_DIR, "rank_fish", "rank_b_fish.bmp"))
PATH_RANK_S = resource_path(os.path.join(IMG_DIR, "rank_fish", "rank_s_fish.bmp"))

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
    def __init__(self, hwnd, stop_event, timeout=60, sell_mode=0, follow_mode=0, roi_offset=0, enable_debug_screenshot=False, stats_callback=None):
        self.hwnd = hwnd
        self.stop_event = stop_event
        self.fish_count = 0          # 总钓数
        self.fish_count_a = 0
        self.fish_count_b = 0
        self.fish_count_s = 0
        self.timeout = timeout
        self.sell_mode = sell_mode
        self.follow_mode = follow_mode
        self.roi_offset = roi_offset
        self.today_forced_sell = False
        self.last_sell_date = ""
        self.enable_debug_screenshot = enable_debug_screenshot
        self.enable_follow = False
        self.roi_follower = None
        self.stats_callback = stats_callback   # 回调函数 (grade: str)

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
                # 掉线检测保持不变
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

                # ---------- 每轮只截一次图 ----------
                frame = capture_window_to_cv(self.hwnd)
                if frame is None:
                    time.sleep(0.02)
                    continue
                if dbg:
                    try:
                        cv2.imwrite(DEBUG_SCREENSHOT_PATH, frame)
                    except:
                        pass
                gray_all = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                def match_in_region(tpl_path, left, top, right, bottom):
                    h, w = gray_all.shape
                    x1 = max(0, min(left, w - 1))
                    y1 = max(0, min(top, h - 1))
                    x2 = max(x1 + 1, min(right, w))
                    y2 = max(y1 + 1, min(bottom, h))
                    if x2 - x1 < 10 or y2 - y1 < 10:
                        return None
                    roi_gray = gray_all[y1:y2, x1:x2]
                    tpl = cv2.imread(tpl_path, cv2.IMREAD_GRAYSCALE)
                    if tpl is None:
                        return None
                    res = cv2.matchTemplate(roi_gray, tpl, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, max_loc = cv2.minMaxLoc(res)
                    if max_val >= MATCH_THRESH:
                        tpl_h, tpl_w = tpl.shape
                        cx = max_loc[0] + tpl_w // 2 + x1
                        cy = max_loc[1] + tpl_h // 2 + y1
                        return (cx, cy)
                    return None

                # 四个图的查找（区域坐标保持不变）
                pos = match_in_region(PATH_DIAOYU, 1153, 548, 1271, 626)
                if pos:
                    logui.info("按 F 进入钓鱼 (后台按键)")
                    press_key(self.hwnd, 0x46)
                    continue

                pos = match_in_region(PATH_KAISHIDIAOYU, 1471, 880, 1730, 993)
                if pos:
                    logui.info("开始钓鱼 (前台点击)")
                    simulate_mouse_click_relative(self.hwnd, pos[0], pos[1])
                    time.sleep(0.8)
                    continue

                # dianjikongbai 按 ESC 后增加 1 秒延迟
                pos = match_in_region(PATH_DIANJIKONGBAI, 826, 918, 1081, 1033)
                if pos:
                    logui.info("点击空白区域关闭界面优先后台ESC (后台ESC)")
                    press_key(self.hwnd, 0x1B)
                    time.sleep(1.0)
                    continue

                pos = match_in_region(PATH_PANDUANDIAOYU, 1346, 919, 1459, 1040)
                if pos:
                    self.enable_follow = True
                    if self.sell_mode == 2:
                        now = time.localtime()
                        if now.tm_hour == 3 and 50 <= now.tm_min <= 59 and not self.today_forced_sell:
                            logui.info("每日3:50-3:59，执行强制卖鱼")
                            sell_fish(self.hwnd)
                            self.today_forced_sell = True

                    yuer = find_image_in_window(PATH_YUER, self.hwnd, timeout=0, save_debug=dbg)
                    if yuer:
                        logui.info("检测到鱼饵不足，自动购买")
                        auto_buy_bait()

                    from core.fishing.throw_rod import throw_rod
                    throw_rod(self.stop_event)
                    break

                if time.time() - last_prompt > 3:
                    logui.info("监测中...")
                    last_prompt = time.time()
                time.sleep(0.02)

            # ========== 启动跟随 ==========
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

            # ========== 等待结果（含心跳检测） ==========
            logui.info("等待结果...")
            start_wait = time.time()
            result = None
            prev_escape_found = False
            success_frame = None
            timeout_count = 0

            while not self.stop_event.is_set():
                frame = capture_window_to_cv(self.hwnd)
                if frame is not None:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                    def check_img(tpl_path, roi, name):
                        left, top, right, bottom = roi
                        h, w = gray.shape
                        x1 = max(0, min(left, w - 1))
                        y1 = max(0, min(top, h - 1))
                        x2 = max(x1 + 1, min(right, w))
                        y2 = max(y1 + 1, min(bottom, h))
                        if x2 - x1 < 10 or y2 - y1 < 10:
                            return False, 0.0
                        roi_gray = gray[y1:y2, x1:x2]
                        tpl = cv2.imread(tpl_path, cv2.IMREAD_GRAYSCALE)
                        if tpl is None:
                            return False, 0.0
                        res = cv2.matchTemplate(roi_gray, tpl, cv2.TM_CCOEFF_NORMED)
                        _, max_val, _, _ = cv2.minMaxLoc(res)
                        found = max_val >= MATCH_THRESH
                        if not found:
                            logui.info(f"[等待结果] {name} 匹配度={max_val:.3f}")
                        return found, max_val

                    # 检测成功
                    found_dian, _ = check_img(PATH_DIANJIKONGBAI,
                                              (826, 918, 1081, 1033),
                                              "dianjikongbai")
                    if found_dian:
                        success_frame = frame
                        result = 'success'
                        break

                    # 检测逃走（连续两次确认）
                    found_pan, _ = check_img(PATH_PANDUANDIAOYU,
                                             (1346, 919, 1459, 1040),
                                             "panduandiaoyu")
                    if found_pan:
                        if prev_escape_found:
                            result = 'escape'
                            break
                        else:
                            prev_escape_found = True
                            time.sleep(0.3)
                            continue
                    else:
                        prev_escape_found = False

                # 超时重置逻辑
                if time.time() - start_wait > self.timeout:
                    timeout_count += 1
                    if timeout_count >= 3:
                        logui.warning(f"等待超时次数过多({self.timeout * 3}秒)，退出跟随")
                        result = 'timeout'
                        break
                    logui.warning(f"等待超时({self.timeout}秒)，仍在跟随中... (第{timeout_count}次)")
                    start_wait = time.time()

                time.sleep(0.15)

            # 停止跟随
            if self.follow_mode == 0 or self.follow_mode == 1:
                if self.roi_follower:
                    self.roi_follower.stop()
            else:
                follow_stop.set()

            self.enable_follow = False

            # ========== 结果处理 ==========
            if result == 'success' and success_frame is not None:
                # 等级识别
                gray = cv2.cvtColor(success_frame, cv2.COLOR_BGR2GRAY)

                def match_grade(tpl_path, left, top, right, bottom, name="?"):
                    h, w = gray.shape
                    x1 = max(0, min(left, w - 1))
                    y1 = max(0, min(top, h - 1))
                    x2 = max(x1 + 1, min(right, w))
                    y2 = max(y1 + 1, min(bottom, h))
                    if x2 - x1 < 10 or y2 - y1 < 10:
                        return False, 0.0
                    roi_gray = gray[y1:y2, x1:x2]
                    tpl = cv2.imread(tpl_path, cv2.IMREAD_GRAYSCALE)
                    if tpl is None:
                        return False, 0.0
                    res = cv2.matchTemplate(roi_gray, tpl, cv2.TM_CCOEFF_NORMED)
                    _, max_val, _, _ = cv2.minMaxLoc(res)
                    logui.info(f"[鱼获识别] {name} 匹配度={max_val:.3f}")
                    return max_val >= MATCH_THRESH, max_val

                # 逃走判定
                is_gone, _ = match_grade(PATH_FISH_GONE, 828, 504, 1091, 578, "fish_gone")
                grade = None
                if is_gone:
                    grade = 'escape'
                else:
                    found_s, _ = match_grade(PATH_RANK_S, 1033, 323, 1160, 439, "rank_s")
                    found_a, _ = match_grade(PATH_RANK_A, 1033, 323, 1160, 439, "rank_a")
                    found_b, _ = match_grade(PATH_RANK_B, 1033, 323, 1160, 439, "rank_b")

                    if found_s:
                        grade = 'S'
                    elif found_a:
                        grade = 'A'
                    elif found_b:
                        grade = 'B'

                # 更新统计
                if grade and grade != 'escape':
                    logui.info(f"钓起{grade}级鱼")
                    self.fish_count += 1
                    if grade == 'A':
                        self.fish_count_a += 1
                    elif grade == 'B':
                        self.fish_count_b += 1
                    elif grade == 'S':
                        self.fish_count_s += 1
                    if self.stats_callback:
                        self.stats_callback(grade)
                elif not grade:
                    logui.info("未识别到鱼获等级，仍计为成功")
                    self.fish_count += 1
                    if self.stats_callback:
                        self.stats_callback('unknown')

                # 最后关掉成功界面
                logui.info("钓鱼成功，后台按 ESC")
                press_key(self.hwnd, 0x1B)
                time.sleep(0.5)
                return True

            elif result == 'escape':
                logui.info("鱼逃走了")
                return False
            elif result == 'timeout':
                logui.info("等待超时次数过多，放弃本次钓鱼")
                return False
            else:
                logui.info("未知状态，退出本次钓鱼")
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
            total = self.fish_count_a + self.fish_count_b + self.fish_count_s
            logui.info(f"结束，共钓鱼 {total} 条 (A:{self.fish_count_a} B:{self.fish_count_b} S:{self.fish_count_s})")

    def _smart_sleep(self, seconds, interval=0.05):
        elapsed = 0
        while elapsed < seconds and not self.stop_event.is_set():
            time.sleep(min(interval, seconds - elapsed))
            elapsed += interval