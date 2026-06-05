#!/usr/bin/env bash
set -euo pipefail

app_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
binary="$app_root/src-tauri/target/release/gravity-omega-native"
state_dir="${XDG_STATE_HOME:-"$HOME/.local/state"}/gravity-omega-native"
log_file="$state_dir/launcher.log"

mkdir -p "$state_dir"

source_head="$(git -C "$app_root" rev-parse --short HEAD 2>/dev/null || true)"
source_commit_epoch="$(git -C "$app_root" log -1 --format=%ct 2>/dev/null || true)"
source_commit_iso=""
if [[ -n "$source_commit_epoch" ]]; then
  source_commit_iso="$(date --date="@$source_commit_epoch" --iso-8601=seconds 2>/dev/null || true)"
fi
binary_mtime_epoch=""
binary_mtime_iso=""
if [[ -e "$binary" ]]; then
  binary_mtime_epoch="$(stat -c %Y "$binary" 2>/dev/null || true)"
  binary_mtime_iso="$(date --date="@$binary_mtime_epoch" --iso-8601=seconds 2>/dev/null || true)"
fi

{
  printf '[%s] launch requested\n' "$(date --iso-8601=seconds)"
  printf 'app_root=%s\n' "$app_root"
  printf 'binary=%s\n' "$binary"
  printf 'source_head=%s\n' "${source_head:-unknown}"
  printf 'source_commit_time=%s\n' "${source_commit_iso:-unknown}"
  printf 'binary_mtime=%s\n' "${binary_mtime_iso:-missing}"
} >>"$log_file"

if [[ ! -x "$binary" ]]; then
  printf '[%s] launch failed: release binary missing or not executable\n' "$(date --iso-8601=seconds)" >>"$log_file"
  exit 1
fi

if [[ -n "$source_commit_epoch" && -n "$binary_mtime_epoch" && "$binary_mtime_epoch" -lt "$source_commit_epoch" ]]; then
  printf '[%s] launch blocked: release binary is older than source HEAD; run npm run build before launching. Set GRAVITY_OMEGA_ALLOW_STALE_BINARY=1 only for deliberate stale-artifact diagnostics.\n' "$(date --iso-8601=seconds)" >>"$log_file"
  if command -v notify-send >/dev/null 2>&1; then
    notify-send "Gravity Omega launch blocked" "Release binary is older than source HEAD. Run npm run build, then launch again." || true
  fi
  if [[ "${GRAVITY_OMEGA_ALLOW_STALE_BINARY:-0}" != "1" ]]; then
    exit 2
  fi
  printf '[%s] launch override: GRAVITY_OMEGA_ALLOW_STALE_BINARY=1\n' "$(date --iso-8601=seconds)" >>"$log_file"
fi

export RUST_BACKTRACE="${RUST_BACKTRACE:-1}"
export WEBKIT_DISABLE_DMABUF_RENDERER="${WEBKIT_DISABLE_DMABUF_RENDERER:-1}"
export G_MESSAGES_DEBUG="${G_MESSAGES_DEBUG:-}"

if [[ "${GRAVITY_OMEGA_LAUNCHER_DRY_RUN:-0}" == "1" ]]; then
  printf '[%s] launch dry-run passed: binary is current and launch environment is ready rust_backtrace=%s webkit_disable_dmabuf=%s\n' "$(date --iso-8601=seconds)" "$RUST_BACKTRACE" "$WEBKIT_DISABLE_DMABUF_RENDERER" >>"$log_file"
  exit 0
fi

cd "$app_root"
set +e
/usr/bin/setsid "$binary" >>"$log_file" 2>&1 &
app_pid=$!
status=$?
set -e
printf '[%s] launch spawn status=%s pid=%s rust_backtrace=%s webkit_disable_dmabuf=%s\n' "$(date --iso-8601=seconds)" "$status" "${app_pid:-unknown}" "$RUST_BACKTRACE" "$WEBKIT_DISABLE_DMABUF_RENDERER" >>"$log_file"
exit "$status"
