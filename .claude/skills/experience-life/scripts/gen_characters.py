#!/usr/bin/env python3
"""Generate an approval / reference sheet for each locked character in a
character bible, so a personal account can reuse a CONSISTENT cast across
videos.

Consistency strategy (best achievable with a free text-to-image endpoint):
  1. Each character has a LOCKED, highly specific appearance fragment that is
     reused verbatim in every prompt.
  2. Each character has a LOCKED seed, so the same description renders the same
     face.
  3. The shared STYLE string is identical across all renders.

This script renders a few angles/expressions per character at the locked seed,
tiled into one sheet you can eyeball + approve. Once approved, episodes call
gen_images.py with --characters and reference a character by "char": "<id>"
(and/or @<id> tokens in the prompt) to pin the look.

characters.json schema:
  { "<id>": { "name": "...", "seed": 123,
              "appearance": "a Chinese man in his early thirties, oval face, ..." },
    ... }

Usage:
  python3 gen_characters.py --characters characters.json \
      --style "<shared style>" --size 640x640 --out characters/
"""
import argparse
import json
import os
import subprocess
import urllib.parse
import urllib.request
import time

POLLINATIONS = "https://image.pollinations.ai/prompt/"

# (label, prompt-fragment) rendered per character to show the look from angles.
POSES = [
    ("front",   "front-facing head and shoulders portrait, neutral calm expression, plain studio background"),
    ("threeq",  "three-quarter view portrait, faint smile, plain studio background"),
    ("profile", "side profile portrait, looking into the distance, plain studio background"),
    ("body",    "full body standing reference, plain neutral clothes, plain studio background"),
]


def fetch(prompt, w, h, seed, out_path, tries=4):
    url = (POLLINATIONS + urllib.parse.quote(prompt)
           + f"?width={w}&height={h}&seed={seed}&nologo=true&model=flux&enhance=true")
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            if len(data) > 3000 and data[:2] == b"\xff\xd8":
                open(out_path, "wb").write(data)
                return True
            last = f"bad response ({len(data)}b)"
        except Exception as e:  # noqa: BLE001
            last = str(e)
        time.sleep(2 * (i + 1))
    print(f"  ! failed {os.path.basename(out_path)}: {last}")
    return False


def tile(paths, out):
    """Stitch the pose renders into a single horizontal reference strip."""
    inputs = []
    for p in paths:
        inputs += ["-i", p]
    n = len(paths)
    fc = "".join(f"[{i}:v]" for i in range(n)) + f"hstack=inputs={n}"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs,
                    "-filter_complex", fc, "-frames:v", "1", out], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--characters", required=True)
    ap.add_argument("--style", required=True)
    ap.add_argument("--size", default="640x640")
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default=None, help="only this character id")
    args = ap.parse_args()

    w, h = (int(x) for x in args.size.lower().split("x"))
    os.makedirs(args.out, exist_ok=True)
    chars = json.load(open(args.characters, encoding="utf-8"))

    for cid, c in chars.items():
        if args.only and cid != args.only:
            continue
        print(f"== {cid} ({c.get('name','')}) seed={c['seed']} ==")
        pose_paths = []
        for label, pose in POSES:
            prompt = f"{args.style}. Character reference: {c['appearance']}. {pose}"
            out = os.path.join(args.out, f"{cid}_{label}.jpg")
            if fetch(prompt, w, h, c["seed"], out):
                pose_paths.append(out)
                print(f"   {label} ok")
        if pose_paths:
            sheet = os.path.join(args.out, f"{cid}_sheet.jpg")
            tile(pose_paths, sheet)
            # canonical portrait = the front pose
            print(f"   sheet -> {sheet}")
    print("done.")


if __name__ == "__main__":
    raise SystemExit(main())
