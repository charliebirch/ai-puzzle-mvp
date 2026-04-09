# Pipeline Technical Reference

Exact models, prompts, and parameters for each step.

**Total cost:** ~$0.57 per full run (steps 1–6).

---

## Step 1: Background Removal

**Model:** `recraft-ai/recraft-remove-background` on Replicate (default)
**Fallback:** `lucataco/remove-bg` — set `BG_REMOVAL_BACKEND=lucataco` env var
**Cost:** ~$0.01
**Code:** `src/remove_background.py`

```python
output = replicate.run(REPLICATE_MODEL, input={_INPUT_KEY: f})
# Returns PNG with transparent background
# Composite onto white: Image.alpha_composite(white_bg, fg).convert("RGB")
```

**Input:** Customer photo (any format, any background)
**Output:** White-background RGB JPG (`bg_removed.jpg`)

---

## Step 2b: Portrait Normalisation

**Model:** `black-forest-labs/flux-kontext-max` on Replicate
**Cost:** ~$0.08
**Code:** `src/pipeline_steps.py` → `step_normalize_portrait()`
**Skip:** Set `NORMALIZE_PORTRAIT=0` env var to bypass (e.g. for already-ideal photos)

**Purpose:** Standardises any input photo to a front-facing, shoulders-and-above,
looking-at-camera portrait before the character generation step. Removes dependency
on the customer sending a perfectly framed photo.

**Prompt:** See `NORMALIZE_PROMPT` constant in `pipeline_steps.py`

**Input:** White-background photo from step 1 (`bg_removed.jpg`)
**Output:** Normalised front-facing photorealistic portrait (`normalized.png`)

---

## Step 3: Character Generation

**Model:** `black-forest-labs/flux-kontext-max` on Replicate
**Cost:** ~$0.08
**Code:** `src/pipeline_steps.py` → `step_generate_character()`
**Prompt builder:** `src/scene_prompts.py` → `get_character_prompt(scene_id, subject, gender)`

**Input:** Normalised portrait from step 2b (face-cropped via `_crop_to_face()`)
**Output:** Pixar-style full-body animated character on white background (`character.png`, ~1024px)

**Identity approach:** AI works directly from the input image. No text attributes
(age, ethnicity, hair colour, skin tone) are injected into the prompt — this preserves
the person's actual likeness rather than generating a generic description-based character.

**Subject:** Always `"the person in the input image"`
**Gender hint:** Always `""` (empty — `gender="person"`)

**Prompt structure (see `scene_prompts.py` for full text):**
- ANATOMY — correct human anatomy, ignore background artifacts
- PROPORTIONS — Pixar cartoon proportions (oversized head, 4 heads tall, slim torso)
- IDENTITY — preserve skin tone, ethnicity, hair, face shape from the image
- FACE STYLE — fully Pixar-stylized, NOT photorealistic CGI
- POSE — full figure, whimsical joyful mid-motion pose, Duchenne smile
- STYLE — Pixar 3D, pure white background, no clothing copying

---

## Step 4: Costume

**Model:** `black-forest-labs/flux-kontext-max` on Replicate
**Cost:** ~$0.08
**Code:** `src/pipeline_steps.py` → `step_costume()`
**Prompt builder:** `src/scene_prompts.py` → `get_costume_prompt(scene_id, subject, outfit_id)`

**Input:** Character on white background from step 3 (`character.png`)
**Output:** Same character in chosen outfit, white background (`costumed.png`)

**Available outfits (village scene):**
- `adventurer` — worn leather vest, wide belt with pouches, swirling cape, boots
- `wizard` — deep-purple robes with gold stars, pointed hat, glowing staff

**Identity preservation:** All costume prompts include an IDENTITY LOCK block:
```
IDENTITY LOCK — preserve ALL of the following exactly as they appear in the input image:
face shape, facial proportions, eye colour, nose shape, mouth shape, skin tone,
hair colour, hair texture, and hairstyle. Every facial feature must remain identical.
```

---

## Step 5: Scene Generation

**Model:** `black-forest-labs/flux-2-pro` on Replicate (text-only — no input image)
**Cost:** ~$0.08
**Code:** `src/pipeline_steps.py` → `step_composite()` (generates scene internally)
**Prompt:** `src/scene_prompts.py` → `scene["scene_prompt"]`

**Why flux-2-pro not flux-kontext-max:** Kontext Max errors on the white placeholder
input that was previously used for scene gen. Flux 2 Pro generates from text alone
and produces better panoramic scenes.

**Input:** Text prompt only
**Output:** Empty detailed village scene, no people, 4:3 landscape (`scene.png`)

**Prompt structure:**
- FOREGROUND — cobblestone path, scattered objects, wheelbarrow, barrels
- MIDGROUND — colourful houses, bakery, clock tower, market stalls, stream
- BACKGROUND — multi-colour sky (cornflower blue + lavender + coral), windmill, hot air balloon, rainbow
- CORNER DETAIL — named objects in every corner (critical for puzzle assembly)
- NO TEXT rule — explicit ban on all text/lettering except clock Roman numerals

---

## Step 6: Compositing + Upscale

**Method E only** (Methods K and Q archived — Method E gives best seamlessness)

### Method E: PIL composite → Kontext Max blend

**Model:** `black-forest-labs/flux-kontext-max` × 3 seeds
**Cost:** ~$0.24 (3 × $0.08)
**Code:** `src/pipeline_steps.py` → `step_composite()`, `src/composite_pil.py`

1. PIL composite: paste costumed character onto scene (remove white bg via numpy mask, feather edges, gradient fade)
2. Send composite as single image to Kontext Max with 3 different seeds
3. Quality-score all 3 candidates → display to user for pick

**Prompt:** `scene["composite_E_prompt"]` — instructs model to: seamlessly blend character
into scene, match golden-hour lighting, add ground shadow, preserve all scene detail
(cobblestones, corners, sky), fill ground with cobblestone texture under character feet.

### Upscale

**Model:** `nightmareai/real-esrgan` (general model, `anime=False`)
**Cost:** ~$0.002
**Code:** `src/pipeline_steps.py` → `step_upscale_final()`

Upscales chosen candidate 4× to ~4096px+ for print quality.

### Print Export

**Code:** `src/pipeline_steps.py` → `step_export_for_print()`
**Runs automatically** after upscale.

Outputs:
- `puzzle_surface.jpg` — sRGB JPG, quality=95, 4:4:4 subsampling, exact Prodigi dimensions
- `tin_lid.jpg` — 869×674px, same format

| Size | Pixels | Physical |
|------|--------|----------|
| 252pc | 4429×3366px | 375×285mm |
| 110pc | 2953×2362px | 250×200mm |

---

## Quality Scoring

**Code:** `src/quality/puzzle_scorer.py`
**Function:** `score_puzzle_quality(image_path, puzzle_pieces, source_path=None)`

13 metrics, 0–100 composite score. Grades: PASS ≥65, WARNING 40–64, FAIL <40, HARD_FAIL (any hard fail trigger).

| Metric | Weight | Purpose |
|--------|--------|---------|
| flat_region_pct | 20% | Detect large flat areas where pieces look identical |
| color_entropy | 12% | Colour distribution richness |
| edge_density | 12% | Amount of detail boundaries |
| corner_detail_ratio | 12% | Detail in corners vs centre (puzzle assembly) |
| grid_uniformity | 10% | Even distribution of detail across image |
| dominant_color_pct | 8% | Single colour domination |
| gradient_magnitude | 6% | Surface texture transitions |
| hue_diversity | 6% | Number of distinct colours |
| laplacian_variance | 5% | Global sharpness |
| gabor_texture_energy | 3% | Variety of surface patterns |
| subject_dominance | 3% | Character leaves room for scene |
| shadow_presence | 3% | Natural ground shadow under character |
| white_patch | 0% | Hard fail only — detects unblended composite background |

---

## File Outputs Per Order

```
orders/{order_id}/
  input_prepared.png     # Original photo, EXIF-corrected, max 1500px
  bg_removed.jpg         # White background version (Recraft output)
  normalized.png         # Front-facing normalised portrait (Kontext Max)
  character_input.png    # Face-cropped version sent to character gen
  character.png          # Pixar character on white
  costumed.png           # Character in themed outfit
  scene.png              # Empty scene (no people)
  candidate_1.png        # Method E composite, seed 1
  candidate_2.png        # Method E composite, seed 2
  candidate_3.png        # Method E composite, seed 3
  final.png              # Upscaled chosen candidate (4×, ~4096px)
  puzzle_surface.jpg     # Print-ready puzzle surface (Prodigi dimensions)
  tin_lid.jpg            # Print-ready tin lid (869×674px)
  manifest.json          # Full metadata, costs, timings, prompts
```
