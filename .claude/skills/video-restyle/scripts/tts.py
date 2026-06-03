#!/usr/bin/env python3
"""Synthesize narration audio + timed subtitles from a script, using the free
Microsoft Edge TTS (edge-tts). No API key required.

Outputs:
  <out>.mp3   narration audio
  <out>.srt   subtitles timed to the narration (from word boundaries)

Usage:
  python3 tts.py --script script.txt --out narration \
      --voice zh-CN-XiaoxiaoNeural --rate +0%

List voices:  edge-tts --list-voices | grep zh-CN
Good zh-CN voices: zh-CN-XiaoxiaoNeural (warm female), zh-CN-YunxiNeural (male),
                   zh-CN-YunyangNeural (news anchor), zh-CN-XiaoyiNeural.
"""
import argparse
import asyncio
import sys


async def synth(text, voice, rate, volume, mp3_path, srt_path):
    import edge_tts

    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
    submaker = edge_tts.SubMaker()
    with open(mp3_path, "wb") as audio:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # edge-tts 7.x: feed the whole boundary dict
                try:
                    submaker.feed(chunk)
                except (AttributeError, TypeError):
                    # older API: create_sub((offset, duration), text)
                    submaker.create_sub(
                        (chunk["offset"], chunk["duration"]), chunk["text"]
                    )
    # write subtitles (API name differs across versions)
    srt = ""
    for getter in ("get_srt", "generate_subs"):
        fn = getattr(submaker, getter, None)
        if fn:
            srt = fn()
            break
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--script", required=True, help="UTF-8 text file with the narration")
    ap.add_argument("--out", required=True, help="output basename (-> .mp3 / .srt)")
    ap.add_argument("--voice", default="zh-CN-XiaoxiaoNeural")
    ap.add_argument("--rate", default="+0%", help="e.g. -10%, +15%")
    ap.add_argument("--volume", default="+0%")
    args = ap.parse_args()

    with open(args.script, encoding="utf-8") as f:
        text = f.read().strip()
    if not text:
        print("script is empty", file=sys.stderr)
        return 2

    mp3, srt = args.out + ".mp3", args.out + ".srt"
    try:
        asyncio.run(synth(text, args.voice, args.rate, args.volume, mp3, srt))
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        print(f"TTS failed: {msg}", file=sys.stderr)
        if "403" in msg or "Handshake" in msg:
            print("  -> 403 usually means the egress policy blocks "
                  "speech.platform.bing.com, or the cloud IP is rate-limited. "
                  "Confirm network access (see bootstrap.sh output).",
                  file=sys.stderr)
        return 1

    import os
    print(f"audio: {mp3} ({os.path.getsize(mp3)} bytes)")
    print(f"subs : {srt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
