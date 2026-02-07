# CLAUDE.md - AI Puzzle MVP

## What This Project Is

An Etsy business that transforms customer photos into **animated kids' jigsaw puzzles** — Pixar-style cartoon art, not photorealistic. Currently **pre-launch** — focused on quality consistency and end-to-end testing before taking real orders.

The owner (Charlie) has some coding ability but relies on Claude Code as the primary engineering partner. He can read and modify code but needs clear documentation to maintain it.

## Working With Charlie

- **Always plan first.** Propose changes before making them. Charlie wants to approve the approach.
- **Be concise.** Don't over-explain or pad responses.
- **Keep costs visible.** Before running any Replicate API calls, show the estimated cost.
- **Don't break working code.** Verify imports/functionality before and after changes.
- **Track decisions.** When we make a significant choice (model, architecture, approach), record it in MEMORY.md with reasoning so we don't revisit settled questions.
- **Document code.** Add docstrings and comments — Charlie reads the code to understand what's happening.

## Production Pipeline

```
Customer Photo → FLUX Kontext Pro ($0.04) → codeplugtech/face-swap ($0.003) → Quality Score → Upscale ($0.002) → Export
```

**Total: ~$0.045/image, ~44 seconds**

This pipeline is settled (TEST-005). Don't suggest switching backends unless Charlie asks.

- **Backend:** `flux_kontext` (only registered backend in `src/backends/registry.py`)
- **Face swap:** On by default (`--no-face-swap` to disable)
- **Why this combo:** Kontext preserves hair/appearance from the photo but produces generic faces (0.33 similarity alone). Face swap fixes facial identity (0.88 combined).

## Key Commands

```bash
# Activate environment first
source .venv/bin/activate

# Process an order (face swap on by default)
python3 src/fulfill_order.py \
  --photo input/Chaz/charlie-ny.jpeg \
  --style storybook_cartoon \
  --subject "a young man" \
  --puzzle-size 500 \
  --order-id TEST-001 \
  --skip-consent

# Quick puzzle (no quality/upscale/export steps)
python3 src/puzzle_maker.py \
  --input input/Chaz/charlie-outside.jpg \
  --output output/puzzle.png \
  --style storybook_cartoon \
  --subject "a young man"

# Run benchmarks
python3 src/benchmark_runner.py --styles storybook_cartoon

# Web interface
uvicorn web.app:app --reload --port 8000

# Verify imports
cd src && python3 -c "from backends.registry import list_backends; print(list_backends())"
```

## Environment

- **macOS** — use `python3` not `python`
- **Photos** are in `input/<Name>/` subfolders (e.g., `input/Chaz/`, `input/Edgar/`)
- **Order output** goes to `orders/<order_id>/` (gitignored)
- **API key** is in `.env` as `REPLICATE_API_TOKEN`
- All AI calls go through **Replicate** — needs internet

## Project Structure

```
src/
  backends/
    base.py              # BaseBackend ABC + _extract_url() helper
    flux_kontext.py      # FLUX Kontext Pro backend (the only active one)
    easel_swap.py        # codeplugtech/face-swap post-processing
    registry.py          # Backend factory (only flux_kontext registered)
  quality/
    __init__.py          # assess_quality() composite scorer (cartoon-tuned weights)
    face_similarity.py   # InsightFace ArcFace embedding comparison
    image_quality.py     # Color vibrancy, edge cleanliness, color diversity, resolution
    human_eval.py        # Manual scoring CLI
  fulfill_order.py       # Full 6-step order pipeline (main entry point)
  puzzle_maker.py        # Quick single-image generation
  style_presets.py       # Active: storybook_cartoon. Shelved: fairytale, superhero, pixel_quest
  export.py              # Preview (with grid) + print-ready (with bleed)
  upscale.py             # Real-ESRGAN via Replicate
  print_specs.py         # Puzzle dimensions for 500pc and 1000pc
  consent.py             # JSONL consent logging
  benchmark_runner.py    # Test matrix runner
web/
  app.py                 # FastAPI + Jinja2 + HTMX
  jobs.py                # SQLite job tracking
  templates/             # HTML templates
docs/                    # Legal (ToS, privacy, consent flow, Etsy listing)
```

## Current Priorities

1. **Quality to 80+ composite** — scoring now tuned for cartoon art (vibrancy + edge cleanliness instead of sharpness + contrast).
2. **End-to-end testing** — run diverse photos (different ages, skin tones, hair types) through storybook_cartoon.
3. **Storybook cartoon prompt tuning** — improve the kontext_prompt for even better output.
4. **Customer preview flow** — easy way to send a preview to the customer and get approval before printing.
5. **New styles** — once storybook_cartoon is dialed in, add more animated styles (anime, watercolor).

## Quality Scoring

Composite 0-100, **pass threshold is 70** (but Charlie wants 80+ before launching).

Tuned for **animated cartoon art** — rewards vivid colors and clean edges, not photorealism.

| Metric | Weight | Source |
|--------|--------|--------|
| Face similarity | 40% | InsightFace ArcFace cosine distance |
| Color vibrancy | 20% | HSV mean saturation + high-saturation ratio |
| Face detection confidence | 10% | Detector confidence |
| Resolution | 10% | vs print target (6000x8400 or 4800x6000) |
| Edge cleanliness | 10% | Canny edge density (5-18% sweet spot) |
| Color diversity | 10% | Histogram entropy |

**Dropped:** sharpness (penalized cartoon soft shading), contrast (penalized warm tones).

## Styles

Four active styles for production. Other styles are shelved in `_SHELVED_STYLES` (still usable for testing/benchmarks via `get_style()`).

Styles can set `"face_swap": False` to auto-disable face swap (e.g. pixel art styles where a photorealistic face looks wrong).

| Style | Status | Face Swap | Theme |
|-------|--------|-----------|-------|
| storybook_cartoon | **Active** | Yes | Pixar-like character in whimsical village |
| space_explorer | **Active** | Yes | Cartoon astronaut in bright, playful outer space |
| underwater_adventure | **Active** | Yes | Cartoon deep-sea explorer with coral reefs and sea creatures |
| pixel_platformer | **Active** | **No** | Pixel art character in colourful side-scrolling platformer |
| fairytale | Shelved | Yes | Enchanted prince/princess in magical forest |
| superhero | Shelved | Yes | Comic-book hero on futuristic skyline |

## Print Specs

| Size | Physical | Pixels (300 DPI) | Target Price |
|------|----------|-------------------|-------------|
| 500pc | 16" x 20" | 4800 x 6000 | $39.99 |
| 1000pc | 20" x 28" | 6000 x 8400 | $49.99 |

Print supplier not yet chosen — not a current priority.

## Decisions Log

| Decision | Choice | Why | Date |
|----------|--------|-----|------|
| Primary backend | FLUX Kontext Pro | Preserves hair/appearance from pixel reference, instruction-based | TEST-003 |
| Face fix method | codeplugtech/face-swap | Simple 2-param API, $0.003, fixes Kontext's weak faces | TEST-005 |
| Dropped InstantID | ArcFace embeddings discard hair | No parameter tuning can fix this — architectural limitation | TEST-004 |
| Dropped Easel advanced-face-swap | Discontinued/stalling | Replaced with codeplugtech which actually works | TEST-005 |
| Dropped 5 legacy backends | Seedream, InstantID, Flux-PuLID, IP-Adapter, NanoBanana | Dead code after benchmarking; Kontext+swap won | Cleanup session |
| Scoring redesign | Cartoon-tuned weights | Old weights rewarded photorealism; storybook_cartoon scored 67.6 avg. New weights reward vivid colors + clean edges | Scoring overhaul |
| Style pivot | storybook_cartoon only | Best fit for animated kids' puzzles product. Other styles shelved. | Scoring overhaul |

## Known Issues

- **Quality inconsistency** — same photo can give different results each run (no seed pinning in production)
- **README.md is outdated** — still references deleted backends and old commands
- **No batch processing** — each order must be run manually
