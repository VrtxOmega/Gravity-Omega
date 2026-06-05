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
binary_source_commit_epoch="$(git -C "$app_root" log -1 --format=%ct -- package.json package-lock.json web src-tauri 2>/dev/null || true)"
binary_source_commit_iso=""
if [[ -n "$binary_source_commit_epoch" ]]; then
  binary_source_commit_iso="$(date --date="@$binary_source_commit_epoch" --iso-8601=seconds 2>/dev/null || true)"
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
  printf 'binary_source_commit_time=%s\n' "${binary_source_commit_iso:-unknown}"
  printf 'binary_mtime=%s\n' "${binary_mtime_iso:-missing}"
} >>"$log_file"

if [[ ! -x "$binary" ]]; then
  printf '[%s] launch failed: release binary missing or not executable\n' "$(date --iso-8601=seconds)" >>"$log_file"
  exit 1
fi

if [[ -n "$binary_source_commit_epoch" && -n "$binary_mtime_epoch" && "$binary_mtime_epoch" -lt "$binary_source_commit_epoch" ]]; then
  printf '[%s] launch blocked: release binary is older than app source inputs; run npm run build before launching. Set GRAVITY_OMEGA_ALLOW_STALE_BINARY=1 only for deliberate stale-artifact diagnostics.\n' "$(date --iso-8601=seconds)" >>"$log_file"
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
export WEBKIT_DISABLE_COMPOSITING_MODE="${WEBKIT_DISABLE_COMPOSITING_MODE:-1}"
export GSK_RENDERER="${GSK_RENDERER:-cairo}"
export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
render_profile="${GRAVITY_OMEGA_RENDER_PROFILE:-x11-safe}"
case "$render_profile" in
  x11-safe)
    if [[ -n "${DISPLAY:-}" ]]; then
      export GDK_BACKEND="${GRAVITY_OMEGA_GDK_BACKEND:-x11}"
    else
      export GDK_BACKEND="${GRAVITY_OMEGA_GDK_BACKEND:-wayland}"
    fi
    ;;
  inherited)
    export GDK_BACKEND="${GRAVITY_OMEGA_GDK_BACKEND:-${GDK_BACKEND:-}}"
    ;;
  *)
    printf '[%s] launch failed: unknown GRAVITY_OMEGA_RENDER_PROFILE=%s; expected x11-safe or inherited\n' "$(date --iso-8601=seconds)" "$render_profile" >>"$log_file"
    exit 3
    ;;
esac
export G_MESSAGES_DEBUG="${G_MESSAGES_DEBUG:-}"

{
  printf 'render_profile=%s\n' "$render_profile"
  printf 'gdk_backend=%s\n' "${GDK_BACKEND:-unset}"
  printf 'display=%s\n' "${DISPLAY:-unset}"
  printf 'wayland_display=%s\n' "${WAYLAND_DISPLAY:-unset}"
  printf 'webkit_disable_compositing=%s\n' "$WEBKIT_DISABLE_COMPOSITING_MODE"
  printf 'gsk_renderer=%s\n' "$GSK_RENDERER"
  printf 'libgl_always_software=%s\n' "$LIBGL_ALWAYS_SOFTWARE"
} >>"$log_file"

if [[ "${GRAVITY_OMEGA_LAUNCHER_DRY_RUN:-0}" == "1" ]]; then
  printf '[%s] launch dry-run passed: binary is current and launch environment is ready rust_backtrace=%s webkit_disable_dmabuf=%s gdk_backend=%s render_profile=%s\n' "$(date --iso-8601=seconds)" "$RUST_BACKTRACE" "$WEBKIT_DISABLE_DMABUF_RENDERER" "${GDK_BACKEND:-unset}" "$render_profile" >>"$log_file"
  exit 0
fi

cd "$app_root"
set +e
/usr/bin/setsid "$binary" >>"$log_file" 2>&1 &
app_pid=$!
status=$?
set -e
printf '[%s] launch spawn status=%s pid=%s rust_backtrace=%s webkit_disable_dmabuf=%s gdk_backend=%s render_profile=%s\n' "$(date --iso-8601=seconds)" "$status" "${app_pid:-unknown}" "$RUST_BACKTRACE" "$WEBKIT_DISABLE_DMABUF_RENDERER" "${GDK_BACKEND:-unset}" "$render_profile" >>"$log_file"
exit "$status"
