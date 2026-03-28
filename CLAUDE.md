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
Photo → Remove BG ($0.01) → Character ($0.08) → Costume ($0.08) → Scene ($0.08) → Composite ($0.08)
```

1. **Background Removal** — `lucataco/remove-bg`, composite onto white
2. **Character Generation** — `flux-kontext-max`, Pixar transform preserving identity
3. **Costume** — `flux-kontext-max`, dress in themed outfit (white bg kept)
4. **Scene Generation** — `flux-kontext-max`, empty detailed scene (no people)
5. **Compositing** — 3 methods to compare:
   - **Method E:** PIL composite → Kontext Max blend (1024px, best seamlessness)
   - **Method K:** FLUX 2 Pro two-image input (2000px, best quality)
   - **Method Q:** FLUX 2 Pro with distance language (2000px, smaller character)

**Cost:** ~$0.33 per puzzle (one method) or ~$0.49 (all three methods)

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
    puzzle_scorer.py     # 11-metric puzzle quality scorer (target: 65+ pass, 80+ good)
  fulfill_order.py       # Simplified pipeline (rebuild pending for full 5-step)
  style_presets.py       # Scene presets (rebuild pending)
  remove_background.py   # Background removal via Replicate ($0.01)
  subject_builder.py     # Structured subject description builder
web/
  app.py                 # FastAPI + Jinja2 + HTMX (rebuild pending)
  jobs.py                # SQLite job tracking
  templates/             # HTML templates
  static/                # CSS
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

Use `src/quality/puzzle_scorer.py` — 11 metrics, 0-100 composite score.

| Threshold | Grade |
|-----------|-------|
| >= 65 | PASS |
| 40-64 | WARNING |
| < 40 | FAIL |
| Hard fail triggers | HARD FAIL |

Best score achieved: **95.3/100** on village scene with costumed character.

Key metrics: flat regions (<25%), corner detail, hue diversity (8+ bins), edge density, subject dominance (<50%).

## Print Specs

| Size | Physical | Pixels (300 DPI) | Target Price |
|------|----------|-------------------|-------------|
| 500pc | 16" x 20" | 4800 x 6000 | $39.99 |
| 1000pc | 20" x 28" | 6000 x 8400 | $49.99 |

## Models Used

| Model | Replicate ID | Cost | Used For |
|-------|-------------|------|----------|
| Remove BG | `lucataco/remove-bg` | $0.01 | Step 1: background removal |
| Kontext Max | `black-forest-labs/flux-kontext-max` | $0.08 | Steps 2-4 + Method E |
| Kontext Pro | `black-forest-labs/flux-kontext-pro` | $0.04 | Available, not default |
| FLUX 2 Pro | `black-forest-labs/flux-2-pro` | ~$0.08 | Methods K & Q compositing |
| Real-ESRGAN | `nightmareai/real-esrgan` | $0.002 | Upscaling (future) |

## Decisions Log

| Decision | Choice | Why | Date |
|----------|--------|-----|------|
| Multi-step pipeline | 5 separate steps | Single prompt fails at both character AND scene quality | 2026-03-28 |
| Background removal first | lucataco/remove-bg | Removes distracting elements, model focuses on person | 2026-03-28 |
| Kontext Max for character | $0.08 over Pro $0.04 | Pro loses too much likeness | 2026-03-28 |
| White background between steps | White, not transparent | Best results for AI model input | 2026-03-28 |
| Separate costume step | Don't combine with character gen | Doing both in one prompt degrades both | 2026-03-28 |
| Empty scenes (no people) | Generate scenes separately | AI can't do character + scene in one shot well | 2026-03-28 |
| 3 compositing methods | E, K, Q for comparison | Each has tradeoffs (seamlessness vs resolution vs size) | 2026-03-28 |
| FLUX 2 Pro for compositing | 2000px output, multi-image | Kontext Max capped at 1024px | 2026-03-28 |
| Don't exaggerate features | "Do not enlarge eyes" | Bug-eyed characters, masculine jaws on women | 2026-03-28 |
| Gender-specific prompts | Feminine/masculine hints | Generic proportions without hints | 2026-03-28 |

## Current Status

- **Pipeline proven** — tested with multiple subjects, quality scores 85-95
- **App rebuild pending** — current web app has old single-step flow
- **Repo cleaned** — old code archived in `_archive/`, active code is minimal
- **Next:** Build app that runs all 5 steps and shows 3 compositing methods side-by-side

## Known Issues

- Character size in compositing is unpredictable — model ignores percentage instructions
- FLUX 2 Pro safety filter occasionally triggers on benign content (retry with different seed)
- Kontext Max outputs capped at ~1024px — hard limit, no workaround
- Quality varies per generation — run multiple seeds and pick best
