"""``win32gui`` 替身：把窗口相关 API 翻译到 macOS 的 Quartz / Accessibility。"""

from __future__ import annotations

import logging
import time

from module.platform.macos import window as mac_window

from . import win32con

_log = logging.getLogger("AALC.win32compat.gui")


class error(Exception):
    """对应 pywin32 的 ``win32gui.error``。"""


# 上游会读取/回写窗口样式（GWL_STYLE / GWL_EXSTYLE），这里用字典模拟
_style_cache: dict[tuple[int, int], int] = {}
_transparent: dict[int, bool] = {}


def _require(win_id: int):
    if not win_id:
        raise error("无效的窗口句柄")


def FindWindow(class_name, title) -> int:
    """macOS 没有 Win32 窗口类名，class_name 仅作参考。"""
    return mac_window.find_window(title or "", class_name)


def EnumWindows(callback, extra=None):
    for item in mac_window.enum_windows():
        try:
            keep_going = callback(item["id"], extra)
        except error:
            raise
        if keep_going is False:
            return


def GetClassName(win_id: int) -> str:
    info = mac_window.window_info(win_id)
    if info is None:
        raise error("窗口不存在")
    return "UnityWndClass" if "limbus" in (info["owner"] + info["name"]).lower() else "MacWindow"


def GetWindowText(win_id: int) -> str:
    info = mac_window.window_info(win_id)
    if info is None:
        return ""
    return info["name"] or info["owner"]


def SetWindowText(win_id: int, text: str) -> None:
    _log.debug("macOS 不支持修改窗口标题: %s", text)


def IsWindow(win_id: int) -> bool:
    return mac_window.is_window(win_id)


def IsIconic(win_id: int) -> bool:
    return mac_window.is_minimized(win_id)


def IsZoomed(win_id: int) -> bool:
    return False


def GetForegroundWindow() -> int:
    from AppKit import NSWorkspace

    try:
        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        pid = int(app.processIdentifier())
    except Exception:
        return 0
    for item in mac_window.list_windows(onscreen_only=False):
        if item["pid"] == pid and item["layer"] == 0:
            return item["id"]
    return 0


def GetWindowRect(win_id: int):
    return mac_window.rect_pixels(win_id, client=False)


def GetClientRect(win_id: int):
    rect = mac_window.rect_pixels(win_id, client=True)
    return (0, 0, rect[2] - rect[0], rect[3] - rect[1])


def ClientToScreen(win_id: int, point):
    rect = mac_window.rect_pixels(win_id, client=True)
    return (rect[0] + point[0], rect[1] + point[1])


def ScreenToClient(win_id: int, point):
    rect = mac_window.rect_pixels(win_id, client=True)
    return (point[0] - rect[0], point[1] - rect[1])


def SetForegroundWindow(win_id: int) -> bool:
    return mac_window.activate(win_id)


def BringWindowToTop(win_id: int) -> bool:
    return mac_window.activate(win_id)


def ShowWindow(win_id: int, cmd: int) -> bool:
    if cmd in (win32con.SW_RESTORE, win32con.SW_SHOW, win32con.SW_SHOWNORMAL, win32con.SW_SHOWMAXIMIZED):
        return mac_window.activate(win_id)
    return True


def SetWindowPos(win_id, insert_after, x, y, cx, cy, flags) -> bool:
    """像素坐标 -> 屏幕点后，通过 Accessibility 调整窗口。"""
    if not win_id:
        return False
    scale = mac_window.scale_of(win_id) or 1.0
    move = not (flags & win32con.SWP_NOMOVE)
    resize = not (flags & win32con.SWP_NOSIZE)
    if move and resize and cx > 0 and cy > 0:
        ok_move = mac_window.set_position(win_id, x / scale, y / scale)
        ok_size = mac_window.set_size(win_id, cx / scale, cy / scale)
        return bool(ok_move or ok_size)
    if move:
        return mac_window.set_position(win_id, x / scale, y / scale)
    if resize and cx > 0 and cy > 0:
        return mac_window.set_size(win_id, cx / scale, cy / scale)
    return True


def GetWindowLong(win_id: int, index: int) -> int:
    return _style_cache.get((win_id, index), 0)


def SetWindowLong(win_id: int, index: int, value: int) -> int:
    previous = _style_cache.get((win_id, index), 0)
    _style_cache[(win_id, index)] = int(value)
    return previous


def SetLayeredWindowAttributes(win_id: int, color_key, alpha: int, flags: int) -> bool:
    _transparent[win_id] = alpha == 0
    return True


def GetWindowDC(win_id: int):
    raise error("macOS 请使用 module.platform.macos.capture 截图")


def ReleaseDC(win_id: int, hdc) -> int:
    return 1


def DeleteObject(obj) -> bool:
    return True


def SendMessage(win_id: int, msg: int, wparam: int = 0, lparam: int = 0):
    return _dispatch_message(win_id, msg, wparam, lparam)


def PostMessage(win_id: int, msg: int, wparam: int = 0, lparam: int = 0):
    return _dispatch_message(win_id, msg, wparam, lparam)


def _split_lparam(lparam: int) -> tuple[int, int]:
    x = lparam & 0xFFFF
    y = (lparam >> 16) & 0xFFFF
    if x >= 0x8000:
        x -= 0x10000
    if y >= 0x8000:
        y -= 0x10000
    return x, y


def _dispatch_message(win_id: int, msg: int, wparam: int, lparam: int):
    """把少数鼠标/键盘消息翻译成真实的 macOS 事件。

    后台输入（不抢焦点）在 macOS 上无法对任意窗口实现，这里退化为“在前台位置
    模拟点击”，效果等同前台模式。
    """
    import pyautogui

    scale = mac_window.scale_of(win_id) or 1.0
    rect = mac_window.rect_pixels(win_id, client=True)

    if msg == win32con.WM_LBUTTONDOWN:
        x, y = _split_lparam(lparam)
        pyautogui.mouseDown((rect[0] + x) / scale, (rect[1] + y) / scale)
        return 0
    if msg == win32con.WM_LBUTTONUP:
        x, y = _split_lparam(lparam)
        pyautogui.mouseUp((rect[0] + x) / scale, (rect[1] + y) / scale)
        return 0
    if msg == win32con.WM_MOUSEMOVE:
        x, y = _split_lparam(lparam)
        pyautogui.moveTo((rect[0] + x) / scale, (rect[1] + y) / scale)
        return 0
    if msg == win32con.WM_MOUSEWHEEL:
        delta = (wparam >> 16) & 0xFFFF
        if delta >= 0x8000:
            delta -= 0x10000
        pyautogui.scroll(-delta // 120)
        return 0
    if msg in (win32con.WM_KEYDOWN, win32con.WM_SYSKEYDOWN):
        _press_vk(int(wparam), down=True)
        return 0
    if msg in (win32con.WM_KEYUP, win32con.WM_SYSKEYUP):
        _press_vk(int(wparam), down=False)
        return 0
    if msg == win32con.WM_CHAR:
        try:
            pyautogui.typewrite(chr(int(wparam)))
        except Exception:
            pass
        return 0
    if msg == win32con.WM_CLOSE:
        _log.debug("macOS 上忽略 WM_CLOSE")
        return 0
    if msg == win32con.WM_ACTIVATE:
        mac_window.activate(win_id)
        return 0
    _log.debug("未翻译的窗口消息: 0x%04X", msg)
    return 0


_VK_TO_PYAUTOGUI = {
    win32con.VK_RETURN: "enter",
    win32con.VK_ESCAPE: "esc",
    win32con.VK_SPACE: "space",
    win32con.VK_TAB: "tab",
    win32con.VK_UP: "up",
    win32con.VK_DOWN: "down",
    win32con.VK_LEFT: "left",
    win32con.VK_RIGHT: "right",
    win32con.VK_SHIFT: "shift",
    win32con.VK_CONTROL: "ctrl",
    win32con.VK_MENU: "alt",
}


def _press_vk(vk: int, down: bool) -> None:
    import pyautogui

    key = _VK_TO_PYAUTOGUI.get(vk)
    if key is None:
        if 0x30 <= vk <= 0x5A:
            key = chr(vk).lower()
        else:
            return
    try:
        if down:
            pyautogui.keyDown(key)
        else:
            pyautogui.keyUp(key)
    except Exception:
        pass


def set_window_transparent_state(win_id: int, transparent: bool) -> None:
    _transparent[win_id] = transparent


def monitor_info_for(win_id: int) -> dict:
    return mac_window.monitor_info(win_id)


def sleep_short(seconds: float = 0.05) -> None:
    time.sleep(seconds)
