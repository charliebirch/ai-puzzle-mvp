# CLAUDE.md - AI Puzzle MVP

## What This Project Is

An Etsy business that transforms customer photos into **animated kids' jigsaw puzzles** — Pixar-style cartoon art, not photorealistic. Currently **pre-launch** — focused on quality consistency and building the production pipeline.

The owner (Charlie) has some coding ability but relies on Claude Code as the primary engineering partner.

## Working With Charlie

- **Always plan first.** Propose changes before making them.
- **Be concise.** Don't over-explain.
- **Keep costs visible.** Show estimated cost before running Replicate API calls.
- **Don't break working code.** Verify imports before and after changes.
- **Track decisions.** Record significant choices in memory.
- **Document code.** Add docstrings and comments.

## The Pipeline (6 Steps + Export)

```
Photo → Remove BG ($0.01) → Normalise ($0.08) → Character ($0.08) → Costume ($0.08) → Scene ($0.24) → Upscale ($0.002) → Export (free)
```

1. **Background Removal** — `recraft-ai/recraft-remove-background`, composite onto white (fallback: `lucataco/remove-bg` via `BG_REMOVAL_BACKEND` env var)
2. **Portrait Normalisation** — `flux-kontext-max`, standardises photo to front-facing, shoulders-up, white bg; skippable via `NORMALIZE_PORTRAIT=0`
3. **Character Generation** — `flux-kontext-max`, Pixar transform from normalised portrait; face is cropped before sending; no text attribute injection — image drives identity
4. **Costume** — `flux-kontext-max`, outfit picker (Adventurer or Wizard); IDENTITY LOCK prompt; `{subject}="the person in the input image"`
5. **Scene Generation** — `flux-2-pro` text-only, detailed empty village scene with puzzle-optimised prompt
6. **Compositing** — Method E only: PIL composite → 3× Kontext Max (different seeds) → quality-score → user picks → upscale → `step_export_for_print()` auto-runs

**Cost:** ~$0.57 per full run

Full technical details: `docs/PIPELINE.md`
All learnings and rules: `docs/BEST_PRACTICES.md`

## Key Commands

```bash
# Web interface — full 5-step wizard
.venv/bin/python3 -m uvicorn web.app:app --reload --port 8000

# Run puzzle quality scorer on an image
.venv/bin/python3 -c "
import sys; sys.path.insert(0, 'src')
from quality.puzzle_scorer import score_puzzle_quality
result = score_puzzle_quality('path/to/image.png', 500)
print(f'{result.composite}/100 — {result.grade.value}')
"

# Test print export manually
.venv/bin/python3 -c "
import sys; sys.path.insert(0, 'src')
from pipeline_steps import step_export_for_print
step_export_for_print('orders/JOB-ID/final.png', '252pc', 'orders/JOB-ID')
"

# Verify imports
cd src && .venv/bin/python3 -c "from backends.registry import list_backends; print(list_backends())"
```

## Environment

- **macOS** — use `.venv/bin/python3` (system python3 is 3.14, venv is 3.9)
- **Photos** in `input/<Name>/` subfolders
- **Order output** goes to `orders/<order_id>/` (gitignored)
- **API key** in `.env` as `REPLICATE_API_TOKEN`
- All AI calls go through **Replicate**

## Project Structure

```
src/
  backends/
    base.py              # BaseBackend ABC + GenerationResult dataclass
    flux_kontext.py      # FLUX Kontext Pro ($0.04/run)
    flux_kontext_max.py  # FLUX Kontext Max ($0.08/run) — primary model
    registry.py          # Backend factory (2 registered)
  quality/
    image_quality.py     # Visual quality metrics
    puzzle_scorer.py     # 12-metric puzzle quality scorer (target: 65+ pass, 80+ good)
  pipeline_steps.py      # All 5 pipeline step functions
  scene_prompts.py       # All prompts + outfit_choices; get_character_prompt(), get_costume_prompt()
  composite_pil.py       # PIL character-onto-scene compositing (pre-Kontext blend)
  detect_attributes.py   # Claude vision auto-detect: age, gender, ethnicity, hair, skin tone
  remove_background.py   # Background removal via Replicate ($0.01)
  subject_builder.py     # Structured subject description builder
  fulfill_order.py       # Legacy simplified pipeline (3-step, not the wizard)
web/
  app.py                 # FastAPI + Jinja2 + HTMX — 5-step wizard
  jobs.py                # SQLite job tracking
  templates/             # HTML templates (wizard_step1–5, base, poll fragment)
  static/style.css       # Pico CSS + wizard progress + wardrobe picker styles
docs/
  BEST_PRACTICES.md      # All learnings from testing (prompts, what works/doesn't)
  PIPELINE.md            # Technical pipeline reference (models, prompts, costs)
  PRODIGI.md             # Prodigi API reference, image specs, SKUs, shipping
  PRODIGI_LAUNCH_CHECKLIST.md  # Step-by-step checklist before first live order
  prodigi-jigsaws-gb-pricing.csv  # Pricing CSV from Prodigi (confirmed 2026-04-06)
  RENDER.md              # Render hosting reference: tiers, persistent disk, render.yaml, upgrade guide
  complete-ai-puzzle-guide-deep-research.md  # Puzzle design research
  consent-flow.md        # Legal: consent flow
  privacy-policy.md      # Legal: privacy policy
  terms-of-service.md    # Legal: terms of service
  etsy-listing-template.md  # Marketing: Etsy listing
api/
  index.py               # Render deployment entrypoint
input/                   # Customer test photos
orders/                  # Generated outputs (gitignored)
_archive/                # Old pipeline code and test outputs (gitignored)
```

## Quality Scoring

Use `src/quality/puzzle_scorer.py` — 13 metrics, 0-100 composite score.

| Threshold | Grade |
|-----------|-------|
| >= 65 | PASS |
| 40-64 | WARNING |
| < 40 | FAIL |
| Hard fail triggers | HARD FAIL |

Best composite score: **96.9/100** (TEST-CHARLIE-SCENE-V1B, 2026-04-06).

Key metrics: flat regions (<25%), corner detail, hue diversity (8+ bins), edge density, subject dominance (<50%), shadow presence (ground shadow under character), white patch (hard fail only — detects unblended character halo).

Note: white_patch detector produces false positives on pure scene images (no character) — this is expected and harmless. It only matters on composited candidates.

## Print Specs (Prodigi — launch sizes)

| SKU | Pieces | Physical | Export pixels | Tin lid | Unit cost | Rec. price | Margin |
|-----|--------|----------|---------------|---------|-----------|------------|--------|
| `JIGSAW-PUZZLE-252` | 252 | 375×285mm | 4429×3366px | 869×674px | £13 | £35 | £13.69 |
| `JIGSAW-PUZZLE-110` | 110 | 250×200mm | 2953×2362px | 869×674px | £12 | £28 | £8.35 |

Export function: `step_export_for_print(upscaled_path, size_code, order_dir)` — outputs `puzzle_surface.jpg` + `tin_lid.jpg`.
Resize strategy: scale-to-fill then center-crop. 252pc is native 4:3 (negligible crop). 110pc is 5:4 (~6% side-crop).
Full pricing: `docs/prodigi-jigsaws-gb-pricing.csv`

## Models Used

| Model | Replicate ID | Cost | Used For |
|-------|-------------|------|----------|
| Remove BG | `recraft-ai/recraft-remove-background` | $0.01 | Step 1: background removal (default; lucataco fallback via env var) |
| Kontext Max | `black-forest-labs/flux-kontext-max` | $0.08 | Steps 2 (normalise), 3, 4, 6 (compositing) |
| Kontext Pro | `black-forest-labs/flux-kontext-pro` | $0.04 | Available, not default |
| FLUX 2 Pro | `black-forest-labs/flux-2-pro` | ~$0.08 | Step 4: scene generation (text-only) |
| Real-ESRGAN | `nightmareai/real-esrgan` | $0.002 | Step 5: upscale after user picks |

## Decisions Log

| Decision | Choice | Why | Date |
|----------|--------|-----|------|
| Multi-step pipeline | 5 separate steps | Single prompt fails at both character AND scene quality | 2026-03-28 |
| Background removal first | lucataco/remove-bg | Removes distracting elements, model focuses on person | 2026-03-28 |
| Kontext Max for character | $0.08 over Pro $0.04 | Pro loses too much likeness | 2026-03-28 |
| White background between steps | White, not transparent | Best results for AI model input | 2026-03-28 |
| Separate costume step | Don't combine with character gen | Doing both in one prompt degrades both | 2026-03-28 |
| Empty scenes (no people) | Generate scenes separately | AI can't do character + scene in one shot well | 2026-03-28 |
| Method E only | Removed K and Q | Method E gives best seamlessness; 3 seeds gives enough variety | 2026-04-06 |
| FLUX 2 Pro for scene | Text-only, not Kontext Max | Kontext Max errors on white placeholder input for scene gen | 2026-04-06 |
| Don't exaggerate features | "Slightly exaggerated Pixar proportions, expressive eyes — not bug-eyed" | Bug-eyed characters, masculine jaws on women | 2026-03-28 |
| Gender-specific prompts | Feminine/masculine hints | Generic proportions without hints | 2026-03-28 |
| {subject} in costume prompts | All costume prompts use get_costume_prompt() | Model alters hair to match outfit archetype without explicit text anchor | 2026-04-06 |
| No text in scene | Explicit NO TEXT rule + per-object "no writing" | AI-generated fake text on signs looks bad | 2026-04-06 |
| Scene prompt structured sections | FOREGROUND / MIDGROUND / BACKGROUND / CORNERS | Unstructured prompt → model ignores corners and produces flat sky | 2026-04-06 |
| Landscape orientation | All outputs 4:3 landscape | Prodigi puzzles are landscape; portrait doesn't fill puzzle well | 2026-04-06 |
| Upscale to 4x | Real-ESRGAN 4x, general model | Print requires 300 DPI; 2x output (~2048px) too low for 252pc+ | 2026-04-06 |
| Prodigi as fulfillment partner | UK fulfillment, 110pc + 252pc launch | No minimums, premium tins, strong UK domestic shipping (2-5 days) | 2026-04-06 |
| Print export format | JPG not PNG, sRGB, quality=95, subsampling=0 | Prodigi prefers JPG; 4:4:4 chroma for max print fidelity | 2026-04-06 |
| Puzzle size in wizard | 252pc default, 110pc option | 252pc is native 4:3 (no crop), better margin, hero product | 2026-04-06 |
| Regenerate buttons | Steps 3 + 4 have "Regenerate" that clears downstream + new seed | Needed before volume; no way to retry without starting over | 2026-04-06 |
| Recraft for BG removal | `recraft-ai/recraft-remove-background` default, lucataco fallback | Better edge quality especially on hair; same cost | 2026-04-07 |
| Portrait normalisation step | New step 2b: flux-kontext-max, front-facing portrait before character gen | Removes dependency on perfect input photo; any angle → standardised portrait | 2026-04-07 |
| No text attribute injection | Subject = "the person in the input image", gender = "person" always | Text descriptions (ethnicity, hair, age) make outputs look generic vs preserving actual likeness | 2026-04-07 |
| IDENTITY LOCK in costume prompts | Full facial feature lock (face shape, eye colour, nose, mouth, proportions) | Previous wording only covered hair/skin — face shape still drifted during costume step | 2026-04-07 |
| Shadow presence metric | 13th quality metric, 3% weight, LAB local-contrast in foot zone | Detects missing ground shadows which make character look composited/pasted | 2026-04-07 |

## Current Status

- **Pipeline proven** — 6-step wizard working end-to-end, scores 93–97/100
- **Portrait normalisation** — new step 2b standardises any input photo to front-facing before character gen (`NORMALIZE_PORTRAIT=0` to skip)
- **Recraft BG removal** — switched to `recraft-ai/recraft-remove-background` for better edge quality; lucataco fallback via `BG_REMOVAL_BACKEND=lucataco`
- **No attribute injection** — prompts no longer inject detected age/gender/ethnicity/hair/skin; AI works from image directly
- **IDENTITY LOCK** — costume prompts now have full identity lock (face shape, eye colour, nose, mouth, proportions, not just hair/skin)
- **Shadow scoring** — 13th quality metric (`shadow_presence`) checks for ground shadow in composited images
- **Prompt CLI** — `scripts/print_prompts.py <JOB_ID>` prints all resolved prompts for any job
- **Wardrobe picker** — Step 4 has interactive outfit choice UI (Adventurer + Wizard)
- **Regenerate buttons** — Steps 3 + 4 have "Regenerate" (clears downstream, new random seed)
- **Prodigi ready** — `step_export_for_print()` outputs print-ready JPGs automatically after upscale; see `docs/PRODIGI.md`
- **Deployed** — live on Render (`main` branch auto-deploys)
- **Next:** Test full pipeline with new normalisation step; order a physical sample via Prodigi dashboard

## Known Issues

- Character size in compositing is unpredictable — model ignores percentage instructions
- FLUX 2 Pro safety filter occasionally triggers on benign content (retry with different seed)
- Kontext Max outputs capped at ~1024px — hard limit; `laplacian_variance` stays low until upscaled
- white_patch scorer produces false positives on pure scene images — expected, only meaningful on composites
- `LIGHTWEIGHT_MODE=1` set in `render.yaml` but **not checked anywhere in code** — leftover env var, does nothing
- Render free tier has ephemeral filesystem — `orders/` wiped on restart; run pipeline locally for real orders
