#!/bin/bash
# Pull ActivityWatch from the phone into Timeless (USB or wireless adb).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${TIMELESS_VENV:-$HOME/Library/Application Support/Timeless/venv}"
MODE="${TIMELESS_ADB_MODE:-wireless}"
"$ROOT/scripts/adb_wireless.sh" || true
pick_serial() {
  if [ "$MODE" = "usb" ]; then
    adb devices | awk 'NR>1 && $2=="device" && $1 !~ /:/ {print $1; exit}'
  else
    adb devices | awk 'NR>1 && $2=="device" && $1 ~ /:/ {print $1; exit}'
  fi
}
SERIAL="$(pick_serial)"
if [ -z "${SERIAL:-}" ]; then
  SERIAL="$(adb devices | awk 'NR>1 && $2=="device"{print $1; exit}')"
fi
if [ -z "${SERIAL:-}" ]; then
  echo "phone not in adb device state"
  exit 0
fi
# AW Android only binds :5600 while the app process has the server up.
adb -s "$SERIAL" shell 'am start -n net.activitywatch.android/.MainActivity' >/dev/null 2>&1 || true
sleep 2
adb -s "$SERIAL" forward --remove tcp:5666 >/dev/null 2>&1 || true
adb -s "$SERIAL" forward tcp:5666 tcp:5600 >/dev/null
export AW_URL="http://127.0.0.1:5666"
export AW_SENSOR="phone_aw"
export TIMELESS_URL="${TIMELESS_URL:-http://127.0.0.1:8787}"
exec "$VENV/bin/python" "$ROOT/scripts/aw_ingest.py"
