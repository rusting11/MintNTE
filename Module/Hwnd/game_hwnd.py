# Module/Hwnd/game_hwnd.py
import win32gui
import win32con
import threading
import time
import logging

logger = logging.getLogger("GameHwnd")

_locked_hwnd = None
_monitor_thread = None
_stop_monitor = threading.Event()

def set_locked_hwnd(hwnd):
    """设置锁定的窗口句柄，并启动防最小化守护线程"""
    global _locked_hwnd, _monitor_thread, _stop_monitor
    _locked_hwnd = hwnd
    # 停止之前的监控线程
    if _monitor_thread and _monitor_thread.is_alive():
        _stop_monitor.set()
        _monitor_thread.join(timeout=1)
    # 启动新监控
    _stop_monitor.clear()
    _monitor_thread = threading.Thread(target=_monitor_window, daemon=True)
    _monitor_thread.start()
    logger.info(f"已绑定并启动防最小化监控: 句柄 {hwnd}")

def clear_locked_hwnd():
    """清除锁定的窗口句柄，并停止监控线程"""
    global _locked_hwnd, _monitor_thread, _stop_monitor
    _locked_hwnd = None
    _stop_monitor.set()
    if _monitor_thread and _monitor_thread.is_alive():
        _monitor_thread.join(timeout=1)
    _monitor_thread = None
    logger.info("已解除窗口锁定，停止防最小化监控")

def _monitor_window():
    global _locked_hwnd
    while not _stop_monitor.is_set():
        hwnd = _locked_hwnd
        if hwnd and win32gui.IsWindow(hwnd):
            if win32gui.IsIconic(hwnd):
                logger.warning(f"检测到窗口 {hwnd} 被最小化，强制恢复")
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                # 注释掉 SetForegroundWindow，避免后台崩溃
                # try:
                #     win32gui.SetForegroundWindow(hwnd)
                # except Exception as e:
                #     logger.debug(f"无法将窗口设为前台: {e}")
        else:
            logger.info("窗口已失效，停止防最小化监控")
            break
        time.sleep(0.2)   # 调整检查间隔为 0.2 秒（之前是 0.001 秒耗 CPU）

def get_game_hwnd():
    """
    获取游戏窗口句柄。仅在已锁定时返回有效句柄，否则返回 None。
    取消基于标题的模糊搜索，防止误抓 QQ、网页等窗口。
    """
    global _locked_hwnd
    if _locked_hwnd and win32gui.IsWindow(_locked_hwnd):
        return _locked_hwnd
    # 不执行任何标题搜索，强制要求先锁定窗口
    return None