#!/usr/bin/env python3
"""Generate one illustration per scene, timed to a narration .srt, for the
"体验XX人生 / experience a life" explainer format.

Images come from Pollinations (https://pollinations.ai) — a free, no-API-key
text-to-image endpoint. Each scene's prompt is prefixed with a shared STYLE so
all frames look like one consistent hand-drawn cartoon set, and a fixed --seed
keeps the character/style stable across scenes.

Scenes file (JSON): a list, in story order:
  [{"prompt": "a tired young woman looking at a laptop in a small rented room",
    "end_cue": 3},
   {"prompt": "...", "end_cue": 6}, ...]
  - end_cue: 1-based index of the LAST srt cue this image covers. A scene starts
    where the previous ended (first starts at 0); the last clamps to audio end.

Outputs into <outdir>:
  img_01.jpg ...     one illustration per scene (matches --size)
  concat.txt         ffmpeg concat list with exact per-image durations
Feed concat.txt to assemble.py --concat to burn the narration subtitles on top.

Usage:
  python3 gen_images.py --srt narration.srt --scenes scenes.json \
      --style "flat hand-drawn cartoon, muted desaturated palette, ..." \
      --seed 12345 --size 1024x768 --out imgs/
"""
import argparse
import json
import os
import time
import urllib.parse
import urllib.request

POLLINATIONS = "https://image.pollinations.ai/prompt/"
DEFAULT_STYLE = (
    "flat hand-drawn cartoon illustration, Chinese webtoon style, "
    "muted desaturated color palette, soft cel shading, clean bold outlines, "
    "simple backgrounds, cinematic lighting, emotional storytelling, "
    "single consistent character"
)


def to_sec(s):
    h, m, rest = s.strip().split(":")
    sec, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000


def parse_srt(path):
    cues = []
    for b in open(path, encoding="utf-8").read().strip().split("\n\n"):
        ln = b.split("\n")
        if len(ln) >= 2 and "-->" in ln[1]:
            a, c = ln[1].split(" --> ")
            cues.append((to_sec(a), to_sec(c)))
    return cues


def fetch(prompt, w, h, seed, out_path, tries=4):
    url = (POLLINATIONS + urllib.parse.quote(prompt)
           + f"?width={w}&height={h}&seed={seed}&nologo=true&model=flux&enhance=true")
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            if len(data) > 3000 and data[:2] == b"\xff\xd8":  # looks like JPEG
                with open(out_path, "wb") as f:
                    f.write(data)
                return True
            last = f"short/non-jpeg response ({len(data)} bytes)"
        except Exception as e:  # noqa: BLE001
            last = str(e)
        time.sleep(2 * (i + 1))
    print(f"  ! failed: {os.path.basename(out_path)} :: {last}")
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--srt", required=True)
    ap.add_argument("--scenes", required=True)
    ap.add_argument("--style", default=DEFAULT_STYLE)
    ap.add_argument("--characters", default=None,
                    help="character bible JSON; scenes may set \"char\":\"<id>\" "
                         "to pin that character's locked seed, and use @<id> "
                         "tokens in the prompt to inject its locked appearance")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--size", default="1024x768")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    w, h = (int(x) for x in args.size.lower().split("x"))
    os.makedirs(args.out, exist_ok=True)
    cues = parse_srt(args.srt)
    scenes = json.load(open(args.scenes, encoding="utf-8"))
    chars = json.load(open(args.characters, encoding="utf-8")) if args.characters else {}
    end_audio = cues[-1][1]

    concat, prev_end = [], 0.0
    for i, sc in enumerate(scenes, 1):
        scene_end = end_audio if i == len(scenes) else cues[sc["end_cue"] - 1][1]
        dur = max(0.3, scene_end - prev_end)
        prev_end = scene_end
        out = os.path.join(args.out, f"img_{i:02d}.jpg")

        # inject any @<id> character tokens with their locked appearance
        scene_text = sc["prompt"]
        for cid, c in chars.items():
            if f"@{cid}" in scene_text:
                scene_text = scene_text.replace(
                    f"@{cid}", f"the recurring character {c['name']} "
                    f"(always the same person: {c['appearance']})")

        # a scene's primary character pins the seed (face stays locked across
        # the whole account); otherwise vary the seed per scene for variety.
        # "seed_offset" re-rolls a single bad/broken frame without touching the
        # appearance lock or any other scene (deterministic, so good frames
        # stay byte-identical on re-run).
        primary = sc.get("char")
        if primary and primary in chars:
            seed = chars[primary]["seed"] + int(sc.get("seed_offset", 0))
            if f"@{primary}" not in sc["prompt"]:  # ensure the lead is described
                scene_text = (f"main character {chars[primary]['name']} "
                              f"({chars[primary]['appearance']}). " + scene_text)
        else:
            seed = args.seed + i + int(sc.get("seed_offset", 0))

        prompt = f"{args.style}. Scene: {scene_text}"
        ok = fetch(prompt, w, h, seed, out)
        print(f"  img_{i:02d}  {dur:5.2f}s  {'ok' if ok else 'MISSING'}  {sc['prompt'][:50]}")
        if ok:
            concat.append((os.path.abspath(out), dur))
        elif concat:  # reuse previous image so timing/audio stays aligned
            concat.append((concat[-1][0], dur))

    listpath = os.path.join(args.out, "concat.txt")
    with open(listpath, "w", encoding="utf-8") as f:
        for path, dur in concat:
            f.write(f"file '{path}'\nduration {dur:.3f}\n")
        f.write(f"file '{concat[-1][0]}'\n")
    print(f"wrote {len(concat)} images + {listpath}")


if __name__ == "__main__":
    raise SystemExit(main())
