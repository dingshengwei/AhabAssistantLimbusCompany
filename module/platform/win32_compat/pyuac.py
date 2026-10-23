"""``pyuac`` 替身：macOS 没有 UAC，默认已具备当前用户权限。"""

from __future__ import annotations

import logging

_log = logging.getLogger("AALC.win32compat.pyuac")

IS_WINDOWS = False


def isUserAdmin() -> bool:
    return True


def isUserAdminOrPowerUser() -> bool:
    return True


def runAsAdmin(*args, **kwargs) -> None:
    _log.debug("macOS 无需提权，忽略 runAsAdmin")


def isUserAdminProcess(*args, **kwargs) -> bool:
    return True
