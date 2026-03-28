# Best Practices — AI Puzzle Character & Scene Generation

Learnings from extensive testing (March 2026). Follow these to avoid re-discovering mistakes.

---

## Input Photos

- **Clear, well-lit face** looking at or near camera
- **One person only** — no group shots
- **No sunglasses on face** (on head is fine)
- **Background doesn't matter** — it gets removed in step 1
- Front-facing or slight angle works best. Avoid full profiles.

## Background Removal (Step 1)

- **Always remove the background first.** This is the single biggest quality improvement we found.
- Replace with **white** (not black, not transparent). White gives the best results for the character generation step.
- Model: `lucataco/remove-bg` on Replicate (~$0.01)
- Composite the transparent result onto a white `(255, 255, 255)` background using PIL alpha compositing.

## Character Generation (Step 2)

### What works
- **Kontext Max** (`flux-kontext-max`, $0.08) — preserves likeness much better than Pro ($0.04)
- **Preserve first, stylize second.** Tell the model to KEEP features, not to exaggerate them.
- **"Do not enlarge the eyes"** — without this, every character gets bug eyes
- **"A warm, natural smile"** — allows creative freedom without over-exaggeration
- **Gender hints** prevent the model defaulting to generic proportions:
  - Female: "Soft feminine features, delicate jawline"
  - Male: "Natural masculine features"
- **Bust portrait composition** with clean silhouette edges for compositing

### What doesn't work
- "Exaggerated cartoon proportions, big expressive eyes" → bug-eyed, masculine jaw on women
- "Inspired by this person's general appearance" → too loose, loses likeness
- "Maintain their exact expression" → too restrictive, makes output stiff
- Kontext Pro ($0.04) → not enough likeness preservation for this step

### Proven character prompt
```
Transform this photo into a Pixar-like 3D animated character. Keep the person's
face shape, skin tone, hair color, and hairstyle exactly as they are. Gentle
Pixar-style cartoon features — keep natural facial proportions and eye size.
[Soft feminine features, delicate jawline | Natural masculine features].
A warm, natural smile. Soft cartoon shading, smooth skin. Do not enlarge the eyes.
Keep the same pose and framing. Plain white background.

Composition:
- Bust portrait, shoulders up
- Slight 3/4 angle, centred
- Plain white background
- Clean silhouette edges suitable for compositing
- Simple [clothing description] without logos or text emphasis
```

## Costume (Step 3)

- Keep it as a **separate step** from character generation. Asking the model to transform AND costume in one shot degrades both.
- Input: the white-background character from Step 2
- Describe the themed outfit explicitly (leather vest, cape, boots, etc.)
- **Always say**: "Keep their face, skin tone, hair, glasses, and expression exactly the same. Keep the white background."
- The costume step is cheap ($0.08) and dramatically improves the final image.

## Scene Generation (Step 4)

- Generate scenes with **NO PEOPLE**. The character gets composited in separately.
- **Pack every inch with detail** — this is what makes a good puzzle:
  - Name 15+ specific objects
  - Specify objects in corners (sleeping cat, potted flowers, postbox)
  - 3 depth layers: foreground objects, midground buildings, background sky/hills
  - Sky must have clouds, rainbow, birds, hot air balloon — not flat blue
- The scene prompt is where puzzle rules belong, NOT the compositing prompt.

## Compositing (Step 5)

Three methods discovered, each with different strengths:

### Method E: Kontext Max single-image blend
- PIL composite character onto scene → send through Kontext Max
- **Best for:** Seamlessness. Character feels like they belong.
- **Downside:** 1024px output. Face detail limited at print size.
- **Cost:** $0.08

### Method K: FLUX 2 Pro two-image
- Send character + scene as two separate `input_images` to FLUX 2 Pro
- **Best for:** Overall quality and resolution (2000x2000)
- **Downside:** Character tends to be too big (~40%). Can't control size reliably.
- **Cost:** ~$0.08

### Method Q: FLUX 2 Pro with distance language
- Same as K but prompt says "further down the path, in the midground"
- **Best for:** Smaller character in the scene while maintaining quality
- **Downside:** Size still somewhat unpredictable
- **Cost:** ~$0.08

### Compositing rules
- **Keep the prompt simple.** Don't overload with puzzle rules — it causes lighting artifacts.
- **Never say** "fill every corner" or "maximum detail" in the compositing prompt — the model interprets this as "blast light on everything."
- **Do say** "keep everything exactly as it is, just make it look unified and natural."
- Run 2-3 seeds and pick the best — quality varies per generation.

## Resolution Constraints

| Model | Max Output | Notes |
|-------|-----------|-------|
| Kontext Max | ~1024px | Hard limit, no resolution parameter |
| Kontext Pro | ~1024px | Same limit |
| FLUX 2 Pro | ~2000px | Set `resolution: "4 MP"` |

This is the fundamental tradeoff: Kontext blends better but at lower resolution. FLUX 2 Pro gives higher resolution but treats inputs as separate things.

## Puzzle Quality Scoring

Use `src/quality/puzzle_scorer.py` to validate final outputs.

- **Pass threshold:** 65/100
- **Target:** 80+
- **Our best score:** 95.3/100

Key metrics (from `docs/complete-ai-puzzle-guide-deep-research.md`):
- Flat regions under 25% (no large single-color areas)
- Detail in all four corners
- 8+ hue bins occupied
- Subject under 50% of image area (ideally 5-15%)
- No dominant colour over 35%

## Cost Summary

| Step | Model | Cost |
|------|-------|------|
| Background removal | lucataco/remove-bg | $0.01 |
| Character generation | flux-kontext-max | $0.08 |
| Costume | flux-kontext-max | $0.08 |
| Scene generation | flux-kontext-max | $0.08 |
| Compositing (per method) | Kontext Max or FLUX 2 Pro | $0.08 |
| **Total (one method)** | | **$0.33** |
| **Total (all 3 methods)** | | **$0.49** |
