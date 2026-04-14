# Eye Gaze Research — Fixing "Bog Eye" in Pixar-Style Character Generation

**Created:** 2026-04-14
**Problem:** When generating Pixar-style cartoon characters from real photos, eyes often end up looking in different directions or not making proper eye contact with the viewer.

---

## Why It Happens

1. **Diffusion models have no geometric understanding** — they don't know eyes should converge on a single gaze point
2. **Bilateral symmetry breaks during generation** — small perturbations during the denoising window are amplified (NeurIPS 2023 paper)
3. **Style transfer amplifies the problem** — enlarging eyes + changing iris ratio + adding catchlights + maintaining gaze direction = competing objectives
4. **Seed sensitivity** — Kontext's input_image is a soft hint, so different seeds produce dramatically different eye results
5. **Even Pixar cheats** — SIGGRAPH 2024 talk revealed Pixar animators spend enormous time polishing eye directions on large-eyed characters. They use camera-relative cheats because physically accurate geometry alone doesn't produce coherent gaze

## Pixar Eye Design Rules

1. Large expressive eyes — 1.5-2.5x real human proportions relative to head
2. Catchlights in upper portion of eye (10-2 o'clock), matching in both eyes
3. **Pupils touching the upper eyelid** — visible sclera all around = surprise/madness only
4. Minimal visible sclera above the iris for warm expressions
5. Both eyes converging on the same gaze point
6. Warm, large pupils for friendly/cute characters
7. Single dominant catchlight per eye (not multiple)

## Current Prompt Weakness

The headshot prompt's eye line is:
```
- Expressive cartoon eyes that feel alive, with a subtle Pixar sparkle catchlight.
```

This describes **aesthetic** but says nothing about **direction**, **alignment**, or **anatomy**. The model can produce expressive, alive, sparkly eyes that look in two different directions.

## Actionable Fixes (Ranked)

### Tier 1: Prompt Engineering (Free, Immediate)

**1. Expand the eye line in character_headshot.txt:**
```
- Expressive Pixar cartoon eyes — both looking directly at the viewer with perfectly
  matched gaze. Large warm irises, centred aligned pupils, a single subtle sparkle
  catchlight in the upper portion of each eye. Upper eyelids resting on the top of
  the iris — no wide-eyed stare.
```

**2. Add "eye gaze direction" to costume prompt preservation list:**
```
Keep their face, skin tone, hair colour, hair texture, hairstyle, nose shape, ear shape,
eye gaze direction, glasses and expression exactly as in the input headshot.
```

**3. Add "eye gaze direction" to composite prompt preservation clause.**

### Tier 2: Pipeline Detection (Low Cost, Dev Time)

**4. Build OpenCV bog-eye detector:**
- Detect face region in generated cartoon
- Extract left/right eye bounding boxes
- Threshold to find iris/pupil blob in each eye
- Compare relative iris centroid position between eyes
- Return gaze alignment score
- Note: better for cartoon faces than GazeTracking library (trained on real faces only)

**5. Integrate into candidate ranking at step 3** — prefer candidates with aligned gaze.

### Tier 3: Correction Pass ($0.08 per trigger)

**6. Kontext Max eye-correction pass:**
```
Adjust the eyes so both are looking directly at the viewer with perfectly matched
gaze direction. Both pupils should be centred in the iris and aligned with each
other. Add a matching Pixar sparkle catchlight in the upper portion of each eye.
Keep everything else completely unchanged — same face, same expression, same style,
same hair, same skin tone, same background.
```
Only triggered when detection flags a problem. Average cost ~$0.03/run if ~1/3 need fixing.

### Not Recommended

- **GFPGAN/CodeFormer** — trained on real faces, will push cartoon eyes toward photorealism
- **GazeTracking library** — uses dlib landmarks trained on real faces, unreliable on cartoons
- **Research gaze models (TextGaze, RTGaze)** — not production-ready, not on Replicate

## Key Insight

The single highest-impact change is expanding the eye line to include explicit gaze direction, bilateral alignment, and pupil positioning. Direction + alignment + anatomy, not just aesthetics.

## Sources

- Pixar Inside Out 2 SIGGRAPH 2024 (eye direction challenges)
- The Pixar Problem — Eye Specular Highlights (grinning-tiger.com)
- A Deep Look into Animated Eyes (PMC/Journal of Optometry)
- BFL Kontext I2I Prompting Guide (working without negative prompts)
- Spontaneous Symmetry Breaking in Generative Diffusion Models (NeurIPS 2023)
- Making Eyes That See (Animator Island)
