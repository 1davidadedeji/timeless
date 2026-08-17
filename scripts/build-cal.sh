#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SUPPORT="$HOME/Library/Application Support/Timeless"
mkdir -p "$ROOT/dist" "$SUPPORT/bin"
swiftc -O -o "$ROOT/dist/TimelessCal" "$ROOT/macos/TimelessCal.swift" -framework EventKit -framework Foundation
cp "$ROOT/dist/TimelessCal" "$SUPPORT/bin/TimelessCal"
chmod +x "$SUPPORT/bin/TimelessCal"
echo "built $SUPPORT/bin/TimelessCal"
