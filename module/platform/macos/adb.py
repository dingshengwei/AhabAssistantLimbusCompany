"""adb 定位与本地模拟器连接（macOS）。

上游把 adb.exe 随 Windows 包一起分发，macOS 上需要自己准备 Android platform-tools。
这里按优先级查找 adb，并把它所在目录塞进 PATH（adbutils 用 ``adb`` 这个名字启动）。

配套脚本：``scripts/setup_adb_macos.sh``（下载官方 platform-tools）。
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from module.logger import log

REPO_ROOT = Path(__file__).resolve().parents[3]
BUNDLED_DIR = REPO_ROOT / "assets" / "binary" / "platform-tools"

#: 常见的本地模拟器 adb 端口
#: 5555: BlueStacks Air / Android Studio AVD / Genymotion
#: 16384: MuMu 12 / MuMu Pro
#: 21503: 夜神；62001: 逍遥；7555: MuMu 部分版本
LOCAL_EMULATOR_PORTS = (5555, 16384, 21503, 62001, 7555)


def candidates() -> list[Path]:
    env_path = os.environ.get("ADBUTILS_ADB_PATH")
    items = [
        Path(env_path) if env_path else None,
        Path(shutil.which("adb")) if shutil.which("adb") else None,
        BUNDLED_DIR / "adb",
        Path.home() / "Library/Android/sdk/platform-tools/adb",
        Path("/opt/homebrew/bin/adb"),
        Path("/usr/local/bin/adb"),
    ]
    return [p for p in items if p is not None]


def find_adb() -> Path | None:
    for path in candidates():
        try:
            if path.is_file() and os.access(path, os.X_OK):
                return path
        except OSError:
            continue
    return None


def ensure_adb_on_path() -> Path | None:
    """把可用的 adb 目录放进 PATH 最前面，返回 adb 路径。"""
    adb = find_adb()
    if adb is None:
        return None
    adb_dir = str(adb.parent)
    current = os.environ.get("PATH", "")
    if adb_dir not in current.split(os.pathsep):
        os.environ["PATH"] = adb_dir + os.pathsep + current if current else adb_dir
        log.debug(f"已把 adb 目录加入 PATH: {adb_dir}")
    return adb


def run_adb(args: list[str], timeout: float = 15.0) -> subprocess.CompletedProcess[str] | None:
    adb = find_adb()
    if adb is None:
        return None
    try:
        return subprocess.run(
            [str(adb), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except Exception as exc:
        log.debug(f"执行 adb {' '.join(args)} 失败: {exc}")
        return None


def version() -> str | None:
    result = run_adb(["version"])
    if result is None or result.returncode != 0:
        return None
    first = (result.stdout or "").splitlines()
    return first[0].strip() if first else None


def devices() -> list[str]:
    result = run_adb(["devices"])
    if result is None or result.returncode != 0:
        return []
    out = []
    for line in (result.stdout or "").splitlines()[1:]:
        line = line.strip()
        if not line or "\t" not in line:
            continue
        serial, state = line.split("\t", 1)
        if state.strip() == "device":
            out.append(serial.strip())
    return out


def connect(endpoint: str, timeout: float = 15.0) -> bool:
    result = run_adb(["connect", endpoint], timeout=timeout)
    if result is None:
        return False
    text = ((result.stdout or "") + (result.stderr or "")).lower()
    return "connected" in text and "cannot" not in text and "failed" not in text


def detect_local_emulator() -> str | None:
    """在常见端口上探测已连接的本地模拟器，返回 adb 设备序列号。"""
    existing = devices()
    if existing:
        return existing[0]
    for port in LOCAL_EMULATOR_PORTS:
        endpoint = f"127.0.0.1:{port}"
        if connect(endpoint):
            log.info(f"已连接本地模拟器: {endpoint}")
            return endpoint
    return None


def status() -> dict:
    adb = find_adb()
    return {
        "adb": str(adb) if adb else None,
        "version": version() if adb else None,
        "devices": devices() if adb else [],
    }
