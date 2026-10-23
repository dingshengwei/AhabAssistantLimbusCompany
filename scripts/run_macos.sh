#!/usr/bin/env bash
# 在 macOS 上从源码启动 AALC。
#
#   ./scripts/run_macos.sh
#
# 首次运行会创建 .venv 并安装依赖（需要 Python 3.12+）。
# 可用环境变量覆盖：
#   PYTHON=/opt/homebrew/bin/python3.12   # 指定解释器
#   PIP_INDEX_URL=...                     # 换源，默认清华镜像
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3.12}"
INDEX="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"

if [ ! -x ".venv/bin/python" ]; then
  if ! command -v "$PYTHON" >/dev/null 2>&1; then
    for candidate in /opt/homebrew/bin/python3.12 /usr/local/bin/python3.12 ../.python/cpython-3.12-macos-aarch64-none/bin/python3.12 python3; do
      if command -v "$candidate" >/dev/null 2>&1; then
        PYTHON="$candidate"
        break
      fi
    done
  fi

  if ! "$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)'; then
    echo "需要 Python 3.12 及以上版本，当前：$("$PYTHON" -V 2>&1)" >&2
    echo "建议：brew install python@3.12，或用 PYTHON=/path/to/python3.12 指定" >&2
    exit 1
  fi

  echo "==> 创建虚拟环境（$PYTHON）"
  "$PYTHON" -m venv .venv
fi

echo "==> 安装/校验依赖"
# uv 创建的虚拟环境可能没有 pip，先补齐
if ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
  .venv/bin/python -m ensurepip --upgrade >/dev/null 2>&1 || true
fi
.venv/bin/python -m pip install -q -U pip -i "$INDEX" >/dev/null || true
.venv/bin/python -m pip install -q -r requirements-macos.txt -i "$INDEX"

echo "==> 启动 AALC（macOS）"
exec .venv/bin/python main.py "$@"
