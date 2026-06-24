#!/usr/bin/env python3
"""Final assembly: concatenate clips (e.g. intro + main) and lay one continuous
reusable music bed under the whole film, ducked by the narration.

- Clips are normalized to a common size/fps so concat is safe.
- The music loops to cover the full duration, is lowered in level, faded in/out,
  and side-chain-ducked by the narration (it swells in silences like the intro
  and dips under speech).

Usage:
  python3 compose.py --clips intro.mp4 main.mp4 --music assets/bgm_tense.mp3 \
      --size 1024x768 --out final_full.mp4
"""
import argparse
import subprocess


def dur_of(path):
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nokey=1:noprint_wrappers=1", path]).strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", nargs="+", required=True, help="ordered video clips")
    ap.add_argument("--music", default=None, help="music bed (looped under all)")
    ap.add_argument("--music-vol", type=float, default=0.55)
    ap.add_argument("--size", default="1024x768")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    w, h = (int(x) for x in args.size.lower().split("x"))
    total = sum(dur_of(c) for c in args.clips)
    n = len(args.clips)

    cmd = ["ffmpeg", "-hide_banner", "-y"]
    for c in args.clips:
        cmd += ["-i", c]
    if args.music:
        cmd += ["-stream_loop", "-1", "-i", args.music]

    parts = []
    for i in range(n):
        parts.append(
            f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=decrease,"
            f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={args.fps},"
            f"format=yuv420p[v{i}];")
    concat_in = "".join(f"[v{i}][{i}:a]" for i in range(n))
    parts.append(f"{concat_in}concat=n={n}:v=1:a=1[v][na];")

    if args.music:
        m = n  # music input index
        parts.append(
            # one copy of the narration drives the mix, one keys the ducking
            "[na]asplit=2[na_mix][na_key];"
            f"[{m}:a]volume={args.music_vol},"
            f"afade=t=in:st=0:d=2,afade=t=out:st={max(0,total-3):.2f}:d=3[musraw];"
            # narration ducks the music
            f"[musraw][na_key]sidechaincompress=threshold=0.03:ratio=6:attack=5:"
            f"release=350[mus];"
            f"[na_mix][mus]amix=inputs=2:normalize=0:duration=first[outa]")
        amap = "[outa]"
    else:
        amap = "[na]"

    fc = "".join(parts).rstrip(";")
    cmd += ["-filter_complex", fc, "-map", "[v]", "-map", amap,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium",
            "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}", args.out]
    subprocess.run(cmd, check=True)
    print(f"wrote {args.out} ({total:.1f}s, {n} clips"
          + (", with music bed" if args.music else "") + ")")


if __name__ == "__main__":
    raise SystemExit(main())
