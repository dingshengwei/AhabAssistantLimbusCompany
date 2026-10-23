"""窗口截图（macOS）。

优先使用 ScreenCaptureKit（macOS 14+ 的 ``SCScreenshotManager``），失败时退回
``screencapture -l<window id>`` 命令行。两者都需要“屏幕录制”权限。

返回的图片是窗口的**像素**尺寸（Retina 下为点数的 2 倍），与上游把截图坐标
直接当做点击坐标使用的假设一致（见 display.to_pixels）。
"""

from __future__ import annotations

import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np
from PIL import Image
from Quartz import (
    CGBitmapContextCreate,
    CGBitmapContextGetData,
    CGColorSpaceCreateDeviceRGB,
    CGContextDrawImage,
    CGImageGetHeight,
    CGImageGetWidth,
    CGRectMake,
    kCGBitmapByteOrder32Little,
    kCGImageAlphaPremultipliedFirst,
)

from module.logger import log

from . import window

try:
    from CoreFoundation import CFRunLoopRunInMode, kCFRunLoopDefaultMode
    from ScreenCaptureKit import (
        SCContentFilter,
        SCScreenshotManager,
        SCShareableContent,
        SCStreamConfiguration,
    )

    _HAS_SCK = True
except Exception:  # pragma: no cover - 老系统或缺 pyobjc
    _HAS_SCK = False

_last_error = ""


def _run_loop(timeout: float) -> bool:
    """驱动 runloop 直到回调把 done 置位或超时。"""
    deadline = time.monotonic() + timeout
    while not done_flag["done"] and time.monotonic() < deadline:
        CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.01, True)
    return done_flag["done"]


done_flag = {"done": False}


def _cgimage_to_pil(cg_image) -> Image.Image:
    width = int(CGImageGetWidth(cg_image))
    height = int(CGImageGetHeight(cg_image))
    color_space = CGColorSpaceCreateDeviceRGB()
    ctx = CGBitmapContextCreate(
        None,
        width,
        height,
        8,
        width * 4,
        color_space,
        kCGImageAlphaPremultipliedFirst | kCGBitmapByteOrder32Little,
    )
    CGContextDrawImage(ctx, CGRectMake(0, 0, width, height), cg_image)
    data = CGBitmapContextGetData(ctx)
    if data is None:
        raise RuntimeError("创建位图上下文失败")
    buffer = data.as_buffer(width * height * 4)
    arr = np.frombuffer(buffer, dtype=np.uint8).reshape((height, width, 4))
    rgb = arr[:, :, 2::-1]
    return Image.fromarray(np.ascontiguousarray(rgb))


def _sck_content(timeout: float = 3.0):
    result = {"content": None, "error": None}
    done_flag["done"] = False

    def handler(content, error):
        result["content"] = content
        result["error"] = error
        done_flag["done"] = True

    SCShareableContent.getShareableContentWithCompletionHandler_(handler)
    _run_loop(timeout)
    if result["error"] is not None:
        raise RuntimeError(f"获取共享内容失败: {result['error']}")
    if result["content"] is None:
        raise RuntimeError("获取共享内容超时")
    return result["content"]


def _sck_window_by_id(content, win_id: int):
    for sc_window in content.windows():
        try:
            if int(sc_window.windowID()) == win_id:
                return sc_window
        except Exception:
            continue
    return None


#: 复用 SCContentFilter / SCStreamConfiguration —— 重新枚举 SCShareableContent
#: 是主要开销（约 150 ms），窗口不变时不应重复做。
_filter_cache: dict[int, tuple[object, object, int, int]] = {}


def _build_filter(win_id: int):
    rect = window.window_info(win_id)["rect"]
    # 按逻辑点截图（Retina 下由 ScreenCaptureKit 下采样到 1x），
    # 保证截图尺寸 == 窗口 rect，从而与模板/点击坐标一致。
    width = max(1, int(round(rect[2] - rect[0])))
    height = max(1, int(round(rect[3] - rect[1])))

    cached = _filter_cache.get(win_id)
    if cached is not None:
        content_filter, config, cached_w, cached_h = cached
        if (cached_w, cached_h) == (width, height):
            return content_filter, config

    content = _sck_content()
    sc_window = _sck_window_by_id(content, win_id)
    if sc_window is None:
        raise RuntimeError(f"ScreenCaptureKit 中未找到窗口 {win_id}")

    content_filter = SCContentFilter.alloc().initWithDesktopIndependentWindow_(sc_window)
    config = SCStreamConfiguration.alloc().init()
    config.setWidth_(width)
    config.setHeight_(height)
    config.setShowsCursor_(False)
    config.setScalesToFit_(True)
    try:
        config.setIgnoreShadowsSingleWindow_(True)
    except Exception:
        pass
    _filter_cache[win_id] = (content_filter, config, width, height)
    return content_filter, config


def _capture_sck(win_id: int) -> Image.Image:
    content_filter, config = _build_filter(win_id)

    result = {"image": None, "error": None}
    done_flag["done"] = False

    def handler(image, error):
        result["image"] = image
        result["error"] = error
        done_flag["done"] = True

    SCScreenshotManager.captureImageWithFilter_configuration_completionHandler_(
        content_filter, config, handler
    )
    _run_loop(5.0)
    if result["error"] is not None:
        raise RuntimeError(f"截图失败: {result['error']}")
    if result["image"] is None:
        raise RuntimeError("截图超时")
    return _cgimage_to_pil(result["image"])


def _capture_cli(win_id: int) -> Image.Image:
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        path = Path(tmp.name)
    try:
        proc = subprocess.run(
            ["screencapture", "-x", "-o", "-l", str(win_id), str(path)],
            capture_output=True,
            timeout=15,
        )
        if proc.returncode != 0 or not path.exists() or path.stat().st_size == 0:
            raise RuntimeError(f"screencapture 失败: {proc.stderr.decode(errors='ignore').strip()}")
        return Image.open(path).convert("RGB").copy()
    finally:
        path.unlink(missing_ok=True)


def _normalize_size(image: Image.Image, rect) -> Image.Image:
    """把截图缩放到窗口的逻辑尺寸，保证“截图像素 == 窗口 rect”这一不变量。

    ScreenCaptureKit 失败退到 ``screencapture -l`` 时，返回的是窗口原生分辨率
    （Retina/模拟器会是 2x 甚至更高），不归一化会让模板匹配与点击坐标错位。
    """
    expected = (max(1, int(round(rect[2] - rect[0]))), max(1, int(round(rect[3] - rect[1]))))
    if image.size == expected:
        return image
    log.debug(f"截图尺寸 {image.size} 与窗口尺寸 {expected} 不一致，归一化后返回")
    return image.resize(expected, Image.LANCZOS)


def capture_window(win_id: int, prefer_sck: bool = True) -> Image.Image | None:
    """截取指定窗口，返回 RGB 图像；失败返回 None。"""
    global _last_error
    if not win_id:
        _last_error = "无效的窗口句柄"
        return None
    rect = None
    info = window.window_info(win_id)
    if info is not None:
        rect = info["rect"]
    if _HAS_SCK and prefer_sck:
        try:
            image = _capture_sck(win_id)
            return _normalize_size(image, rect) if rect else image
        except Exception as exc:
            _last_error = str(exc)
            _filter_cache.pop(win_id, None)
            log.debug(f"ScreenCaptureKit 截图失败，改用 screencapture: {exc}")
    try:
        image = _capture_cli(win_id)
        return _normalize_size(image, rect) if rect else image
    except Exception as exc:
        _last_error = str(exc)
        log.debug(f"screencapture 截图失败: {exc}")
        return None


def last_error() -> str:
    return _last_error


def capture_full_screen(scale: float | None = None) -> Image.Image | None:
    """整屏截图（含其它窗口），作为窗口截图的兜底方案。"""
    global _last_error
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        path = Path(tmp.name)
    try:
        proc = subprocess.run(["screencapture", "-x", str(path)], capture_output=True, timeout=15)
        if proc.returncode != 0 or not path.exists():
            _last_error = proc.stderr.decode(errors="ignore").strip()
            return None
        return Image.open(path).convert("RGB").copy()
    finally:
        path.unlink(missing_ok=True)


def screen_permission_ok() -> bool:
    try:
        from Quartz import CGPreflightScreenCaptureAccess

        return bool(CGPreflightScreenCaptureAccess())
    except Exception:
        return False
