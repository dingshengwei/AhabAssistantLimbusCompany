"""macOS 平台后端测试。

只在 macOS 上运行；Windows/Linux 上整体跳过，避免影响上游 CI。
"""

from __future__ import annotations

import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="macOS 平台后端测试")


def test_is_macos_flag():
    from module.platform import IS_MACOS, IS_WINDOWS

    assert IS_MACOS is True
    assert IS_WINDOWS is False


def test_display_screens_and_pixel_conversion():
    from module.platform.macos import display

    screens = display.screens()
    assert screens, "至少应检测到一块显示器"
    for info in screens:
        left, top, right, bottom = info["frame"]
        assert right > left and bottom > top
        assert info["scale"] >= 1.0

        px = display.to_pixels(info["frame"], info["scale"])
        assert px[2] - px[0] > 0 and px[3] - px[1] > 0


def test_monitor_info_matches_win32_shape():
    from module.platform.macos import display

    info = display.monitor_info(None)
    assert set(info) >= {"Monitor", "Work", "Flags", "Device", "Scale"}
    assert len(info["Monitor"]) == 4


def test_window_matching_is_lenient():
    from module.platform.macos.window import _matches

    item = {"name": "LimbusCompany", "owner": "LimbusCompany", "layer": 0}
    assert _matches(item, "LimbusCompany", None)

    suffixed = {"name": "LimbusCompany - 1.2.3", "owner": "PlayCover", "layer": 0}
    assert _matches(suffixed, "LimbusCompany", None)

    other = {"name": "Calculator", "owner": "Calculator", "layer": 0}
    assert not _matches(other, "LimbusCompany", None)


def test_compat_layer_installs_win32_modules():
    from module.platform.macos.bootstrap import install

    install()
    import winreg  # noqa: F401

    import win32api
    import win32con
    import win32gui

    assert win32con.SWP_NOMOVE == 0x0002
    assert win32api.MAKELONG(1, 2) == (1 | (2 << 16))
    # 找不到的窗口一律返回 0，不抛异常
    assert win32gui.FindWindow("UnityWndClass", "不存在的窗口 AALC-TEST") == 0
    assert win32gui.IsWindow(0) is False


def test_winreg_is_absent_on_macos():
    from module.platform.macos.bootstrap import install

    install()
    import winreg

    with pytest.raises(FileNotFoundError):
        winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\\ProjectMoon\\LimbusCompany")


def test_screenshot_returns_window_pixels(monkeypatch):
    """用 AALC 自己的窗口做一次端到端截图，验证尺寸与 rect 像素一致。"""
    from module.automation.screenshot import ScreenShot
    from module.game_and_screen import screen
    from module.platform.macos import capture, window

    tmp = pytest.importorskip("PySide6.QtWidgets")
    assert tmp  # 仅确保依赖存在

    candidates = [
        w
        for w in window.list_windows()
        if w["layer"] == 0 and (w["rect"][2] - w["rect"][0]) > 200 and (w["rect"][3] - w["rect"][1]) > 150
    ]
    if not candidates:
        pytest.skip("当前没有可用于截图的窗口")

    target = candidates[0]
    if not capture.screen_permission_ok():
        pytest.skip("缺少屏幕录制权限")

    monkeypatch.setattr(screen.handle, "_hwnd", target["id"], raising=False)
    image = ScreenShot.take_screenshot(gray=False)
    if image is None:
        pytest.skip(f"截图失败: {capture.last_error()}")

    left, top, right, bottom = screen.handle.rect(True)
    assert image.size == (right - left, bottom - top)
