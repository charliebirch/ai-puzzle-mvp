# Seed Consistency Plan — FLUX Kontext Max

**Owner:** Charlie
**Created:** 2026-04-13
**Status:** 🎉 **Tier 1+2 prompt pattern VALIDATED 2026-04-13** — Lucy 3/3 on seeds 7/256/9999. Pattern applied to all character + costume prompts. Next: build step 4 costume-from-headshot.
**Research source:** `memory/project_seed_consistency_research.md`
**Winning pattern doc:** `memory/feedback_winning_headshot_pattern.md`

---

## 🎉 2026-04-13 Update: prompt pattern won

A single headshot prompt hit 3/3 recognisable likeness on Lucy across seeds 7/256/9999 — a breakthrough vs the previous ~1/3 hit rate. The 9-rule pattern has been applied to:

- New file `prompts/village/character_headshot.txt` — the validated headshot prompt with `{shoulders_hint}`, `{age_face_hint}`, `{teeth_hint}` slots
- All 5 existing character prompts (`character_boy.txt`, `character_girl.txt`, `character_child.txt`, `character_toddler.txt`, `character.txt`) — transferable wins applied: verb swap, "instantly recognisable" bookends, nose emphasis in STYLE, nose/ear shape in IDENTITY, "faithfully preserve actual" language, "cartoon NOT photorealistic" explicit, removed self-contradicting negatives
- All 3 costume prompts (`costume_adventurer.txt`, `costume_wizard.txt`, `costume_default.txt`) — nose/ear shape added to preservation list, "instantly recognisable" closer added

**What this changes in the plan below:**
- Tier 1 (verb-swap, identity-block-end, prompt-slim) — **DONE**, bundled into the writes above
- Tier 2a headshot — **validated at step 3**, step 4 costume-from-headshot is the remaining work
- Tier 2b multi-image Kontext — **deprioritised** (headshot alone solved the problem)
- Tier 3 arcface-ranking — **still worthwhile** as a production safety net, less urgent

**Next work to pick up:**
1. Validate the headshot pattern on subjects we haven't tested: Charlie (adult male), Edgar (child)
2. Wire the new `character_headshot.txt` into `scene_prompts.py` with slot-filling logic
3. Rewrite `costume_*.txt` to generate full body from headshot input + age-routed `{body_hint}`
4. Update `src/pipeline_steps.py` step 3 to call headshot path
5. End-to-end wizard test

---

## Problem recap

Step 3 character generation (`flux-kontext-max`) is seed-sensitive: same prompt + same input → ~1/3 good, 1/3 acceptable, 1/3 unusable likeness. Current bandaid is multi-seed-with-user-pick. Goal is **3/3 good** so the user picks their favourite, not filters out failures.

**Constraints:** Replicate only exposes `prompt`, `input_image`, `aspect_ratio`, `output_format`, `seed`, `safety_tolerance`, `prompt_upsampling`. No CFG, sampler, steps, LoRAs, ControlNet, or negative prompts.

---

## Legend

- [ ] Not started
- [~] Branch exists, untested
- [x] Tested and decided
- ✅ Merged to `feature/prompt-files`

---

## Branch plan

### Tier 1 — Prompt-only tweaks (run first, basically free)

These are cheap, fast, and the research predicts high impact. Run all three, A/B against current main in the parallel system.

| # | Branch | Status | Change | Hypothesis |
|---|---|---|---|---|
| 1 | `experiment/verb-swap` | [ ] | `"Transform this face reference into"` → `"Render this person as"` across all `character_*.txt` | BFL docs flag "transform" as the identity-replacement trigger verb |
| 2 | `experiment/identity-block-end` | [ ] | Move IDENTITY section to end of prompt; remove self-contradicting `"do NOT copy pose/hands/arms"` line | Kontext's documented ordering: end with what to preserve |
| 3 | `experiment/prompt-slim` | [ ] | Drop head-ratio + micro-proportion instructions; reallocate tokens to identity preservation | Proportion instructions don't land; they steal attention budget from identity |

**Test cost per branch:** ~$0.72 (3 subjects × 3 seeds at $0.08).

#### Tier 1 — exact text diffs to apply

**Branch `experiment/verb-swap`** — in every `prompts/village/character_*.txt`, line 1:

```
- Transform this face reference into a full Pixar-like 3D animated character …
+ Render this person as a full Pixar-like 3D animated character …
```

**Branch `experiment/identity-block-end`** — move the `IDENTITY (preserve exactly):` block to be the last block before `STYLE`. Also delete:

```
- Use this image ONLY as a face and identity reference — do NOT copy the pose, hands, arms, or body position from the source.
```

Replace with a positive framing at the end:

```
+ FINAL INSTRUCTION: this person's face, ethnicity, skin tone, hair, and facial structure must remain recognisably them. The only thing changing is their rendering into Pixar 3D style.
```

**Branch `experiment/prompt-slim`** — in each character prompt, remove the `PROPORTIONS` block's most specific lines:

```
- Oversized cartoon head: the head is approximately ONE THIRD of the character's total visible height …
- Body: approximately 3 to 3.5 heads tall …
```

Keep `"Pixar 3D cartoon proportions — head slightly oversized for cartoon appeal"` only. Reinvest the saved tokens into the IDENTITY block.

---

### Tier 2 — Structural experiments

These are larger bets. Run after Tier 1 has told us which prompt direction is best.

#### 2a. `experiment/character-headshot` — Charlie's idea

**Current:** Step 3 generates a full-body Pixar character.
**New:** Step 3 generates only a head-and-shoulders animated portrait, generate 6 candidates, user picks one. Step 4 (costume) generates the full body and outfit from that headshot.

**Design decisions (confirmed 2026-04-13):**
- **Collapse 5 character prompts → 1.** Face instructions are ~90% shared across boy/girl/child/toddler/person; all body divergence moves to step 4 as a `{body_hint}` slot. Single `prompts/village/character_headshot.txt` with slots `{subject}`, `{gender_hint}`, `{teeth_hint}`.
- **Neutral `body_hint` routes by detected gender.** Only use the truly gender-neutral body_hint when gender is genuinely unknown. If detect_attributes has gender, use the male/female body_hint even on the "person" prompt path.
- **Archive old prompts under `prompts/village/_archive/`.** Move the 5 existing `character_*.txt` files into an `_archive/` subdirectory rather than deleting. Easy rollback if the headshot experiment underperforms.
- **Teeth-preservation line applies to everyone.** Not just kids. Protects adults with gap teeth / unusual dentition from Kontext regularising them to "celebrity-grade" perfection.

See `/Users/charlie.birch/.claude/plans/warm-meandering-leaf.md` for the full design including the proposed headshot prompt text and body_hint table.

**Why:**
- Tighter scope → better likeness. Most perceived quality is face.
- Step 4 already does heavy Kontext work; giving it a stronger face anchor should help.
- Simpler prompts at step 3 = fewer places for Kontext to drift.

**Risk:**
- Prior session (2026-04-12) found `"stripping to headshot-only breaks likeness"` — but that was before the no-subject-text change and normalise step landed. Worth retesting.
- Costume step face drift is already a known issue (`feedback_hair_preservation.md` context). If we ask it to also generate the whole body, we need to pair this with `experiment/costume-identity-lock`.

**Files touched:**
- `prompts/village/character_*.txt` — rewrite as headshot prompts
- `prompts/village/costume_*.txt` — rewrite to build full body from headshot
- `src/pipeline_steps.py` — step 3 generates 6 not 3 candidates
- `web/templates/wizard_step3.html` — wider picker UI for 6 thumbnails
- `src/composite_pil.py` — no change (still gets full body from costume step)

**New character prompt draft (headshot variant):**

```
Render this person as a Pixar-like 3D animated head-and-shoulders portrait.

ANATOMY:
- Standard human anatomy: exactly two eyes, two ears, one nose, one mouth.
- Source image may have imperfect background removal — ignore any edge blobs.

FRAMING:
- Head-and-shoulders only, head centred, shoulders visible at bottom of frame.
- Face turned toward the viewer, fully visible and unobscured.
- Slight 3/4 angle or direct-to-camera is fine.

STYLE:
- Pixar 3D animated style, rich cartoon shading, smooth skin with warm subsurface scattering, dramatic cartoon lighting.
- Oversized cartoon head proportions, expressive cartoon eyes that feel alive.
- Natural joyous smile — bright white celebrity-grade teeth. Not forced.
- PURE WHITE BACKGROUND (#FFFFFF). No environment, no shadows, no ground plane.

IDENTITY (this is the whole job):
- Preserve this person's skin tone, ethnicity, hair colour, hair texture, hairstyle, face shape, and any glasses.
- This person is {subject}.
- They must remain recognisably themselves after stylisation.
```

**New costume prompt draft (headshot-aware):**

```
Take this animated headshot and expand it into a full-body Pixar 3D character wearing a whimsical fantasy adventurer outfit — a worn leather vest over a linen shirt, a wide belt with pouches and a small dagger, a dramatic swirling cape, and sturdy adventurer boots.

Character build: Pixar-style cartoon proportions, body approximately 3.5 heads tall, dynamic adventurous pose, weight on one foot, arms mid-motion, face toward viewer, natural joyous smile.

Background: pure white (#FFFFFF), no environment, no shadows.

This character is {subject}. Keep their face, skin tone, hair colour, hair texture, hairstyle, glasses and expression exactly as in the input headshot.
```

#### 2b. `experiment/multi-image-kontext` — biggest potential structural win

**Change:** Swap `black-forest-labs/flux-kontext-max` → `flux-kontext-apps/multi-image-kontext-max`. Pass two inputs: the customer's normalised headshot (image 1, identity) + a Pixar style plate (image 2, style).

**Why:** The research flagged this as the biggest potential structural win. Dedicating a slot to style should compress variance significantly — the model isn't inventing "Pixar" from scratch each time.

**Blocker:** We need a style plate (see Pixar Exemplar section below).

**Files touched:**
- `src/backends/` — new `multi_image_kontext.py` backend
- `src/backends/registry.py` — register it
- `src/pipeline_steps.py` — step 3 uses new backend
- `assets/pixar_style_plate.png` — new asset

#### 2c. `experiment/character-aspect-ratio` — already exists

Untested branch already on the repo. Adds `aspect_ratio="3:4"` to character gen. Merge-test only — see if portrait canvas produces better full-body framing.

#### 2d. `experiment/costume-identity-lock` — already exists

Untested branch. Adds explicit face/eye/nose/mouth lock phrasing to costume prompts. Pair-test with `experiment/character-headshot`.

---

### Tier 3 — Mitigation / infrastructure (independent)

#### 3a. `experiment/arcface-ranking`

**Change:** Add `insightface` or equivalent ArcFace embedding to the character candidate step. For each of N generated candidates, compute cosine similarity vs the normalised input, rank by score, auto-reject anything below threshold, show user only ranked-good candidates.

**Why:** BFL themselves use AuraFace embeddings to measure character drift in the Kontext paper. This replaces "user picks best of 3 including a bad one" with "user picks from 3 known-good" — same UX, stronger floor.

**Files touched:**
- `pyproject.toml` / requirements — add `insightface` (check bundle size for Render)
- `src/quality/face_similarity.py` — new module
- `src/pipeline_steps.py` — integrate into step 3

**Cost:** ~30ms/image CPU. No Replicate cost.

**Independence:** Works on top of whatever wins Tier 1 + 2.

---

## Pixar style plate — recommendation

**For `experiment/multi-image-kontext`.**

### DON'T use a real Pixar character still

- Copyright risk (Disney/Pixar)
- Kontext will bias toward that specific character's face shape, eye colour, hair — undermines the identity preservation we're trying to protect
- Famous character poses/backgrounds pull unwanted composition

### DO: generate a neutral style plate ourselves

**Target:** a generic Pixar-style render that encodes the *aesthetic* (rendering, lighting, proportions) without injecting a specific identity.

**Characteristics:**
- Head-and-shoulders framing (matches what we'll feed as identity slot)
- Ambiguous gender, ambiguous ethnicity, neutral age (young adult)
- Neutral friendly expression — slight smile, eyes looking at camera
- Pure white background #FFFFFF
- Lighting: warm key light top-left, cool fill, characteristic Pixar subsurface scatter on skin
- Hair: something simple — a short mid-brown style that won't bias outputs

**Generation:** use `flux-2-pro` (text-only, already in pipeline for scene gen — Pixar-capable).

**Candidate prompt to generate the plate:**

```
A generic Pixar-style 3D animated head-and-shoulders portrait of a young adult character with ambiguous ethnicity and gender, short mid-brown hair, warm friendly neutral expression, slight smile, looking directly at camera. Rich Pixar 3D rendering — smooth skin with warm subsurface scattering, soft warm key light from upper left, cool fill light, gentle rim light. Pixar cartoon proportions with slightly oversized head and expressive cartoon eyes. Simple light-grey t-shirt. Pure white background (#FFFFFF), no environment, no shadows on the ground, no props. High detail, production-quality 3D animation render.
```

**Workflow:**
1. Generate 6 candidates at different seeds
2. Hand-pick the one with the cleanest neutral face, cleanest white BG, and most "textbook Pixar" lighting
3. Save to `assets/pixar_style_plate.png`
4. Commit to repo (this is a fixed asset, not generated per-order)

**Possible v2 later:** generate 2 plates (kid / adult) and route based on detected age. Don't bother until v1 proves the approach.

---

## Parallel system test prompts (for tomorrow's testing)

Charlie asked for simple-outfit prompts to test in the parallel system first, before re-introducing Adventurer.

### Headshot character prompt (test in parallel)

Paste as the Kontext Max prompt. Input image = normalised headshot output.

```
Render this person as a Pixar-like 3D animated head-and-shoulders portrait.

ANATOMY:
- Standard human anatomy: exactly two eyes, two ears, one nose, one mouth.
- Source image may have imperfect background removal — ignore any edge blobs.

FRAMING:
- Head-and-shoulders only, head centred, shoulders visible at bottom of frame.
- Face turned toward the viewer, fully visible and unobscured.
- Slight 3/4 angle or direct-to-camera is fine.

STYLE:
- Pixar 3D animated style, rich cartoon shading, smooth skin with warm subsurface scattering, dramatic cartoon lighting.
- Oversized cartoon head proportions, expressive cartoon eyes that feel alive.
- Natural joyous smile — bright white celebrity-grade teeth. Not forced.
- PURE WHITE BACKGROUND (#FFFFFF). No environment, no shadows, no ground plane.

IDENTITY (this is the whole job):
- Preserve this person's skin tone, ethnicity, hair colour, hair texture, hairstyle, face shape, and any glasses.
- This person is {subject}.
- They must remain recognisably themselves after stylisation.
```

Params: `aspect_ratio="1:1"`, `output_format="png"`, `safety_tolerance=2`, `prompt_upsampling=false`. Test with seeds 7, 256, 9999.

### Simple-outfit costume prompt (test after headshot works)

Input image = the selected headshot from the step above.

```
Take this animated headshot and expand it into a full-body Pixar 3D character wearing simple casual clothes — a plain short-sleeved t-shirt and comfortable trousers, no logos. No hat.

Character build: Pixar-style cartoon proportions, body approximately 3.5 heads tall, relaxed standing pose with weight on one foot, arms slightly away from body, face toward viewer, natural joyous smile.

Background: pure white (#FFFFFF), no environment, no shadows, no ground plane.

This character is {subject}. Keep their face, skin tone, hair colour, hair texture, hairstyle, glasses and expression exactly as in the input headshot.
```

Params: `aspect_ratio="3:4"`, rest same. Test with seeds 7, 256, 9999.

### Adventurer costume prompt (test after simple outfit works)

Same framing, swap clothes description:

```
Take this animated headshot and expand it into a full-body Pixar 3D character wearing a whimsical fantasy adventurer outfit — a worn leather vest over a linen shirt, a wide belt with pouches and a small dagger, a dramatic swirling cape, and sturdy adventurer boots.

Character build: Pixar-style cartoon proportions, body approximately 3.5 heads tall, dynamic adventurous pose, weight on one foot, arms mid-motion, face toward viewer, natural joyous smile.

Background: pure white (#FFFFFF), no environment, no shadows.

This character is {subject}. Keep their face, skin tone, hair colour, hair texture, hairstyle, glasses and expression exactly as in the input headshot.
```

---

## Testing methodology

For every branch, use the parallel Replicate system per `memory/feedback_parallel_system.md`.

**Test set (fixed across all branches for comparability):**
- 3 subjects: Edgar (child), Lucy (woman), Charlie (man)
- 3 seeds each: 7, 256, 9999
- Total: 9 generations per branch at $0.08 = $0.72/branch

**Scoring:**
1. ArcFace cosine similarity to normalised input (once `experiment/arcface-ranking` exists — until then, manual)
2. Manual "recognisable as them?" Y/N
3. Puzzle quality scorer composite (for completeness)

**Target:** 9/9 recognisable. Current baseline is ~6/9.

**Promotion criteria:** a branch merges into `feature/prompt-files` only if it improves the 9/9 score without regressing puzzle quality scorer below 80.

---

## Suggested merge order

1. **Tier 1 in parallel** (verb-swap, identity-block-end, prompt-slim) → merge winners into `feature/prompt-files`
2. **Tier 3 arcface-ranking** in parallel (independent infra work) — this makes all future A/B testing cheaper
3. **Generate Pixar style plate** — needed for 2b
4. **Tier 2a headshot pair** (`experiment/character-headshot` + `experiment/costume-identity-lock` tested together)
5. **Tier 2b multi-image** tested separately
6. Pick winner between the two structural approaches (2a vs 2b) → that becomes new step 3+4
7. Merge `experiment/character-aspect-ratio` test result on top of winner
8. `feature/prompt-files` → `main` → Render

---

## Open questions for future sessions

1. **Can we use `prompts/village/<scene>/` prompt file structure** for headshot-variant prompts, or do we need a parallel directory like `prompts/village_headshot/`? Probably fork the prompts dir per experiment branch and decide on merge.
2. **Multi-seed N** — currently 3 for compositing. For the headshot experiment, should step 3 generate 6 since they're cheaper to filter? 6 × $0.08 = $0.48/run just for step 3. Probably worth it if likeness becomes the bottleneck.
3. **Pixar style plate per age group** — one plate for adults, one for kids? Defer until v1 multi-image works.
4. **Does `prompt_upsampling=false` need to be explicit?** Research says it defaults to false but let's set it explicitly on every call for reproducibility.

---

## Reference material

- `memory/project_seed_consistency_research.md` — full research report with sources
- `memory/project_seed_consistency.md` — original problem statement
- `memory/project_session_2026_04_12.md` — prior learnings
- `memory/feedback_parallel_system.md` — how to use the parallel test harness
- `memory/reference_nano_banana_compositing.md` — alternative compositing models if multi-image Kontext underwhelms
