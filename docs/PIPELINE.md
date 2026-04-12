# Pipeline Technical Reference

Exact models, prompts, and parameters for each step.

---

## Step 1: Background Removal

**Model:** `recraft-ai/recraft-remove-background` on Replicate
**Cost:** ~$0.01
**Code:** `src/remove_background.py`

```python
output = replicate.run(REPLICATE_MODEL, input={"image": f})
# Returns PNG with transparent background
# Composite onto white: Image.alpha_composite(white_bg, fg).convert("RGB")
```

**Input:** Customer photo (any format, any background)
**Output:** Same photo with white background, RGB JPG

---

## Step 2: Character Generation

**Model:** `black-forest-labs/flux-kontext-max` on Replicate
**Cost:** ~$0.08
**Code:** Uses `src/backends/flux_kontext_max.py` via registry

**Input:** White-background photo from Step 1
**Output:** Pixar-style character on white background (~1024px)

**Prompt template:**
```
Transform this photo into a Pixar-like 3D animated character. Keep the person's
face shape, skin tone, hair color, and hairstyle exactly as they are. Gentle
Pixar-style cartoon features — keep natural facial proportions and eye size.
{gender_hint}. A warm, natural smile. Soft cartoon shading, smooth skin.
Do not enlarge the eyes. Keep the same pose and framing. Plain white background.

Composition:
- Bust portrait, shoulders up
- Slight 3/4 angle, centred
- Plain white background
- Clean silhouette edges suitable for compositing
- Simple {clothing_description} without logos or text emphasis
```

**Gender hints:**
- Female: `Soft feminine features, delicate jawline`
- Male: `Natural masculine features`

---

## Step 3: Costume

**Model:** `black-forest-labs/flux-kontext-max`
**Cost:** ~$0.08

**Input:** Character on white background from Step 2
**Output:** Same character in themed outfit, still on white background

**Prompt template (village example):**
```
Take this animated character and dress them in a whimsical fantasy adventurer
outfit — leather vest, belt with pouches, a small cape, and boots. Keep their
face, skin tone, hair, glasses, and expression exactly the same. Keep the white
background. Same framing and pose.
```

**Costume ideas per scene:**
- Village: fantasy adventurer (leather vest, cape, boots, belt)
- Space: colourful cartoon astronaut suit with clear helmet visor
- Underwater: playful diving suit or mermaid costume

---

## Step 4: Scene Generation

**Model:** `black-forest-labs/flux-kontext-max`
**Cost:** ~$0.08

**Input:** Text prompt only (no input image, or scene as style reference)
**Output:** Empty detailed scene with no people (~1024px)

**Prompt template (village example):**
```
A vibrant magical storybook village scene with no people or characters.
Ultra-detailed Pixar 3D rendering. Cobblestone streets winding between colorful
crooked houses with flower boxes and thatched roofs. Floating lanterns, a stone
bridge over a sparkling stream, a bakery with a striped awning, a clock tower,
market stalls with colorful fruit. Foreground: scattered leaves, potted
sunflowers, a sleeping cat, a red postbox, a wheelbarrow of flowers. Background:
rolling green hills, a windmill, fluffy clouds, a hot air balloon, birds flying,
a rainbow. Every inch filled with color and detail. Warm golden-hour lighting,
rich saturated colors. No people, no characters, empty scene.
```

---

## Step 5: Compositing (3 Methods)

### Method E: Kontext Max single-image blend

**Model:** `black-forest-labs/flux-kontext-max`
**Cost:** ~$0.08
**Output:** ~1024x1024

1. PIL composite: paste costumed character onto scene (remove white bg via numpy mask, feather edges)
2. Send composite as single image to Kontext Max

**Prompt:**
```
Make this image look like a single seamless Pixar 3D rendered scene. The animated
character should blend perfectly into the village — match the warm golden-hour
lighting, add natural shadows, smooth all edges. Keep everything exactly as it is,
just make it look unified and natural. Do not change the character or the village layout.
```

### Method K: FLUX 2 Pro two-image

**Model:** `black-forest-labs/flux-2-pro`
**Cost:** ~$0.08
**Output:** ~2000x2000

Send costumed character + scene as two `input_images`.

**Parameters:**
```python
replicate.run('black-forest-labs/flux-2-pro', input={
    'prompt': prompt,
    'input_images': [character_file, scene_file],
    'resolution': '4 MP',
    'aspect_ratio': '1:1',
    'output_format': 'png',
    'output_quality': 100,
    'safety_tolerance': 5,
})
```

**Prompt:**
```
Place the animated Pixar character from the first image seamlessly into the
magical village scene from the second image. The character should be standing on
the cobblestone path in the centre of the village, taking up about 40% of the
image height. Match the warm golden-hour lighting of the scene onto the character.
Add natural ground shadows beneath their feet. The final image should look like a
single unified Pixar 3D rendered scene — no visible compositing artifacts,
seamless edges, consistent lighting throughout. Keep the character exactly as they
are — same face, glasses, beard, hair, costume.
```

### Method Q: FLUX 2 Pro with distance language

Same as Method K but with distance cue in prompt:

**Prompt (key difference bolded):**
```
Place the animated Pixar character from the first image seamlessly into the
magical village scene from the second image. The character should be standing
**further down the cobblestone path in the midground of the scene, appearing at
a natural distance as if they are walking through the village**. Match the warm
golden-hour lighting...
```

---

## Quality Validation

After compositing, run the puzzle scorer:

```python
from quality.puzzle_scorer import score_puzzle_quality
result = score_puzzle_quality('path/to/composite.png', 500)
print(f'{result.composite}/100 — {result.grade.value}')
```

**Pass:** >= 65. **Target:** 80+. **Best achieved:** 95.3/100.

---

## File Outputs Per Order

```
orders/{order_id}/
  input_prepared.png     # Original photo, EXIF-corrected
  bg_removed.jpg         # White background version
  character.png          # Pixar character on white
  costumed.png           # Character in themed outfit
  scene.png              # Empty scene (no people)
  composite_E.png        # Method E result (1024px)
  composite_K.png        # Method K result (2000px)
  composite_Q.png        # Method Q result (2000px)
  manifest.json          # Full metadata, costs, timings
```
