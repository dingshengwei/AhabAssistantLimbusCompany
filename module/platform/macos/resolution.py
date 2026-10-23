"""分辨率对齐（macOS）。

AALC 的所有模板与坐标都以 ``cfg.set_win_size``（= 截图高度）为基准换算，
上游在 Windows 上通过“把窗口改成 1920x1080”来保证一致。macOS 上（尤其 PlayCover）
窗口尺寸由用户/应用决定，因此这里改为反方向适配：

1. 截图与坐标统一使用逻辑点（1x）；
2. 找到游戏窗口后，把本次会话的 ``cfg.set_win_size`` 对齐到窗口高度；
3. 比例不是 16:9 时给出明确告警——模板是按 16:9 制作的，4:3 会错位。

注意：只改当前进程内的 ``cfg.config``，不会写回 config.yaml，避免影响模拟器模式。
"""

from __future__ import annotations

from module.config import cfg
from module.logger import log

#: 允许的宽高比误差（16:9 = 1.777...）
ASPECT_TOLERANCE = 0.03
TARGET_ASPECT = 16 / 9


def plan_window_metrics(width: int, height: int) -> dict:
    """根据窗口尺寸给出会话分辨率方案（纯函数，便于测试）。"""
    width = int(width)
    height = int(height)
    if height <= 0 or width <= 0:
        return {"valid": False, "height": 0, "aspect": 0.0, "aspect_ok": False}
    aspect = width / height
    return {
        "valid": True,
        "height": height,
        "aspect": aspect,
        "aspect_ok": abs(aspect - TARGET_ASPECT) <= ASPECT_TOLERANCE,
    }


def sync_window_metrics(hwnd: int) -> dict | None:
    """把当前会话的 set_win_size 对齐到窗口高度，返回方案字典。"""
    from . import window

    rect = window.rect_pixels(hwnd)
    plan = plan_window_metrics(rect[2] - rect[0], rect[3] - rect[1])
    if not plan["valid"]:
        return None

    if not plan["aspect_ok"]:
        log.warning(
            f"游戏窗口比例 {plan['aspect']:.2f}:1 不是 16:9（{rect[2] - rect[0]}x{rect[3] - rect[1]}），"
            "模板按 16:9 制作，识别可能错位。PlayCover 请在「应用设置 → 显示」里把窗口设为 1920x1080。"
        )

    current = int(cfg.get_value("set_win_size", 1080))
    if abs(current - plan["height"]) > 1:
        log.info(f"按当前窗口高度调整本次会话分辨率基准: {current} -> {plan['height']}")
        # 只改内存中的配置，不落盘
        cfg.config.set_win_size = plan["height"]
    return plan
