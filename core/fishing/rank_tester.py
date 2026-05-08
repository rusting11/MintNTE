# core/fishing/rank_tester.py
"""
独立测试脚本：基于固定窗口句柄 20977790 检测鱼获等级 (A/B/S/逃走)
使用后台截图 PrintWindow，并保存识别区域截图以供校验。
"""
import os
import sys
import time
import cv2
import numpy as np
import win32gui

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE_DIR)

from core.fishing.fishing_utils import capture_window_to_cv

HWND = 20977790                 # 固定句柄

IMG_DIR = os.path.join(BASE_DIR, "core", "fishing", "fishingimages", "rank_fish")
PATH_FISH_GONE = os.path.join(IMG_DIR, "fish_gone.bmp")
PATH_RANK_A    = os.path.join(IMG_DIR, "rank_a_fish.bmp")
PATH_RANK_B    = os.path.join(IMG_DIR, "rank_b_fish.bmp")
PATH_RANK_S    = os.path.join(IMG_DIR, "rank_s_fish.bmp")

MATCH_THRESH = 0.7              # 匹配阈值

# 检测区域（客户区坐标）
ROI_FISH_GONE = (1305, 585, 1473, 637)      # 逃走图标区域
ROI_RANK      = (1033, 323, 1160, 439)       # 等级图标区域（新）

# 截图保存路径（保存在脚本所在目录下）
SAVE_GONE = "debug_gone.png"
SAVE_RANK = "debug_rank.png"

def match_region(frame, template_path, left, top, right, bottom, name="?"):
    """在指定区域内匹配模板，返回(是否找到, 最大匹配度)"""
    h, w = frame.shape[:2]
    x1 = max(0, left)
    y1 = max(0, top)
    x2 = min(w, right)
    y2 = min(h, bottom)
    if x2 - x1 < 5 or y2 - y1 < 5:
        return False, 0.0
    roi = frame[y1:y2, x1:x2]
    tpl = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if tpl is None:
        print(f"模板加载失败: {template_path}")
        return False, 0.0
    roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    res = cv2.matchTemplate(roi_gray, tpl, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, _ = cv2.minMaxLoc(res)
    found = max_val >= MATCH_THRESH
    return found, max_val

def main():
    print(f"开始监测窗口句柄 {HWND}，按 Ctrl+C 停止")
    print(f"等级识别区域已更新为 {ROI_RANK}")
    print(f"识别区域截图将保存为 {SAVE_GONE} 和 {SAVE_RANK}\n")

    while True:
        frame = capture_window_to_cv(HWND)
        if frame is None:
            print("截图失败，等待窗口...")
            time.sleep(1)
            continue

        # 裁剪并保存 fish_gone 检测区域
        x1, y1, x2, y2 = ROI_FISH_GONE
        h, w = frame.shape[:2]
        x1 = max(0, x1); y1 = max(0, y1)
        x2 = min(w, x2); y2 = min(h, y2)
        if x2 > x1 and y2 > y1:
            cv2.imwrite(SAVE_GONE, frame[y1:y2, x1:x2])

        # 裁剪并保存 rank 检测区域（新）
        x1, y1, x2, y2 = ROI_RANK
        x1 = max(0, x1); y1 = max(0, y1)
        x2 = min(w, x2); y2 = min(h, y2)
        if x2 > x1 and y2 > y1:
            cv2.imwrite(SAVE_RANK, frame[y1:y2, x1:x2])

        # 检测
        is_gone, m_gone = match_region(frame, PATH_FISH_GONE, *ROI_FISH_GONE, "fish_gone")
        found_s, m_s = match_region(frame, PATH_RANK_S, *ROI_RANK, "rank_s")
        found_a, m_a = match_region(frame, PATH_RANK_A, *ROI_RANK, "rank_a")
        found_b, m_b = match_region(frame, PATH_RANK_B, *ROI_RANK, "rank_b")

        t = time.strftime("%H:%M:%S")
        result = "无"
        if is_gone:
            result = "逃走"
        elif found_s:
            result = "S级"
        elif found_a:
            result = "A级"
        elif found_b:
            result = "B级"

        print(f"{t}  |  {result:4s}  | "
              f"gone={m_gone:.2f} S={m_s:.2f} A={m_a:.2f} B={m_b:.2f}")

        time.sleep(0.5)

if __name__ == "__main__":
    main()