#!/usr/bin/env bash
# Download a LOW-RES copy of the reference video and sample keyframes, so the
# agent can visually inspect the source's style (color, layout, captions, pace).
#
# Produces in <outdir>:
#   frames/frame_0001.jpg ...   one frame every N seconds
#   contact_sheet.jpg           tiled montage of frames (easy single-image view)
#
# Usage: sample_frames.sh <url> <outdir> [interval_seconds] [max_height]
set -euo pipefail
URL=${1:?usage: sample_frames.sh <url> <outdir> [interval=4] [max_height=360]}
OUT=${2:?missing outdir}
INTERVAL=${3:-4}
MAXH=${4:-360}

mkdir -p "$OUT/frames"
VID="$OUT/source_lowres.mp4"

if [ ! -f "$VID" ]; then
  echo "[frames] downloading low-res copy (<=${MAXH}p)..."
  yt-dlp -q --no-warnings \
    -f "bestvideo[height<=${MAXH}]+bestaudio/best[height<=${MAXH}]/best" \
    --merge-output-format mp4 -o "$VID" "$URL"
fi

echo "[frames] sampling 1 frame / ${INTERVAL}s..."
ffmpeg -hide_banner -loglevel error -y -i "$VID" \
  -vf "fps=1/${INTERVAL},scale=-2:${MAXH}" \
  "$OUT/frames/frame_%04d.jpg"

# contact sheet (tile up to 4x4 = 16 frames)
echo "[frames] building contact sheet..."
ffmpeg -hide_banner -loglevel error -y -i "$VID" \
  -vf "fps=1/${INTERVAL},scale=320:-2,tile=4x4" -frames:v 1 \
  "$OUT/contact_sheet.jpg" 2>/dev/null || true

N=$(find "$OUT/frames" -name 'frame_*.jpg' | wc -l | tr -d ' ')
echo "[frames] done: $N frames in $OUT/frames , contact_sheet.jpg"
