#!/usr/bin/env bash
# 归档外挂：无常驻服务。不接入 GEOFlow 主栈。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
echo "[archive] RAG-CLI 为归档外挂，主栈不安装。见 ../guide/cli-plugins.md"
exec "$ROOT/verify.sh"
