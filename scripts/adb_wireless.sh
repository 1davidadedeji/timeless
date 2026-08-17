#!/bin/bash
# Keep an ADB connection to the phone without a cable when the network allows it.
set -euo pipefail
CONF="${TIMELESS_ADB_CONF:-$HOME/Library/Application Support/Timeless/phone-adb.conf}"
MODE="${TIMELESS_ADB_MODE:-wireless}"
mkdir -p "$(dirname "$CONF")"

usb_ready() {
  adb devices | awk 'NR>1 && $2=="device" && $1 !~ /:/ {found=1} END {exit found?0:1}'
}

any_device() {
  adb devices | awk 'NR>1 && $2=="device" {found=1} END {exit found?0:1}'
}

wireless_connected() {
  adb devices | awk 'NR>1 && $2=="device" && $1 ~ /:/ {found=1} END {exit found?0:1}'
}

phone_ip() {
  adb shell ip -f inet addr show wlan0 2>/dev/null | awk '/inet /{print $2}' | cut -d/ -f1 | head -1
}

connect_host() {
  local host="$1" port="$2"
  if nc -z -G 2 "$host" "$port" 2>/dev/null; then
    adb connect "$host:$port" >/dev/null || true
    return 0
  fi
  return 1
}

if [ "$MODE" = "usb" ]; then
  if usb_ready; then
    echo "usb adb ready"
    exit 0
  fi
  echo "no usb adb phone"
  exit 0
fi

if usb_ready; then
  IP="$(phone_ip)"
  if [ -n "${IP:-}" ]; then
    {
      echo "ADB_HOST=$IP"
      echo "ADB_PORT=5555"
    } > "$CONF"
  fi
  if ! wireless_connected && [ -n "${IP:-}" ]; then
    adb tcpip 5555 >/dev/null || true
    sleep 1
    connect_host "$IP" 5555 && echo "wireless adb ready at $IP:5555" || echo "saved $IP:5555; Wi-Fi may block phone↔Mac"
  fi
fi

if [ -f "$CONF" ] && ! wireless_connected; then
  # shellcheck disable=SC1090
  source "$CONF"
  if [ -n "${ADB_PAIR_HOST:-}" ] && [ -n "${ADB_PAIR_PORT:-}" ] && [ -n "${ADB_PAIR_CODE:-}" ]; then
    adb pair "${ADB_PAIR_HOST}:${ADB_PAIR_PORT}" "${ADB_PAIR_CODE}" >/dev/null 2>&1 || true
  fi
  if [ -n "${ADB_HOST:-}" ]; then
    connect_host "${ADB_HOST}" "${ADB_PORT:-5555}" || echo "wireless ${ADB_HOST}:${ADB_PORT:-5555} not reachable"
  fi
fi

# Android Wireless debugging (mDNS), if advertised
if ! wireless_connected; then
  while read -r _name _type addr; do
    [ -z "${addr:-}" ] && continue
    host="${addr%%:*}"
    port="${addr##*:}"
    [ "$port" = "$addr" ] && continue
    connect_host "$host" "$port" || true
  done < <(adb mdns services 2>/dev/null | awk 'NF>=3 {print $1,$2,$NF}')
fi

if any_device; then
  exit 0
fi
echo "no adb phone (USB unauthorized/unplugged, or Wi-Fi blocked client-to-client)"
exit 0
