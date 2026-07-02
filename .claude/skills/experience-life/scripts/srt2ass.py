#!/usr/bin/env python3
"""Convert a narration .srt into a modern animated .ass subtitle track.

Body cues: bold white text with a soft dark glow (blurred border, no hard
1990s outline), each line fades in with a subtle pop (96%->100% scale).
Chapter cues (text starting with "Level"): rendered as a golden chapter
stinger — larger, screen-centered, stronger pop + glow.

Usage:
  python3 srt2ass.py --srt narration.srt --size 1024x768 --out narration.ass
"""
import argparse
import re

FONT = "WenQuanYi Zen Hei"


def t2ass(s):
    h, m, rest = s.strip().split(":")
    sec, ms = rest.split(",")
    cs = int(ms) // 10
    return f"{int(h)}:{int(m):02d}:{int(sec):02d}.{cs:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--srt", required=True)
    ap.add_argument("--size", default="1024x768")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    w, h = (int(x) for x in args.size.lower().split("x"))
    fs = max(26, int(h * 0.058))       # body font size
    fs_ch = int(fs * 1.7)              # chapter stinger size
    margin_v = int(h * 0.055)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
ScaledBorderAndShadow: yes
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Body,{FONT},{fs},&H00FFFFFF,&H00FFFFFF,&H00101010,&H96000000,-1,0,0,0,100,100,1,0,1,3,0,2,40,40,{margin_v},1
Style: Chapter,{FONT},{fs_ch},&H006BD5FF,&H00FFFFFF,&H00081018,&H96000000,-1,0,0,0,100,100,2,0,1,4,0,5,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    body_fx = r"{\fad(140,110)\blur4\fscx96\fscy96\t(0,130,\fscx100\fscy100)}"
    chap_fx = (r"{\fad(160,160)\blur6\fscx70\fscy70"
               r"\t(0,220,\fscx104\fscy104)\t(220,340,\fscx100\fscy100)}")

    lines = []
    for block in open(args.srt, encoding="utf-8").read().strip().split("\n\n"):
        ln = block.split("\n")
        if len(ln) < 2 or "-->" not in ln[1]:
            continue
        a, b = (t2ass(x) for x in ln[1].split(" --> "))
        text = " ".join(ln[2:]).strip().replace("\n", r"\N")
        if re.match(r"^\s*Level\s*\d", text, re.I):
            lines.append(f"Dialogue: 0,{a},{b},Chapter,,0,0,0,,{chap_fx}{text}")
        else:
            lines.append(f"Dialogue: 0,{a},{b},Body,,0,0,0,,{body_fx}{text}")

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(lines) + "\n")
    print(f"wrote {args.out} ({len(lines)} events, body fs={fs}, chapter fs={fs_ch})")


if __name__ == "__main__":
    raise SystemExit(main())
