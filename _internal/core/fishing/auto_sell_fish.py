import time
import os
import sys
import cv2
import numpy as np
import win32gui
from PIL import ImageGrab

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from Module.click.NET_click import send_key_down, send_key_up, simulate_mouse_click_relative
from UI import logui

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

IMG_DIR = "fishingimages"
PATH_KUAISUTIJIAO = resource_path(os.path.join(IMG_DIR, "kuaisutijiao.png"))
PATH_DIANJIKONGBAI = resource_path(os.path.join(IMG_DIR, "dianjikongbai.png"))
PATH_YIJIANCHUSHOUJIEMIAN = resource_path(os.path.join(IMG_DIR, "yijianchushoujiemian.png"))
PATH_GUILIUYUCHANG = resource_path(os.path.join(IMG_DIR, "guiliuyuchang.png"))
PATH_YIJIANCHUSHOU = resource_path(os.path.join(IMG_DIR, "yijianchushou.png"))
PATH_YIJIANCHUSHOUYES = resource_path(os.path.join(IMG_DIR, "yijianchushouyes.png"))
PATH_X = resource_path(os.path.join(IMG_DIR, "x.png"))

MATCH_THRESH = 0.7

def fake_activate(hwnd):
    try:
        win32gui.SendMessage(hwnd, 0x0006, 1, 0)
    except:
        pass

def press_key(hwnd, vk_code, duration=0.05):
    fake_activate(hwnd)
    send_key_down(hwnd, vk_code)
    time.sleep(duration)
    send_key_up(hwnd, vk_code)

def find_image_in_window(template_path, hwnd, timeout=0):
    if not hwnd or not win32gui.IsWindow(hwnd):
        return None
    rect = win32gui.GetClientRect(hwnd)
    lt = win32gui.ClientToScreen(hwnd, (0, 0))
    rb = win32gui.ClientToScreen(hwnd, (rect[2], rect[3]))
    bbox = (lt[0], lt[1], rb[0], rb[1])
    start = time.time()
    while timeout <= 0 or (time.time() - start) < timeout:
        try:
            img = ImageGrab.grab(bbox=bbox)
            gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
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
        time.sleep(0.2)
    return None

def sell_fish(hwnd):
    logui.info("开始自动售卖鱼获")
    # 1. 进入卖鱼界面
    press_key(hwnd, 0x51)   # Q键
    logui.info("进入【卖鱼界面】")
    time.sleep(1)

    # 2. 循环找到快速出售
    logui.info("寻找【快速出售】")
    while not find_image_in_window(PATH_GUILIUYUCHANG, hwnd, timeout=0):
        pos = find_image_in_window(PATH_KUAISUTIJIAO, hwnd, timeout=0)
        if pos:
            logui.info("点击【快速出售】")
            simulate_mouse_click_relative(hwnd, pos[0], pos[1])
            time.sleep(1)
        pos = find_image_in_window(PATH_DIANJIKONGBAI, hwnd, timeout=0)
        if pos:
            logui.info("成功卖出【按esc】")
            press_key(hwnd, 0x1B)
            time.sleep(1.5)
        pos = find_image_in_window(PATH_YIJIANCHUSHOUJIEMIAN, hwnd, timeout=0)
        if pos:
            logui.info("点击进入【归流鱼舱界面】")
            simulate_mouse_click_relative(hwnd, pos[0], pos[1])
            time.sleep(1)
        # 如果已经进入了归流鱼舱，则 guiliuyuchang.png 会出现，外部循环退出
        time.sleep(0.2)

    logui.info("当前【归流鱼舱界面】")

    # 3. 一键出售
    while True:
        pos = find_image_in_window(PATH_X, hwnd, timeout=0)
        if pos:
            logui.info("【退出卖鱼】")
            press_key(hwnd, 0x1B)
            break
        pos = find_image_in_window(PATH_YIJIANCHUSHOU, hwnd, timeout=0)
        if pos:
            logui.info("点击【一键出售】")
            simulate_mouse_click_relative(hwnd, pos[0], pos[1])
            time.sleep(1)
        pos = find_image_in_window(PATH_YIJIANCHUSHOUYES, hwnd, timeout=0)
        if pos:
            logui.info("【确认一键出售】")
            simulate_mouse_click_relative(hwnd, pos[0], pos[1])
            time.sleep(1)
        pos = find_image_in_window(PATH_DIANJIKONGBAI, hwnd, timeout=0)
        if pos:
            logui.info("成功卖出【按esc】")
            press_key(hwnd, 0x1B)
        time.sleep(0.2)