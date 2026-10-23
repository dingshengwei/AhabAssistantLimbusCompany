"""用 ``adb shell input`` 实现的触摸后端。

为什么要它：minitouch 需要读取 ``/dev/input/event*``，而 Android 11+ 的
Google Play 镜像里 shell 用户已经没有这个权限（实测报
``open: Permission denied`` → 拿不到 banner）。此时 AALC 的拖拽/滑动会直接失败，
只剩点击能用。

这个后端用 ``input motionevent`` / ``input swipe`` 兜底：
* 不需要 root、不需要 /dev/input 权限，AVD、USB 真机、任何模拟器都能用；
* 每条命令约 30~80 ms，比 minitouch 慢，但足够跑日常与镜牢；
* 接口对齐 :class:`pyminitouch.actions.MNTDevice` 中被 SimulatorControl 使用的那部分。

坐标：``input`` 使用当前显示方向下的真实像素坐标，与 minitouch 归一化坐标不同，
因此这里不做任何缩放/旋转，直接使用调用方传入的坐标（SimulatorControl 已经换算好）。
"""

from __future__ import annotations

from time import sleep
from types import SimpleNamespace

from module.logger import log

#: 单条 adb 命令的估算耗时，用于控制插值步数
_COMMAND_LATENCY = 0.035


class AdbShellInput:
    """minitouch 的替代实现（仅覆盖 SimulatorControl 用到的接口）。"""

    def __init__(self, device) -> None:
        self.device = device
        self.real_width = 0
        self.real_height = 0
        self._last = (1, 1)
        # 上游用 connection.max_x 区分“蓝叠像素坐标系”；这里给 0，走竖屏旋转换算那条路径
        self.connection = SimpleNamespace(max_x=0, max_y=0)
        log.info("已启用 adb shell input 触摸后端（minitouch 不可用时的兜底）")

    # ---------------------------------------------------------------- 基础事件
    def _send(self, action: str, x, y) -> None:
        x, y = int(x), int(y)
        self.device.shell(["input", "motionevent", action, str(x), str(y)])
        if action != "UP":
            self._last = (x, y)

    def down(self, point) -> None:
        self._send("DOWN", *point)

    def move_to(self, point, wait: float = 0.0) -> None:
        if wait > 0:
            sleep(wait)
        self._send("MOVE", *point)

    def up(self, point=None) -> None:
        self._send("UP", *(point or self._last))

    def stop(self) -> None:
        """保持接口一致；没有后台进程需要回收。"""

    def reset(self) -> None:
        self.stop()

    # ---------------------------------------------------------------- 组合手势
    def tap(self, points, pressure: int = 100, duration=None, no_up=None) -> None:
        point = points[0] if points else self._last
        self.down(point)
        sleep(0.05)
        if not no_up:
            self.up(point)

    def swipe(self, points, pressure: int = 100, duration=None, no_down=None, no_up=None) -> None:
        """沿折线滑动；每段用一条 ``input swipe``（比 motionevent 快很多）。"""
        pts = [(int(x), int(y)) for x, y in points]
        if not pts:
            return
        if len(pts) == 1:
            self.tap(pts)
            return
        total_ms = int(duration or 200)
        segment_ms = max(20, total_ms // max(1, len(pts) - 1))
        for index in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[index], pts[index + 1]
            self.device.shell(
                ["input", "swipe", str(x0), str(y0), str(x1), str(y1), str(segment_ms)]
            )
        self._last = pts[-1]

    def ext_smooth_swipe(
        self,
        points,
        pressure: int = 100,
        duration=None,
        part=None,
        no_down=None,
        no_up=None,
    ) -> None:
        """平滑滑动：按 ``part`` 步插值发送 MOVE。

        ``duration`` 是“每段”的毫秒数（与 minitouch 语义一致），这里按步数均摊。
        """
        pts = [(int(x), int(y)) for x, y in points]
        if not pts:
            return
        steps = max(2, min(int(part or 10), 8))  # 每条命令 ~35ms，步数不宜过多
        segment_seconds = (duration or 100) / 1000.0

        if not no_down:
            self.down(pts[0])
        for index in range(len(pts) - 1):
            (x0, y0), (x1, y1) = pts[index], pts[index + 1]
            for step in range(1, steps + 1):
                ratio = step / steps
                self.move_to(
                    (x0 + (x1 - x0) * ratio, y0 + (y1 - y0) * ratio),
                    wait=max(0.0, segment_seconds / steps - _COMMAND_LATENCY),
                )
        if not no_up:
            self.up()

    def _send_swipe_plan_in_one_batch(self, plan, pressure: int = 100) -> None:
        """按 (坐标, 到达前等待秒数) 计划连续滑动，结束时抬起（对应快速滚动手势）。"""
        if not plan:
            return
        (start_x, start_y), _ = plan[0]
        self.down((start_x, start_y))
        for (x, y), wait_seconds in plan[1:]:
            if wait_seconds:
                sleep(float(wait_seconds))
            self._send("MOVE", x, y)
        self.up()
