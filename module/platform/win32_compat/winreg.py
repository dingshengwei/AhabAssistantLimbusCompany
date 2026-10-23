"""``winreg`` 替身：macOS 没有注册表，读取路径统一视为“键不存在”。

上游用注册表读取 MuMu 安装路径、游戏渲染设置、启动项等，这些在 macOS 上都走
“未找到”分支（会退化为默认值或提示用户手动设置），不会崩溃。
"""

from __future__ import annotations

import logging

_log = logging.getLogger("AALC.win32compat.winreg")

HKEY_CLASSES_ROOT = 0x80000000
HKEY_CURRENT_USER = 0x80000001
HKEY_LOCAL_MACHINE = 0x80000002
HKEY_USERS = 0x80000003
HKEY_CURRENT_CONFIG = 0x80000005

KEY_READ = 0x20019
KEY_WRITE = 0x20006
KEY_ALL_ACCESS = 0xF003F
KEY_SET_VALUE = 0x0002
KEY_WOW64_64KEY = 0x0100
KEY_WOW64_32KEY = 0x0200

REG_SZ = 1
REG_EXPAND_SZ = 2
REG_BINARY = 3
REG_DWORD = 4
REG_QWORD = 11
REG_MULTI_SZ = 7


class OpenKeyError(FileNotFoundError):
    pass


class _Key:
    def __init__(self, path: str = "", root=None):
        self.path = path
        self.root = root

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def Close(self):
        return None


def _fake_path(path) -> str:
    return str(path) if path is not None else ""


def OpenKey(key, sub_key, reserved=0, access=KEY_READ):
    raise FileNotFoundError(f"macOS 不支持注册表: {_fake_path(sub_key)}")


def CreateKey(key, sub_key):
    return _Key(_fake_path(sub_key), key)


def CreateKeyEx(key, sub_key, reserved=0, access=KEY_WRITE):
    return _Key(_fake_path(sub_key), key), 0


def ConnectRegistry(machine, key):
    return key


def QueryValueEx(key, value_name):
    raise FileNotFoundError(f"macOS 不支持注册表: {_fake_path(value_name)}")


def SetValueEx(key, value_name, reserved, type_, value) -> None:
    _log.debug("忽略注册表写入: %s", value_name)


def DeleteValue(key, value_name) -> None:
    raise FileNotFoundError(_fake_path(value_name))


def DeleteKey(key, sub_key) -> None:
    raise FileNotFoundError(_fake_path(sub_key))


def CloseKey(key) -> None:
    return None


def EnumKey(key, index):
    raise OSError(259, "没有更多数据")


def EnumValue(key, index):
    raise OSError(259, "没有更多数据")


def QueryInfoKey(key):
    return (0, 0, 0)
