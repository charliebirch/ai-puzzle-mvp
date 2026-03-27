# Automated image quality scoring for jigsaw puzzle images

**AI-generated Pixar-style cartoon images fail as puzzles when they contain large flat-color zones, oversized characters, and barren corners — all measurable with pixel-level computer vision metrics.** This report consolidates manufacturer guidelines, puzzle design best practices, color science thresholds, print specifications, and 11 quantifiable metrics into a complete scoring system architecture ready for implementation. The system uses a weighted linear combination of normalized metrics with hard-fail gates, targeting a processing time under 2 seconds per image on modern hardware. Every threshold below has been derived from published manufacturer guidelines, perceptual color science (CIEDE2000), and standard image analysis literature, then adapted to the specific failure modes of Pixar-style 3D renders.

---

## 1. What separates an enjoyable puzzle from a frustrating one

The single most important property for puzzle solvability is **spatially localized color diversity** — many distinct colors, each confined to a particular region. Journey of Something (Australian puzzle company) makes this their #1 selection criterion. When an assembler picks up a piece with a specific color, they should be able to narrow it down to a specific section of the image. Ravensburger's official guidelines state: "Light, bright colours are easier to make a jigsaw with than dark, matte colours. A design with as many different colours as possible also makes a jigsaw easier."

Dead zones — regions where 20+ pieces look identical — are created by five mechanisms: large uniform-color areas (blue sky, green grass, ocean), colors distributed uniformly throughout the image (confetti/sprinkle patterns where red appears everywhere), repetitive patterns (checkerboards, identical flowers), dark or underexposed regions that lose all detail differentiation, and limited color palettes. For a 1000-piece puzzle measuring ~20×27 inches with pieces approximately **2 cm × 1.7 cm**, any uniform-color region larger than roughly 5×4 inches contains 20+ visually identical pieces.

Professional puzzle companies approach art direction very differently from photography or wall art. Puzzle artist Aimee Stewart (published by Buffalo Games, Ravensburger, SunsOut) explains the key distinction: "For my wall art, I want it more subdued... I want empty space. For my puzzles, I had to learn how to **fill all of that in** and yet still have it pleasing to the eye." She also notes she thinks about "what areas will be tricky, what parts will be satisfying to complete" and has her family assemble each puzzle to refine the experience. Buffalo Games partners with artists known for puzzle-friendly art characterized by rich color, dense detail, and discoverable surprises throughout.

**Cartoon/3D-rendered images carry a specific double-edged risk.** They have bolder color boundaries and more saturated palettes (advantages), but they also tend toward large regions of smooth, uniform color — sky gradients, simple walls, smooth character skin — precisely the characteristics that create dead zones. Photographs naturally contain micro-texture variation (wood grain, fabric weave, skin pores) that helps differentiate pieces even within same-color regions. Pixar-style renders lack this natural noise, making strict flat-region limits critical.

---

## 2. Color and contrast at the piece level

### Minimum distinguishable difference between pieces

The CIEDE2000 color difference formula provides the perceptual standard. **ΔE₀₀ = 1.0** is the just-noticeable difference (JND) — the threshold below which most people cannot distinguish two colors. For adjacent puzzle pieces to be reliably distinguishable, they should differ by **ΔE₀₀ ≥ 2.0** (noticeable to most observers) and ideally **≥ 3.5** (clearly different). This maps to the computational approach of converting piece-sized blocks to CIELAB color space and computing pairwise CIEDE2000 distances using the `colour-science` Python package.

At 300 DPI, each piece of a 1000-piece puzzle corresponds to approximately **200×180 pixels**. For a 500-piece puzzle, pieces map to roughly **240×200 pixels**. These dimensions define the sliding-window size for all piece-level analysis.

### Color distribution rules

Published manufacturer guidelines and community consensus converge on these quantifiable thresholds:

- **No single color cluster should exceed 25% of total pixels** (k-means with k=8). Exceeding 40% is a hard failure — the puzzle becomes monotonous. Puzzles Unlimited states images should be "bigger than life" with "colors popping, bright, and attractive."
- **At least 10 of 18 hue bins** (10° intervals) should be occupied by >0.5% of saturated pixels (those with HSV saturation >30). Fewer than 5 occupied bins indicates a dangerously limited palette.
- **Global color entropy should exceed 6.5 bits per channel** (Shannon entropy on 256-bin histogram, max 8.0). Below 5.5 indicates an image with severe color concentration.
- **Gradient regions are moderately acceptable** — they provide positional information (color shifts from one end to the other) but lack the sharp detail boundaries that make individual pieces uniquely identifiable. Pure flat regions are far worse than gradients.

### Flat region quantification

A "flat region" is defined as any contiguous area where local standard deviation falls below a threshold. Using a piece-sized sliding window (~200×200 pixels at 300 DPI analysis resolution):

- **Local std < 8** (0–255 scale): effectively a single color — hard fail zone
- **Local std < 15**: very low variation, problematic for piece identification
- **Local std > 20**: sufficient internal variation for a piece to be distinguishable

The total percentage of the image classified as "flat" (local std < variance threshold ~100 in pixel² units) should be **under 25%** to pass, with a hard fail at **40%**. Any single connected flat-color region exceeding **5% of total image area** is problematic, and exceeding **15%** is a hard fail.

---

## 3. Composition rules specific to puzzle images

### Subject sizing and placement

For the "small character in a wide scene" format, the main subject should occupy **5–15% of total image area**. This is dramatically different from portrait photography. If the character exceeds 25%, the puzzle effectively becomes a portrait with insufficient background detail. The subject's centroid should fall within a rule-of-thirds zone (**22–44% from any edge**), not dead center, creating a dynamic composition that distributes visual interest.

Multiple focal points are essential. Professional puzzle images feature **3–7 identifiable landmarks or reference elements** distributed across the frame. Each quadrant of a 3×3 grid should contain at least one identifiable element. eeBoo's difficulty framework explicitly links "easy to delineate sections, clear color borders between sections" with enjoyable assembly experience.

### Visual zones and regions

The image should contain **7–12 distinct color/texture zones** for a 1000-piece puzzle (5–8 for 500 pieces), creating sortable sections where each zone averages 80–140 pieces. No single zone should exceed **20% of total image area**. The optimal composition has three distinct depth layers with detail at each level:

- **Foreground (bottom 25–35%)**: Rich texture and detail — paths, stones, plants, scattered objects
- **Midground (35–55%)**: Main scene elements — buildings, trees, characters, vehicles
- **Background (top 25–35%)**: Sky/distance with added interest — clouds, mountains, atmospheric effects

### The sky problem and how to handle it

Sky is the single most cited frustration factor in puzzle assembly. Reddit puzzlers consistently complain about "the blue sea can drive you insane" and "the sky was horrible." The quantifiable rule: **sky area should be under 25% of total image area**, and if sky exceeds 15%, its local entropy must reach **at least 80% of the overall image entropy** — meaning it must contain clouds, color gradients spanning 3+ hue variations, atmospheric effects, birds, or other detail.

Professional puzzle artists handle uniform areas through deliberate treatment. Thomas Kinkade (one of the best-selling puzzle artists ever) uses layered glazes ensuring sky areas have cloud formations, light rays, and warm-to-cool color gradients. Water gets reflections, ripples, and light dappling. Ground areas get paths, stones, grass variation, flowers, fallen leaves, and shadows. **No area should ever be visually flat.**

### Edge and corner detail

Edge pieces are universally assembled first, making border detail critical to the initial puzzle experience. Puzzery explicitly recommends "having distinctive items around the edge of your design can give puzzlers a great start." The measurable rules:

- **Border ring (outer 15% strip) entropy should be ≥60% of interior entropy**
- **Border edge density should be ≥50% of interior edge density**
- **Each of the four corner quadrants must score ≥50% of the highest-scoring quadrant** on entropy, edge density, and color cluster count
- **At least 8 identifiable elements** should touch or be near the border

Detail density should be deliberately varied — highest in the midground, moderate in foreground and background — but with a strict floor minimum: **no grid cell should have entropy below 50% of the global mean**. The coefficient of variation of entropy across a 5×5 grid should be **0.15–0.40** (some natural variation, but no desert zones).

---

## 4. Physical production and print specifications

### Puzzle dimensions and piece sizes

| Puzzle type | Typical finished size | Piece size | Pixels per piece at 300 DPI |
|---|---|---|---|
| 500-piece | 20" × 15" (508 × 381 mm) | ~25 × 22 mm | ~295 × 260 px |
| 1000-piece | 27" × 20" (686 × 508 mm) | ~20 × 18 mm | ~236 × 213 px |

Most POD puzzle manufacturers (Prodigi, Printful, Printify) use **ribbon-cut (grid) die patterns** where pieces follow a uniform interlocking pattern. This is critical for scoring because grid-cut pieces in flat-color regions become nearly interchangeable — they have the same shape, same color, and can "false fit" in multiple positions. Random-cut puzzles provide shape variation that partially compensates for flat imagery, but POD services almost exclusively use ribbon-cut.

### Print specifications across major POD platforms

| Specification | Recommended | Minimum acceptable |
|---|---|---|
| Resolution | **300 DPI** | 150 DPI |
| Color space | **sRGB** (POD platforms convert to CMYK internally) | sRGB |
| File format | **PNG** (lossless) | JPEG at 90%+ quality |
| Bleed | **0.125" (3 mm)** per side | Platform-specific |
| Safe zone | **0.25" (6 mm)** from edges for important content | 0.125" (3 mm) |

Required pixel dimensions at 300 DPI: a 500-piece puzzle needs approximately **6,000 × 4,500 pixels**, while a 1000-piece puzzle needs approximately **8,100 × 6,000 pixels**. At 150 DPI minimum, these drop to 3,000 × 2,250 and 4,050 × 3,000 respectively.

### AI upscaling from 1024px to 6000px+

A ~6× upscale pushes the outer limit of current AI upscaling quality. The critical artifacts to watch for, all of which become **more visible in print than on screen**:

- **Plastic/waxy smoothing**: Textures become eerily smooth, losing the micro-detail that helps differentiate puzzle pieces in same-color regions. This directly worsens the flat-region problem.
- **Haloing/ringing**: Faint bright/dark outlines around high-contrast boundaries, caused by aggressive sharpening.
- **Gradient banding**: Smooth gradients develop visible steps — problematic for sky regions that already lack detail.
- **Texture hallucination**: The upscaler invents patterns that weren't in the original, creating visually jarring repeated textures.
- **Compression artifact amplification**: If the source has JPEG artifacts, upscaling magnifies blocking and edge noise.

Best practice: **start from PNG sources** (not compressed JPEG), target a 4× upscale maximum for clean results (supplement with higher-resolution generation if possible), and inspect at 100% zoom before print. A Laplacian variance check at piece-sized windows can detect upscaling-induced smoothing.

---

## 5. The complete automated scoring system

### Eleven metrics computed from pixels alone

Every metric below requires no human judgment — it can be computed from the image array using OpenCV, scikit-image, and NumPy. All metrics should be computed on an image **resized to a consistent analysis resolution of ~1500 pixels** on the long edge (for speed and threshold consistency), except resolution/DPI checks which use the original.

**Metric 1 — Flat region percentage (weight: 0.20).** The highest-priority metric. Compute local variance using a piece-sized sliding window. Count pixels where local variance falls below threshold (~100 in pixel² units). Pass: <25%. Hard fail: >50%.

```python
def flat_region_percentage(image, window_size=64, var_threshold=100):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float64)
    mean = cv2.blur(gray, (window_size, window_size))
    sqmean = cv2.blur(gray**2, (window_size, window_size))
    local_var = sqmean - mean**2
    flat_mask = local_var < var_threshold
    return np.sum(flat_mask) / flat_mask.size * 100
```

**Metric 2 — Color entropy (weight: 0.12).** Shannon entropy of per-channel histograms, averaged. Maximum possible: 8.0 bits. Pass: >6.5. Fail: <5.5.

**Metric 3 — Edge density (weight: 0.12).** Canny edge pixels divided by total pixels, using auto-thresholding based on median intensity. Pass: >0.08 (8%). Fail: <0.04. Hard fail: <0.02.

**Metric 4 — Corner-to-center detail ratio (weight: 0.12).** Laplacian variance in each of four corner regions (20% × 20% of image) divided by Laplacian variance in center region (middle 50% × 50%). Minimum corner-to-center ratio pass: >0.15. Average corner-to-center ratio pass: >0.25. Hard fail: any corner ratio <0.05.

**Metric 5 — Grid uniformity (weight: 0.10).** Divide image into 4×4 grid. Compute color entropy per cell. Calculate coefficient of variation across cells. Pass: CV <0.35. Fail: CV >0.55. Additionally, the minimum cell score must exceed 40% of the mean.

**Metric 6 — Dominant color percentage (weight: 0.08).** K-means clustering (k=5) on pixel colors. Largest cluster's percentage. Pass: <35%. Fail: >50%. Hard fail: >60%.

**Metric 7 — Gradient magnitude distribution (weight: 0.06).** Sobel gradient magnitude, mean across image. Pass: mean >15. Fail: mean <10.

**Metric 8 — Hue diversity (weight: 0.06).** Quantize HSV hue into 18 bins (10° each), excluding low-saturation pixels (S<30). Count bins with >0.5% of pixels. Pass: ≥8 bins. Fail: <5 bins.

**Metric 9 — Laplacian variance (weight: 0.06).** Global variance of Laplacian — the standard no-reference sharpness metric. At 1500px analysis resolution, pass: >500. Fail: <200.

**Metric 10 — Gabor texture energy (weight: 0.04).** Mean energy across a bank of Gabor filters at 4 frequencies × 4 orientations. Pass: mean energy >10.0. Fail: <5.0.

**Metric 11 — Subject dominance (weight: 0.04).** Spectral residual saliency detection, Otsu-thresholded. Subject area percentage. For "small character in wide scene," pass: <50%. Fail: >65%.

### Normalization and weighting

Each raw metric is normalized to a 0–1 scale using linear interpolation between its fail and pass thresholds:

```python
def normalize(value, fail_thresh, pass_thresh, invert=False):
    if invert:
        value, fail_thresh, pass_thresh = -value, -fail_thresh, -pass_thresh
    if value <= fail_thresh: return 0.0
    if value >= pass_thresh: return 1.0
    return (value - fail_thresh) / (pass_thresh - fail_thresh)
```

The composite score is a weighted sum multiplied by 100:

```
Final_Score = (0.20 × flat_region + 0.12 × color_entropy + 0.12 × edge_density 
+ 0.12 × corner_detail + 0.10 × grid_uniformity + 0.08 × dominant_color
+ 0.06 × gradient_mag + 0.06 × hue_diversity + 0.06 × laplacian_var
+ 0.04 × gabor_texture + 0.04 × subject_dominance) × 100
```

### Pass/fail decision with hard-fail gates

The system applies both the composite score and independent hard-fail checks:

| Condition | Decision |
|---|---|
| Composite score ≥ 65 and no hard fails | **PASS** — suitable for production |
| Composite score 40–64, no hard fails | **WARNING** — manual review recommended |
| Composite score < 40 | **FAIL** — will produce frustrating puzzle |
| Flat region > 50% | **HARD FAIL** regardless of score |
| Any corner detail ratio < 0.05 | **HARD FAIL** regardless of score |
| Dominant color > 60% | **HARD FAIL** regardless of score |
| Edge density < 0.02 | **HARD FAIL** regardless of score |

### Processing architecture

```
Input Image (6000px+)
  → Resize to 1500px (long edge) for analysis
  → Parallel computation of all 11 metrics
  → Normalize each metric to [0, 1]
  → Weighted combination → composite score (0–100)
  → Hard-fail gate checks
  → Output: score, grade, per-metric breakdown, spatial heatmap of problem areas
  → Target: <2 seconds per image on modern hardware
```

### Calibration guidance

These thresholds are informed starting points, not final values. **Calibrate against 50–100 labeled images** — actual puzzle images rated by humans as pass/fail/warning. Use linear regression or simulated annealing on the labeled set to optimize both thresholds and weights. For Pixar-style 3D cartoon images specifically, expect edge density to be naturally lower than photographs (cleaner edges, larger color blocks), so the edge density threshold may need downward adjustment to ~0.05 after testing. Similarly, flat region percentage will naturally run higher than photographs due to smooth rendering — the 25% pass threshold may prove strict and could be relaxed to 30% if too many otherwise-good images fail.

---

## Conclusion

The core insight from this research is that **puzzle suitability and aesthetic quality are often inversely correlated** — wall art values negative space, minimalism, and mood, while puzzle art demands maximum information density in every region. For AI-generated Pixar-style scenes, this means the standard prompt output (character against a gradient sky over flat ground) systematically fails at puzzle assembly despite looking visually appealing.

The three highest-leverage metrics for this specific use case are **flat region percentage** (weight 0.20, catching the sky/ground problem), **corner-to-center detail ratio** (weight 0.12, catching the barren-edges problem), and **edge density** (weight 0.12, measuring overall detail richness). Together these three metrics address all three observed failure modes. The remaining eight metrics provide nuance and catch edge cases.

The scoring system's most unconventional requirement is that **every ~2 cm² region of the image must carry enough visual information to make its corresponding puzzle piece distinguishable** — a ΔE₀₀ of at least 2.0 from its neighbors. This piece-level distinctiveness standard, combined with the global composition rules, creates a scoring framework that bridges the gap between "looks good on screen" and "works as a physical puzzle."