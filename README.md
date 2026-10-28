# AF Pod Blender goo package

Procedural Blender pipeline for the Almost Friday Podcast YouTube intro, three transitions and end card: glossy 3D goo built from the 2026 rebrand art, rendered as transparent ProRes 4444 overlays with sound design.

See **SKILL.md** for pieces, commands, options and the gotchas. To use it as a Claude Code skill, copy this folder to `~/.claude/skills/afpod-blender-goo/`.

Needs: Blender 4.5 LTS, Python 3 with numpy + opencv (art tracing) and pypdf + fonttools (fonts), ffmpeg, macOS (PDFKit for the PDF render).

**This public copy is code only.** The AF Pod brand art, fonts and the traced shape files (`src/art_shapes.json`, `src/text_shapes.json`) are not included, and neither are the licensed Mister Horse SFX samples `sfx.py` layers in. Generate `src/` from your own brand PDF with the steps under "Rebuilding the art" in SKILL.md before rendering.
