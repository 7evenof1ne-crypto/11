#!/usr/bin/env python3
"""Generate per-scene slide images timed to a narration .srt, for a slideshow
that auto-switches in sync with the voiceover.

Each "scene" covers a span of subtitle cues and renders as one bright slide
(big emoji + 1-2 headline lines), 小魔/轻漫科普 style. Output:
  <outdir>/slide_01.png ...   one PNG per scene (matches --size)
  <outdir>/concat.txt         ffmpeg concat list with exact per-slide durations

Then feed concat.txt to assemble.py --concat to burn the running subtitles on
top, so the visuals change with the content while captions track the speech.

Scenes file (JSON): a list of objects, in order:
  [{"emoji": "🧅", "lines": ["切洋葱", "为什么会流泪？"],
    "bg": "#E74C3C", "end_cue": 2}, ...]
  - end_cue: 1-based index of the LAST srt cue this scene covers. A scene starts
    where the previous one ended (first scene starts at 0). The final scene's
    end is clamped to the last cue's end time.

Usage:
  python3 make_slides.py --srt narration.srt --scenes scenes.json \
      --size 1080x1920 --out slides/
"""
import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont

CJK_FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
EMOJI_STRIKE = 109  # NotoColorEmoji ships a single 109px bitmap strike


def parse_srt(path):
    cues = []
    blocks = open(path, encoding="utf-8").read().strip().split("\n\n")
    for b in blocks:
        ln = b.split("\n")
        if len(ln) < 2 or "-->" not in ln[1]:
            continue
        a, c = ln[1].split(" --> ")
        cues.append((to_sec(a), to_sec(c)))
    return cues


def to_sec(s):
    h, m, rest = s.strip().split(":")
    sec, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000


def render_emoji(emoji, target_h):
    """Render a (possibly multi-) emoji string to an RGBA image ~target_h tall."""
    if not emoji:
        return None
    try:
        font = ImageFont.truetype(EMOJI_FONT, EMOJI_STRIKE)
    except OSError:
        return None
    tmp = Image.new("RGBA", (EMOJI_STRIKE * len(emoji) + 40, EMOJI_STRIKE + 40),
                    (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    try:
        d.text((20, 20), emoji, font=font, embedded_color=True)
    except TypeError:  # very old Pillow without embedded_color
        d.text((20, 20), emoji, font=font)
    bbox = tmp.getbbox()
    if not bbox:
        return None
    cropped = tmp.crop(bbox)
    scale = target_h / cropped.height
    return cropped.resize((max(1, int(cropped.width * scale)), target_h),
                          Image.LANCZOS)


def lighten(hex_color, amt=0.18):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(int(c + (255 - c) * amt) for c in (r, g, b))


def draw_slide(scene, w, h, font_path):
    bg = scene.get("bg", "#E74C3C")
    base = tuple(int(bg.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    top = lighten(bg, 0.22)
    img = Image.new("RGB", (w, h), base)
    # soft vertical gradient (lighter at top) for a less flat, cartoon-y look
    grad = Image.new("RGB", (1, h))
    for y in range(h):
        t = (y / h) ** 1.3
        grad.putpixel((0, y), tuple(int(top[i] + (base[i] - top[i]) * t)
                                    for i in range(3)))
    img = grad.resize((w, h))
    d = ImageDraw.Draw(img)

    # emoji block, upper third
    emoji_h = int(h * 0.16)
    em = render_emoji(scene.get("emoji", ""), emoji_h)
    cy = int(h * 0.30)
    if em:
        img.paste(em, ((w - em.width) // 2, cy - em.height // 2), em)

    # headline lines, centered below the emoji.
    # auto-shrink font so the widest line fits within 90% of the width.
    lines = scene.get("lines", [])
    max_w = w * 0.90
    fsize = int(w * 0.115)
    while fsize > 24:
        font = ImageFont.truetype(font_path, fsize)
        stroke = max(3, fsize // 14)
        widest = max((d.textbbox((0, 0), ln, font=font, stroke_width=stroke)[2]
                      - d.textbbox((0, 0), ln, font=font, stroke_width=stroke)[0])
                     for ln in lines) if lines else 0
        if widest <= max_w:
            break
        fsize -= 4
    font = ImageFont.truetype(font_path, fsize)
    stroke = max(3, fsize // 14)
    line_gap = int(fsize * 0.28)
    heights = []
    for ln in lines:
        bb = d.textbbox((0, 0), ln, font=font, stroke_width=stroke)
        heights.append(bb[3] - bb[1])
    total = sum(heights) + line_gap * (len(lines) - 1)
    y = int(h * 0.44)
    for ln, lh in zip(lines, heights):
        bb = d.textbbox((0, 0), ln, font=font, stroke_width=stroke)
        tw = bb[2] - bb[0]
        x = (w - tw) // 2 - bb[0]
        d.text((x, y), ln, font=font, fill=(255, 255, 255),
               stroke_width=stroke, stroke_fill=(40, 20, 10))
        y += lh + line_gap
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--srt", required=True)
    ap.add_argument("--scenes", required=True, help="JSON list of scene specs")
    ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--out", required=True)
    ap.add_argument("--font", default=CJK_FONT)
    args = ap.parse_args()

    w, h = (int(x) for x in args.size.lower().split("x"))
    os.makedirs(args.out, exist_ok=True)
    cues = parse_srt(args.srt)
    scenes = json.load(open(args.scenes, encoding="utf-8"))
    end_audio = cues[-1][1]

    concat = []
    prev_end = 0.0
    for i, sc in enumerate(scenes, 1):
        end_cue = sc["end_cue"]
        scene_end = end_audio if i == len(scenes) else cues[end_cue - 1][1]
        dur = max(0.2, scene_end - prev_end)
        prev_end = scene_end
        png = os.path.join(args.out, f"slide_{i:02d}.png")
        draw_slide(sc, w, h, args.font).save(png)
        concat.append((os.path.abspath(png), dur))

    listpath = os.path.join(args.out, "concat.txt")
    with open(listpath, "w", encoding="utf-8") as f:
        for path, dur in concat:
            f.write(f"file '{path}'\n")
            f.write(f"duration {dur:.3f}\n")
        f.write(f"file '{concat[-1][0]}'\n")  # repeat last for concat demuxer
    print(f"wrote {len(concat)} slides + {listpath}")
    for i, (p, dur) in enumerate(concat, 1):
        print(f"  slide_{i:02d}  {dur:5.2f}s  {os.path.basename(p)}")


if __name__ == "__main__":
    raise SystemExit(main())
