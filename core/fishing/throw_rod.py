# core/fishing/throw_rod.py
# 基于窗口句柄  D:\Github\NTE_boheAI\Module\Hwnd\game_hwnd.py
# 在窗口区域找图
# 在区域1731,925,1818,1012找fish_hook.png
# 找到后while循环按F
# 在基于窗口内478,26,591,123找endurance_fish.bmp找后突出循环
# core/fishing/throw_rod.py
import os, sys, time, cv2, numpy as np, win32gui

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path: sys.path.insert(0, BASE_DIR)

from Module.Hwnd.game_hwnd import get_game_hwnd
from Module.click.NET_click import send_key_down, send_key_up
from UI import logui

def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except: base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

IMG_DIR = "fishingimages"
PATH_FISH_HOOK = resource_path(os.path.join(IMG_DIR, "fish_hook.png"))
PATH_ENDURANCE_FISH = resource_path(os.path.join(IMG_DIR, "endurance_fish.bmp"))
MATCH_THRESH = 0.7

TIMEOUT_FIND_HOOK = 35      # 等待鱼钩出现的最长时间（秒）
TIMEOUT_FISHING = 60      # 抛竿阶段的最长时间（秒）

def fake_activate(hwnd):
    try: win32gui.SendMessage(hwnd, 0x0006, 1, 0)
    except: pass

def press_key(hwnd, vk_code, duration=0.05):
    fake_activate(hwnd)
    send_key_down(hwnd, vk_code)
    time.sleep(duration)
    send_key_up(hwnd, vk_code)

def find_image_in_region(hwnd, template_path, left, top, right, bottom, threshold=MATCH_THRESH):
    if not win32gui.IsWindow(hwnd): return None
    from core.fishing.fishing_utils import capture_window_to_cv
    img = capture_window_to_cv(hwnd)
    if img is None: return None
    h, w = img.shape[:2]
    x1, y1 = max(0, min(left, w-1)), max(0, min(top, h-1))
    x2, y2 = max(x1+1, min(right, w)), max(y1+1, min(bottom, h))
    if x2-x1 < 10 or y2-y1 < 10: return None
    roi = img[y1:y2, x1:x2]
    tpl = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if tpl is None: return None
    res = cv2.matchTemplate(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), tpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(res)
    if max_val >= threshold:
        th, tw = tpl.shape
        return (max_loc[0] + tw//2 + x1, max_loc[1] + th//2 + y1)
    return None

def throw_rod(stop_event=None):
    """抛竿自动化，加入超时检测，掉线后自动退出循环"""
    logui.info("当前在钓鱼界面全速后台钓鱼")

    # —— 等待鱼钩 ——
    start = time.time()
    while True:
        if stop_event and stop_event.is_set(): return False
        if time.time() - start > TIMEOUT_FIND_HOOK:
            logui.warning(f"等待鱼钩超时({TIMEOUT_FIND_HOOK}s)，可能已掉线")
            return False
        hwnd = get_game_hwnd()
        if not hwnd or not win32gui.IsWindow(hwnd):
            time.sleep(0.5)
            continue
        if find_image_in_region(hwnd, PATH_FISH_HOOK, 1731, 925, 1818, 1012):
            logui.info("检测到鱼钩，开始持续按F")
            break
        time.sleep(1.5)

    # —— 持续按F，直到出现结束图标或超时 ——
    start = time.time()
    while True:
        if stop_event and stop_event.is_set():
            send_key_up(hwnd, 0x46)
            return False
        if time.time() - start > TIMEOUT_FISHING:
            logui.warning(f"抛竿超时({TIMEOUT_FISHING}s)，可能掉线")
            send_key_up(hwnd, 0x46)
            return False
        hwnd = get_game_hwnd()
        if not hwnd or not win32gui.IsWindow(hwnd):
            logui.warning("窗口丢失，退出抛竿")
            return False
        if find_image_in_region(hwnd, PATH_ENDURANCE_FISH, 478, 26, 591, 123):
            logui.info("检测到结束图标，停止按F")
            return True
        press_key(hwnd, 0x46, duration=0.05)
        time.sleep(0.1)
# 单独测试入口----------→只判断起勾
if __name__ == "__main__":
    throw_rod()