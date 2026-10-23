"""窗口枚举 / 几何 / 激活（macOS，Quartz + Accessibility）。

窗口句柄直接使用 ``CGWindowID``（整数），因此可以塞进上游的 ``hwnd`` 变量。
所有对外返回的矩形都在“像素”空间（= 点 * backingScale），与 Win32 DPI 感知进程保持一致。
"""

from __future__ import annotations

import time

from Quartz import (
    CGWindowListCopyWindowInfo,
    CGWindowListCreateDescriptionFromArray,
    kCGNullWindowID,
    kCGWindowBounds,
    kCGWindowIsOnscreen,
    kCGWindowLayer,
    kCGWindowListExcludeDesktopElements,
    kCGWindowListOptionIncludingWindow,
    kCGWindowListOptionOnScreenOnly,
    kCGWindowName,
    kCGWindowNumber,
    kCGWindowOwnerName,
    kCGWindowOwnerPID,
)

from module.logger import log

from . import display

try:  # Accessibility 权限不足时这些调用会直接报错，统一在函数内兜底
    from ApplicationServices import (
        AXIsProcessTrusted,
        AXUIElementCopyAttributeValue,
        AXUIElementCreateApplication,
        AXUIElementPerformAction,
        AXUIElementSetAttributeValue,
        AXValueCreate,
        kAXPositionAttribute,
        kAXRaiseAction,
        kAXSizeAttribute,
        kAXValueCGPointType,
        kAXValueCGSizeType,
        kAXWindowsAttribute,
    )

    _HAS_AX = True
except Exception:  # pragma: no cover - 仅在缺少 pyobjc 时
    _HAS_AX = False


def _bounds_of(info: dict) -> tuple[float, float, float, float]:
    rect = info.get(kCGWindowBounds) or {}
    x = float(rect.get("X", 0.0))
    y = float(rect.get("Y", 0.0))
    w = float(rect.get("Width", 0.0))
    h = float(rect.get("Height", 0.0))
    return (x, y, x + w, y + h)


def _parse_window(info) -> dict:
    return {
        "id": int(info.get(kCGWindowNumber, 0)),
        "pid": int(info.get(kCGWindowOwnerPID, 0)),
        "owner": str(info.get(kCGWindowOwnerName) or ""),
        "name": str(info.get(kCGWindowName) or ""),
        "layer": int(info.get(kCGWindowLayer, 0) or 0),
        "onscreen": bool(info.get(kCGWindowIsOnscreen, False)),
        "rect": _bounds_of(info),
    }


def list_windows(onscreen_only: bool = True) -> list[dict]:
    """列出窗口，返回含 id / owner / name / rect（点） / layer / pid 的字典列表。"""
    options = kCGWindowListExcludeDesktopElements
    if onscreen_only:
        options |= kCGWindowListOptionOnScreenOnly
    raw = CGWindowListCopyWindowInfo(options, kCGNullWindowID) or []
    out = []
    for info in raw:
        try:
            out.append(_parse_window(info))
        except Exception as exc:  # pragma: no cover - 防御性
            log.debug(f"解析窗口信息失败: {exc}")
    return out


def window_info(win_id: int) -> dict | None:
    """只查询单个窗口（比枚举全部窗口快一个数量级，截图/点击每帧都会调用）。"""
    if not win_id:
        return None
    try:
        raw = CGWindowListCopyWindowInfo(kCGWindowListOptionIncludingWindow, win_id) or []
    except Exception:
        raw = []
    for info in raw:
        try:
            item = _parse_window(info)
        except Exception:
            continue
        if item["id"] == win_id:
            return item
    # 窗口可能被隐藏/最小化，退化为全量枚举
    for item in list_windows(onscreen_only=False):
        if item["id"] == win_id:
            return item
    return None


def _matches(item: dict, title: str, class_name: str | None) -> bool:
    """宽松匹配：macOS 没有 Win32 的窗口类名，改用 owner/name 对比。"""
    name = (item.get("name") or "").strip()
    owner = (item.get("owner") or "").strip()
    wanted = (title or "").strip()
    if not wanted:
        return item["layer"] == 0
    if name.lower() == wanted.lower() or owner.lower() == wanted.lower():
        return True
    # PlayCover 下窗口标题可能带后缀，或标题为空只剩 owner
    if wanted.lower() in name.lower() or wanted.lower() in owner.lower():
        return True
    return False


def find_window(title: str, class_name: str | None = None) -> int:
    """按标题/应用名查找窗口，返回 CGWindowID，找不到返回 0。"""
    candidates = [w for w in list_windows(onscreen_only=True) if w["layer"] == 0]
    for item in candidates:
        if _matches(item, title, class_name):
            return item["id"]
    # 退化：窗口可能被其它窗口完全覆盖，仍允许在全部窗口里找
    for item in list_windows(onscreen_only=False):
        if item["layer"] == 0 and _matches(item, title, class_name):
            return item["id"]
    return 0


def enum_windows() -> list[dict]:
    return [w for w in list_windows(onscreen_only=False) if w["layer"] == 0]


def is_window(win_id: int) -> bool:
    return window_info(win_id) is not None


def is_minimized(win_id: int) -> bool:
    """macOS 没有等价的“最小化”标志；窗口不在屏上即视为不可见。"""
    info = window_info(win_id)
    if info is None:
        return True
    return not info.get("onscreen", False)


def is_foreground(win_id: int) -> bool:
    """通过 Accessibility 读取当前焦点窗口并与目标比对。"""
    if not _HAS_AX or not win_id:
        return False
    try:
        from AppKit import NSWorkspace

        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if app is None:
            return False
        info = window_info(win_id)
        if info is None:
            return False
        if int(app.processIdentifier()) != info["pid"]:
            return False
        focused = _focus_window_id(info["pid"])
        return focused in (None, win_id)
    except Exception:
        return False


def _ax_windows(pid: int):
    if not _HAS_AX:
        return []
    app_ref = AXUIElementCreateApplication(pid)
    err, windows = AXUIElementCopyAttributeValue(app_ref, kAXWindowsAttribute, None)
    if err != 0 or windows is None:
        return []
    return list(windows)


def _ax_attr(element, attribute: str):
    err, value = AXUIElementCopyAttributeValue(element, attribute, None)
    if err != 0:
        return None
    return value


def _focus_window_id(pid: int) -> int | None:
    """返回该进程焦点窗口的 CGWindowID（借助 AXTitle 无法拿到 id，故用位置匹配）。"""
    for element in _ax_windows(pid):
        attr = _ax_attr(element, "AXFocused") or _ax_attr(element, "AXMain")
        if attr:
            position = _ax_attr(element, kAXPositionAttribute)
            size = _ax_attr(element, kAXSizeAttribute)
            if position is not None and size is not None:
                try:
                    from ApplicationServices import AXValueGetValue

                    point = AXValueGetValue(position, kAXValueCGPointType, None)
                    extent = AXValueGetValue(size, kAXValueCGSizeType, None)
                    rect = (point[0], point[1], point[0] + extent[0], point[1] + extent[1])
                    return _id_by_rect(rect)
                except Exception:
                    return None
    return None


def _id_by_rect(rect, tolerance: float = 4.0) -> int | None:
    for item in list_windows(onscreen_only=False):
        left, top, right, bottom = item["rect"]
        if (
            abs(left - rect[0]) <= tolerance
            and abs(top - rect[1]) <= tolerance
            and abs(right - rect[2]) <= tolerance
            and abs(bottom - rect[3]) <= tolerance
        ):
            return item["id"]
    return None


def activate(win_id: int) -> bool:
    """把窗口所在应用带到前台，并尝试 raise 对应 AX 窗口。"""
    info = window_info(win_id)
    if info is None:
        return False
    pid = info["pid"]
    ok = False
    try:
        from AppKit import NSApplicationActivateIgnoringOtherApps, NSRunningApplication

        running = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
        if running is not None:
            ok = bool(running.activateWithOptions_(NSApplicationActivateIgnoringOtherApps))
            time.sleep(0.05)
    except Exception as exc:
        log.debug(f"激活应用失败: {exc}")

    if _HAS_AX:
        try:
            target = _ax_window_by_rect(info["rect"], pid)
            if target is not None:
                AXUIElementPerformAction(target, kAXRaiseAction)
                ok = True
        except Exception:
            pass
    return ok


def _ax_window_by_rect(rect, pid: int):
    if not _HAS_AX:
        return None
    for element in _ax_windows(pid):
        position = _ax_attr(element, kAXPositionAttribute)
        size = _ax_attr(element, kAXSizeAttribute)
        if position is None or size is None:
            continue
        try:
            from ApplicationServices import AXValueGetValue

            point = AXValueGetValue(position, kAXValueCGPointType, None)
            extent = AXValueGetValue(size, kAXValueCGSizeType, None)
        except Exception:
            continue
        if (
            abs(point[0] - rect[0]) <= 4
            and abs(point[1] - rect[1]) <= 4
            and abs(extent[0] - (rect[2] - rect[0])) <= 4
            and abs(extent[1] - (rect[3] - rect[1])) <= 4
        ):
            return element
    return None


def _set_ax_frame(win_id: int, x: float, y: float, width: float, height: float, move: bool, resize: bool) -> bool:
    if not _HAS_AX:
        return False
    info = window_info(win_id)
    if info is None:
        return False
    element = _ax_window_by_rect(info["rect"], info["pid"])
    if element is None:
        return False
    try:
        if move:
            value = AXValueCreate(kAXValueCGPointType, (x, y))
            if AXUIElementSetAttributeValue(element, kAXPositionAttribute, value) != 0:
                return False
        if resize:
            value = AXValueCreate(kAXValueCGSizeType, (width, height))
            if AXUIElementSetAttributeValue(element, kAXSizeAttribute, value) != 0:
                return False
        return True
    except Exception as exc:
        log.debug(f"设置窗口位置/大小失败: {exc}")
        return False


def set_position(win_id: int, x: float, y: float) -> bool:
    return _set_ax_frame(win_id, x, y, 0, 0, move=True, resize=False)


def set_size(win_id: int, width: float, height: float) -> bool:
    return _set_ax_frame(win_id, 0, 0, width, height, move=False, resize=True)


def rect_pixels(win_id: int, client: bool = False) -> tuple[int, int, int, int]:
    """窗口矩形。

    macOS 统一使用“逻辑点”（logical points）作为坐标系，也就是 Retina 下的 1x 尺寸：
    截图、模板匹配、点击坐标全部在同一空间，避免 2x 屏上出现 2 倍错位。
    macOS 不做客户区/外框区分，client 参数仅为兼容上游接口。
    """
    info = window_info(win_id)
    if info is None:
        return (0, 0, 0, 0)
    left, top, right, bottom = info["rect"]
    return (
        int(round(left)),
        int(round(top)),
        int(round(right)),
        int(round(bottom)),
    )


def scale_of(win_id: int) -> float:
    """兼容上游“像素坐标 -> 屏幕坐标”的换算；macOS 全程逻辑点，故恒为 1.0。"""
    return 1.0


def monitor_info(win_id: int) -> dict:
    info = window_info(win_id)
    if info is None:
        return display.monitor_info(None, scale=1.0)
    return display.monitor_info(info["rect"], scale=1.0)


def pid_of(win_id: int) -> int:
    info = window_info(win_id)
    return int(info["pid"]) if info else 0


def accessibility_trusted() -> bool:
    if not _HAS_AX:
        return False
    try:
        return bool(AXIsProcessTrusted())
    except Exception:
        return False


__all__ = [
    "list_windows",
    "find_window",
    "enum_windows",
    "is_window",
    "is_minimized",
    "is_foreground",
    "activate",
    "set_position",
    "set_size",
    "rect_pixels",
    "scale_of",
    "monitor_info",
    "pid_of",
    "accessibility_trusted",
    "CGWindowListCreateDescriptionFromArray",
]
