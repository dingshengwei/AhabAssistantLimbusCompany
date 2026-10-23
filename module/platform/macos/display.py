"""屏幕与显示器信息（macOS）。

坐标约定：统一转换为“屏幕左上角为原点、y 轴向下”的坐标系（与 Win32 屏幕坐标一致），
这样才能让上游基于 Win32 的窗口/截图/点击代码保持不变。

NSScreen 的 frame 使用 Cocoa 坐标（主屏左下角为原点、y 轴向上），这里按主屏高度翻转。
"""

from __future__ import annotations

from AppKit import NSScreen

#: 系统级“点 -> 像素”的换算回调，由 window/capture 模块按需覆盖
_CACHED_SCREENS: list[dict] | None = None


def _flip(rect, main_height: float) -> tuple[float, float, float, float]:
    x, y, w, h = rect.origin.x, rect.origin.y, rect.size.width, rect.size.height
    top = main_height - (y + h)
    return (x, top, x + w, top + h)


def screens(refresh: bool = False) -> list[dict]:
    """返回所有显示器的信息，坐标系为左上原点、y 向下。

    每项包含 name / frame / work / scale：
    * ``frame``：整块屏幕 ``(left, top, right, bottom)``（点）
    * ``work``：去掉菜单栏与 Dock 的可用区域（点）
    * ``scale``：backing scale factor（Retina 通常为 2.0）
    """
    global _CACHED_SCREENS
    if _CACHED_SCREENS is not None and not refresh:
        return _CACHED_SCREENS

    ns_screens = NSScreen.screens()
    if not ns_screens:
        _CACHED_SCREENS = []
        return _CACHED_SCREENS

    main_height = float(ns_screens[0].frame().size.height)
    result = []
    for screen in ns_screens:
        try:
            name = str(screen.localizedName())
        except Exception:
            name = "Display"
        result.append(
            {
                "name": name,
                "frame": _flip(screen.frame(), main_height),
                "work": _flip(screen.visibleFrame(), main_height),
                "scale": float(screen.backingScaleFactor()),
            }
        )
    _CACHED_SCREENS = result
    return result


def invalidate() -> None:
    """显示器布局变化后清空缓存。"""
    global _CACHED_SCREENS
    _CACHED_SCREENS = None


def scale_at_point(x: float, y: float) -> float:
    """返回屏幕坐标所在显示器的 backing scale factor。"""
    for info in screens():
        left, top, right, bottom = info["frame"]
        if left <= x < right and top <= y < bottom:
            return info["scale"]
    return screens()[0]["scale"] if screens() else 1.0


def screen_for_rect(rect: tuple[float, float, float, float]) -> dict:
    """返回与给定矩形（点，左上原点）重叠面积最大的显示器。"""
    all_screens = screens()
    if not all_screens:
        return {"name": "Unknown", "frame": (0, 0, 0, 0), "work": (0, 0, 0, 0), "scale": 1.0}

    left, top, right, bottom = rect
    best = all_screens[0]
    best_area = -1.0
    for info in all_screens:
        s_left, s_top, s_right, s_bottom = info["frame"]
        w = max(0.0, min(right, s_right) - max(left, s_left))
        h = max(0.0, min(bottom, s_bottom) - max(top, s_top))
        area = w * h
        if area > best_area:
            best_area = area
            best = info
    return best


def monitor_info(rect: tuple[float, float, float, float] | None = None, scale: float | None = None) -> dict:
    """生成与 ``win32api.GetMonitorInfo`` 兼容的字典。

    注意：返回的矩形会按 backing scale 放大到“像素”，以匹配 Win32 DPI 感知进程
    下窗口矩形即物理像素的语义。
    """
    info = screen_for_rect(rect) if rect else (screens()[0] if screens() else None)
    if info is None:
        info = {"name": "Unknown", "frame": (0, 0, 0, 0), "work": (0, 0, 0, 0), "scale": 1.0}
    factor = scale if scale is not None else info["scale"]

    def _to_px(r):
        return tuple(int(round(v * factor)) for v in r)

    return {
        "Monitor": _to_px(info["frame"]),
        "Work": _to_px(info["work"]),
        "Flags": 0,
        "Device": info["name"],
        "Scale": factor,
    }


def to_pixels(rect: tuple[float, float, float, float], scale: float) -> tuple[int, int, int, int]:
    left, top, right, bottom = rect
    return (
        int(round(left * scale)),
        int(round(top * scale)),
        int(round(right * scale)),
        int(round(bottom * scale)),
    )
