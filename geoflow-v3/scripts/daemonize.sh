#!/usr/bin/env bash
# 双 fork 脱离控制终端，避免 Cursor/IDE shell 结束后子进程被杀
set -euo pipefail
SCRIPT="$1"
LOG="$2"
PIDFILE="$3"

/usr/bin/python3 - "$SCRIPT" "$LOG" "$PIDFILE" <<'PY'
import os
import subprocess
import sys

script, log, pidfile = sys.argv[1], sys.argv[2], sys.argv[3]

if os.fork() > 0:
    sys.exit(0)
os.setsid()
if os.fork() > 0:
    os._exit(0)

with open(log, "a", encoding="utf-8") as fh:
    proc = subprocess.Popen(
        ["bash", script],
        stdin=subprocess.DEVNULL,
        stdout=fh,
        stderr=fh,
        start_new_session=True,
        close_fds=True,
    )
with open(pidfile, "w", encoding="utf-8") as pf:
    pf.write(str(proc.pid))
os._exit(0)
PY

# 等 pidfile 落盘
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if [ -s "${PIDFILE}" ] && kill -0 "$(cat "${PIDFILE}")" 2>/dev/null; then
    exit 0
  fi
  sleep 0.2
done
echo "daemonize failed: ${SCRIPT}" >&2
exit 1
