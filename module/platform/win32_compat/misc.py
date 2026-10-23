"""``win32ui`` / ``win32process`` / ``win32crypt`` 替身。"""

from __future__ import annotations

import logging

_log = logging.getLogger("AALC.win32compat.misc")


# ---------------------------------------------------------------- win32process
def GetWindowThreadProcessId(hwnd):
    from module.platform.macos import window as mac_window

    return (0, mac_window.pid_of(hwnd))


def GetCurrentProcessId() -> int:
    import os

    return os.getpid()


def TerminateProcess(handle, exit_code) -> bool:
    return True


def OpenProcess(*args, **kwargs):
    return None


# ---------------------------------------------------------------- win32crypt
def CryptProtectData(data, description=None, entropy=None, reserved=None, prompt=None, flags=0) -> bytes:
    """macOS 上没有 DPAPI：退化为 base64（仅用于本地配置里的弱敏感字段）。"""
    import base64

    return base64.b64encode(bytes(data))


def CryptUnprotectData(data, entropy=None, reserved=None, prompt=None, flags=0):
    import base64

    return (None, base64.b64decode(bytes(data)))


# ---------------------------------------------------------------- win32ui
class _NotAvailable:
    def __init__(self, name: str):
        self._name = name

    def __call__(self, *args, **kwargs):
        raise NotImplementedError(
            f"macOS 使用了 module.platform.macos.capture，不应调用 win32ui.{self._name}"
        )


CreateDCFromHandle = _NotAvailable("CreateDCFromHandle")
CreateBitmapFromHandle = _NotAvailable("CreateBitmapFromHandle")
CreateBitmap = _NotAvailable("CreateBitmap")
CreateWindowDC = _NotAvailable("CreateWindowDC")
