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

## The Pipeline (5 Steps)

```
Photo → Remove BG ($0.01) → Character ($0.08) → Costume ($0.08) → Scene ($0.24) → Upscale ($0.002)
```

1. **Background Removal** — `lucataco/remove-bg`, composite onto white
2. **Character Generation** — `flux-kontext-max`, Pixar transform preserving identity; face is cropped before sending
3. **Costume** — `flux-kontext-max`, outfit picker (Adventurer or Wizard); prompts include `{subject}` for hair preservation
4. **Scene Generation** — `flux-2-pro` text-only, detailed empty village scene with puzzle-optimised prompt
5. **Compositing** — Method E only: PIL composite → 3× Kontext Max (different seeds) → quality-score → user picks → upscale

**Cost:** ~$0.49 per full run

Full technical details: `docs/PIPELINE.md`
All learnings and rules: `docs/BEST_PRACTICES.md`

## Key Commands

```bash
# Use venv python directly (source activate doesn't work in this shell)
.venv/bin/python3 src/remove_background.py input/photo.jpg output/bg_removed.jpg

# Run the simplified pipeline (character generation only — app rebuild pending)
.venv/bin/python3 src/fulfill_order.py \
  --photo input/amyg/amyg-beach.JPG \
  --style village \
  --subject "a young woman with dark hair" \
  --order-id TEST-001

# Run puzzle quality scorer on an image
.venv/bin/python3 -c "
import sys; sys.path.insert(0, 'src')
from quality.puzzle_scorer import score_puzzle_quality
result = score_puzzle_quality('path/to/image.png', 500)
print(f'{result.composite}/100 — {result.grade.value}')
"

# Web interface (currently simplified — rebuild pending)
.venv/bin/python3 -m uvicorn web.app:app --reload --port 8000

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

Use `src/quality/puzzle_scorer.py` — 12 metrics, 0-100 composite score.

| Threshold | Grade |
|-----------|-------|
| >= 65 | PASS |
| 40-64 | WARNING |
| < 40 | FAIL |
| Hard fail triggers | HARD FAIL |

Best composite score: **96.9/100** (TEST-CHARLIE-SCENE-V1B, 2026-04-06).

Key metrics: flat regions (<25%), corner detail, hue diversity (8+ bins), edge density, subject dominance (<50%), white patch (hard fail only — detects unblended character halo).

Note: white_patch detector produces false positives on pure scene images (no character) — this is expected and harmless. It only matters on composited candidates.

## Print Specs

| Size | Physical | Pixels (300 DPI) | Target Price |
|------|----------|-------------------|-------------|
| 500pc | 16" x 20" | 4800 x 6000 | $39.99 |
| 1000pc | 20" x 28" | 6000 x 8400 | $49.99 |

## Models Used

| Model | Replicate ID | Cost | Used For |
|-------|-------------|------|----------|
| Remove BG | `lucataco/remove-bg` | $0.01 | Step 1: background removal |
| Kontext Max | `black-forest-labs/flux-kontext-max` | $0.08 | Steps 2, 3, 5 (compositing) |
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

## Current Status

- **Pipeline proven** — 5-step wizard working end-to-end, scores 93–97/100
- **Wardrobe picker** — Step 4 has interactive outfit choice UI (Adventurer + Wizard)
- **Scene prompt v3** — landscape 4:3, wide panoramic, character left-of-centre composition
- **Hair preservation** — costume prompts now inject `{subject}` via `get_costume_prompt()`
- **Prodigi integration** — fulfillment partner selected; see `docs/PRODIGI.md` + `docs/PRODIGI_LAUNCH_CHECKLIST.md`
- **Upscale 4x** — now outputs print-ready resolution for 110pc + 252pc puzzles
- **Next:** Order sample puzzle via Prodigi dashboard, add export step for print-ready files

## Known Issues

- Character size in compositing is unpredictable — model ignores percentage instructions
- FLUX 2 Pro safety filter occasionally triggers on benign content (retry with different seed)
- Kontext Max outputs capped at ~1024px — hard limit; `laplacian_variance` stays low until upscaled
- white_patch scorer produces false positives on pure scene images — expected, only meaningful on composites
