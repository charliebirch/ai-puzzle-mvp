# AI Puzzle MVP

Transform family photos into magical fantasy character jigsaw puzzles using AI. Supports multiple AI backends with face-preserving identity lock, automated quality scoring, print-ready export, and a web interface for order processing.

## Architecture

```
AI-PUZZLE-MVP/
├── src/
│   ├── backends/              # AI model backends
│   │   ├── base.py            # Abstract base class
│   │   ├── seedream.py        # ByteDance Seedream-4 (two-step)
│   │   ├── instantid.py       # InstantID (SDXL + face lock)
│   │   ├── flux_pulid.py      # Flux-PuLID (face identity)
│   │   ├── ip_adapter_faceid.py  # IP-Adapter FaceID
│   │   └── registry.py        # Backend factory
│   ├── quality/               # Quality assessment
│   │   ├── face_similarity.py # InsightFace ArcFace embeddings
│   │   ├── image_quality.py   # Sharpness, contrast, color metrics
│   │   ├── human_eval.py      # Human evaluation CLI
│   │   └── __init__.py        # Unified assess_quality()
│   ├── puzzle_maker.py        # Main CLI pipeline (model-agnostic)
│   ├── benchmark_runner.py    # Multi-backend benchmark matrix
│   ├── fulfill_order.py       # End-to-end order fulfillment
│   ├── export.py              # Print-ready & preview export
│   ├── upscale.py             # Real-ESRGAN upscaling
│   ├── print_specs.py         # Puzzle dimensions & print profiles
│   ├── style_presets.py       # 4 style presets
│   ├── consent.py             # Consent event logging
│   ├── test_suite.py          # Test photo registry
│   └── face_guidance.py       # Legacy guidance maps
├── web/
│   ├── app.py                 # FastAPI web interface
│   ├── jobs.py                # SQLite job tracking
│   ├── templates/             # Jinja2 + HTMX templates
│   └── static/                # CSS
├── docs/
│   ├── terms-of-service.md
│   ├── privacy-policy.md
│   ├── consent-flow.md
│   └── etsy-listing-template.md
├── input/                     # Customer photos (one subfolder per person)
├── output/                    # Generated output
└── orders/                    # Per-order directories
```

## Quick Start

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set API key
echo "REPLICATE_API_TOKEN=r8_your_key_here" > .env
```

## Usage

### Generate a puzzle (CLI)
```bash
python src/puzzle_maker.py \
  --input input/Chaz/charlie-outside.jpg \
  --output output/puzzle.png \
  --style fairytale \
  --subject "a young girl" \
  --backend instantid
```

### Run benchmarks
```bash
python src/benchmark_runner.py \
  --backends instantid flux_pulid seedream \
  --styles fairytale storybook_cartoon \
  --subject "a smiling child"
```

### Fulfill an order
```bash
python src/fulfill_order.py \
  --photo customer.jpg \
  --style fairytale \
  --subject "a young girl" \
  --puzzle-size 1000 \
  --order-id ETSY-12345 \
  --backend instantid
```

### Web interface
```bash
uvicorn web.app:app --reload --port 8000
# Open http://localhost:8000
```

### Quality scoring
```bash
# Image quality metrics
python src/quality/image_quality.py output/generated.png

# Human evaluation
python src/quality/human_eval.py eval output/benchmarks/ --source input/Chaz/charlie-outside.jpg
python src/quality/human_eval.py summary
```

## AI Backends

| Backend | Face Lock | Mode | Cost/Run |
|---------|-----------|------|----------|
| Seedream-4 | No | Two-step | $0.03 |
| Seedream-4 Single | No | Single | $0.03 |
| InstantID | Yes | Single | $0.015 |
| Flux-PuLID | Yes | Single | $0.021 |
| IP-Adapter FaceID | Yes | Single | $0.058 |

## Styles

- **fairytale** - Enchanted prince/princess in magical forest
- **superhero** - Comic-book hero on futuristic skyline
- **pixel_quest** - 8-bit RPG adventurer in retro world
- **storybook_cartoon** - Pixar-like character in whimsical village

## Quality Scoring

Composite 0-100 score:
- Face similarity (35%) - InsightFace ArcFace embeddings
- Resolution (20%) - vs print target dimensions
- Sharpness (15%) - Laplacian variance
- Color diversity (15%) - Histogram entropy
- Contrast (10%) - RMS contrast
- Face detection confidence (5%)

## Print Specs

| Size | Dimensions | Pixels (300 DPI) | Price |
|------|-----------|-------------------|-------|
| 500pc | 16" x 20" | 4800 x 6000 | $39.99 |
| 1000pc | 20" x 28" | 6000 x 8400 | $49.99 |

## Requirements

- Python 3.10+
- Replicate API key
- Internet connection for AI and upscaling
