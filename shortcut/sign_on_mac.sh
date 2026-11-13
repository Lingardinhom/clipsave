#!/usr/bin/env bash
set -euo pipefail

# Chạy script này trên máy Mac (macOS Monterey trở lên) để ký số file .shortcut trước khi gửi sang iPhone.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DIST_DIR="${SCRIPT_DIR}/dist"

if ! command -v shortcuts >/dev/null 2>&1; then
  echo "Lỗi: Lệnh 'shortcuts' chỉ có sẵn trên macOS."
  exit 1
fi

for f in "${DIST_DIR}"/*.unsigned.shortcut; do
  [ -e "$f" ] || continue
  signed="${f%.unsigned.shortcut}.shortcut"
  echo "Đang ký $(basename "$f") -> $(basename "$signed")..."
  shortcuts sign --mode anyone -i "$f" -o "$signed"
done

echo "Hoàn tất! Hãy AirDrop file .shortcut đã ký sang iPhone hoặc mở trực tiếp trên Mac rồi bấm Share -> Copy iCloud Link."
