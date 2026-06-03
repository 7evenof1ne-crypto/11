#!/usr/bin/env bash
# Bootstrap dependencies for the video-restyle skill.
# Idempotent: safe to run at the start of every (ephemeral) session.
#
# Installs: ffmpeg (apt), yt-dlp + edge-tts (pip).
# Fixes the TLS-inspection CA issue: the sandbox egress proxy re-signs HTTPS
# with "Anthropic ... TLS Inspection CA", which lives in the system CA store
# but NOT in Python's bundled certifi. We append the system bundle into
# certifi so yt-dlp / edge-tts can verify the proxy-presented certs.
set -euo pipefail

log() { printf '\033[36m[bootstrap]\033[0m %s\n' "$*"; }

# --- ffmpeg -----------------------------------------------------------------
if command -v ffmpeg >/dev/null 2>&1; then
  log "ffmpeg present: $(ffmpeg -version | head -1)"
else
  log "installing ffmpeg via apt..."
  sudo apt-get update -qq || true
  sudo apt-get install -y -qq ffmpeg
fi

# --- python tools -----------------------------------------------------------
need_pip=()
python3 -c "import yt_dlp" 2>/dev/null || need_pip+=(yt-dlp)
python3 -c "import edge_tts" 2>/dev/null || need_pip+=(edge-tts)
if [ "${#need_pip[@]}" -gt 0 ]; then
  log "pip installing: ${need_pip[*]}"
  pip install --break-system-packages -q "${need_pip[@]}"
else
  log "yt-dlp + edge-tts already importable"
fi

# --- certifi <- system CA (idempotent) --------------------------------------
SYS_CA=/etc/ssl/certs/ca-certificates.crt
MARKER="# >>> video-restyle: system CA appended >>>"
CERTIFI=$(python3 -c "import certifi; print(certifi.where())")
if grep -qF "$MARKER" "$CERTIFI" 2>/dev/null; then
  log "certifi already patched with system CA"
elif [ -f "$SYS_CA" ]; then
  [ -f "${CERTIFI}.orig" ] || cp "$CERTIFI" "${CERTIFI}.orig"
  { echo ""; echo "$MARKER"; cat "$SYS_CA"; } >> "$CERTIFI"
  log "appended system CA into certifi ($CERTIFI)"
else
  log "WARN: system CA bundle not found at $SYS_CA"
fi

# --- egress sanity check ----------------------------------------------------
log "checking egress to YouTube + TTS endpoint..."
check() {
  local name=$1 url=$2
  local code reason
  code=$(curl -s -m 8 -o /dev/null -w "%{http_code}" -D /tmp/_vh "$url" 2>/dev/null || echo 000)
  reason=$(grep -i '^x-deny-reason' /tmp/_vh 2>/dev/null | tr -d '\r' || true)
  if [ "$code" = "403" ] && [ -n "$reason" ]; then
    printf '  \033[31m✗\033[0m %-10s blocked by egress policy (%s)\n' "$name" "${reason#*: }"
    return 1
  else
    printf '  \033[32m✓\033[0m %-10s reachable (HTTP %s)\n' "$name" "$code"
  fi
}
ok=0
check youtube https://www.youtube.com/youtubei/v1/player || ok=1
check tts      https://speech.platform.bing.com || ok=1
if [ "$ok" -ne 0 ]; then
  cat <<'EOF'

  ──────────────────────────────────────────────────────────────────────
  Network policy blocks the sources this skill needs (x-deny-reason:
  host_not_allowed). yt-dlp/edge-tts are installed and TLS is fixed, but
  they cannot reach YouTube / the TTS endpoint from this environment.

  Fix (user action): recreate the Claude-Code-on-the-web environment with
  "Full network access", or a custom allowlist including:
    youtube.com, *.youtube.com, *.googlevideo.com,
    youtubei.googleapis.com, i.ytimg.com, speech.platform.bing.com
  Docs: https://code.claude.com/docs/en/claude-code-on-the-web
  ──────────────────────────────────────────────────────────────────────
EOF
fi
rm -f /tmp/_vh
log "bootstrap done."
