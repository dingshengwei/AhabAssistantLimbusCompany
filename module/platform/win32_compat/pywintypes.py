"""``pywintypes`` 替身。"""

from __future__ import annotations


class error(Exception):
    """对应 pywin32 的 ``pywintypes.error``。"""

    def __init__(self, *args):
        super().__init__(*args)
        self.winerror = args[0] if args else 0
        self.funcname = args[1] if len(args) > 1 else ""
        self.strerror = args[2] if len(args) > 2 else ""


class com_error(Exception):
    """对应 pywin32 的 ``pywintypes.com_error``。"""


class HANDLE(int):
    pass
