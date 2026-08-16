#!/bin/bash
# Pull ActivityWatch from the phone into Timeless (USB or wireless adb).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${TIMELESS_VENV:-$HOME/Library/Application Support/Timeless/venv}"
"$ROOT/scripts/adb_wireless.sh"
if ! adb devices | awk 'NR>1 && $2=="device"{ok=1} END{exit ok?0:1}'; then
  echo "phone not in adb device state"
  exit 0
fi
SERIAL="$(adb devices | awk 'NR>1 && $2=="device"{print $1; exit}')"
adb -s "$SERIAL" forward tcp:5666 tcp:5600 >/dev/null
export AW_URL="http://127.0.0.1:5666"
export AW_SENSOR="phone_aw"
export TIMELESS_URL="${TIMELESS_URL:-http://127.0.0.1:8787}"
exec "$VENV/bin/python" "$ROOT/scripts/aw_ingest.py"
