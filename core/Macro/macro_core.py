# core/Macro/macro_core.py
import threading
import time
import json
import sys
import os
import win32gui
import win32con
import win32api
from PyQt5.QtCore import QObject, pyqtSignal, Qt

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
from UI import logui
from Module.Hwnd.game_hwnd import get_game_hwnd   # 使用全局锁定的句柄

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

    def __init__(self, loop_count=99):
        super().__init__()
        self.recording = False
        self.macro_running = False
        self.target_hwnd = None
        self.recorded_actions = []
        self.last_record_time = None
        self.loop_count = loop_count

    def get_current_hwnd(self):
        """从全局锁定模块实时获取句柄"""
        return get_game_hwnd()

    def start_recording(self):
        """开始录制（不再检查窗口，录制时实时获取句柄）"""
        if self.macro_running:
            self.stop_macro()
        self.recorded_actions.clear()
        self.recording = True
        self.recording_state_changed.emit(True)
        self.status_message.emit("录制中... (Alt+Y 停止)")
        logui.info("开始录制宏")
        self.last_record_time = time.time()

    def stop_recording(self):
        self.recording = False
        self.recording_state_changed.emit(False)
        self.status_message.emit("录制已停止")
        logui.info("停止录制")

    def toggle_record(self):
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()

    def toggle_macro(self):
        if not self.macro_running:
            self.start_macro()
        else:
            self.stop_macro()

    def start_macro(self):
        hwnd = self.get_current_hwnd()
        if not hwnd or not win32gui.IsWindow(hwnd):
            self.status_message.emit("❌ 未锁定目标窗口，请先在窗口检测中锁定")
            return
        self.target_hwnd = hwnd
        if self.recording:
            self.stop_recording()
        if not self.recorded_actions:
            self.status_message.emit("❌ 无录制动作")
            return
        self.macro_running = True
        self.running_state_changed.emit(True)
        self.status_message.emit("▶ 宏运行中... (Alt+T 停止)")
        logui.info("开始回放宏")
        threading.Thread(target=self._run_macro_loop, daemon=True).start()

    def stop_macro(self):
        self.macro_running = False
        self.running_state_changed.emit(False)
        self.status_message.emit("⏹ 宏已停止")
        logui.info("停止回放")

    def _run_macro_loop(self):
        for _ in range(self.loop_count):
            if not self.macro_running:
                break
            # 每次循环前更新句柄（可在窗口检测中更换锁定窗口）
            hwnd = self.get_current_hwnd()
            if not hwnd or not win32gui.IsWindow(hwnd):
                self.status_message.emit("❌ 目标窗口丢失，停止回放")
                self.stop_macro()
                return
            self.target_hwnd = hwnd
            for action in self.recorded_actions:
                if not self.macro_running:
                    break
                act_type, data, is_down, delay = action
                if delay > 0.001:
                    time.sleep(delay)
                if not self.macro_running:
                    break
                fake_activate(hwnd)
                if act_type == 'key':
                    send_keyboard_message(hwnd, data, is_down)
                elif act_type == 'mouse':
                    send_mouse_message(hwnd, data, is_down)
                time.sleep(0.005)
            time.sleep(0.05)
        self.stop_macro()

    def save_config(self):
        cfg = {
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
            self.loop_count = cfg.get("loop_count", 99)
            actions_list = cfg.get("actions", [])
            self.recorded_actions = [
                (a["type"], a["data"], a["is_down"], a["delay"])
                for a in actions_list
            ]
            self.status_message.emit("📂 配置已加载")
            logui.info(f"加载了 {len(self.recorded_actions)} 条动作")
            return True, self.loop_count, self.recorded_actions
        except Exception as e:
            logui.error(f"加载配置失败: {e}")
            self.status_message.emit(f"❌ 加载失败: {e}")
            return False, None, None

    def cleanup(self):
        self.stop_macro()
        self.stop_recording()