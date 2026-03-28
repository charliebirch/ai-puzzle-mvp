# AI Puzzle MVP

Transform customer photos into personalised Pixar-style animated jigsaw puzzles for Etsy.

## How It Works

A 5-step AI pipeline turns a customer photo into a puzzle-ready image:

1. **Remove Background** — strips the background, isolates the person
2. **Generate Character** — transforms the person into a Pixar-style 3D animated character
3. **Apply Costume** — dresses the character in a themed outfit (fantasy adventurer, astronaut, etc.)
4. **Generate Scene** — creates a detailed empty scene packed with puzzle-friendly detail
5. **Composite** — places the costumed character into the scene seamlessly

Each step uses AI models on [Replicate](https://replicate.com). Total cost per puzzle: **~$0.33-$0.49**.

## Scenes

- **Magical Village** — cobblestone streets, crooked houses, floating lanterns, bridge over a stream
- **Space Adventure** — planets, rocket ships, nebulas, friendly aliens
- **Underwater World** — coral reefs, sea creatures, sunken treasure, shimmering bubbles

## Quality

Every output is scored by an automated puzzle quality checker (11 metrics, 0-100 scale). A good puzzle needs detail in every corner, diverse colours, and no large flat areas. Our best score: **95.3/100**.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env  # Add your REPLICATE_API_TOKEN
```

## Status

**Pre-launch.** Pipeline proven with multiple test subjects. Web app rebuild in progress.

## Docs

- [Best Practices](docs/BEST_PRACTICES.md) — what works, what doesn't, prompt engineering rules
- [Pipeline Reference](docs/PIPELINE.md) — exact models, prompts, parameters, costs
- [Puzzle Design Guide](docs/complete-ai-puzzle-guide-deep-research.md) — research on what makes a good puzzle
