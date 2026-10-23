"""macOS 通知（替代 Windows Toast）。

使用 osascript 调系统通知中心；失败时退回日志，不影响主流程。
"""

from __future__ import annotations

import subprocess
import threading

from module.logger import log


def _escape(text: str) -> str:
    return (text or "").replace("\\", "\\\\").replace('"', '\\"')


def notify(title: str, message: str, sound: bool = False) -> bool:
    script = (
        f'display notification "{_escape(message)}" '
        f'with title "{_escape(title)}"'
    )
    if sound:
        script += ' sound name "default"'
    try:
        proc = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            timeout=10,
        )
        if proc.returncode != 0:
            log.debug(f"系统通知失败: {proc.stderr.decode(errors='ignore').strip()}")
            return False
        return True
    except Exception as exc:
        log.debug(f"系统通知异常: {exc}")
        return False


def notify_async(title: str, message: str, sound: bool = False) -> None:
    threading.Thread(target=notify, args=(title, message, sound), daemon=True).start()
