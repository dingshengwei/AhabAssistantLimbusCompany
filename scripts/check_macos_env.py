#!/usr/bin/env python3
"""macOS 环境自检：权限、adb、游戏窗口、截图、分辨率。

    ./scripts/check_macos_env.py

不启动游戏、不发送点击，只做只读检查，适合排查“为什么 AALC 找不到窗口/截图失败”。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from module.platform.macos import adb, capture, display, resolution, window  # noqa: E402

OK = "✅"
WARN = "⚠️ "
FAIL = "❌"


def report(title: str, state: str, detail: str = "") -> None:
    print(f"{state} {title}" + (f"：{detail}" if detail else ""))


def main() -> int:
    print("=== AALC macOS 环境自检 ===\n")
    problems = 0

    # 1. 系统与显示器
    import platform

    print(f"系统: macOS {platform.mac_ver()[0]} / {platform.machine()}")
    for info in display.screens():
        left, top, right, bottom = info["frame"]
        report(
            f"显示器 {info['name']}",
            OK,
            f"{int(right - left)}x{int(bottom - top)} 点, scale={info['scale']}",
        )

    # 2. 权限
    screen_ok = capture.screen_permission_ok()
    report(
        "屏幕录制权限",
        OK if screen_ok else FAIL,
        "已授权" if screen_ok else "系统设置 > 隐私与安全性 > 屏幕录制，勾选运行本脚本的终端",
    )
    problems += 0 if screen_ok else 1

    ax_ok = window.accessibility_trusted()
    report(
        "辅助功能权限",
        OK if ax_ok else FAIL,
        "已授权" if ax_ok else "系统设置 > 隐私与安全性 > 辅助功能，勾选运行本脚本的终端",
    )
    problems += 0 if ax_ok else 1

    # 3. adb
    adb_status = adb.status()
    if adb_status["adb"]:
        report("adb", OK, f"{adb_status['version']} ({adb_status['adb']})")
        if adb_status["devices"]:
            report("已连接的 Android 设备", OK, ", ".join(adb_status["devices"]))
        else:
            report(
                "已连接的 Android 设备",
                WARN,
                "无。模拟器方案请先启动 BlueStacks Air / AVD，再 adb connect 127.0.0.1:5555",
            )
    else:
        report("adb", WARN, "未安装。模拟器方案需要：./scripts/setup_adb_macos.sh")

    # 4. 游戏窗口
    # 排除 AALC 自己的窗口（标题里也带 Limbus Company）
    def is_self(item: dict) -> bool:
        owner = item["owner"].lower()
        name = item["name"].lower()
        return owner in {"python", "python3"} or "ahab assistant" in name

    candidates = []
    for item in window.list_windows():
        if item["layer"] != 0 or is_self(item):
            continue
        text = (item["owner"] + " " + item["name"]).lower()
        if "limbus" in text:
            candidates.append(item)

    if not candidates:
        report(
            "游戏窗口",
            FAIL,
            "未找到 LimbusCompany 窗口。PlayCover / 模拟器里先把游戏开起来",
        )
        problems += 1
    else:
        target = candidates[0]
        left, top, right, bottom = window.rect_pixels(target["id"])
        width, height = right - left, bottom - top
        plan = resolution.plan_window_metrics(width, height)
        report(
            "游戏窗口",
            OK,
            f"{target['owner']} / {target['name']} id={target['id']} {width}x{height}",
        )
        report(
            "宽高比",
            OK if plan["aspect_ok"] else FAIL,
            f"{plan['aspect']:.2f}:1"
            + ("" if plan["aspect_ok"] else "（不是 16:9，模板会错位；PlayCover 请设 1920x1080）"),
        )
        problems += 0 if plan["aspect_ok"] else 1

        image = capture.capture_window(target["id"])
        if image is None:
            report("截图", FAIL, capture.last_error() or "未知错误")
            problems += 1
        else:
            out = Path("/tmp/aalc_selfcheck_capture.png")
            image.save(out)
            report("截图", OK, f"{image.size[0]}x{image.size[1]} -> {out}")

    print()
    if problems == 0:
        print("结论：环境就绪，可以启动 AALC 了（./scripts/run_macos.sh）")
    else:
        print(f"结论：还有 {problems} 项待处理，按上面的提示逐项修复后再试")
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
