#!/usr/bin/env bash
# ⚠️ 现版 Limbus（Unity 6）在 AVD 上会崩溃，见 docs/MACOS.md；本脚本仅为历史/旧版保留。
#
# 启动 AALC 的 AVD（竖屏 1080x1920，游戏横屏后即 1920x1080）。
#
#   ./scripts/start_avd_macos.sh                     # 自动探测本地代理（Clash 7897 等）
#   PROXY=http://127.0.0.1:7897 ./scripts/start_avd_macos.sh
#   PROXY=none ./scripts/start_avd_macos.sh          # 不走代理（已开全局 TUN 时用）
#
# 为什么需要代理：模拟器走 QEMU NAT，用的是宿主机网络；如果宿主机只有「系统代理」
# 而没有 TUN/全局路由，Android 自己不会用这个代理，Play 商店/Google 登录就会转圈。
set -euo pipefail
SDK="${ANDROID_HOME:-$HOME/Library/Android/sdk}"
AVD_NAME="${AVD_NAME:-AALC_1080p}"

if ! "$SDK/emulator/emulator" -list-avds | grep -qx "$AVD_NAME"; then
  echo "未找到 AVD: $AVD_NAME，先运行 ./scripts/setup_avd_macos.sh" >&2
  exit 1
fi

detect_proxy() {
  # 常见本地代理端口：Clash Verge 7897 / Clash 7890 / Surge 6152 / V2Ray 1087 / 通用 8888
  for port in 7897 7890 6152 1087 8888 1080; do
    if nc -z -G 1 127.0.0.1 "$port" 2>/dev/null; then
      echo "http://127.0.0.1:$port"
      return 0
    fi
  done
  return 1
}

PROXY="${PROXY:-}"
if [ -z "$PROXY" ]; then
  if PROXY="$(detect_proxy)"; then
    echo "==> 检测到本地代理: ${PROXY}（Play 商店/Google 登录需要它）"
  else
    PROXY="none"
  fi
fi

ARGS=(-avd "$AVD_NAME" -gpu host -no-boot-anim -no-metrics)
if [ "$PROXY" != "none" ]; then
  ARGS+=(-http-proxy "$PROXY")
else
  echo "==> 不设置模拟器代理（已开系统级 TUN 分流时正常）"
fi

if [ "${DRY_RUN:-0}" = "1" ]; then
  echo "DRY_RUN: $SDK/emulator/emulator ${ARGS[*]}"
  exit 0
fi

exec "$SDK/emulator/emulator" "${ARGS[@]}"
