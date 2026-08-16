#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/dist" "$HOME/Library/Application Support/Timeless/logs"
swiftc -O -o "$ROOT/dist/TimelessOverlay" "$ROOT/macos/TimelessOverlay.swift" -framework Cocoa -framework WebKit
echo "built $ROOT/dist/TimelessOverlay"
