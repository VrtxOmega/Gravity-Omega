#!/usr/bin/env bash
set -euo pipefail

app_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
binary="$app_root/src-tauri/target/release/gravity-omega-native"
state_dir="${XDG_STATE_HOME:-"$HOME/.local/state"}/gravity-omega-native"
log_file="$state_dir/launcher.log"

mkdir -p "$state_dir"

{
  printf '[%s] launch requested\n' "$(date --iso-8601=seconds)"
  printf 'app_root=%s\n' "$app_root"
  printf 'binary=%s\n' "$binary"
} >>"$log_file"

if [[ ! -x "$binary" ]]; then
  printf '[%s] launch failed: release binary missing or not executable\n' "$(date --iso-8601=seconds)" >>"$log_file"
  exit 1
fi

cd "$app_root"
set +e
/usr/bin/setsid -f "$binary" >>"$log_file" 2>&1
status=$?
set -e
printf '[%s] launch spawn status=%s\n' "$(date --iso-8601=seconds)" "$status" >>"$log_file"
exit "$status"
