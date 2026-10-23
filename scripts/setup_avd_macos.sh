#!/usr/bin/env bash
# 在 macOS（Apple Silicon）上准备一套免费的 Android 模拟器：
# Android SDK commandline-tools + emulator + Google Play arm64 系统镜像 + 1920x1080 的 AVD。
#
#   ./scripts/setup_avd_macos.sh            # 安装/检查（幂等）
#   ./scripts/setup_avd_macos.sh --start    # 装完直接启动模拟器
#
# 之后在模拟器里登录 Google Play、安装 Limbus Company，AALC 用 adb 连接即可：
#   simulator: true / simulator_type: 10 / simulator_host: 127.0.0.1 / simulator_port: 5555
set -euo pipefail

SDK="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
API_LEVEL="${API_LEVEL:-33}"
AVD_NAME="${AVD_NAME:-AALC_1080p}"
IMAGE="system-images;android-${API_LEVEL};google_apis_playstore;arm64-v8a"
START=0
[ "${1:-}" = "--start" ] && START=1

echo "==> SDK 目录: $SDK"
mkdir -p "$SDK"

# ---------------------------------------------------------------- 1. cmdline-tools
SDKMANAGER="$SDK/cmdline-tools/latest/bin/sdkmanager"
if [ ! -x "$SDKMANAGER" ]; then
  TOOLS_URL="https://dl.google.com/android/repository/commandlinetools-mac-13114758_latest.zip"
  TMP_ZIP="$(mktemp -t cmdtools).zip"
  TMP_DIR="$(mktemp -d)"
  trap 'rm -f "$TMP_ZIP"; rm -rf "$TMP_DIR"' EXIT
  echo "==> 下载 Android commandline-tools"
  curl -fL --retry 3 --progress-bar -o "$TMP_ZIP" "$TOOLS_URL"
  unzip -q "$TMP_ZIP" -d "$TMP_DIR"
  mkdir -p "$SDK/cmdline-tools"
  rm -rf "$SDK/cmdline-tools/latest"
  mv "$TMP_DIR/cmdline-tools" "$SDK/cmdline-tools/latest"
fi

export ANDROID_HOME="$SDK"
export ANDROID_SDK_ROOT="$SDK"

if ! command -v java >/dev/null 2>&1; then
  echo "需要 Java 17+（sdkmanager 依赖）。建议安装 Android Studio 或 temurin JDK。" >&2
  exit 1
fi

# ---------------------------------------------------------------- 2. 组件
echo "==> 接受许可协议"
yes | "$SDKMANAGER" --licenses >/dev/null 2>&1 || true

echo "==> 安装 emulator / platform-tools / $IMAGE"
"$SDKMANAGER" --install "platform-tools" "emulator" "$IMAGE"

# ---------------------------------------------------------------- 3. AVD
AVDMANAGER="$SDK/cmdline-tools/latest/bin/avdmanager"
if "$SDK/emulator/emulator" -list-avds 2>/dev/null | grep -qx "$AVD_NAME"; then
  echo "==> AVD 已存在: $AVD_NAME"
else
  echo "==> 创建 AVD: $AVD_NAME"
  echo "no" | "$AVDMANAGER" create avd \
    --name "$AVD_NAME" \
    --package "$IMAGE" \
    --device "pixel_5" \
    --force
fi

CONFIG="$HOME/.android/avd/$AVD_NAME.avd/config.ini"
if [ -f "$CONFIG" ]; then
  echo "==> 调整 AVD 配置（1080x1920 竖屏 / 480dpi / 4G 内存 / 4 核）"
  python3 - "$CONFIG" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
wanted = {
    # 竖屏 1080x1920：与 MuMu 一致，游戏横屏后 AALC 的坐标旋转才有意义
    "hw.lcd.width": "1080",
    "hw.lcd.height": "1920",
    "hw.lcd.density": "480",
    "hw.keyboard": "yes",
    "hw.ramSize": "4096",
    "vm.heapSize": "512",
    "hw.cpu.ncore": "4",
    "disk.dataPartition.size": "8G",
    "hw.gpu.enabled": "yes",
    "hw.gpu.mode": "auto",
    "playstore.enabled": "true",
}
lines = path.read_text().splitlines()
index = {}
out = []
for line in lines:
    key = line.split("=", 1)[0].strip()
    if key in wanted:
        index[key] = len(out)
        out.append(f"{key}={wanted[key]}")
    else:
        out.append(line)
for key, value in wanted.items():
    if key not in index:
        out.append(f"{key}={value}")
path.write_text("\n".join(out) + "\n")
print("config.ini 已更新:", path)
PY
fi

echo
echo "==> 完成。启动模拟器："
echo "    $SDK/emulator/emulator -avd $AVD_NAME -gpu host"
echo
echo "启动后："
echo "    1) 在模拟器里登录 Google 账号 -> Play 商店安装 Limbus Company"
echo "    2) 确认 adb 能连上：$SDK/platform-tools/adb devices"
echo "    3) AALC 设置：模拟器 -> 其他 -> 主机 127.0.0.1，端口填 0（自动选择 adb 设备）"

if [ "$START" = "1" ]; then
  echo "==> 启动模拟器（关闭本终端会同时结束）"
  exec "$SDK/emulator/emulator" -avd "$AVD_NAME" -gpu host
fi
