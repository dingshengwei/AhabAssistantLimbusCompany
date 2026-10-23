"""``win32com.client`` 替身：定时任务等 COM 功能在 macOS 上不可用，统一返回空壳对象。"""

from __future__ import annotations

import logging

_log = logging.getLogger("AALC.win32compat.com")


class _Dummy:
    """任意属性访问都返回自身的空壳，调用返回 None。"""

    def __getattr__(self, name):
        return _Dummy()

    def __call__(self, *args, **kwargs):
        return None

    def __bool__(self):
        return False

    def __iter__(self):
        return iter(())


def Dispatch(*args, **kwargs) -> _Dummy:
    _log.debug("macOS 忽略 COM 调用: %s", args)
    return _Dummy()


def DispatchEx(*args, **kwargs) -> _Dummy:
    return Dispatch(*args, **kwargs)


def GetObject(*args, **kwargs) -> _Dummy:
    return Dispatch(*args, **kwargs)


gencache = _Dummy()
constants = _Dummy()
