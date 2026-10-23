"""macOS 输入后端。

上游 ``Input`` 基于 pyautogui（在其内部就是 Quartz CGEvent），因此前台点击/拖拽/
滚轮可以直接复用，只需要修正两处平台差异：

1. 坐标：上游用“窗口像素坐标”，macOS 的 CGEvent 用“屏幕点坐标”，需要除以
   backing scale 并加上窗口原点。
2. 文本输入：pyautogui 无法输入中文，改用剪贴板 + Cmd+V。

需要“辅助功能(Accessibility)”权限，否则 CGEvent 会被系统静默丢弃。
"""

from __future__ import annotations

import time

import pyautogui

from module.automation.input_handlers import AbstractInput
from module.automation.input_handlers.input import Input
from module.logger import log
from utils.singletonmeta import SingletonMeta

from . import window


class MacInput(Input, metaclass=SingletonMeta):
    """前台输入（PlayCover 原生窗口 / 任意 macOS 窗口）。"""

    def _scale(self) -> float:
        from module.game_and_screen import screen

        hwnd = screen.handle.hwnd
        return window.scale_of(hwnd) if hwnd else 1.0

    def pos_offset(self, *args) -> tuple[float, float]:
        """把“窗口内像素坐标”转换成“屏幕点坐标”。"""
        if len(args) == 2:
            x, y = args
        elif len(args) == 1 and isinstance(args[0], tuple):
            x, y = args[0]
        else:
            raise ValueError("pos_offset 接受两个整数参数或一个包含两个整数的元组")

        from module.game_and_screen import screen

        rect = screen.handle.rect(True)
        scale = window.scale_of(screen.handle.hwnd) or 1.0
        return (rect[0] + x) / scale, (rect[1] + y) / scale

    def get_mouse_position(self) -> tuple[int, int]:
        """返回窗口像素坐标系下的鼠标位置（与上游语义一致）。"""
        try:
            point_x, point_y = pyautogui.position()
        except Exception:
            return (0, 0)
        scale = self._scale() or 1.0
        return int(point_x * scale), int(point_y * scale)

    def mouse_move(self, coordinate=(1, 1)) -> None:
        pyautogui.moveTo(*self.pos_offset(coordinate))
        self.wait_pause()

    def mouse_to_blank(self, coordinate=(1, 1), move_back=False) -> None:
        if move_back:
            current = self.get_mouse_position()
        log.debug("鼠标移动到空白，避免遮挡", stacklevel=2)
        pyautogui.moveTo(*self.pos_offset(coordinate))
        if move_back and current:
            self.mouse_move(current)
        self.wait_pause()

    def mouse_scroll(self, direction: int = -3) -> bool:
        if direction <= 0:
            log.debug("鼠标滚动滚轮，远离界面", stacklevel=2)
        else:
            log.debug("鼠标滚动滚轮，拉近界面", stacklevel=2)
        # macOS 的滚轮方向与 Windows 相反，这里取反以保持“正值=拉近”的语义
        pyautogui.scroll(-direction)
        return True

    def key_press(self, key: str) -> None:
        mapping = {
            "esc": "esc",
            "enter": "enter",
            "space": "space",
            "up": "up",
            "down": "down",
            "left": "left",
            "right": "right",
            "tab": "tab",
            "shift": "shift",
            "ctrl": "ctrl",
            "alt": "alt",
            "home": "home",
            "end": "end",
            "pageup": "pageup",
            "pagedown": "pagedown",
            "insert": "insert",
            "delete": "delete",
            "win": "command",
        }
        target = mapping.get((key or "").lower(), key)
        try:
            pyautogui.press(target)
        except Exception as exc:
            log.error(f"按键 {key} 失败: {exc}")

    def input_text(self, text: str) -> None:
        """剪贴板 + Cmd+V，兼容中文。"""
        if not text:
            log.warning("未提供要粘贴的文本")
            return
        try:
            import pyperclip

            pyperclip.copy(text)
            time.sleep(0.05)
            pyautogui.hotkey("command", "v")
        except Exception as exc:
            log.debug(f"剪贴板输入失败，尝试直接键入: {exc}")
            try:
                pyautogui.typewrite(text)
            except Exception:
                log.error("pyautogui 直接输入失败")


class MacAdbInput(AbstractInput):
    """占位：模拟器模式使用上游的 MuMu / PyMiniTouch 实现，无需 macOS 后端。"""

    def __init__(self) -> None:  # pragma: no cover
        super().__init__()
        raise RuntimeError("模拟器模式应使用上游的 MumuControl / SimulatorControl")
