#!/usr/bin/env bash
# macOS 下脱离父 shell 的后台启动（子进程 reparent 到 launchd）
set -euo pipefail
SCRIPT="$1"
LOG="$2"
PIDFILE="$3"
/bin/bash -c "nohup \"${SCRIPT}\" >>\"${LOG}\" 2>&1 & echo \$! >\"${PIDFILE}\""
