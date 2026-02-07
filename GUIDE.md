# AI Puzzle MVP - Your Guide

This is your tool for turning customer photos into personalised animated jigsaw puzzles — Pixar-style cartoon characters that look like the person in the photo.

A customer sends you a photo of their kid on Etsy. You feed it into this tool. Out comes a magical cartoon version of that kid, sized and ready to send to a puzzle printer. That's the whole idea.

---

## What's in this project

Here's what each folder does - you only need to care about a few of them:

```
AI-PUZZLE-MVP/
│
├── input/              << PUT CUSTOMER PHOTOS HERE (one subfolder per person)
│   ├── Chaz/           e.g. input/Chaz/charlie-outside.jpg
│   ├── Edgar/          e.g. input/Edgar/edgar-bar.jpg
│   └── ...
├── orders/             << FINISHED ORDERS APPEAR HERE
├── output/             << TEST RUNS AND BENCHMARKS GO HERE
│
├── src/                   (all the code - you don't need to edit these)
│   ├── backends/          AI model connections (FLUX Kontext Pro + face swap)
│   ├── quality/           Face checking and image quality scoring
│   ├── puzzle_maker.py    Quick one-off puzzle generation
│   ├── benchmark_runner.py  Test runner
│   ├── fulfill_order.py   MAIN TOOL - full order start to finish
│   ├── upscale.py         Makes images big enough for printing
│   ├── export.py          Creates print-ready files with correct margins
│   ├── print_specs.py     Puzzle size and printer settings
│   ├── style_presets.py   Art style (storybook cartoon)
│   ├── consent.py         Logs that the customer said "yes, use my photo"
│   └── test_suite.py      Registry of test photos for benchmarking
│
├── web/                   Web interface (upload form, progress tracking)
├── docs/                  Legal stuff (terms of service, privacy policy)
│
├── requirements.txt       List of software this project needs
├── .env                   Your Replicate API key (private, not shared)
├── GUIDE.md               THIS FILE
└── README.md              Technical reference
```

**The folders you'll actually use day-to-day:** `input/` and `orders/`.

---

## First-time setup

You only need to do this once.

### 1. Open Terminal

On Mac: press `Cmd + Space`, type "Terminal", press Enter.

### 2. Go to the project folder

```bash
cd ~/Personal/"AI Puzzle"/AI-PUZZLE-MVP
```

### 3. Set up Python environment

This creates an isolated space for the project's software so it doesn't mess with anything else on your computer:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

You'll see `(.venv)` appear at the start of your terminal line. That means it's working.

### 4. Install the required software

```bash
pip install -r requirements.txt
```

This will take a minute or two. It's downloading the AI face detection tools, web framework, image processing libraries, etc.

### 5. Set up your API key

Your Replicate API key should already be in the `.env` file. If you need to change it:

```bash
nano .env
```

It should contain:
```
REPLICATE_API_TOKEN=r8_your_key_here
```

Press `Ctrl+X`, then `Y`, then `Enter` to save.

### 6. Done!

You're set up. Jump to whichever section below matches what you want to do.

---

## Every time you come back

Whenever you open a new Terminal window to use this tool, you need to do two things:

```bash
cd ~/Personal/"AI Puzzle"/AI-PUZZLE-MVP
source .venv/bin/activate
```

That's it. Now you can run any of the commands below.

---

## How to: Process a customer order (the main thing)

This is the command you'll use most. It takes a customer photo and produces everything you need: a preview to send them for approval, and a print-ready file to send to the puzzle printer.

```bash
cd src && python3 fulfill_order.py \
  --photo ../input/Chaz/charlie-outside.jpg \
  --style storybook_cartoon \
  --subject "a young boy with brown hair" \
  --puzzle-size 1000 \
  --order-id ETSY-12345
```

**What to fill in:**

| Flag | What it means | Your options |
|------|--------------|--------------|
| `--photo` | Path to the customer's photo | Whatever you named the file in `input/` |
| `--style` | The art style | `storybook_cartoon` (default), `space_explorer`, `underwater_adventure`, `pixel_platformer` |
| `--subject` | Describe who's in the photo | e.g. "a young boy", "a smiling woman", "two siblings" |
| `--puzzle-size` | How many pieces | `500` or `1000` |
| `--order-id` | Your tracking ID | Match your Etsy order e.g. `ETSY-12345` |

**What it does (step by step):**

1. Checks the photo is good enough (not too small, fixes phone rotation)
2. Logs that the customer consented to AI processing
3. Sends the photo to FLUX Kontext Pro to create the cartoon version
4. Runs face swap to make sure the face matches the original person
5. Checks quality (face similarity, colour vibrancy, edge cleanliness)
6. Upscales the image to full print resolution (6000x8400 pixels for 1000pc)
7. Creates a preview image (with puzzle grid lines overlaid)
8. Creates a print-ready file (correct size, margins, 300 DPI)

**Where to find the results:**

Everything lands in `orders/ETSY-12345/` (or whatever order ID you used):

```
orders/ETSY-12345/
├── preview.jpg          << Send this to the customer for approval
├── print_ready.jpg      << Send this to the puzzle printer
├── generated.png        << The AI output (no grid, no margins)
├── upscaled.png         << High-res version
├── input_resized.jpg    << The photo you fed in
├── faces/               << Cropped face comparisons
│   ├── face_source.jpg
│   └── face_generated.jpg
└── manifest.json        << Full details of the run (cost, scores, etc.)
```

**Typical cost per order:** About $0.045 in API fees (the AI processing + face swap + upscaling).

---

## How to: Quick test a single photo

If you just want to see what a photo looks like in the cartoon style without the full order process:

```bash
cd src && python3 puzzle_maker.py \
  --input ../input/Chaz/charlie-outside.jpg \
  --output ../output/test_puzzle.png \
  --style storybook_cartoon \
  --subject "a smiling person"
```

This is faster and cheaper - it skips upscaling and print prep. Good for experimenting.

---

## How to: Use the web interface

Instead of typing commands, you can use a browser-based interface:

```bash
cd ~/Personal/"AI Puzzle"/AI-PUZZLE-MVP
source .venv/bin/activate
uvicorn web.app:app --reload --port 8000
```

Then open your browser and go to: **http://localhost:8000**

You'll see an upload form where you can:
1. Pick a photo file
2. Describe the subject
3. Tick the consent box
4. Hit "Start Processing"

It'll show you a progress page that updates every few seconds. When done, you can preview and download the results right from the browser.

**To stop the web server:** go back to Terminal and press `Ctrl+C`.

---

## Art styles

Four styles are available — three Pixar-style cartoon and one pixel art. All are fun, colourful, and kid-friendly.

| Style | What it looks like |
|-------|-------------------|
| **Storybook Cartoon** | Character in a colourful whimsical village with floating lanterns and playful details. Exaggerated expressive eyes and soft cartoon shading. |
| **Space Explorer** | Cartoon astronaut floating in a bright outer space scene with colourful planets, a rocket ship, friendly aliens, and glowing nebulas. Deep blues/purples with pops of orange, pink, and teal. |
| **Underwater Adventure** | Cartoon deep-sea explorer surrounded by coral reefs, friendly sea creatures (clownfish, turtles, octopus), sunken treasure, and shimmering bubbles. Warm turquoise tones with golden light rays. |
| **Pixel Platformer** | Pixel art character in a colourful side-scrolling platformer level with platforms, clouds, coins, pipes, and blocks against a bright blue sky. Classic 16-bit game aesthetic. Face swap is automatically disabled (pixel art + realistic face = bad). |

To choose a style, use the `--style` flag:

```bash
--style storybook_cartoon    # default
--style space_explorer
--style underwater_adventure
--style pixel_platformer
```

---

## How it works (the AI pipeline)

1. **FLUX Kontext Pro** ($0.04) — transforms the photo into a cartoon illustration, preserving hair and appearance
2. **codeplugtech/face-swap** ($0.003) — swaps the face from the original photo onto the cartoon to ensure it's clearly recognisable
3. **Quality scoring** — checks face similarity, colour vibrancy, and edge cleanliness
4. **Real-ESRGAN upscale** ($0.002) — scales up to print resolution

If face swap fails for any reason, the pipeline continues with the un-swapped image and logs a warning.

---

## Puzzle sizes

| Size | Finished dimensions | Print file size | Price |
|------|-------------------|-----------------|-------|
| **500 pieces** | 16" x 20" | 4800 x 6000 pixels | $39.99 |
| **1000 pieces** | 20" x 28" | 6000 x 8400 pixels | $49.99 |

---

## Your Etsy order workflow

1. Customer messages you on Etsy with their photo and chosen style
2. Save their photo to a subfolder in `input/` named after the person (e.g. `input/CustomerName/photo.jpg`)
3. Run the `fulfill_order.py` command (see above)
4. Open `orders/<order-id>/preview.jpg` and send it to the customer on Etsy for approval
5. Customer approves
6. Upload `orders/<order-id>/print_ready.jpg` to createjigsawpuzzles.com
7. Ship the puzzle to the customer

---

## Quality scores explained

After each generation, you'll see a quality score out of 100. Here's what it means:

- **70+** = Good to go. Face is recognisable, colours are vivid.
- **50-70** = Might be okay. Check the preview carefully, especially the face.
- **Below 50** = Probably not good enough. Re-run or try a different photo.

The score is made up of:
- **Face similarity (40%)** - Does the face still look like the original person?
- **Colour vibrancy (20%)** - Are the colours vivid and saturated (good cartoon style)?
- **Face detection confidence (10%)** - Did the AI produce a clear, undistorted face?
- **Resolution (10%)** - Is it big enough for print?
- **Edge cleanliness (10%)** - Are the edges clean and deliberate (not noisy)?
- **Colour diversity (10%)** - Does it have rich, varied colours?

You can also check the `orders/<id>/faces/` folder - it saves a side-by-side crop of the original face vs the generated face so you can eyeball it yourself.

---

## Legal docs

These are in the `docs/` folder, ready for your Etsy shop:

- **`terms-of-service.md`** - Licence to process photos, refund policy, usage rights
- **`privacy-policy.md`** - What data you collect, how long you keep it, customer rights (GDPR/CCPA covered)
- **`consent-flow.md`** - How you get and log customer consent
- **`etsy-listing-template.md`** - Copy-paste title, description, tags, and pricing for your Etsy listing

---

## Troubleshooting

**"command not found: python" or "No module named..."**
You probably forgot to activate the virtual environment:
```bash
source .venv/bin/activate
```

**"REPLICATE_API_TOKEN not set" or authentication errors**
Check your `.env` file has a valid API key.

**Face similarity score is very low**
Make sure the input photo has a clear, well-lit face - avoid sunglasses, heavy shadows, or extreme angles. The face swap step should fix most identity issues.

**Generated image looks nothing like the person**
Things that help:
- Use a clear, front-facing photo
- Write a specific subject description ("a 5-year-old girl with blonde curly hair" not just "a child")
- Face swap is on by default and should handle most cases

**Web interface won't start**
Make sure nothing else is using port 8000, and that you're in the project folder with the venv activated. The full command is:
```bash
cd ~/Personal/"AI Puzzle"/AI-PUZZLE-MVP && source .venv/bin/activate && uvicorn web.app:app --reload --port 8000
```
