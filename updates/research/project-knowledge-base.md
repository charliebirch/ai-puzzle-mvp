# AI Puzzle MVP — Project Knowledge Base

## The Business

We're building an Etsy store that sells **personalised animated kids' jigsaw puzzles**. A customer sends us a photo of their child (or themselves, a pet, etc.), picks a cartoon style, and we produce a physical jigsaw puzzle featuring that person as a Pixar-style cartoon character in a fun themed scene.

**Target customer:** Parents buying a novelty gift for their child. The puzzle features *their kid* as the cartoon character — that's the magic.

**Products:**

| Size | Physical | Pixels (300 DPI) | Target Price |
|------|----------|-------------------|-------------|
| 500-piece | 16" x 20" | 4800 x 6000 | $39.99 |
| 1000-piece | 20" x 28" | 6000 x 8400 | $49.99 |

**Status:** Pre-launch. The AI pipeline works, the web app works, but quality isn't consistent enough yet. We need 80+ on our quality score (currently ~70) before listing on Etsy.

**Print supplier:** Not yet chosen. Not a current priority — we're focused on the AI output quality first.

---

## The Art Style

**Pixar-style cartoon — NOT photorealistic.** This is a deliberate creative choice:

- Cartoon art is more fun and appealing for kids' puzzles
- It's more forgiving across different photo qualities and lighting conditions
- It differentiates us from competitors doing basic "print your photo on a puzzle" products
- It makes sense as a jigsaw puzzle — realistic faces on puzzle pieces look weird when cut up

The primary style is **"storybook cartoon"** — a whimsical village scene with floating lanterns, warm colours, and a Pixar-like character. We also have space, underwater, and pixel art variants.

### Active Styles

| Style | Theme | Face Swap? |
|-------|-------|-----------|
| storybook_cartoon | Pixar-like character in whimsical village with floating lanterns | Yes |
| space_explorer | Cartoon astronaut in bright, playful outer space | Yes |
| underwater_adventure | Deep-sea explorer with coral reefs and sea creatures | Yes |
| pixel_platformer | Pixel art character in colourful side-scrolling game | No (photorealistic face swap looks wrong on pixel art) |

---

## The AI Pipeline

```
Customer Photo
  → FLUX Kontext Pro (cartoon transformation, ~$0.04, ~13s)
  → codeplugtech/face-swap (facial identity fix, ~$0.003, ~30s)
  → Quality Scoring (face similarity + image metrics)
  → Real-ESRGAN Upscale (to print resolution, ~$0.002)
  → Export (preview with grid overlay + print-ready with bleed)
```

**Total: ~$0.045 per image, ~44 seconds**

### Step 1: FLUX Kontext Pro (Cartoon Transformation)

- **Model:** `black-forest-labs/flux-kontext-pro` on Replicate
- **What it does:** Takes the customer photo as a pixel reference and follows a text instruction to transform it into a cartoon character in a themed scene
- **How it works:** It's an instruction-based image editor — you give it the photo + a text prompt like "Transform this photo into a Pixar-like cartoon illustration..."
- **Strengths:** Preserves hair colour, hairstyle, clothing details, and general appearance from the original photo. Good at following style instructions.
- **Weakness:** Produces generic/averaged faces. The face in the cartoon doesn't look specifically like the person — it looks like "a cartoon person with that hair." Face similarity score is only 0.33 when used alone.
- **Cost:** ~$0.04 per run
- **Parameters we use:** aspect_ratio 4:3, PNG output, no seed pinning currently

### Step 2: codeplugtech/face-swap (Identity Fix)

- **Model:** `codeplugtech/face-swap:278a81e7...` on Replicate
- **What it does:** Takes the original customer photo and the cartoon output, and swaps the face from the photo onto the cartoon body
- **Why we need it:** Fixes Kontext's generic face problem. Combined face similarity jumps from 0.33 to 0.88.
- **API:** Simple — just two image inputs (swap_image + input_image), no configuration needed
- **Cost:** ~$0.003 per run
- **Risk:** The swapped face is more photorealistic than the cartoon body, which can look slightly uncanny. This is our main quality challenge.

### Models We Tested and Rejected

We tested 7+ models/pipelines before landing on the current one:

| Model | Problem | Why Rejected |
|-------|---------|-------------|
| InstantID | ArcFace embeddings discard hair entirely | Architectural limitation — no parameter tuning can fix it |
| Flux-PuLID | Similar face embedding limitations | Couldn't preserve full appearance |
| IP-Adapter | Generic results | Didn't meet quality bar |
| Seedream | Inconsistent | Unreliable outputs |
| NanoBanana | Quality issues | Didn't meet quality bar |
| Easel advanced-face-swap | API discontinued/stalling | Replaced with codeplugtech |

---

## Quality Scoring System

Every generated image gets a composite score from 0-100. **Pass threshold is 70, launch target is 80+.**

The scoring is specifically tuned for **cartoon art** — we had to redesign it because the original scoring rewarded photorealism, which penalised the exact style we want.

| Metric | Weight | What It Measures |
|--------|--------|-----------------|
| Face Similarity | 40% | InsightFace ArcFace cosine distance between original photo and generated face. "Does this still look like the same person?" |
| Color Vibrancy | 20% | HSV mean saturation + high-saturation pixel ratio. Rewards vivid, saturated cartoon colours. |
| Face Detection Confidence | 10% | How confidently the detector finds a face. Catches distorted/mangled faces. |
| Resolution | 10% | Compared to print target (4800x6000 or 6000x8400). Mostly binary after upscale. |
| Edge Cleanliness | 10% | Canny edge density — sweet spot is 5-18%. Clean cartoon edges, not noisy artifacts. |
| Color Diversity | 10% | Histogram entropy. Rich, varied colour palette. |

**Metrics we dropped:**
- **Sharpness** — penalised cartoon soft shading (which is correct for the style)
- **Contrast** — penalised warm tones (which we want in storybook art)

### Current Benchmark Results

| Test | Pipeline | Composite | Face Similarity | Time | Cost |
|------|----------|-----------|----------------|------|------|
| TEST-003 | Kontext only (no face swap) | 59.9 FAIL | 0.33 | 13s | $0.042 |
| TEST-004 | InstantID + face swap | 83.2 PASS | 0.86 | 178s | $0.020 |
| TEST-005 | Kontext + face swap | 70.1 PASS | 0.88 | 44s | $0.045 |

TEST-005 is our current pipeline. The composite score was 70.1 under old weights — the new cartoon-tuned weights should score higher but we haven't re-benchmarked yet.

---

## The Core Challenge: Photo Input Friction vs Output Quality

This is our biggest unsolved problem.

**The issue:** The quality of the output is highly dependent on the quality and characteristics of the input photo. We're worried that customers will upload suboptimal photos (bad lighting, low resolution, side angles, multiple people, sunglasses, etc.) and get disappointing results.

**What we've observed:**
- Face swap works best with clear, front-facing photos with good lighting
- Kontext can handle some variation in pose/lighting but the face swap step is more brittle
- No seed pinning means the same photo can give different results each run (quality inconsistency)
- We haven't tested across diverse faces yet (different ages, skin tones, hair types)

**What we need to figure out:**
- How to pre-process or validate input photos to maximise output quality
- Whether there are better models or pipelines that are more robust to varied input
- Whether a photo guidance/coaching step ("upload a front-facing photo with good lighting") is enough, or if we need automated photo improvement
- How to handle edge cases: glasses, hats, multiple people, pets, side profiles
- Whether face detection/alignment pre-processing could help
- Whether there are newer models on Replicate (or elsewhere) that handle the cartoon transformation + face preservation better than our two-step approach

---

## Technology Stack

- **AI Models:** All run via Replicate API (pay-per-use, no GPU infrastructure needed)
- **Backend:** Python, FastAPI
- **Frontend:** Pico CSS + HTMX (minimal JS, server-rendered)
- **Database:** SQLite (job tracking + feedback)
- **Hosting:** Render free tier (lightweight mode — no quality scoring or upscaling) for partner testing. Full pipeline runs locally only.
- **Image Processing:** Pillow, Real-ESRGAN (via Replicate) for upscaling
- **Face Analysis:** InsightFace with ArcFace embeddings (for quality scoring only — too heavy for free hosting at 282MB)

---

## Prompt Engineering

The cartoon transformation is driven entirely by the text prompt sent to FLUX Kontext Pro. Here's the current storybook_cartoon prompt:

> "Transform this photo into a Pixar-like cartoon illustration. Give the person exaggerated expressive eyes, soft shading, and a playful costume. Place them in a colorful whimsical village with floating lanterns, detailed props, and layered depth. Use a warm storybook illustration style. Keep the person's face, hair, and expression exactly as they are."

Negative prompt:
> "hyper-realistic, uncanny valley, stiff pose, washed colors, facial distortion, wrong hair color, changed hairstyle, altered hair texture"

**Key tension:** The prompt says "keep the face exactly as they are" but Kontext still produces generic faces. That's why we need the face swap step. If we could get Kontext (or another model) to preserve facial identity better, we could potentially drop the face swap step entirely — which would reduce the uncanny valley risk and simplify the pipeline.

---

## What Research Would Be Most Valuable

1. **Better cartoon transformation models** — Are there newer models on Replicate (or fine-tuned checkpoints) that preserve facial identity better during style transfer? Could we eliminate the face swap step?

2. **Input photo robustness** — What preprocessing, validation, or enhancement steps could make the pipeline more tolerant of varied customer photos? Face alignment, super-resolution on the input, background removal, lighting normalisation?

3. **Face swap alternatives** — Are there face swap models that produce more stylistically consistent results (cartoon face onto cartoon body, rather than realistic face onto cartoon body)?

4. **Consistency/reproducibility** — How to reduce run-to-run variation? Seed pinning strategies, or models that are more deterministic?

5. **Multi-step pipelines** — Are there creative multi-model flows we haven't considered? E.g., photo → face mesh extraction → cartoon rendering, or photo → multiple candidates → best-of-N selection?

6. **Diverse face handling** — Which models perform best across different ethnicities, ages, and face shapes? Are there known biases to watch for?

7. **Quality gating** — Automated ways to detect bad outputs before they reach the customer, beyond our current scoring system?
