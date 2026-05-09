import win32gui
import win32con
import time
import win32api

WM_ACTIVATE = 0x0006
WA_ACTIVE = 1

def fake_activate_window(hwnd):
    try:
        win32gui.SendMessage(hwnd, WM_ACTIVATE, WA_ACTIVE, 0)
    except Exception as e:
        print(e)

def bring_window_to_top(hwnd):
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
    except:
        pass

def simulate_key_down(handle, vk_code):
    try:
        win32gui.PostMessage(handle, win32con.WM_KEYDOWN, vk_code, 0)
    except Exception as e:
        print(e)

def simulate_key_up(handle, vk_code):
    try:
        win32gui.PostMessage(handle, win32con.WM_KEYUP, vk_code, 0)
    except Exception as e:
        print(e)

def send_key_down(handle, vk_code):
    simulate_key_down(handle, vk_code)

def send_key_up(handle, vk_code):
    simulate_key_up(handle, vk_code)

def client_to_screen(hwnd, x, y):
    pt = win32gui.ClientToScreen(hwnd, (x, y))
    return pt[0], pt[1]

def simulate_mouse_click_relative(hwnd, x, y, duration=0.05):
    fake_activate_window(hwnd)
    bring_window_to_top(hwnd)
    time.sleep(0.03)
    screen_x, screen_y = client_to_screen(hwnd, x, y)
    win32api.SetCursorPos((screen_x, screen_y))
    time.sleep(0.02)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(duration)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

def simulate_mouse_down_relative(hwnd, x, y):
    fake_activate_window(hwnd)
    bring_window_to_top(hwnd)
    screen_x, screen_y = client_to_screen(hwnd, x, y)
    win32api.SetCursorPos((screen_x, screen_y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)

def simulate_mouse_up_relative(hwnd, x, y):
    fake_activate_window(hwnd)
    bring_window_to_top(hwnd)
    screen_x, screen_y = client_to_screen(hwnd, x, y)
    win32api.SetCursorPos((screen_x, screen_y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)

# if __name__ == "__main__":
#     print("NET_click 模块已加载 - 前台点击，无随机偏差")