import threading
import time
import json
import sys
import os
import keyboard
import mouse
import win32gui
import win32con
import win32api
from PyQt5.QtCore import QObject, pyqtSignal, Qt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from UI import logui

def send_keyboard_message(hwnd, vk_code, is_down):
    msg = win32con.WM_KEYDOWN if is_down else win32con.WM_KEYUP
    lparam = (1) | (1 << 30) if is_down else (1) | (1 << 30) | (1 << 31)
    try:
        win32gui.PostMessage(hwnd, msg, vk_code, lparam)
    except Exception as e:
        logui.error(f"发送键盘消息失败: {e}")

def send_mouse_message(hwnd, button, is_down):
    msg_map = {
        'left':   (win32con.WM_LBUTTONDOWN, win32con.WM_LBUTTONUP),
        'right':  (win32con.WM_RBUTTONDOWN, win32con.WM_RBUTTONUP),
        'middle': (win32con.WM_MBUTTONDOWN, win32con.WM_MBUTTONUP),
    }
    if button not in msg_map:
        return
    msg = msg_map[button][0] if is_down else msg_map[button][1]
    try:
        win32gui.PostMessage(hwnd, msg, 0, 0)
    except Exception as e:
        logui.error(f"发送鼠标消息失败: {e}")

def fake_activate(hwnd):
    try:
        win32gui.SendMessage(hwnd, 0x0006, 1, 0)
    except:
        pass

class MacroCore(QObject):
    script_updated = pyqtSignal(list)
    status_message = pyqtSignal(str)
    recording_state_changed = pyqtSignal(bool)
    running_state_changed = pyqtSignal(bool)
    hwnd_updated = pyqtSignal(str)

    def __init__(self, loop_count=99, target_title="异环"):
        super().__init__()
        self.recording = False
        self.macro_running = False
        self.target_hwnd = None
        self.target_title = target_title
        self.recorded_actions = []
        self.last_record_time = None
        self.loop_count = loop_count

    def find_window(self, title=None):
        if title:
            self.target_title = title
        hwnd = self._find_window_by_title(self.target_title)
        if hwnd:
            self.target_hwnd = hwnd
            msg = f"已绑定窗口: {self.target_title} (句柄 {hwnd})"
            self.status_message.emit(msg)
            self.hwnd_updated.emit(f"句柄: {hwnd}")
            logui.info(msg)
            return True
        else:
            self.target_hwnd = None
            self.status_message.emit("未找到匹配窗口")
            self.hwnd_updated.emit("句柄: 未找到")
            logui.error("未找到匹配窗口")
            return False

    def _find_window_by_title(self, title):
        result = None
        def callback(hwnd, _):
            nonlocal result
            if win32gui.IsWindowVisible(hwnd) and title in win32gui.GetWindowText(hwnd):
                result = hwnd
        win32gui.EnumWindows(callback, None)
        return result

    def toggle_record(self):
        if not self.recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        if self.macro_running:
            self._stop_macro()
        self.recorded_actions.clear()
        self.recording = True
        self.recording_state_changed.emit(True)
        self.status_message.emit("录制中... (Alt+Y 停止)")
        logui.info("开始录制宏")
        self.last_record_time = time.time()
        keyboard.hook(self._on_keyboard_event, suppress=False)
        mouse.hook(self._on_mouse_event)

    def _stop_recording(self):
        self.recording = False
        self.recording_state_changed.emit(False)
        self.status_message.emit("录制已停止")
        logui.info("停止录制")
        keyboard.unhook(self._on_keyboard_event)
        mouse.unhook(self._on_mouse_event)

    def _on_keyboard_event(self, e):
        if not self.recording:
            return
        if e.event_type in ('down', 'up'):
            now = time.time()
            delay = now - self.last_record_time if self.last_record_time else 0
            self.last_record_time = now
            vk = key_name_to_vk(e.name, e.scan_code)
            if vk is None:
                return
            is_down = (e.event_type == 'down')
            self.recorded_actions.append(('key', vk, is_down, delay))

    def _on_mouse_event(self, e):
        if not self.recording or not isinstance(e, mouse.ButtonEvent):
            return
        if e.event_type not in ('down', 'up'):
            return
        now = time.time()
        delay = now - self.last_record_time if self.last_record_time else 0
        self.last_record_time = now
        button = normalize_mouse_button(e.button)
        if button is None:
            return
        is_down = (e.event_type == 'down')
        self.recorded_actions.append(('mouse', button, is_down, delay))

    def toggle_macro(self):
        if not self.macro_running:
            self._start_macro()
        else:
            self._stop_macro()

    def _start_macro(self):
        if not self.target_hwnd:
            self.find_window()
        if not self.target_hwnd:
            self.status_message.emit("❌ 目标窗口未绑定")
            return
        if self.recording:
            self._stop_recording()
        if not self.recorded_actions:
            self.status_message.emit("❌ 无录制动作")
            return
        self.macro_running = True
        self.running_state_changed.emit(True)
        self.status_message.emit("▶ 宏运行中... (Alt+T 停止)")
        logui.info("开始回放宏")
        threading.Thread(target=self._run_macro_loop, daemon=True).start()

    def _stop_macro(self):
        self.macro_running = False
        self.running_state_changed.emit(False)
        self.status_message.emit("⏹ 宏已停止")
        logui.info("停止回放")

    def _run_macro_loop(self):
        for _ in range(self.loop_count):
            if not self.macro_running:
                break
            for action in self.recorded_actions:
                if not self.macro_running:
                    break
                act_type, data, is_down, delay = action
                if delay > 0.001:
                    time.sleep(delay)
                if not self.macro_running:
                    break
                fake_activate(self.target_hwnd)
                if act_type == 'key':
                    send_keyboard_message(self.target_hwnd, data, is_down)
                elif act_type == 'mouse':
                    send_mouse_message(self.target_hwnd, data, is_down)
                time.sleep(0.005)
            time.sleep(0.05)
        self._stop_macro()

    def save_config(self):
        cfg = {
            "target_title": self.target_title,
            "loop_count": self.loop_count,
            "actions": [
                {"type": t, "data": d, "is_down": b, "delay": de}
                for (t, d, b, de) in self.recorded_actions
            ]
        }
        with open("macro_config.json", "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        self.status_message.emit("💾 配置已保存")
        logui.info("配置已保存到 macro_config.json")

    def load_config(self):
        try:
            with open("macro_config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self.target_title = cfg.get("target_title", "异环")
            self.loop_count = cfg.get("loop_count", 99)
            actions_list = cfg.get("actions", [])
            self.recorded_actions = [
                (a["type"], a["data"], a["is_down"], a["delay"])
                for a in actions_list
            ]
            self.status_message.emit("📂 配置已加载")
            logui.info(f"加载了 {len(self.recorded_actions)} 条动作")
            return True, self.target_title, self.loop_count, self.recorded_actions
        except Exception as e:
            logui.error(f"加载配置失败: {e}")
            self.status_message.emit(f"❌ 加载失败: {e}")
            return False, None, None, None

    def register_hotkeys(self):
        try:
            keyboard.add_hotkey('alt+y', self.toggle_record)
            keyboard.add_hotkey('alt+t', self.toggle_macro)
            logui.info("热键已注册: Alt+Y 录制/停止, Alt+T 回放/停止")
        except Exception as e:
            logui.error(f"注册热键失败: {e}")

    def unregister_hotkeys(self):
        try:
            keyboard.remove_hotkey('alt+y')
        except:
            pass
        try:
            keyboard.remove_hotkey('alt+t')
        except:
            pass

    def cleanup(self):
        self._stop_macro()
        self._stop_recording()
        self.unregister_hotkeys()

def key_name_to_vk(name, scan_code):
    special = {
        'enter': win32con.VK_RETURN, 'space': win32con.VK_SPACE,
        'backspace': win32con.VK_BACK, 'tab': win32con.VK_TAB,
        'escape': win32con.VK_ESCAPE, 'shift': win32con.VK_SHIFT,
        'ctrl': win32con.VK_CONTROL, 'alt': win32con.VK_MENU,
        'up': win32con.VK_UP, 'down': win32con.VK_DOWN,
        'left': win32con.VK_LEFT, 'right': win32con.VK_RIGHT,
        'caps lock': win32con.VK_CAPITAL,
        'page up': win32con.VK_PRIOR, 'page down': win32con.VK_NEXT,
        'end': win32con.VK_END, 'home': win32con.VK_HOME,
        'insert': win32con.VK_INSERT, 'delete': win32con.VK_DELETE,
        'f1': win32con.VK_F1, 'f2': win32con.VK_F2, 'f3': win32con.VK_F3,
        'f4': win32con.VK_F4, 'f5': win32con.VK_F5, 'f6': win32con.VK_F6,
        'f7': win32con.VK_F7, 'f8': win32con.VK_F8, 'f9': win32con.VK_F9,
        'f10': win32con.VK_F10, 'f11': win32con.VK_F11, 'f12': win32con.VK_F12,
    }
    if name in special:
        return special[name]
    try:
        return win32api.MapVirtualKey(scan_code, 1) or ord(name.upper())
    except:
        if len(name) == 1:
            return ord(name.upper())
    return None

def normalize_mouse_button(button):
    if button == 'left':
        return 'left'
    if button == 'right':
        return 'right'
    if button in ('middle', 'mouse_middle'):
        return 'middle'
    return None