#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOME_DIR="$HOME"
SUPPORT="$HOME/Library/Application Support/Timeless"
VENV="$SUPPORT/venv"
DEST="$HOME/Library/LaunchAgents"
LOG="$SUPPORT/logs"
mkdir -p "$DEST" "$LOG" "$SUPPORT/bin" "$ROOT/dist"

if [ ! -x "$VENV/bin/timeless" ]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -e "$ROOT" -q
fi

if [ ! -x "$ROOT/dist/TimelessOverlay" ]; then
  swiftc -O -o "$ROOT/dist/TimelessOverlay" "$ROOT/macos/TimelessOverlay.swift" -framework Cocoa -framework WebKit
fi
cp "$ROOT/dist/TimelessOverlay" "$SUPPORT/bin/TimelessOverlay"
chmod +x "$SUPPORT/bin/TimelessOverlay"

render() {
  local src="$1" dst="$2"
  sed -e "s|VENV|$VENV|g" -e "s|SUPPORT|$SUPPORT|g" -e "s|ROOT|$ROOT|g" -e "s|HOME|$HOME_DIR|g" "$src" > "$dst"
}

render "$ROOT/macos/launchd/com.timeless.brain.plist.tmpl" "$DEST/com.timeless.brain.plist"
render "$ROOT/macos/launchd/com.timeless.overlay.plist.tmpl" "$DEST/com.timeless.overlay.plist"
render "$ROOT/macos/launchd/com.timeless.aw-ingest.plist.tmpl" "$DEST/com.timeless.aw-ingest.plist"

launchctl bootout "gui/$(id -u)/com.timeless.brain" 2>/dev/null || true
launchctl bootout "gui/$(id -u)/com.timeless.overlay" 2>/dev/null || true
launchctl bootout "gui/$(id -u)/com.timeless.aw-ingest" 2>/dev/null || true
pkill -f TimelessOverlay 2>/dev/null || true
pkill -f '/Timeless/venv/bin/timeless' 2>/dev/null || true
sleep 1

launchctl bootstrap "gui/$(id -u)" "$DEST/com.timeless.brain.plist"
launchctl bootstrap "gui/$(id -u)" "$DEST/com.timeless.overlay.plist"
launchctl bootstrap "gui/$(id -u)" "$DEST/com.timeless.aw-ingest.plist"
launchctl enable "gui/$(id -u)/com.timeless.brain"
launchctl enable "gui/$(id -u)/com.timeless.overlay"
launchctl enable "gui/$(id -u)/com.timeless.aw-ingest"
launchctl kickstart -k "gui/$(id -u)/com.timeless.brain"
launchctl kickstart -k "gui/$(id -u)/com.timeless.overlay"
launchctl kickstart -k "gui/$(id -u)/com.timeless.aw-ingest"

osascript -e 'tell application "System Events" to make login item at end with properties {path:"/Applications/ActivityWatch.app", hidden:false}' >/dev/null 2>&1 || true

echo "LaunchAgents installed. Brain: http://127.0.0.1:8787"
