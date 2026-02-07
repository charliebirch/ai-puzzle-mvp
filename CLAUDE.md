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

Two pipeline modes, both using FLUX Kontext:

```
Animation (single-step):  Photo → FLUX Kontext Pro ($0.04) → Quality Score → Upscale ($0.002) → Export
Cartoon (two-step):       Photo → Cartoonify ($0.04) → FLUX Kontext Pro ($0.04) → Quality Score → Upscale ($0.002) → Export
```

**Cost: ~$0.04 (animation) or ~$0.08 (cartoon two-step) + $0.002 upscale**

Face swap is **disabled for all active styles** — it made images too photorealistic for the cartoon art direction. The codeplugtech/face-swap backend is still available for CLI testing if needed.

- **Default backend:** `flux_kontext` (Kontext Pro, $0.04/run) — web default
- **Also available:** `flux_kontext_max` (Kontext Max, $0.08/run), `flux_cartoonify` (cartoon filter, $0.04/run)
- **Default style:** `animation_village` (Pixar-like character in magical village)

## Key Commands

```bash
# Activate environment first
source .venv/bin/activate

# Process an order
python3 src/fulfill_order.py \
  --photo input/Chaz/charlie-ny.jpeg \
  --style animation_village \
  --subject "a young man" \
  --puzzle-size 500 \
  --order-id TEST-001 \
  --skip-consent

# Quick puzzle (no quality/upscale/export steps)
python3 src/puzzle_maker.py \
  --input input/Chaz/charlie-outside.jpg \
  --output output/puzzle.png \
  --style animation_village \
  --subject "a young man"

# Run benchmarks
python3 src/benchmark_runner.py --styles animation_village

# Web interface
python3 -m uvicorn web.app:app --reload --port 8000

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
    base.py                # BaseBackend ABC + _extract_url() helper
    flux_kontext.py        # FLUX Kontext Pro backend ($0.04/run)
    flux_kontext_max.py    # FLUX Kontext Max backend ($0.08/run)
    flux_cartoonify.py     # Cartoon filter backend ($0.04/run, step 1 of cartoon pipeline)
    easel_swap.py          # codeplugtech/face-swap (available but disabled for active styles)
    registry.py            # Backend factory (3 registered: Pro, Max, Cartoonify)
  quality/
    __init__.py            # assess_quality() composite scorer (cartoon-tuned weights)
    face_similarity.py     # InsightFace ArcFace embedding comparison
    image_quality.py       # Color vibrancy, edge cleanliness, color diversity, resolution
    human_eval.py          # Manual scoring CLI
  fulfill_order.py         # Full pipeline (main entry point), supports both single/two-step
  puzzle_maker.py          # Quick single-image generation
  style_presets.py         # 6 active styles (3 animation + 3 cartoon), shelved styles for testing
  export.py                # Preview (with grid) + print-ready (with bleed)
  upscale.py               # Real-ESRGAN via Replicate (~$0.002/run)
  print_specs.py           # Puzzle dimensions for 500pc and 1000pc
  consent.py               # JSONL consent logging
  benchmark_runner.py      # Test matrix runner
  benchmark_report.py      # HTML benchmark report generator
  test_photos.json         # Test photo matrix for benchmarking
web/
  app.py                   # FastAPI + Jinja2 + HTMX
  jobs.py                  # SQLite job tracking
  templates/               # HTML templates
docs/                      # Legal (ToS, privacy, consent flow, Etsy listing)
```

## Current Priorities

1. **Quality to 80+ composite** — scoring reweighted for cartoon-only pipeline (vibrancy + edges + color diversity).
2. **End-to-end testing** — run diverse photos through animation + cartoon styles.
3. **Prompt tuning** — improve kontext_prompt for each style.
4. **Customer preview flow** — easy way to send a preview to the customer and get approval before printing.
5. **New styles** — expand beyond the 6 active styles once quality is dialed in.

## Quality Scoring

Composite 0-100, **pass threshold is 70** (but Charlie wants 80+ before launching).

Tuned for **cartoon-only pipeline** (no face swap) — reduced face similarity weight since cartoon transforms naturally score 0.30–0.42. Visual quality metrics carry most of the weight.

| Metric | Weight | Source |
|--------|--------|--------|
| Color vibrancy | 25% | HSV mean saturation + high-saturation ratio |
| Edge cleanliness | 20% | Canny edge density (5-18% sweet spot) |
| Color diversity | 20% | Histogram entropy |
| Face similarity | 15% | InsightFace ArcFace cosine distance |
| Face detection confidence | 10% | Detector confidence |
| Resolution | 10% | vs print target (6000x8400 or 4800x6000) |

**Dropped:** sharpness (penalized cartoon soft shading), contrast (penalized warm tones).

A good cartoon with face sim 0.35 can now score ~81 (achievable target).

## Styles

Six active styles across two art modes. Styles are selected in the web UI via Art Style + Scene dropdowns which combine into a style key (e.g., `animation_village`).

All active styles have **face swap disabled** — cartoon art looks better without photorealistic face overlay.

| Style | Pipeline | Theme |
|-------|----------|-------|
| animation_village | Single-step Kontext | Pixar-like character in magical village |
| animation_space | Single-step Kontext | Cartoon astronaut in whimsical outer space |
| animation_underwater | Single-step Kontext | Cartoon diver in vibrant underwater world |
| cartoon_village | Two-step (Cartoonify + Kontext) | Cartoon filter then magical village scene |
| cartoon_space | Two-step (Cartoonify + Kontext) | Cartoon filter then space scene |
| cartoon_underwater | Two-step (Cartoonify + Kontext) | Cartoon filter then underwater scene |

Shelved styles (CLI/benchmark only): storybook_cartoon, space_explorer, underwater_adventure, pixel_platformer, storybook_identity, storybook_stylized, fairytale, superhero.

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
| Dropped 5 legacy backends | Seedream, InstantID, Flux-PuLID, IP-Adapter, NanoBanano | Dead code after benchmarking; Kontext+swap won | Cleanup session |
| Scoring redesign | Cartoon-tuned weights | Old weights rewarded photorealism; storybook_cartoon scored 67.6 avg. New weights reward vivid colors + clean edges | Scoring overhaul |
| Disable face swap for all styles | Cartoon-only pipeline | Face swap made output too photorealistic for kids' puzzle product | New models session |
| Default model: Pro not Max | Kontext Pro ($0.04) | Half the cost of Max, comparable quality for cartoon art. Max stays available for premium orders | New models session |
| Scoring reweight | Face sim 15%, vibrancy 25%, edges 20%, diversity 20% | 80+ composite achievable without face swap (face sim 0.35 → ~81 score) | New models session |
| Added Kontext Max + Cartoonify | 3 registered backends | Max for premium quality, Cartoonify enables two-step cartoon pipeline | New models session |
| 6 active styles | 3 animation + 3 cartoon | Two art modes (single-step vs two-step) x 3 scenes (village, space, underwater) | New models session |

## Known Issues

- **Quality inconsistency** — same photo can give different results each run (seed now exposed in web UI for reproducibility)
- **README.md is outdated** — still references deleted backends and old commands
- **No batch processing** — each order must be run manually
