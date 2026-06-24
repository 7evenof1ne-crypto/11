#!/usr/bin/env bash
# Bootstrap deps for the experience-life skill.
# Idempotent: safe to run at the start of every (ephemeral) session.
#
# Installs: ffmpeg (apt), edge-tts + Pillow (pip).
# faster-whisper (pip) is optional — only needed to transcribe a reference
# video for style analysis; install on demand.
# Also patches certifi with the system CA so HTTPS through the sandbox proxy
# verifies (same fix as video-restyle).
set -euo pipefail
log() { printf '\033[36m[bootstrap]\033[0m %s\n' "$*"; }

if command -v ffmpeg >/dev/null 2>&1; then
  log "ffmpeg present"
else
  log "installing ffmpeg..."; sudo apt-get update -qq || true
  sudo apt-get install -y -qq ffmpeg
fi

need=()
python3 -c "import edge_tts" 2>/dev/null || need+=(edge-tts)
python3 -c "import PIL" 2>/dev/null || need+=(Pillow)
if [ "${#need[@]}" -gt 0 ]; then
  log "pip installing: ${need[*]}"
  pip install --break-system-packages -q "${need[@]}"
else
  log "edge-tts + Pillow already present"
fi

# certifi <- system CA (idempotent)
SYS_CA=/etc/ssl/certs/ca-certificates.crt
MARKER="# >>> experience-life: system CA appended >>>"
CERTIFI=$(python3 -c "import certifi; print(certifi.where())")
if grep -qF "$MARKER" "$CERTIFI" 2>/dev/null; then
  log "certifi already patched"
elif [ -f "$SYS_CA" ]; then
  [ -f "${CERTIFI}.orig" ] || cp "$CERTIFI" "${CERTIFI}.orig"
  { echo ""; echo "$MARKER"; cat "$SYS_CA"; } >> "$CERTIFI"
  log "appended system CA into certifi"
fi

# egress check: image gen + TTS
log "checking egress..."
check() {
  local name=$1 url=$2 code
  code=$(curl -s -m 12 -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo 000)
  if [ "$code" = "200" ] || [ "$code" = "400" ] || [ "$code" = "405" ]; then
    printf '  \033[32m✓\033[0m %-12s reachable (HTTP %s)\n' "$name" "$code"
  else
    printf '  \033[31m✗\033[0m %-12s HTTP %s — may be blocked by network policy\n' "$name" "$code"
  fi
}
check pollinations "https://image.pollinations.ai/prompt/test?width=64&height=64"
check edge-tts     "https://speech.platform.bing.com"
log "bootstrap done. If a host is blocked, recreate the web env with Full network access."
