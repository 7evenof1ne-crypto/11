---
name: video-restyle
description: >-
  Given a reference video URL (e.g. a YouTube link) plus the user's own custom
  topic/content, produce a NEW narrated explainer video that mimics the
  reference's style. Use when the user gives a video link and asks to make a
  similar-style video with different/custom content, or to analyze a video's
  style. Fully local & free pipeline: yt-dlp (fetch transcript + frames),
  Claude (style analysis + new script), edge-tts (free voiceover), ffmpeg
  (assemble). Requires an environment with open network egress.
---

# video-restyle

Turn "here's a video I like → make one like it but about MY topic" into an
actual narrated mp4, using only free/local tools.

## What this can and cannot do

- ✅ Extract a reference video's transcript, metadata, chapters, and sample
  frames; analyze its **style** (hook, pacing, tone, structure, captions).
- ✅ Write a **new script** in that style for the user's custom content.
- ✅ Generate **free voiceover** (edge-tts) + timed subtitles.
- ✅ Assemble a **narration/explainer video** (slideshow / captions / b-roll
  images + burned subtitles) with ffmpeg.
- ❌ It does NOT generate cinematic AI motion footage (Sora/Veo/Kling). That
  needs a paid external service and is out of scope for the free pipeline.

## Network requirement (read first)

This skill reaches out to YouTube (yt-dlp) and the Edge TTS endpoint
(edge-tts). Restricted Claude-Code-on-the-web environments block these with
`x-deny-reason: host_not_allowed`. Always run **`scripts/bootstrap.sh` first** —
it installs deps, fixes the TLS-inspection CA, and prints whether egress is
open. If blocked, tell the user to recreate the environment with **Full
network access** (or a custom allowlist including `*.youtube.com`,
`*.googlevideo.com`, `youtubei.googleapis.com`, `i.ytimg.com`,
`speech.platform.bing.com`). Docs: https://code.claude.com/docs/en/claude-code-on-the-web

## Workflow

Work inside a per-project dir, e.g. `video_projects/<slug>/` (gitignored).

1. **Bootstrap** (every session — container is ephemeral):
   ```bash
   bash .claude/skills/video-restyle/scripts/bootstrap.sh
   ```

2. **Fetch the reference** transcript + metadata:
   ```bash
   python3 .claude/skills/video-restyle/scripts/fetch_reference.py \
       "<reference_url>" video_projects/<slug>/ref
   ```
   Optionally sample frames to inspect visual style (then Read the contact sheet):
   ```bash
   bash .claude/skills/video-restyle/scripts/sample_frames.sh \
       "<reference_url>" video_projects/<slug>/ref 4 360
   ```

3. **Analyze style** — Read `ref/transcript.txt`, `ref/metadata.json`, and
   `ref/contact_sheet.jpg`. Summarize: opening hook, pacing/segment length,
   tone & vocabulary, structure (problem→explain→payoff), caption style,
   typical sentence length. Write findings to `style_profile.md`.

4. **Write the new script** for the user's custom topic, matching that style.
   Save as `script.txt` (plain narration text; this is what gets voiced).
   Confirm topic/voice/aspect ratio with the user before generating.

5. **Voiceover + subtitles:**
   ```bash
   python3 .claude/skills/video-restyle/scripts/tts.py \
       --script video_projects/<slug>/script.txt \
       --out   video_projects/<slug>/narration \
       --voice zh-CN-XiaoxiaoNeural --rate +0%
   ```

6. **Visuals (optional):** drop images into `video_projects/<slug>/visuals/`
   (reuse sampled frames, or images the user provides). Skip for a clean
   caption-on-color look.

7. **Assemble:**
   ```bash
   python3 .claude/skills/video-restyle/scripts/assemble.py \
       --audio video_projects/<slug>/narration.mp3 \
       --srt   video_projects/<slug>/narration.srt \
       --images video_projects/<slug>/visuals \
       --size 1920x1080 --out video_projects/<slug>/final.mp4
   ```
   Vertical short: `--size 1080x1920`. Then surface `final.mp4` to the user.

## Voice cheatsheet (zh-CN)

| voice | feel |
|---|---|
| zh-CN-XiaoxiaoNeural | warm female, default |
| zh-CN-YunxiNeural | natural male |
| zh-CN-YunyangNeural | news-anchor male |
| zh-CN-XiaoyiNeural | lively female |

`edge-tts --list-voices` for the full list (en-US-*, etc.).

## Notes

- Respect copyright: reference the *style*, produce *original* content. Don't
  reupload or closely reproduce the source's actual script.
- `bootstrap.sh` is idempotent; safe to re-run anytime.
