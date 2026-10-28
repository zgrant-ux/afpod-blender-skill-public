---
name: afpod-blender-goo
description: Build or update the Almost Friday Podcast (AF Pod) YouTube motion package in Blender — 3D glossy goo intro, drip/splat/sweep transitions and end card, rendered as transparent ProRes 4444 overlays with sound. Use when asked to re-render, retime, resize, recolor or extend the AF Pod intro/transitions/end card, or to make a new goo-style animated overlay from brand art.
---

# AF Pod Blender goo package

Everything is code: brand art is traced to polygons once, then one Blender script builds each piece procedurally and renders transparent PNG frames, which are encoded to ProRes 4444 with alpha (+ optional sound).

## Pieces

| piece | length @30fps | what happens | cut / cover |
|---|---|---|---|
| `intro` | 112 f | light-blue flood, brand-blue drips land, pool rises, 3D logo splashes up, bugs pop on, light sweep, everything drains | covered 16–106 |
| `trans_drip` | 40 f | light then blue sheets fall over the frame, blue leaves first | cut on 18 |
| `trans_splat` | 40 f | goo blobs splat out to fill frame, AF POD mark pops, all sucks back | cut on 18 |
| `trans_sweep` | 46 f | goo floods left→right with Liam (grasshopper) riding the front, Angus (wizard beetle) the back | cut on 21 |
| `endcard` | 150 f | floods in, then an end screen: logo, SUBSCRIBE circle, KEEP WATCHING + two 16:9 slots, "NEW EPISODES EVERY THURSDAY 8AM PT/11AM ET"; frames 30–149 loop seamlessly | 20 s after encode |

## Run

```
# one piece, stills for a look (half res)
/Applications/Blender.app/Contents/MacOS/Blender -b -P scripts/afpod_scene.py -- intro renders/test --still 20,60 --pct 50 --samples 16
# everything, 1080p
scripts/render_all.sh                 # -> renders/<piece>/f_####.png
python3 scripts/sfx.py sfx            # -> sfx/<piece>.wav
python3 scripts/encode.py             # -> out/AF POD - <Name>.mov (+ out/previews/*.mp4)
# 4K, 20% slower, silent (and a supersampled 1080 copy)
scripts/render_4k_slow.sh
```

Scene options: `--slow 1.2` stretches timing (still full frame rate), `--pct 200` = 4K, `--samples N`, `--frames a-b`, `--still f1,f2`.
Encode options: `--src <render dir> --out <dir> --tag <label> --nosound --size 1920x1080`.

## Building the art (required: `src/` is not included in this public copy)

1. `swift scripts/pdf_render.swift <rebrand.pdf> <page> 8000 src/pageN.png` (PDFKit, transparent canvas; the artboard itself has a white background).
2. `python3 scripts/trace_art.py src` → `src/art_shapes.json` (color-separated: logo goo, letters, shine, each bug's line + white fill; AF POD social mark from page 3).
3. Fonts: pull the embedded subsets out of the PDF with pypdf (`/FontFile3`), then `python3 scripts/text_shapes.py src` → `src/text_shapes.json`. The Sanurumi subset has no J Q X Z 0 2–7, so only words built from the letters in the PDF can be set.

## Brand

#0061EF blue, #62B1FF mid, #B3DBFF light, white. Bruch (headlines), Sanurumi Handwritten all caps (secondary). Bugs: Angus = wizard beetle, Liam = sunglasses grasshopper, plus the sinking bug.

## Gotchas (each one cost a re-render)

- World gradient must run on **+Y** (scene up; camera on +z). A Z gradient makes every front face reflect white.
- Force ring winding: outer rings CCW, holes CW by nesting depth (`orient()`), or fills face away and look see-through.
- Art with thin parts must **not** use `offset = -bevel`; the inset collapses the fill. Only broad goo sheets inset (`inset=True`).
- **Motion blur off.** Sheets are rebuilt every sub-frame and Eevee deformation blur turns that into streaks (`cycles.use_deform_motion` does nothing in Eevee).
- Split a sheet into separate rings wherever it pinches to zero thickness; degenerate strips render as streaks.
- A sheet moving along (0,1) has its `a` axis mirrored — flip shape functions (`a = -a`).
- zsh: `${@:-a b}` is one word; use an array for piece lists.
- `sfx.py` reads Mister Horse library samples from `~/Library/Application Support/MisterHorse/...` (licensed, not in this repo); swap paths if they move.

## Delivery

ProRes 4444, `yuva444p`, 29.97 fps (rendered at 30, conformed), PCM audio. Drops onto a track above the footage in Premiere. MP4 can't carry alpha, which is why the deliverables are .mov.
