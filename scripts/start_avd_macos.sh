#!/usr/bin/env bash
# 启动已创建好的 AALC AVD（默认竖屏 1080x1920，可跑 Limbus Company 横屏）。
set -euo pipefail
SDK="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
AVD_NAME="${AVD_NAME:-AALC_1080p}"

if ! "$SDK/emulator/emulator" -list-avds | grep -qx "$AVD_NAME"; then
  echo "未找到 AVD: $AVD_NAME，先运行 ./scripts/setup_avd_macos.sh" >&2
  exit 1
fi

exec "$SDK/emulator/emulator" -avd "$AVD_NAME" -gpu host -no-boot-anim
