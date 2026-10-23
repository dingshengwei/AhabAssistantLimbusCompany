"""平台适配层。

AALC 上游是纯 Windows 项目，直接依赖 win32gui / win32ui / winreg / pyuac 等
Windows 专有模块。为了在不改动大量业务代码的前提下移植到 macOS，这里提供：

* ``module.platform.macos``：真正的 macOS 后端（Quartz/AX/ScreenCaptureKit）。
* ``module.platform.win32_compat``：在 macOS 上以同名模块的形式注入
  ``win32gui`` / ``win32con`` / ``win32api`` / ``win32ui`` / ``win32process`` /
  ``winreg`` / ``pywintypes`` / ``pyuac`` 等替身，把 Win32 语义翻译到 macOS。

这样业务代码里的 ``import win32gui`` 保持原样，上游合并冲突最小。
仅当 ``sys.platform == "darwin"`` 时才会安装替身，Windows 行为完全不变。
"""

import sys

IS_WINDOWS = sys.platform == "win32"
IS_MACOS = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

#: 当前平台是否走 Win32 兼容层
USES_WIN32_COMPAT = IS_MACOS

__all__ = ["IS_WINDOWS", "IS_MACOS", "IS_LINUX", "USES_WIN32_COMPAT"]
