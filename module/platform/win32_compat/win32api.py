"""``win32api`` 替身。"""

from __future__ import annotations

import logging

import pyautogui

from module.platform.macos import display as mac_display
from module.platform.macos import window as mac_window

from . import win32con, win32gui

_log = logging.getLogger("AALC.win32compat.api")


def MAKELONG(a: int, b: int) -> int:
    return (int(a) & 0xFFFF) | ((int(b) & 0xFFFF) << 16)


def LOWORD(value: int) -> int:
    return int(value) & 0xFFFF


def HIWORD(value: int) -> int:
    return (int(value) >> 16) & 0xFFFF


def GetCursorPos() -> tuple[int, int]:
    x, y = pyautogui.position()
    scale = mac_display.scale_at_point(x, y) or 1.0
    return int(x * scale), int(y * scale)


def SetCursorPos(x: int, y: int) -> bool:
    scale = mac_display.scale_at_point(x, y) or 1.0
    pyautogui.moveTo(x / scale, y / scale)
    return True


def PostMessage(hwnd, msg, wparam=0, lparam=0):
    return win32gui.PostMessage(hwnd, msg, wparam, lparam)


def SendMessage(hwnd, msg, wparam=0, lparam=0):
    return win32gui.SendMessage(hwnd, msg, wparam, lparam)


def MonitorFromWindow(hwnd, flags=win32con.MONITOR_DEFAULTTONEAREST):
    return hwnd


def MonitorFromPoint(point, flags=win32con.MONITOR_DEFAULTTONEAREST):
    return 0


def GetMonitorInfo(hmonitor) -> dict:
    if hmonitor:
        return mac_window.monitor_info(hmonitor)
    return mac_display.monitor_info(None)


def MapVirtualKey(vk: int, map_type: int = 0) -> int:
    """macOS 不需要扫描码，返回 0 让上游构造的 lParam 保持合法。"""
    return 0


def GetAsyncKeyState(vk: int) -> int:
    return 0


def mouse_event(dw_flags, dx, dy, dw_data=0, dw_extra=0) -> None:
    scale = mac_display.scale_at_point(dx, dy) or 1.0
    pyautogui.moveTo(dx / scale, dy / scale)


def keybd_event(b_vk, b_scan, dw_flags, dw_extra=0) -> None:
    _log.debug("keybd_event 未实现: vk=%s", b_vk)


def SetProcessDPIAware() -> None:
    """macOS 由系统统一管理 Retina 缩放，无需处理。"""


def GetSystemMetrics(index: int) -> int:
    screens = mac_display.screens()
    if not screens:
        return 0
    left, top, right, bottom = screens[0]["frame"]
    scale = screens[0]["scale"]
    if index == 0:  # SM_CXSCREEN
        return int((right - left) * scale)
    if index == 1:  # SM_CYSCREEN
        return int((bottom - top) * scale)
    return 0


def GetLastError() -> int:
    return 0


def sleep(ms: int) -> None:
    import time

    time.sleep(ms / 1000)
