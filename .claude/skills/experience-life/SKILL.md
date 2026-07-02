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

5. **Voiceover + subtitles** (reuses video-restyle's tts.py). **Series standard
   narration voice = `zh-CN-YunxiNeural --rate=+2%`** — use this for every
   episode (and the intro uses it by default) so the channel sounds consistent.
   Note: pass negative rate/pitch with `=` (e.g. `--rate=-8%`) so argparse
   doesn't read them as flags.
   ```bash
   python3 .claude/skills/video-restyle/scripts/tts.py \
       --script video_projects/<slug>/script.txt \
       --out   video_projects/<slug>/narration \
       --voice zh-CN-YunxiNeural --rate=+2%
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

7.5 **Animated subtitles.** Convert the .srt into a modern animated .ass track
   before assembling — soft glow instead of a hard 90s outline, per-line fade +
   subtle pop, and any cue starting with "Level" automatically becomes a golden
   screen-centered chapter stinger:
   ```bash
   python3 .claude/skills/experience-life/scripts/srt2ass.py \
       --srt video_projects/<slug>/narration.srt --size 1024x768 \
       --out video_projects/<slug>/narration.ass
   ```
   Then pass the `.ass` to assemble.py's `--srt` (it detects the extension and
   uses the embedded styling). The carousel intro uses the same animated title
   language (rise/fade/pop/glow), so the whole film reads as one design.

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

## Character bible — account-exclusive recurring cast

To make every video star the SAME people (a personal-account identity), this
skill keeps a locked cast in `characters/characters.json`. Each character has:
- a **locked appearance fragment** (very specific face/hair/build), reused
  verbatim so the text-to-image model keeps drawing the same person;
- a **locked seed** so that description renders the same face every time.

Current cast (style: muted grey-blue manhua):
- `ahai` 阿海 — male lead / everyman "你".
- `axia` 小夏 — female lead / everywoman "你".

Approved reference sheets live next to the JSON (`ahai_sheet.jpg`,
`axia_sheet.jpg`). The same locked face re-ages and re-costumes across a whole
lifetime — only change the age/clothing words in the scene prompt.

**Use the cast in an episode:** in `scenes.json`, set the primary character and
reference it with an `@id` token; gen_images.py injects the locked appearance
and pins that character's seed:
```json
{ "prompt": "@ahai in his twenties, in an orange diving suit on a ship deck",
  "char": "ahai", "end_cue": 5 }
```
```bash
python3 .claude/skills/experience-life/scripts/gen_images.py \
    --srt narration.srt --scenes scenes.json \
    --characters .claude/skills/experience-life/characters/characters.json \
    --style "<the cast's style>" --size 1024x768 --out imgs/
```
- `"char": "<id>"` → uses that character's locked seed (face stays stable).
- `@<id>` anywhere in a prompt → expands to the character's locked appearance.
- `"seed_offset": N` → re-rolls just that one scene (e.g. to fix a broken
  hand/limb) without touching the appearance lock or any other frame.
- Scenes with no `char` fall back to the `--seed` + variety behaviour.

**Fixing broken anatomy:** AI image models still mangle hands/limbs sometimes.
To strictly fix a bad frame: (1) reframe the prompt to avoid the hard part —
gloves, hands in pockets / at sides / out of frame, holding a simple object,
upper-body crop; and (2) add `"seed_offset"` to re-roll until clean. Because
seeds are deterministic, re-running regenerates ONLY the changed scenes and
leaves the good frames byte-identical. Add `anatomically correct, natural
proportions, correct hands, no deformed limbs` to the `--style`.

**Add / edit a character:** append to `characters.json` (give it a unique seed
and a detailed appearance), then regenerate its sheet to approve the look:
```bash
python3 .claude/skills/experience-life/scripts/gen_characters.py \
    --characters .claude/skills/experience-life/characters/characters.json \
    --style "<the cast's style>" --only <id> \
    --out .claude/skills/experience-life/characters/
```
Keep the STYLE string identical to the rest of the cast so they look like one
world. The character bible is committed to the repo so it persists across the
ephemeral web sessions.

## Reusable intro animation + music bed

The series has reusable, brandable assets in `assets/`:
- `intro_bg.jpg` — a topic-agnostic dramatic background (silhouettes of many
  lives under a spotlight) for the opening title.
- `bgm_tense.mp3` — a royalty-free, synthesized **tense** music bed (drone +
  heartbeat tick + throb), 60s, looped under any video.

**Opening animation — carousel (preferred).** A stack of "life covers"
(`assets/covers/*.jpg`, ~8 dramatic poster illustrations of different lives)
flicks past at ~0.4s/cover with a synthesized whoosh + white flash on every
cut, then slams (impact hit) onto THIS episode's cover where the golden title
and the catchphrase narration land. Per episode only `--topic` and
`--final-cover` change; everything else is reused:
```bash
python3 .claude/skills/experience-life/scripts/make_intro_carousel.py \
    --topic "饱和潜水员的一生" \
    --final-cover .claude/skills/experience-life/assets/covers/diver.jpg \
    --size 1024x768 --out video_projects/<slug>/intro.mp4
```
For a new episode whose life isn't in the covers yet, generate one poster-style
cover via Pollinations into `assets/covers/<life>.jpg` (it then also enriches
the flicker pool for future episodes). All switch sounds are synthesized
locally by the script — no sample files needed.

**Opening animation — simple (fallback):** a single Ken-Burns push over
`intro_bg.jpg` with three fading title lines:
```bash
python3 .claude/skills/experience-life/scripts/make_intro.py \
    --topic "饱和潜水员的一生" --size 1024x768 \
    --out video_projects/<slug>/intro.mp4
```

**Compose** intro + main and lay the looped music bed under the whole film
(narration side-chain-ducks the music — it swells in the intro/pauses and dips
under speech):
```bash
python3 .claude/skills/experience-life/scripts/compose.py \
    --clips video_projects/<slug>/intro.mp4 video_projects/<slug>/final.mp4 \
    --music .claude/skills/experience-life/assets/bgm_tense.mp3 \
    --size 1024x768 --out video_projects/<slug>/final_full.mp4
```

**Regenerate / re-style the assets** (they're reusable, so tweak once):
```bash
# a different tense bed (tempo, length)
python3 .claude/skills/experience-life/scripts/make_music.py \
    --duration 90 --bpm 132 --out .claude/skills/experience-life/assets/bgm_tense.mp3
# a new branded intro background: generate via Pollinations into assets/intro_bg.jpg
```
`make_intro.py` and the music bed are series-level (reused verbatim); only the
`--topic` and the per-episode main video change. Assets are committed to the
repo so they survive the ephemeral web sessions.

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
