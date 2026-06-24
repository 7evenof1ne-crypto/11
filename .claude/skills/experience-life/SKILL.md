---
name: experience-life
description: >-
  Produce a "体验XX人生 / experience a life" narrated explainer video: a
  second-person, game-level ("Level 1/2/3") immersive story that walks the
  viewer through a life ordinary people can't easily reach or imagine (a
  saturation diver, an astronaut, a lighthouse keeper, a death-row inmate's
  last day...). Each scene's illustration is AI-generated to match the
  narration text, with free TTS voiceover and burned subtitles. Use when the
  user wants this storytelling format, or references a "体验人生/人生副本"
  style video. Fully free pipeline: Pollinations (text-to-image), edge-tts
  (voiceover), ffmpeg (assemble). Needs open network egress.
---

# experience-life （体验XX人生）

Turn "let me experience the life of a ___" into a narrated illustrated video,
in the style of channels like 「赛博观察员 / 带你体验一百种人生副本」.

## The genre (what makes it work)

A calm, slightly melancholic **observer** narrates in the **second person** —
*you ARE this person*. The viewer is dropped into a life they'd never normally
live. The structure is borrowed from video games.

**Script DNA (copy this):**
- **Opening hook (fixed):** "带你体验一百种人生副本。今天我们要体验的，是 ___。"
- **Game-level structure:** `Level 1` (setup) → `Level 2` (the turn) →
  `Level 3` (the grind / the cost) → a quiet ending beat.
- **Second person "你"** throughout; the viewer is the protagonist.
- **Concrete setup:** age, background, money in real numbers
  (房租1100、月薪4000). Specificity = immersion.
- **Mundane, hyper-real details** that quietly accumulate emotional weight.
- **Short sentences.** One image per sentence. Restrained tone, no melodrama.
- **Gut-punch beats:** "她说这两个字的时候，嘴角笑了一下，但眼睛没笑。"
- **Pick lives that are hard to reach or imagine** — extreme jobs, extreme
  circumstances, rare experiences — not everyday ones.

**Visual DNA:** flat hand-drawn cartoon / manhua illustration, muted
desaturated palette, a single **consistent character**, simple but specific
backgrounds, cinematic framing, ~4:3, burned subtitles at the bottom.

## Network requirement (read first)

Reaches Pollinations (image gen) + the edge-tts endpoint. Restricted web
environments block these. Run **`scripts/bootstrap.sh` first**; if a host is
blocked, recreate the environment with **Full network access** (or allowlist
`image.pollinations.ai`, `speech.platform.bing.com`).
Docs: https://code.claude.com/docs/en/claude-code-on-the-web

## Workflow

Work inside `video_projects/<slug>/` (gitignored).

1. **Bootstrap** (every session):
   ```bash
   bash .claude/skills/experience-life/scripts/bootstrap.sh
   ```

2. **(Optional) Analyze a reference** the user supplies. Sample frames and
   transcribe to extract style:
   ```bash
   ffmpeg -i ref.mp4 -vf "fps=1/20,scale=240:-2,tile=5x4" -frames:v 1 contact.jpg
   ffmpeg -i ref.mp4 -vn -ac 1 -ar 16000 audio.wav
   # transcribe with faster-whisper (pip install --break-system-packages faster-whisper)
   ```
   Read `contact.jpg` for the art style; read the transcript for script cadence.

3. **Conceive the theme.** Confirm with the user (or pick) a "体验XX人生"
   subject that is hard to reach/imagine. Outline the Level 1/2/3 beats.

4. **Write the script** in the genre DNA above → `script.txt` (plain narration
   text, one idea per sentence — sentence breaks become subtitle cues AND
   scene boundaries).

5. **Voiceover + subtitles** (reuses video-restyle's tts.py). A calm male
   observer voice fits best:
   ```bash
   python3 .claude/skills/video-restyle/scripts/tts.py \
       --script video_projects/<slug>/script.txt \
       --out   video_projects/<slug>/narration \
       --voice zh-CN-YunxiNeural --rate +2%
   ```

6. **Map scenes → image prompts.** Inspect `narration.srt` cue timings, then
   write `scenes.json`: a list of `{ "prompt": "<English visual description>",
   "end_cue": <last srt cue index this image covers> }`. Keep the SAME
   character described across prompts ("the same 30-year-old man, ...") for
   consistency. English prompts give better image results.

7. **Generate illustrations** (Pollinations, free, timed to the narration):
   ```bash
   python3 .claude/skills/experience-life/scripts/gen_images.py \
       --srt    video_projects/<slug>/narration.srt \
       --scenes video_projects/<slug>/scenes.json \
       --style  "flat hand-drawn cartoon illustration, Chinese webtoon manhua style, muted desaturated grey-blue palette, soft cel shading, clean dark outlines, cinematic, melancholic, consistent character design" \
       --seed 7777 --size 1024x768 \
       --out  video_projects/<slug>/imgs
   ```
   A fixed `--seed` + a consistent character description keeps the cast stable.
   Re-run a single bad scene by tweaking its prompt and bumping its seed.

8. **Assemble** (reuses video-restyle's assemble.py `--concat`, burns subs):
   ```bash
   python3 .claude/skills/video-restyle/scripts/assemble.py \
       --audio  video_projects/<slug>/narration.mp3 \
       --srt    video_projects/<slug>/narration.srt \
       --concat video_projects/<slug>/imgs/concat.txt \
       --size 1024x768 --out video_projects/<slug>/final.mp4
   ```
   Then surface `final.mp4`. Vertical variant: `--size 1080x1920` (and render
   images at a portrait size to match).

## Tips

- **Consistency** is the hard part of AI illustration. Lock the character with
  one description reused verbatim; keep `--seed` fixed; keep the STYLE string
  identical across all scenes.
- **One sentence = one image.** Long sentences → split them so no subtitle is a
  wall of text and each beat gets its own illustration.
- **Respect the source:** imitate the *format and tone*, write *original*
  stories. Don't reproduce a reference's actual script.
- Pollinations occasionally returns a weak image; gen_images.py retries and
  falls back to the previous frame so audio/subtitle timing never drifts.
