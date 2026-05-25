#!/usr/bin/env bash
set -euo pipefail

app_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
desktop_dir="${XDG_DATA_HOME:-"$HOME/.local/share"}/applications"
source_entry="$app_root/packaging/gravity-omega-native.desktop"
launcher_script="$app_root/packaging/launch-gravity-omega-native.sh"
target_entry="$desktop_dir/gravity-omega-native.desktop"

if [[ ! -x "$app_root/src-tauri/target/release/gravity-omega-native" ]]; then
  printf 'Release binary is missing or not executable: %s\n' "$app_root/src-tauri/target/release/gravity-omega-native" >&2
  exit 1
fi

if [[ ! -f "$launcher_script" ]]; then
  printf 'Launcher script is missing: %s\n' "$launcher_script" >&2
  exit 1
fi

install -d "$desktop_dir"
chmod 0755 "$launcher_script"
install -m 0644 "$source_entry" "$target_entry"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$desktop_dir" || true
fi

printf 'Installed %s\n' "$target_entry"
