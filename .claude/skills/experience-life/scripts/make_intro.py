#!/usr/bin/env python3
"""Build a REUSABLE animated opening title for the 体验XX人生 series.

Same branded look every episode, only the topic changes:
  - a reusable dramatic background (assets/intro_bg.jpg) with a slow Ken-Burns
    push-in + vignette,
  - three title lines that fade in in sequence:
        带你体验一百种人生
        今天，体验的人生是
        《<topic>》            (gold accent, larger)
  - narration: "带你体验一百种人生。今天，体验的人生是 <topic>。"

Outputs intro.mp4 (video + narration audio only — lay the shared music bed over
the whole film later with compose.py so it runs continuously).

Usage:
  python3 make_intro.py --topic "饱和潜水员的一生" \
      --bg assets/intro_bg.jpg --size 1024x768 --voice zh-CN-YunxiNeural \
      --out video_projects/<slug>/intro.mp4
"""
import argparse
import math
import os
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
TTS = os.path.join(HERE, "..", "..", "video-restyle", "scripts", "tts.py")


def dur_of(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nokey=1:noprint_wrappers=1", path])
    return float(out.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", required=True)
    ap.add_argument("--bg", default=os.path.join(HERE, "..", "assets", "intro_bg.jpg"))
    ap.add_argument("--size", default="1024x768")
    ap.add_argument("--voice", default="zh-CN-YunjianNeural")
    ap.add_argument("--rate", default="+0%")
    ap.add_argument("--pitch", default="-2Hz")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    w, h = (int(x) for x in args.size.lower().split("x"))
    workdir = tempfile.mkdtemp()

    # 1) narration for the opening
    vo_text = f"带你体验一百种人生。今天，体验的人生是，{args.topic}。"
    scriptf = os.path.join(workdir, "vo.txt")
    open(scriptf, "w", encoding="utf-8").write(vo_text)
    vo_base = os.path.join(workdir, "vo")
    # use --opt=value form so negative rate/pitch (e.g. -4%) aren't parsed as flags
    subprocess.run(["python3", TTS, "--script", scriptf, "--out", vo_base,
                    f"--voice={args.voice}", f"--rate={args.rate}",
                    f"--pitch={args.pitch}"], check=True)
    vo_mp3 = vo_base + ".mp3"
    vo = dur_of(vo_mp3)
    dur = max(vo + 1.0, 5.0)
    frames = math.ceil(dur * args.fps)

    # reveal timings tied to the narration
    t1, t2 = 0.3, max(1.6, vo * 0.42)
    t3 = max(t2 + 1.0, vo * 0.72)

    # 2) title text files (avoids shell escaping of CJK)
    def tf(name, text):
        p = os.path.join(workdir, name)
        open(p, "w", encoding="utf-8").write(text)
        return p
    l1 = tf("l1.txt", "带你体验一百种人生")
    l2 = tf("l2.txt", "今天，体验的人生是")
    l3 = tf("l3.txt", f"《{args.topic}》")

    f_small = max(20, int(w * 0.050))
    f_big = max(28, int(w * 0.072))

    def dt(textfile, size, color, ypos, t0, border="black@0.85"):
        return (f"drawtext=fontfile='{FONT}':textfile='{textfile}':"
                f"fontsize={size}:fontcolor={color}:borderw={max(3,size//14)}:"
                f"bordercolor={border}:shadowx=2:shadowy=2:shadowcolor=black@0.6:"
                f"x=(w-text_w)/2:y={ypos}:"
                f"alpha='clip((t-{t0})/0.7\\,0\\,1)'")

    vf = (
        f"scale={w*2}:{h*2},setsar=1,"
        f"zoompan=z='min(zoom+0.0009,1.22)':d={frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={args.fps},"
        f"eq=brightness=-0.10:saturation=0.92,vignette=PI/4.2,"
        + dt(l1, f_small, "white", f"{h}*0.28", t1) + ","
        + dt(l2, f_small, "white", f"{h}*0.42", t2) + ","
        + dt(l3, f_big, "0xFFD56B", f"{h}*0.55", t3) + ","
        f"format=yuv420p"
    )

    cmd = [
        "ffmpeg", "-hide_banner", "-y",
        "-loop", "1", "-t", f"{dur:.3f}", "-i", args.bg,
        "-i", vo_mp3,
        "-vf", vf,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(args.fps),
        "-preset", "medium", "-c:a", "aac", "-b:a", "192k",
        "-t", f"{dur:.3f}", args.out,
    ]
    subprocess.run(cmd, check=True)
    print(f"wrote {args.out} ({dur:.1f}s intro, vo {vo:.1f}s)")


if __name__ == "__main__":
    raise SystemExit(main())
