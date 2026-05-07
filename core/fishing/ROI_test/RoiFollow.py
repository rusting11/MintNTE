# core/fishing/fishing_roi/RoiFollow.py
import sys
import time
import threading
import math
import win32gui
from Module.click.NET_click import send_key_down, send_key_up, fake_activate_window
from core.fishing.fishing_roi.fishing_roi_core import FishingROICore
from Module.Hwnd.game_hwnd import set_locked_hwnd, get_game_hwnd

# ---------- 可配置参数 ----------
BASE_ROI = (606, 64, 1319, 85)
TITLEBAR_OFFSET = 0
ACTUAL_ROI = (BASE_ROI[0], BASE_ROI[1] + TITLEBAR_OFFSET, BASE_ROI[2], BASE_ROI[3] + TITLEBAR_OFFSET)

MOVE_THRESHOLD = 15
BASE_KEY_DURATION = 0.05
MAX_KEY_DURATION = 0.15
SPEED_FACTOR = 0.002
UPDATE_INTERVAL = 0.02
LEFT_KEY = 0x41      # 'A'
RIGHT_KEY = 0x44     # 'D'

# 默认窗口句柄（您提供的）
DEFAULT_HWND = 423432556

class FishingFollower:
    def __init__(self, hwnd=None):
        if hwnd is None:
            hwnd = DEFAULT_HWND
            # 仍然检查窗口是否有效
            if not win32gui.IsWindow(hwnd):
                # 如果无效，再尝试获取已锁定的窗口
                hwnd = get_game_hwnd()
                if not hwnd or not win32gui.IsWindow(hwnd):
                    raise RuntimeError(f"默认句柄 {DEFAULT_HWND} 无效，且未找到锁定的窗口")
        else:
            set_locked_hwnd(hwnd)
            if not win32gui.IsWindow(hwnd):
                raise RuntimeError(f"无效窗口句柄: {hwnd}")
        self.hwnd = hwnd
        self.roi_core = FishingROICore(ACTUAL_ROI)
        if self.roi_core.hwnd != self.hwnd:
            self.roi_core.hwnd = self.hwnd
        self.running = False
        self.thread = None
        self.lock = threading.Lock()
        self.last_a_center = None
        self.last_time = None
        self.current_speed = 0.0

    def start(self):
        if self.running:
            return
        self.running = True
        self.roi_core.start()
        self.thread = threading.Thread(target=self._control_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
        self.roi_core.stop()
        send_key_up(self.hwnd, LEFT_KEY)
        send_key_up(self.hwnd, RIGHT_KEY)

    def _get_center(self, rect):
        if rect is None:
            return None
        x1, y1, x2, y2 = rect
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    def _calculate_speed(self, current_center):
        with self.lock:
            if self.last_a_center and self.last_time:
                dt = time.time() - self.last_time
                if dt > 0.001:
                    dx = current_center[0] - self.last_a_center[0]
                    dy = current_center[1] - self.last_a_center[1]
                    speed = math.hypot(dx, dy) / dt
                    self.current_speed = speed
            self.last_a_center = current_center
            self.last_time = time.time()
        return self.current_speed

    def _get_key_duration(self, speed):
        duration = BASE_KEY_DURATION + speed * SPEED_FACTOR
        return min(duration, MAX_KEY_DURATION)

    def _control_loop(self):
        while self.running:
            fake_activate_window(self.hwnd)
            data = self.roi_core.get_data()
            rect_a = data['color_a']['rect']
            rect_b = data['color_b']['rect']
            if rect_a is None or rect_b is None:
                send_key_up(self.hwnd, LEFT_KEY)
                send_key_up(self.hwnd, RIGHT_KEY)
                time.sleep(UPDATE_INTERVAL)
                continue

            center_a = self._get_center(rect_a)
            center_b = self._get_center(rect_b)
            if center_a is None or center_b is None:
                continue

            speed = self._calculate_speed(center_a)
            key_duration = self._get_key_duration(speed)

            offset = center_b[0] - center_a[0]
            if offset < -MOVE_THRESHOLD:
                send_key_up(self.hwnd, LEFT_KEY)
                send_key_down(self.hwnd, RIGHT_KEY)
                time.sleep(key_duration)
                send_key_up(self.hwnd, RIGHT_KEY)
            elif offset > MOVE_THRESHOLD:
                send_key_up(self.hwnd, RIGHT_KEY)
                send_key_down(self.hwnd, LEFT_KEY)
                time.sleep(key_duration)
                send_key_up(self.hwnd, LEFT_KEY)
            else:
                send_key_up(self.hwnd, LEFT_KEY)
                send_key_up(self.hwnd, RIGHT_KEY)

            time.sleep(UPDATE_INTERVAL)


# ---------- 独立测试入口 ----------
if __name__ == "__main__":
    # 支持命令行参数覆盖默认句柄，但如果不传参则直接使用默认句柄
    if len(sys.argv) == 2:
        try:
            hwnd = int(sys.argv[1])
            print(f"使用命令行传入的句柄: {hwnd}")
        except ValueError:
            print("句柄必须是整数")
            sys.exit(1)
    else:
        hwnd = DEFAULT_HWND
        print(f"使用默认窗口句柄: {hwnd}")

    if not win32gui.IsWindow(hwnd):
        print(f"窗口句柄 {hwnd} 无效，请检查游戏是否运行")
        sys.exit(1)

    fake_activate_window(hwnd)
    time.sleep(0.1)

    try:
        follower = FishingFollower(hwnd=hwnd)
        print("开始跟随，按 Ctrl+C 停止")
        follower.start()
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n停止跟随")
        follower.stop()
    except Exception as e:
        print(f"错误: {e}")
        if 'follower' in locals():
            follower.stop()