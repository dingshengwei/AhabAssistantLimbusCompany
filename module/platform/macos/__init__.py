"""macOS 后端：窗口（Quartz/AX）、截图（ScreenCaptureKit）、输入（CGEvent）、通知。

上游业务代码通过 ``module.platform.win32_compat`` 的替身间接调用这里的功能。

注意：本包 ``__init__`` 刻意不做 eager import —— 兼容层安装过程中会导入
``bootstrap``，此时 win32 替身尚未全部就绪，提前导入 ``input`` 会触发循环导入。
请直接 ``from module.platform.macos import window`` 这样按子模块导入。
"""

__all__ = ["capture", "display", "input", "notify", "window", "bootstrap"]
