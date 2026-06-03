#!/usr/bin/env python3
"""Fetch style-reference material from a YouTube (or other yt-dlp supported) URL.

Outputs into <outdir>:
  metadata.json   - title, uploader, duration, chapters, tags, description, ...
  transcript.txt  - cleaned plain-text transcript (from subtitles, if available)
  transcript.srt  - raw subtitle file (timing kept), if available

This does NOT download the video itself (use sample_frames.sh for visuals).

Usage:
  python3 fetch_reference.py <url> <outdir> [--lang en]
"""
import argparse
import json
import os
import re
import sys


def clean_vtt(text: str) -> str:
    """Turn a .vtt/.srt blob into deduplicated plain prose."""
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.upper().startswith("WEBVTT"):
            continue
        if line.isdigit():
            continue
        if "-->" in line:
            continue
        # strip inline tags like <00:00:01.000><c> ... </c>
        line = re.sub(r"<[^>]+>", "", line)
        line = line.strip()
        if not line:
            continue
        if lines and lines[-1] == line:  # dedup consecutive repeats (auto-caps)
            continue
        lines.append(line)
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("outdir")
    ap.add_argument("--lang", default=None,
                    help="preferred subtitle language (default: original / first available)")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    try:
        import yt_dlp
    except ImportError:
        print("yt-dlp not installed. Run scripts/bootstrap.sh first.", file=sys.stderr)
        return 2

    sub_langs = [args.lang] if args.lang else ["en", "zh-Hans", "zh", "zh-CN"]
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": sub_langs + ["all"],
        "subtitlesformat": "vtt",
        "outtmpl": os.path.join(args.outdir, "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": False,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(args.url, download=True)  # download=subs only

    keep = {k: info.get(k) for k in (
        "id", "title", "uploader", "channel", "duration", "duration_string",
        "view_count", "like_count", "upload_date", "categories", "tags",
        "chapters", "description", "webpage_url", "language",
    )}
    with open(os.path.join(args.outdir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(keep, f, ensure_ascii=False, indent=2)

    # locate a downloaded subtitle file
    vid = info.get("id", "")
    sub_file = None
    for fn in sorted(os.listdir(args.outdir)):
        if fn.startswith(vid) and fn.endswith(".vtt"):
            sub_file = os.path.join(args.outdir, fn)
            # prefer preferred lang if multiple
            if args.lang and f".{args.lang}." in fn:
                break
    if sub_file:
        with open(sub_file, encoding="utf-8") as f:
            raw = f.read()
        with open(os.path.join(args.outdir, "transcript.txt"), "w", encoding="utf-8") as f:
            f.write(clean_vtt(raw))
        os.replace(sub_file, os.path.join(args.outdir, "transcript.vtt"))
        print(f"transcript saved ({len(raw)} bytes raw)")
    else:
        print("WARNING: no subtitles available for this video.", file=sys.stderr)
        print("  -> consider transcribing the audio (sample_frames.sh can grab it).",
              file=sys.stderr)

    print(f"title   : {keep.get('title')}")
    print(f"uploader: {keep.get('uploader')}")
    print(f"duration: {keep.get('duration_string')}")
    print(f"chapters: {len(keep.get('chapters') or [])}")
    print(f"output  : {args.outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
