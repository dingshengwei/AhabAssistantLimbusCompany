#!/usr/bin/env bash
# 为 macOS 下载官方 Android platform-tools（含 adb），供 AALC 的模拟器模式使用。
#
#   ./scripts/setup_adb_macos.sh
#
# 安装位置：assets/binary/platform-tools/adb（已在 .gitignore 中，不会提交）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TARGET_DIR="$ROOT/assets/binary/platform-tools"
URL="${PLATFORM_TOOLS_URL:-https://dl.google.com/android/repository/platform-tools-latest-darwin.zip}"

if [ -x "$TARGET_DIR/adb" ]; then
  echo "==> adb 已存在：$("$TARGET_DIR/adb" version | head -1)"
  exit 0
fi

TMP_ZIP="$(mktemp -t platform-tools).zip"
TMP_DIR="$(mktemp -d)"
trap 'rm -f "$TMP_ZIP"; rm -rf "$TMP_DIR"' EXIT

echo "==> 下载 platform-tools: $URL"
curl -fL --retry 3 --progress-bar -o "$TMP_ZIP" "$URL"

echo "==> 解压到 assets/binary/platform-tools"
unzip -q "$TMP_ZIP" -d "$TMP_DIR"
mkdir -p "$ROOT/assets/binary"
rm -rf "$TARGET_DIR"
mv "$TMP_DIR/platform-tools" "$TARGET_DIR"
chmod +x "$TARGET_DIR/adb" "$TARGET_DIR/fastboot" 2>/dev/null || true

# macOS 会对网上下载的可执行文件打隔离标记，去掉后才能运行
xattr -dr com.apple.quarantine "$TARGET_DIR" 2>/dev/null || true

echo "==> 完成：$("$TARGET_DIR/adb" version | head -1)"
echo "提示：本地模拟器默认 adb 端口 5555（BlueStacks Air / Android Studio AVD）、16384（MuMu Pro）"
