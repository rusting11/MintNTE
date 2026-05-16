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
PATH_CATCH_FISH = resource_path(os.path.join(IMG_DIR, "catch_fish.png"))
PATH_ENDURANCE_FISH = resource_path(os.path.join(IMG_DIR, "endurance_fish.bmp"))
MATCH_THRESH = 0.7

TIMEOUT_FIND_HOOK = 35      # 等待鱼钩出现的最长时间（秒）
TIMEOUT_CATCH_FISH = 15     # 等待上鱼信号的最长时间（秒）
TIMEOUT_FISHING = 60        # 按F起钩阶段的最长时间（秒）

def fake_activate(hwnd):
    try: win32gui.SendMessage(hwnd, 0x0006, 1, 0)
    except: pass

def press_key(hwnd, vk_code, duration=0.05):
    fake_activate(hwnd)
    send_key_down(hwnd, vk_code)
    time.sleep(duration)
    send_key_up(hwnd, vk_code)

DEBUG_DIR = os.path.join(BASE_DIR, "debug_screenshots")

def find_image_in_region(hwnd, template_path, left, top, right, bottom, threshold=MATCH_THRESH, debug=False):
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
    if debug:
        logui.info(f"[DEBUG] {os.path.basename(template_path)} match={max_val:.4f} region=({left},{top},{right},{bottom})")
        _save_debugScreenshot(img, template_path, left, top, right, bottom, max_val, threshold)
    if max_val >= threshold:
        th, tw = tpl.shape
        return (max_loc[0] + tw//2 + x1, max_loc[1] + th//2 + y1)
    return None

def _save_debugScreenshot(img, template_path, left, top, right, bottom, match_val, threshold):
    try:
        os.makedirs(DEBUG_DIR, exist_ok=True)
        debug_img = img.copy()
        h, w = debug_img.shape[:2]
        for gx in range(0, w, 100):
            cv2.line(debug_img, (gx, 0), (gx, h), (80, 80, 80), 1)
            cv2.putText(debug_img, str(gx), (gx+2, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200,200,200), 1)
        for gy in range(0, h, 100):
            cv2.line(debug_img, (0, gy), (w, gy), (80, 80, 80), 1)
            cv2.putText(debug_img, str(gy), (2, gy+14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200,200,200), 1)
        x1 = max(0, min(left, w-1))
        y1 = max(0, min(top, h-1))
        x2 = max(x1+1, min(right, w))
        y2 = max(y1+1, min(bottom, h))
        color = (0, 255, 0) if match_val >= threshold else (0, 0, 255)
        cv2.rectangle(debug_img, (x1, y1), (x2, y2), color, 2)
        label = f"{os.path.basename(template_path)} {match_val:.4f}"
        cv2.putText(debug_img, label, (x1, max(y1 - 8, 16)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        ts = time.strftime("%H%M%S")
        fname = f"debug_{ts}_{os.path.basename(template_path).split('.')[0]}.png"
        cv2.imwrite(os.path.join(DEBUG_DIR, fname), debug_img)
        logui.info(f"[DEBUG] 截图已保存: {fname}")
    except Exception as e:
        logui.warning(f"[DEBUG] 保存截图失败: {e}")

def throw_rod(stop_event=None):
    """抛竿自动化：按F抛竿 → 等鱼钩 → 等上鱼信号 → 按F起钩 → 持续按F直到结束图标"""
    logui.info("当前在钓鱼界面，按F抛竿")
    hwnd = get_game_hwnd()
    if not hwnd or not win32gui.IsWindow(hwnd):
        logui.warning("窗口无效，无法抛竿")
        return False

    press_key(hwnd, 0x46, duration=0.05)
    time.sleep(0.5)

    # —— 1. 等待鱼钩出现（确认抛竿成功）——
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
            logui.info("检测到鱼钩，等待上鱼信号...")
            break
        time.sleep(1.5)

    # —— 2. 等待上鱼信号（catch_fish.png）再按F ——
    start = time.time()
    last_debug = 0
    while True:
        if stop_event and stop_event.is_set(): return False
        if time.time() - start > TIMEOUT_CATCH_FISH:
            logui.warning(f"等待上鱼信号超时({TIMEOUT_CATCH_FISH}s)，鱼可能跑了")
            return False
        hwnd = get_game_hwnd()
        if not hwnd or not win32gui.IsWindow(hwnd):
            logui.warning("窗口丢失，退出抛竿")
            return False
        if time.time() - last_debug >= 2:
            find_image_in_region(hwnd, PATH_CATCH_FISH, 783, 247, 1170, 275)
            last_debug = time.time()
        if find_image_in_region(hwnd, PATH_CATCH_FISH, 783, 247, 1170, 275):
            logui.info("检测到上鱼信号，按F起钩")
            press_key(hwnd, 0x46, duration=0.05)
            break
        time.sleep(0.3)

    # —— 3. 持续按F，直到出现结束图标或超时 ——
    start = time.time()
    while True:
        if stop_event and stop_event.is_set():
            send_key_up(hwnd, 0x46)
            return False
        if time.time() - start > TIMEOUT_FISHING:
            logui.warning(f"起钩超时({TIMEOUT_FISHING}s)，可能掉线")
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