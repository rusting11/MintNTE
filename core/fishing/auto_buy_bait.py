import time
import random
import sys
import os
import cv2
import numpy as np
import win32gui
import win32con
from PIL import ImageGrab

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)
from Module.Hwnd.game_hwnd import get_game_hwnd
from Module.click.NET_click import (
    send_key_down, send_key_up,
    simulate_mouse_click_relative
)
from UI import logui

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

IMG_DIR = "fishingimages"
PATH_WANNGENYUER = resource_path(os.path.join(IMG_DIR, "wannengyuer.png"))
PATH_YUERLAMAN = resource_path(os.path.join(IMG_DIR, "yuerlaman.png"))
PATH_GOUMAIYUER = resource_path(os.path.join(IMG_DIR, "goumaiyuer.png"))
PATH_QUEREN = resource_path(os.path.join(IMG_DIR, "queren.png"))
PATH_YUERTISHIQUEREN = resource_path(os.path.join(IMG_DIR, "yueertishiqueren.png"))
PATH_DIANJIKONGBAI = resource_path(os.path.join(IMG_DIR, "dianjikongbai.png"))
PATH_GENGHUANWANNGYUER = resource_path(os.path.join(IMG_DIR, "genghuanwannnegyuer.png"))
PATH_GENGHUAN = resource_path(os.path.join(IMG_DIR, "genghuan.png"))
PATH_PANDUANDIAOYU = resource_path(os.path.join(IMG_DIR, "panduandiaoyu.png"))
MATCH_THRESH = 0.7

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

def find_image_in_window(template_path, hwnd, timeout=0, interval=0.2):
    if not hwnd:
        return None
    rect = win32gui.GetClientRect(hwnd)
    left_top = win32gui.ClientToScreen(hwnd, (0, 0))
    right_bottom = win32gui.ClientToScreen(hwnd, (rect[2], rect[3]))
    client_rect = (left_top[0], left_top[1], right_bottom[0], right_bottom[1])
    start = time.time()
    while timeout <= 0 or (time.time() - start) < timeout:
        try:
            img = ImageGrab.grab(bbox=client_rect)
            gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
            template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
            if template is None:
                return None
            res = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            if max_val >= MATCH_THRESH:
                h, w = template.shape
                return (max_loc[0] + w//2, max_loc[1] + h//2)
        except:
            pass
        time.sleep(interval)
    return None

def click_image_in_window(template_path, hwnd, wait=0.5, timeout=2):
    pos = find_image_in_window(template_path, hwnd, timeout=timeout)
    if pos:
        simulate_mouse_click_relative(hwnd, pos[0], pos[1])
        time.sleep(wait)
        return True
    return False

def do_buy_bait(hwnd):
    logui.info("[购买] 开始购买鱼饵流程")
    press_key(hwnd, 0x52)   # R
    time.sleep(1)

    if not click_image_in_window(PATH_WANNGENYUER, hwnd, wait=0.5, timeout=3):
        logui.error("万能鱼饵已经没了 (后台检测)")
        press_key(hwnd, 0x1B)
        return False
    logui.info("点击万能鱼饵 (前台点击)")

    click_image_in_window(PATH_YUERLAMAN, hwnd, wait=0.5, timeout=3)
    logui.info("鱼饵拉满99 (前台点击)")

    simulate_mouse_click_relative(hwnd, 1824, 956)
    logui.info("再次点击防止只购买一个")
    time.sleep(0.1)

    click_image_in_window(PATH_GOUMAIYUER, hwnd, wait=1, timeout=3)
    logui.info("购买 (前台点击)")

    click_image_in_window(PATH_QUEREN, hwnd, wait=1, timeout=3)
    logui.info("确认 (前台点击)")

    click_image_in_window(PATH_YUERTISHIQUEREN, hwnd, wait=1, timeout=3)
    logui.info("确认 (前台点击)")

    logui.info("点击空白区域关闭界面优先后台ESC (后台ESC)")
    press_key(hwnd, 0x1B)
    time.sleep(1)
    logui.info("点击空白区域关闭界面优先后台ESC (后台ESC)")
    press_key(hwnd, 0x1B)
    time.sleep(1)

    logui.info("[购买] 购买完成，开始更换鱼饵")
    if not find_image_in_window(PATH_PANDUANDIAOYU, hwnd, timeout=5):
        logui.error("[更换] 未回到钓鱼界面")
        return False
    press_key(hwnd, 0x45)   # E
    time.sleep(1)

    click_image_in_window(PATH_GENGHUAN, hwnd, wait=1, timeout=3)
    logui.info("你没有选择鱼饵 选择更换 (前台点击)")
    time.sleep(1)

    if find_image_in_window(PATH_PANDUANDIAOYU, hwnd, timeout=5):
        logui.info("[更换] 更换成功")
    return True

def auto_buy_bait():
    hwnd = get_game_hwnd()
    if not hwnd:
        logui.error("[自动购买] 未找到游戏窗口")
        return False
    logui.info(f"[自动购买] 获取到窗口句柄: {hwnd}")
    return do_buy_bait(hwnd)