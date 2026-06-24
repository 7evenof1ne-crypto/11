#!/usr/bin/env python3
"""Synthesize a royalty-free, reusable TENSE background-music bed with ffmpeg
(no samples, no downloads — generated from oscillators, so it's free to reuse).

The bed layers:
  - a low detuned drone (unease),
  - a slow swell on the drone (apulsator),
  - a rhythmic sub-bass throb (heartbeat-like tension),
  - a decaying "tick" every half second (suspense clock, ~120 bpm),
  - a faint airy hiss (tension shimmer).
Then it's loudness-limited and given fade in/out. Loop it under a video.

Usage:
  python3 make_music.py --duration 60 --out assets/bgm_tense.mp3
"""
import argparse
import subprocess


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration", type=float, default=60.0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--bpm", type=float, default=120.0, help="tick tempo")
    args = ap.parse_args()

    d = args.duration
    beat = 60.0 / args.bpm  # seconds between ticks
    sr = 44100

    inputs = [
        ("sine", f"sine=frequency=55:sample_rate={sr}:duration={d}"),
        ("sine", f"sine=frequency=82.5:sample_rate={sr}:duration={d}"),
        ("sine", f"sine=frequency=50:sample_rate={sr}:duration={d}"),
        ("anoisesrc", f"anoisesrc=color=pink:sample_rate={sr}:duration={d}:amplitude=0.3"),
        # decaying ping every `beat` seconds -> suspense clock / heartbeat
        ("aevalsrc",
         f"aevalsrc=sin(2*PI*1320*t)*exp(-28*mod(t\\,{beat:.4f})):s={sr}:d={d}"),
    ]
    cmd = ["ffmpeg", "-hide_banner", "-y"]
    for _, src in inputs:
        cmd += ["-f", "lavfi", "-i", src]

    fc = (
        "[0:a][1:a]amix=inputs=2:weights=1 0.6:normalize=0[dr0];"
        "[dr0]volume=0.32,apulsator=hz=0.18:amount=0.5[drone];"
        "[2:a]apulsator=hz=1.9:amount=0.9,volume=0.34[throb];"
        "[3:a]highpass=f=2600,volume=0.05[air];"
        "[4:a]volume=0.20[tick];"
        "[drone][throb][air][tick]amix=inputs=4:normalize=0[mix];"
        f"[mix]loudnorm=I=-18:TP=-2,afade=t=in:st=0:d=2,"
        f"afade=t=out:st={d-2:.2f}:d=2[out]"
    )
    cmd += ["-filter_complex", fc, "-map", "[out]",
            "-c:a", "libmp3lame", "-b:a", "160k", args.out]
    subprocess.run(cmd, check=True)
    print(f"wrote {args.out} ({d:.0f}s tense bed)")


if __name__ == "__main__":
    raise SystemExit(main())
