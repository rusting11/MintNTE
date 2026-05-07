# background_core.py —— 纯后台截图核心（替换后即可生效）
import threading, time, cv2, numpy as np
from collections import deque
import win32gui, win32ui, win32con
import pydirectinput

# ================= 全局动态参数（由 UI 写入） =================
MIN_TRIGGER_PIXELS = None
JUDGE_RADIUS = None
JUDGE_Y_OFFSET = None
COOLDOWN_MS = None

# ================= 颜色配置 =================
TRACK_COLORS = {
    'D': [ (255, 244, 86), (28, 27, 27) ],
    'F': [ (132, 216, 255), (26, 26, 26) ],
    'J': [ (111, 130, 255), (26, 26, 26) ],
    'K': [ (26, 26, 26) ],
}

def build_hsv_ranges(bgr_list, h_ext=20, sv_ext=40):
    ranges = []
    for bgr in bgr_list:
        col = np.uint8([[bgr]])
        hsv = cv2.cvtColor(col, cv2.COLOR_BGR2HSV)[0][0]
        h, s, v = hsv
        if v < 30:
            h_ext_dark, sv_ext_dark = 10, 25
            h_low = max(0, h - h_ext_dark)
            h_high = min(179, h + h_ext_dark)
            s_low = max(0, s - sv_ext_dark)
            s_high = min(255, s + sv_ext_dark)
            v_low = max(0, v - sv_ext_dark)
            v_high = min(255, v + sv_ext_dark)
        else:
            h_low = max(0, h - h_ext)
            h_high = min(179, h + h_ext)
            s_low = max(0, s - sv_ext)
            s_high = min(255, s + sv_ext)
            v_low = max(0, v - sv_ext)
            v_high = min(255, v + sv_ext)
            if v_low < 80:
                v_low = 80
        ranges.append( (np.array([h_low, s_low, v_low], dtype=np.uint8),
                        np.array([h_high, s_high, v_high], dtype=np.uint8)) )
    return ranges

HSV_RANGES = {}
for name, colors in TRACK_COLORS.items():
    HSV_RANGES[name] = build_hsv_ranges(colors)

TRACKS = [
    {'name': 'D', 'key': 'd', 'circle_base': (442, 838)},
    {'name': 'F', 'key': 'f', 'circle_base': (779, 838)},
    {'name': 'J', 'key': 'j', 'circle_base': (1141, 838)},
    {'name': 'K', 'key': 'k', 'circle_base': (1477, 838)},
]

def capture_window_background(hwnd):
    """使用 PrintWindow 获取窗口离屏图像（BGR格式）"""
    if not win32gui.IsWindow(hwnd):
        return None
    rect = win32gui.GetClientRect(hwnd)
    w, h = rect[2] - rect[0], rect[3] - rect[1]
    if w <= 0 or h <= 0:
        return None

    hwndDC = win32gui.GetWindowDC(hwnd)
    mfcDC = win32ui.CreateDCFromHandle(hwndDC)
    saveDC = mfcDC.CreateCompatibleDC()
    saveBitMap = win32ui.CreateBitmap()
    saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
    saveDC.SelectObject(saveBitMap)

    result = win32gui.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)
    if result != 1:
        result = win32gui.PrintWindow(hwnd, saveDC.GetSafeHdc(), 0)

    bmpinfo = saveBitMap.GetInfo()
    bmpstr = saveBitMap.GetBitmapBits(True)
    img = np.frombuffer(bmpstr, dtype=np.uint8).reshape((bmpinfo['bmHeight'], bmpinfo['bmWidth'], 4))

    win32gui.DeleteObject(saveBitMap.GetHandle())
    saveDC.DeleteDC()
    mfcDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, hwndDC)

    if img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    return img


class BackgroundPlayer:
    def __init__(self, hwnd, tracks):
        self.hwnd = hwnd
        self.tracks = tracks
        self.num_tracks = len(tracks)

        if MIN_TRIGGER_PIXELS is None or JUDGE_RADIUS is None or COOLDOWN_MS is None:
            raise RuntimeError("❌ 参数未由 UI 设置")

        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.frame_queue = deque(maxlen=2)
        self.cond = threading.Condition(self.lock)

        self.color_counts = [0] * self.num_tracks
        self.active_states = [False] * self.num_tracks
        self.last_trigger_time = [0.0] * self.num_tracks
        self.prev_judge_active = [False] * self.num_tracks
        self.prev_judge_cnt = [0] * self.num_tracks

        self.processing_time = 0.0
        self.cap_thread = None
        self.det_thread = None

    def start(self):
        self.cap_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.cap_thread.start()
        self.det_thread = threading.Thread(target=self._detect_loop, daemon=True)
        self.det_thread.start()

    def stop(self):
        self.stop_event.set()
        with self.cond:
            self.cond.notify_all()
        if self.cap_thread and self.cap_thread.is_alive():
            self.cap_thread.join(timeout=1.5)
        if self.det_thread and self.det_thread.is_alive():
            self.det_thread.join(timeout=1.5)

    def get_shared_data(self):
        with self.lock:
            return (list(self.color_counts), list(self.active_states),
                    {'last_frame_time': time.perf_counter(), 'processing_time': self.processing_time})

    def _capture_loop(self):
        while not self.stop_event.is_set():
            frame = capture_window_background(self.hwnd)
            if frame is not None:
                with self.cond:
                    self.frame_queue.append(frame)
                    self.cond.notify_all()
            time.sleep(0.005)

    def _detect_loop(self):
        while not self.stop_event.is_set():
            frame = None
            with self.cond:
                while not self.frame_queue and not self.stop_event.is_set():
                    self.cond.wait(timeout=0.01)
                if self.stop_event.is_set():
                    break
                if self.frame_queue:
                    frame = self.frame_queue.popleft()
            if frame is None:
                continue

            t0 = time.perf_counter()
            now = t0

            for i, track in enumerate(self.tracks):
                track_name = track['name']
                cx_base, cy_base = track['circle_base']
                r = JUDGE_RADIUS.get(track_name, 15)
                cy = cy_base + (JUDGE_Y_OFFSET.get(track_name, 0) if JUDGE_Y_OFFSET else 0)

                x1, y1 = cx_base - r, cy - r
                x2, y2 = cx_base + r, cy + r
                if x1 < 0 or y1 < 0 or x2 > frame.shape[1] or y2 > frame.shape[0]:
                    continue

                roi_bgr = frame[y1:y2, x1:x2]
                mask = np.zeros((2 * r, 2 * r), dtype=np.uint8)
                cv2.circle(mask, (r, r), r, 255, -1)
                circle_pixels = roi_bgr[mask == 255]
                if circle_pixels.size == 0:
                    judge_cnt = 0
                else:
                    hsv = cv2.cvtColor(circle_pixels.reshape(-1, 1, 3), cv2.COLOR_BGR2HSV).reshape(-1, 3)
                    matched = np.zeros(len(hsv), dtype=bool)
                    for (lower, upper) in HSV_RANGES[track_name]:
                        m_h = (hsv[:, 0] >= lower[0]) & (hsv[:, 0] <= upper[0])
                        m_s = (hsv[:, 1] >= lower[1]) & (hsv[:, 1] <= upper[1])
                        m_v = (hsv[:, 2] >= lower[2]) & (hsv[:, 2] <= upper[2])
                        matched |= (m_h & m_s & m_v)
                    judge_cnt = int(np.count_nonzero(matched))

                self.color_counts[i] = judge_cnt
                is_active = judge_cnt >= MIN_TRIGGER_PIXELS.get(track_name, 3)

                cooldown = COOLDOWN_MS.get(track_name, 20) / 1000.0
                in_cooldown = (now - self.last_trigger_time[i]) < cooldown

                if self.prev_judge_active[i] and judge_cnt < MIN_TRIGGER_PIXELS.get(track_name, 3):
                    if not in_cooldown:
                        self.prev_judge_active[i] = False

                if track_name == 'J' or track_name == 'F':
                    jump_threshold = 5
                elif track_name == 'K':
                    jump_threshold = 4
                else:
                    jump_threshold = 8

                pixel_jump = judge_cnt - self.prev_judge_cnt[i] > jump_threshold

                trigger = False
                if is_active:
                    if not self.prev_judge_active[i]:
                        if not in_cooldown:
                            trigger = True
                    else:
                        if not in_cooldown and pixel_jump:
                            trigger = True

                if trigger:
                    threading.Thread(target=self._press_async, args=(track['key'], i), daemon=True).start()
                    self.last_trigger_time[i] = now
                    self.active_states[i] = True
                else:
                    if now - self.last_trigger_time[i] > 0.3:
                        self.active_states[i] = False

                self.prev_judge_active[i] = is_active
                self.prev_judge_cnt[i] = judge_cnt

            self.processing_time = time.perf_counter() - t0
            time.sleep(0.001)

    def _press_async(self, key, idx):
        pydirectinput.press(key)

