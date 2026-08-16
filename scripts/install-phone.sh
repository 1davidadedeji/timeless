#!/bin/bash
# Install ActivityWatch on a USB-connected Samsung phone.
set -euo pipefail
APK="${TIMELESS_AW_APK:-$HOME/Library/Application Support/Timeless/installers/aw-android.apk}"
if [ ! -f "$APK" ]; then
  echo "APK missing: $APK"
  exit 1
fi
if ! adb devices | awk 'NR>1 && $2=="device" {found=1} END {exit found?0:1}'; then
  echo "No phone in adb 'device' state."
  echo "1. Plug USB into this MacBook."
  echo "2. Samsung: USB for file transfer / MTP (not charge-only)."
  echo "3. Enable Developer options + USB debugging, then tap Allow on the RSA prompt."
  echo "4. Re-run: $0"
  adb devices
  exit 2
fi
adb install -r "$APK"
echo "Installed ActivityWatch. On the phone: Usage access ON, battery optimization OFF for ActivityWatch."
