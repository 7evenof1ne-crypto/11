#!/usr/bin/env python3
"""Assemble a narration video from: audio + (optional) subtitles + visuals.

Visual modes (auto-picked):
  - if --images DIR has images -> timed slideshow across them
  - else                       -> solid color background

Subtitles, if given, are burned in. Output is H.264/AAC mp4.

Usage:
  python3 assemble.py --audio narration.mp3 --srt narration.srt \
      --images frames/ --size 1920x1080 --out final.mp4
  python3 assemble.py --audio narration.mp3 --srt narration.srt \
      --size 1080x1920 --bg 0x111827 --out final_vertical.mp4
"""
import argparse
import glob
import os
import shlex
import subprocess
import sys
import tempfile

IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".bmp")


def ffprobe_duration(path: str) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nokey=1:noprint_wrappers=1", path,
    ])
    return float(out.strip())


def run(cmd):
    print("+ " + " ".join(shlex.quote(c) for c in cmd))
    subprocess.run(cmd, check=True)


def esc_sub(path: str) -> str:
    # escape for the subtitles= filter (colons, backslashes, quotes)
    p = os.path.abspath(path)
    p = p.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--srt", default=None)
    ap.add_argument("--images", default=None, help="folder of images for a slideshow")
    ap.add_argument("--size", default="1920x1080", help="WxH, e.g. 1080x1920 for vertical")
    ap.add_argument("--bg", default="0x0f172a", help="bg color when no images")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    w, h = (int(x) for x in args.size.lower().split("x"))
    dur = ffprobe_duration(args.audio)

    images = []
    if args.images and os.path.isdir(args.images):
        for f in sorted(glob.glob(os.path.join(args.images, "*"))):
            if f.lower().endswith(IMG_EXT):
                images.append(f)

    sub_filter = ""
    if args.srt and os.path.exists(args.srt) and os.path.getsize(args.srt) > 0:
        style = ("FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
                 "BorderStyle=1,Outline=2,Shadow=1,MarginV=60,Alignment=2")
        sub_filter = f",subtitles='{esc_sub(args.srt)}':force_style='{style}'"

    scale_pad = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                 f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color={args.bg},setsar=1")

    if images:
        per = max(dur / len(images), 0.5)
        listfile = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
        for img in images:
            listfile.write(f"file '{os.path.abspath(img)}'\n")
            listfile.write(f"duration {per:.3f}\n")
        listfile.write(f"file '{os.path.abspath(images[-1])}'\n")  # last frame repeat
        listfile.close()
        vf = f"{scale_pad},fps={args.fps}{sub_filter}"
        cmd = [
            "ffmpeg", "-hide_banner", "-y",
            "-f", "concat", "-safe", "0", "-i", listfile.name,
            "-i", args.audio,
            "-vf", vf,
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium",
            "-c:a", "aac", "-b:a", "192k", "-shortest", args.out,
        ]
        run(cmd)
        os.unlink(listfile.name)
    else:
        vf = f"fps={args.fps}{sub_filter}" if sub_filter else f"fps={args.fps}"
        cmd = [
            "ffmpeg", "-hide_banner", "-y",
            "-f", "lavfi", "-i", f"color=c={args.bg}:s={w}x{h}:d={dur:.3f}",
            "-i", args.audio,
            "-vf", vf,
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium",
            "-c:a", "aac", "-b:a", "192k", "-shortest", args.out,
        ]
        run(cmd)

    print(f"\n✓ wrote {args.out} ({os.path.getsize(args.out)} bytes, ~{dur:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
