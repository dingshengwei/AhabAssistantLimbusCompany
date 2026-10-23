"""Win32 兼容层：在 macOS 上以同名模块注入 win32* 替身。

安装入口见 :func:`module.platform.macos.bootstrap.install`。
每个子模块都尽量保持与 pywin32 相同的调用签名，业务代码无需改动。
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType

MODULE_MAP = {
    "win32con": "win32con",
    "pywintypes": "pywintypes",
    "win32gui": "win32gui",
    "win32api": "win32api",
    "winreg": "winreg",
    "pyuac": "pyuac",
    "win32process": "misc",
    "win32crypt": "misc",
    "win32ui": "misc",
}

#: win32com 是包，单独处理
COM_MODULES = ("win32com", "win32com.client")


def _load(name: str) -> ModuleType:
    return importlib.import_module(f"{__name__}.{name}")


def install() -> list[str]:
    """把替身模块写进 ``sys.modules``，返回实际安装的模块名列表。"""
    installed: list[str] = []
    for public_name, local_name in MODULE_MAP.items():
        if public_name in sys.modules:
            continue
        sys.modules[public_name] = _load(local_name)
        installed.append(public_name)

    if "win32com" not in sys.modules:
        package = ModuleType("win32com")
        package.__path__ = []  # type: ignore[attr-defined]
        client = _load("win32com_client")
        package.client = client  # type: ignore[attr-defined]
        sys.modules["win32com"] = package
        sys.modules["win32com.client"] = client
        installed.extend(COM_MODULES)

    return installed
