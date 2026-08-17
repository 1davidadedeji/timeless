#!/bin/bash
# Open the macOS panes Timeless still needs a human click for.
set -euo pipefail
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Automation" 2>/dev/null || true
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility" 2>/dev/null || true
open "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture" 2>/dev/null || true
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Calendars" 2>/dev/null || true
open "/System/Applications/Mail.app" 2>/dev/null || true
echo "Allow: Screen Recording + Accessibility for screenpipe; Automation (osascript → Mail); Calendar already ingesting if you saw mac_cal."
