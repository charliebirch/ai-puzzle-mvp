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
- Model: `recraft-ai/recraft-remove-background` on Replicate (~$0.01)
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
- **Always include `{subject}` in the costume prompt** — "This character is {subject}. Keep their face, skin tone, hair colour, hair texture, and hairstyle exactly as they are — do not alter the hair in any way." Without explicit text the model will alter hair to match outfit archetype (e.g. wizard hat → long flowing hair replaces the original).
- **Wizard outfit special case** — add: "the wizard hat sits on top of their existing hair, it does not replace or hide it." Without this the hat replaces the hair entirely.
- Use `get_costume_prompt(scene_id, subject, outfit_id)` in `scene_prompts.py` — it handles both outfit selection and `{subject}` formatting.
- The costume step is cheap ($0.08) and dramatically improves the final image.

## Orientation — Landscape 4:3

All pipeline outputs are landscape (4:3 aspect ratio). This matches all Prodigi puzzle formats.

- **FLUX 2 Pro scene gen:** `"aspect_ratio": "4:3"` in Replicate inputs
- **Kontext Max compositing:** `aspect_ratio="4:3"` passed to backend
- **Composite layout:** Character at ~38% from left centre — leaves right ~60% as visible scene
- **Scene prompt:** Must describe a wide horizontal composition — street running left-to-right, elements on both sides, wide sky

## Scene Generation (Step 4)

- Generate scenes with **NO PEOPLE**. The character gets composited in separately.
- **Pack every inch with detail** — this is what makes a good puzzle:
  - Name 20+ specific objects across 3 depth layers
  - **Explicit corner callouts are critical** — name one object per corner; corners are assembled first
  - 3 depth layers: foreground objects, midground buildings, background sky/hills
  - Sky must have 3+ hue variations (golden-orange → coral → lavender-blue), light rays, and layered cloud formations — not flat blue
  - Stream/water needs surface detail: reflections, ripples, lily pads — otherwise it's a flat zone
  - Houses need interior window detail: curtains, flower pots visible inside — missed texture zone
  - Ground needs texture variation: moss between cobblestones, puddles, fallen petals, worn edges
  - Add a hard rule: "no large areas of uniform colour anywhere — every surface has texture, wear, or pattern"
- **NO TEXT rule** — specify "No text, words, letters, or writing anywhere. All signs, awnings, and surfaces must be plain or patterned." The only exception is clock faces with Roman numerals (which look great).
  - Name risky objects explicitly: "plain red postbox with no text", "blank arrow-shaped signpost boards (no writing)", "plain striped awning (no name)"
- The scene prompt is where puzzle rules belong, NOT the compositing prompt.
- **Sky hue diversity** — explicitly name the colours: "vivid cornflower blue and lavender-purple at the top, fading through coral and pink toward the horizon." Without this the model defaults to warm golden-only palette (5 hue bins) and fails the hue_diversity metric (needs 8+).

## Compositing (Step 5)

Only Method E is currently active. Methods K and Q are removed.

### Method E: Kontext Max single-image blend (active)
- PIL composite character onto scene → send through Kontext Max 3× with different seeds → quality-score → user picks
- **Best for:** Seamlessness. Character feels like they belong.
- **Downside:** 1024px output. Face detail limited at print size.
- **Cost:** $0.08 × 3 = $0.24

### Compositing rules
- **Protect scene detail explicitly.** Kontext Max will simplify the background to make the blend look clean — catastrophic for puzzle quality. The composite prompt MUST say "keep ALL background detail exactly as it is — do not alter, blur, or simplify any buildings, textures, or objects."
- **Name the corners in the composite prompt.** If the scene prompt names corner objects, name them again in the composite prompt so the model knows to preserve them.
- **Never say** "fill every corner" or "maximum detail" — the model interprets this as "blast light on everything."
- **Do say** "keep everything exactly as it is, just make it look unified and natural."
- Run 3 seeds and pick the best — quality varies per generation. Seeds should be widely spaced (base, base+31337, base+77777).
- **Add no-text rule to composite prompt too** — "Do not add any text, words, letters, or writing anywhere."

## Resolution Constraints

| Model | Max Output | Notes |
|-------|-----------|-------|
| Kontext Max | ~1024px | Hard limit, no resolution parameter |
| Kontext Pro | ~1024px | Same limit |
| FLUX 2 Pro | ~2000px | Set `resolution: "4 MP"` |

This is the fundamental tradeoff: Kontext blends better but at lower resolution. FLUX 2 Pro gives higher resolution but treats inputs as separate things.

### Print Resolution Requirements (Prodigi)

Upscale uses Real-ESRGAN **4x** (not 2x). Anime model (xinntao) currently broken on Replicate — use general model.

| Puzzle | Physical size | Required px @ 300 DPI | Covered by 4x upscale? |
|--------|--------------|----------------------|----------------------|
| 110pc | 250×200mm | 2953×2362px | ✓ (1024→4096px) |
| 252pc | 375×285mm | 4429×3366px | ✓ (1152→4608px) |
| 500pc | 530×390mm | 6260×4606px | Marginal (1536→6144px) |
| 1000pc | 765×525mm | 9035×6165px | ✓ (2048→8192px) |

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
| Background removal | recraft-ai/recraft-remove-background | $0.01 |
| Character generation | flux-kontext-max | $0.08 |
| Costume | flux-kontext-max | $0.08 |
| Scene generation | flux-kontext-max | $0.08 |
| Compositing (per method) | Kontext Max or FLUX 2 Pro | $0.08 |
| **Total (one method)** | | **$0.33** |
| **Total (all 3 methods)** | | **$0.49** |
