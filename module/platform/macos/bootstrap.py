"""macOS 兼容层安装入口。

在 ``main.py`` 的最前面调用 :func:`install`，之后所有 ``import win32gui`` 之类的
语句都会拿到 ``module.platform.win32_compat`` 里的替身。
"""

from __future__ import annotations

import ctypes

from module.logger import log
from module.platform import IS_MACOS


class _NoopFunction:
    """任何调用都返回 0 的桩函数（用于 ctypes.windll.*）。"""

    def __call__(self, *args, **kwargs):
        return 0

    def __getattr__(self, name):
        return 0


class _NoopDLL:
    def __getattr__(self, name):
        return _NoopFunction()


class _FakeWindll:
    """替代 ``ctypes.windll``，避免 ``from ctypes import windll`` 直接 ImportError。"""

    def __getattr__(self, name):
        return _NoopDLL()


_installed = False


def install(verbose: bool = True) -> bool:
    """安装 Windows 兼容层（仅 macOS 生效，可重复调用）。"""
    global _installed
    if not IS_MACOS:
        return False
    if _installed:
        return True

    if not hasattr(ctypes, "windll"):
        ctypes.windll = _FakeWindll()  # type: ignore[attr-defined]
    # 有些模块（如 HDR 检测）在 import 期就使用 Win32 专属的 ctypes 名字
    # 第三方库常用 ctypes.WinDLL 判断“是否 Windows”，故只补 WINFUNCTYPE，
    # 不能提供 WinDLL，否则会被误判为 Windows 平台。
    if not hasattr(ctypes, "WINFUNCTYPE"):
        ctypes.WINFUNCTYPE = ctypes.CFUNCTYPE  # type: ignore[attr-defined]
    if not hasattr(ctypes, "WinError"):

        def _win_error(code=None, descr=None):
            return OSError(code or 0, descr or "Windows API 在 macOS 上不可用")

        ctypes.WinError = _win_error  # type: ignore[attr-defined]
    if not hasattr(ctypes, "HRESULT"):
        ctypes.HRESULT = ctypes.c_long  # type: ignore[attr-defined]

    from module.platform.win32_compat import install as install_compat

    installed = install_compat()

    # adb 供模拟器模式使用；找不到时只记日志，不影响原生窗口模式
    try:
        from . import adb as mac_adb

        mac_adb.ensure_adb_on_path()
    except Exception as exc:  # pragma: no cover
        log.debug(f"adb 初始化失败: {exc}")

    _installed = True
    if verbose and installed:
        log.debug(f"macOS Win32 兼容层已安装: {', '.join(installed)}")
    return True


def ensure_permissions() -> dict:
    """检查屏幕录制 / 辅助功能权限，返回状态字典。"""
    from module.platform.macos import capture, window

    return {
        "screen_recording": capture.screen_permission_ok(),
        "accessibility": window.accessibility_trusted(),
    }


def detect_game_runtimes() -> dict:
    """检测本机可能的游戏运行方式，用于启动时给出提示。"""
    import glob
    import os

    def _find(*patterns):
        found = []
        for pattern in patterns:
            found.extend(glob.glob(os.path.expanduser(pattern)))
        return found

    return {
        "mumu_pro": _find("/Applications/MuMu*.app", "~/Applications/MuMu*.app"),
        "playcover": _find("/Applications/PlayCover.app", "~/Applications/PlayCover.app"),
    }


def log_runtime_hints() -> None:
    runtimes = detect_game_runtimes()
    if runtimes["mumu_pro"]:
        log.info("检测到 MuMu 模拟器 Pro：可在设置中选择「使用模拟器 → 其他」，地址 127.0.0.1，端口 16384")
    if runtimes["playcover"]:
        log.info("检测到 PlayCover：可直接使用原生窗口模式（实验性，需要屏幕录制 + 辅助功能权限）")
    if not runtimes["mumu_pro"] and not runtimes["playcover"]:
        log.info("未检测到 MuMu Pro / PlayCover，请安装后把游戏窗口跑起来再启动任务")


def log_adb_hints() -> None:
    """模拟器模式依赖 adb，给出可执行的修复建议。"""
    try:
        from module.config import cfg

        from . import adb as mac_adb
    except Exception:
        return
    if not cfg.get_value("simulator", False):
        return
    status = mac_adb.status()
    if status["adb"] is None:
        log.warning("模拟器模式需要 adb，但当前未找到：请运行 ./scripts/setup_adb_macos.sh（下载官方 platform-tools）")
        return
    if status["devices"]:
        log.info(f"adb 已就绪: {status['version']}，设备: {', '.join(status['devices'])}")
        return
    log.warning(
        "adb 已找到但还没有连接设备。免费模拟器可用 BlueStacks Air / Android Studio AVD，"
        "开启 ADB 后运行 adb connect 127.0.0.1:5555（MuMu Pro 为 16384）"
    )


def log_permission_hints() -> None:
    log_runtime_hints()
    log_adb_hints()
    status = ensure_permissions()
    if not status["screen_recording"]:
        log.warning(
            "未获得「屏幕录制」权限，AALC 无法截取游戏画面。"
            "请到 系统设置 > 隐私与安全性 > 屏幕录制 中勾选运行 AALC 的终端/应用。"
        )
    if not status["accessibility"]:
        log.warning(
            "未获得「辅助功能」权限，AALC 的点击/按键可能无效。"
            "请到 系统设置 > 隐私与安全性 > 辅助功能 中勾选运行 AALC 的终端/应用。"
        )


def apply_macos_defaults() -> None:
    """macOS 上强制使用前台输入、关闭 Win32 专有的窗口设置功能。"""
    try:
        from module.config import cfg
    except Exception as exc:  # pragma: no cover
        log.debug(f"跳过 macOS 配置默认值: {exc}")
        return

    try:
        if cfg.get_value("background_click", True):
            cfg.set_value("background_click", False)
        if cfg.get_value("win_input_type", "background") == "background":
            cfg.set_value("win_input_type", "foreground")
        if cfg.get_value("use_post_message", False):
            cfg.set_value("use_post_message", False)
        if cfg.get_value("set_windows", True):
            log.info("macOS 上默认关闭「自动设置窗口大小/位置」，如需固定画面可在设置中手动开启")
            cfg.set_value("set_windows", False)
    except Exception as exc:
        log.debug(f"应用 macOS 配置默认值失败: {exc}")


def patch_qt_macos() -> None:
    """修正第三方 Qt 组件在 macOS 上的兼容问题（需在 QApplication 创建后调用）。"""
    _patch_qframelesswindow()


def _patch_qframelesswindow() -> None:
    """qframelesswindow 在 macOS 上对没有标准按钮的窗口会抛 AttributeError，
    这里包一层保护，避免 paintEvent 反复刷异常。"""
    try:
        from qframelesswindow.mac import MacFramelessWindowBase
    except Exception as exc:  # pragma: no cover
        log.debug(f"跳过 qframelesswindow 补丁: {exc}")
        return

    if getattr(MacFramelessWindowBase, "_aalc_patched", False):
        return

    original = MacFramelessWindowBase.setSystemTitleBarButtonVisible

    def safe_set_visible(self, is_visible):
        try:
            original(self, is_visible)
        except Exception:
            # 没有原生标题栏按钮（QDialog / 非原生窗口）时只记录状态
            try:
                self._isSystemButtonVisible = is_visible
            except Exception:
                pass

    safe_set_visible._aalc_patched = True  # type: ignore[attr-defined]
    MacFramelessWindowBase.setSystemTitleBarButtonVisible = safe_set_visible
    MacFramelessWindowBase._aalc_patched = True  # type: ignore[attr-defined]
    log.debug("已应用 qframelesswindow macOS 兼容补丁")
