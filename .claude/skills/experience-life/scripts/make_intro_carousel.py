#!/usr/bin/env python3
"""REUSABLE rapid-carousel opening for the 体验XX人生 series.

A stack of episode "life covers" flicks past with a whoosh on every cut —
like spinning a wheel of a hundred lives — then SLAMS onto this episode's
cover (impact hit), where the golden title and the catchphrase narration land:

    带你体验一百种人生。今天，体验的人生是，《<topic>》。

All sounds are synthesized locally (no samples): whoosh = band-passed noise
burst, impact = decaying low sine + click. Covers live in assets/covers/ and
are reused across episodes; per episode you only change --topic and
--final-cover.

Usage:
  python3 make_intro_carousel.py --topic "饱和潜水员的一生" \
      --final-cover .claude/skills/experience-life/assets/covers/diver.jpg \
      --covers-dir  .claude/skills/experience-life/assets/covers \
      --size 1024x768 --out video_projects/<slug>/intro.mp4
"""
import argparse
import glob
import math
import os
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
TTS = os.path.join(HERE, "..", "..", "video-restyle", "scripts", "tts.py")


def run(cmd):
    subprocess.run(cmd, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def dur_of(path):
    return float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nokey=1:noprint_wrappers=1", path]).strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", required=True)
    ap.add_argument("--final-cover", required=True,
                    help="this episode's cover (the carousel lands on it)")
    ap.add_argument("--covers-dir",
                    default=os.path.join(HERE, "..", "assets", "covers"))
    ap.add_argument("--size", default="1024x768")
    ap.add_argument("--cut", type=float, default=0.40,
                    help="seconds each carousel cover is shown")
    ap.add_argument("--voice", default="zh-CN-YunxiNeural")
    ap.add_argument("--rate", default="+2%")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    w, h = (int(x) for x in args.size.lower().split("x"))
    fps, cut = args.fps, args.cut
    tmp = tempfile.mkdtemp()

    # --- narration (series-standard voice) --------------------------------
    vo_txt = os.path.join(tmp, "vo.txt")
    open(vo_txt, "w", encoding="utf-8").write(
        f"带你体验一百种人生。今天，体验的人生是，{args.topic}。")
    subprocess.run(["python3", TTS, "--script", vo_txt,
                    "--out", os.path.join(tmp, "vo"),
                    f"--voice={args.voice}", f"--rate={args.rate}"], check=True)
    vo = os.path.join(tmp, "vo.mp3")
    vo_d = dur_of(vo)

    # --- carousel covers (final cover excluded from the flicker) ----------
    fc = os.path.abspath(args.final_cover)
    covers = [f for f in sorted(glob.glob(os.path.join(args.covers_dir, "*.jpg")))
              if os.path.abspath(f) != fc][:9]
    n = len(covers)
    if n < 3:
        raise SystemExit("need at least 3 covers in --covers-dir")

    t_land = n * cut                      # when the carousel slams onto the topic
    total = max(vo_d + 0.9, t_land + 3.0)
    land_d = total - t_land

    # --- synthesized switching sounds --------------------------------------
    whoosh = os.path.join(tmp, "whoosh.wav")
    run(["ffmpeg", "-y", "-f", "lavfi",
         "-i", "anoisesrc=color=white:sample_rate=44100:duration=0.30",
         "-af", "bandpass=f=900:width_type=o:w=1.2,"
                "afade=t=in:st=0:d=0.03,afade=t=out:st=0.08:d=0.22,volume=1.4",
         whoosh])
    impact = os.path.join(tmp, "impact.wav")
    run(["ffmpeg", "-y", "-f", "lavfi",
         "-i", f"aevalsrc=sin(2*PI*68*t)*exp(-9*t)+0.35*sin(2*PI*136*t)*exp(-14*t):s=44100:d=1.2",
         "-af", "volume=2.0", impact])

    # --- build video: n quick punch-in cards + landing Ken Burns ----------
    # NOTE: feed each still as a single frame — zoompan's d= then emits exactly
    # the frames we need. (-loop with zoompan would multiply frames and break
    # every segment's duration.)
    cmd = ["ffmpeg", "-hide_banner", "-y"]
    for c in covers:
        cmd += ["-i", c]
    cmd += ["-i", fc]                                            # input n
    cmd += ["-i", vo]                                            # input n+1
    sound_base = n + 2
    for k in range(n - 1):                                       # whooshes on cuts
        cmd += ["-i", whoosh]
    cmd += ["-i", impact]                                        # landing hit

    parts = []
    cf = math.ceil(cut * fps)
    for i in range(n):
        # fast alternating punch-in / pull-back so the flicker feels alive
        z = ("min(zoom+0.006,1.25)" if i % 2 == 0
             else "max(1.25-0.006*on,1.0)")
        parts.append(
            f"[{i}:v]scale={w * 2}:{h * 2},zoompan=z='{z}':d={cf}:"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps},"
            f"eq=saturation=0.9,setsar=1[v{i}];")
    lf = math.ceil(land_d * fps)
    parts.append(
        f"[{n}:v]scale={w * 2}:{h * 2},zoompan=z='min(zoom+0.0011,1.2)':d={lf}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps},"
        f"eq=brightness=-0.06:saturation=0.95,vignette=PI/4.5,setsar=1[vl];")
    parts.append("".join(f"[v{i}]" for i in range(n)) + f"[vl]concat=n={n + 1}:v=1[cat];")

    # white flash frame on every cut (fades in 2 frames) + titles on landing
    def tfile(name, text):
        p = os.path.join(tmp, name)
        open(p, "w", encoding="utf-8").write(text)
        return p
    l1 = tfile("l1.txt", "带你体验一百种人生")
    l2 = tfile("l2.txt", "今天，体验的人生是")
    l3 = tfile("l3.txt", f"《{args.topic}》")
    fs, fb = max(20, int(w * 0.050)), max(28, int(w * 0.075))
    t2 = t_land + 0.15
    t3 = max(t2 + 0.9, vo_d * 0.74)

    flash = "+".join(
        f"0.85*exp(-18*(t-{cut * k:.3f}))*between(t,{cut * k:.3f},{cut * k + 0.30:.3f})"
        for k in range(1, n + 1))
    def dt(tf_, size, color, ypos, t0):
        return (f"drawtext=fontfile='{FONT}':textfile='{tf_}':fontsize={size}:"
                f"fontcolor={color}:borderw={max(3, size // 14)}:bordercolor=black@0.85:"
                f"shadowx=2:shadowy=2:shadowcolor=black@0.6:"
                f"x=(w-text_w)/2:y={ypos}:alpha='clip((t-{t0})/0.6,0,1)'")
    parts.append(
        f"[cat]eq=brightness='{flash}':eval=frame,"
        + dt(l1, fs, "white", f"{h}*0.26", 0.35) + ","
        + dt(l2, fs, "white", f"{h}*0.40", t2) + ","
        + dt(l3, fb, "0xFFD56B", f"{h}*0.54", t3) + ",format=yuv420p[v];")

    # --- audio mix: narration + whooshes at cuts + impact at landing -------
    amix = [f"[{n + 1}:a]volume=1.0[a_vo];"]
    labels = ["[a_vo]"]
    for k in range(1, n):
        ms = int(cut * k * 1000)
        amix.append(f"[{sound_base + k - 1}:a]adelay={ms}|{ms},volume=0.5[a_w{k}];")
        labels.append(f"[a_w{k}]")
    ms = int(t_land * 1000)
    amix.append(f"[{sound_base + n - 1}:a]adelay={ms}|{ms},volume=0.9[a_hit];")
    labels.append("[a_hit]")
    amix.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0[a];")

    fc_str = "".join(parts) + "".join(amix).rstrip(";")
    cmd += ["-filter_complex", fc_str, "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps),
            "-preset", "medium", "-c:a", "aac", "-b:a", "192k",
            "-t", f"{total:.3f}", args.out]
    subprocess.run(cmd, check=True)
    print(f"wrote {args.out} ({total:.1f}s: {n} covers x {cut}s flicker -> land at {t_land:.1f}s)")


if __name__ == "__main__":
    raise SystemExit(main())
