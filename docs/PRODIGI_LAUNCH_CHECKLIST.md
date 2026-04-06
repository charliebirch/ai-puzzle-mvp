# Prodigi Launch Checklist

Step-by-step from "pipeline ready" to "first customer puzzle shipped."

---

## Phase 1 — Setup (one-time)

- [ ] Create Prodigi account at dashboard.prodigi.com
- [ ] Download GBP price sheet from dashboard → verify unit costs for 110pc + 252pc
- [ ] Confirm exact Prodigi SKU codes for 110pc and 252pc puzzles
- [ ] Get API key: Settings → Integrations → API → Show API Key
- [ ] Save API key in `.env` as `PRODIGI_API_KEY`

---

## Phase 2 — Pipeline Fixes (before any order)

- [ ] **Fix upscale to 4x** — change `step_upscale()` in `pipeline_steps.py` to use scale=4 (not 2)
- [ ] **Add landscape output to FLUX 2 Pro** — pass `width=1344, height=1008` (4:3) in scene generation
- [ ] **Redesign scene prompt for landscape** — update `scene_prompts.py` village prompt with wider composition
- [ ] **Update composite layout** — adjust `composite_pil.py` for landscape canvas, character left-of-center
- [ ] **Verify quality scorer** — confirm no portrait-specific assumptions in `puzzle_scorer.py`
- [ ] **Add export step** — write `step_export_for_print()` in `pipeline_steps.py`:
  - Input: upscaled image + target size ('110pc', '252pc', etc.)
  - Output: puzzle surface JPG at exact pixel dimensions + tin lid JPG (center-cropped)

---

## Phase 3 — Sandbox Testing (no charge)

- [ ] Run a test order through Prodigi sandbox API using a real pipeline output
- [ ] Verify both assets (puzzle surface + tin lid) upload successfully
- [ ] Confirm order status transitions: `InProgress` → `Complete`
- [ ] Check order in Prodigi dashboard matches what the API returns

---

## Phase 4 — Sample Order (real charge, ~£15-20)

- [ ] Generate a puzzle from a real photo using the fixed pipeline
- [ ] Export print-ready files (puzzle surface + tin lid at correct dimensions)
- [ ] Upload assets to a public URL (manually for now)
- [ ] Place a real Prodigi order (your own address, UK)
- [ ] Wait ~72h production + 2-5 day shipping
- [ ] **QC the physical puzzle:**
  - [ ] Color accuracy vs screen
  - [ ] Print clarity and sharpness
  - [ ] Piece cut quality (no rough edges, pieces interlock well)
  - [ ] Tin lid print quality
  - [ ] Box condition on arrival

---

## Phase 5 — Etsy Listing

- [ ] Set pricing (based on Phase 1 cost sheet):
  - 110pc: £22-25 (verify with exact costs)
  - 252pc: £27-32 (verify with exact costs)
- [ ] Create Etsy listing with:
  - Sample puzzle photos from Phase 4
  - Clear description: "Personalised Pixar-style jigsaw puzzle from your photo"
  - Size options: 110pc / 252pc
  - Turnaround time: 5-8 working days (production 3 days + shipping 2-5 days)
  - Shipping: included in price or explicit shipping charge
- [ ] Set Etsy processing time to 3-4 days (matches Prodigi 72h production)

---

## Phase 6 — First Customer Order

- [ ] Receive Etsy order + customer photo
- [ ] Run wizard pipeline
- [ ] Review output — confirm quality before ordering
- [ ] Export print-ready files
- [ ] Upload to public URL
- [ ] Place Prodigi order via dashboard (manual v1)
- [ ] Note: Prodigi deletes images after ~2 weeks — keep your copy in `orders/<order_id>/`
- [ ] Confirm dispatch notification from Prodigi
- [ ] Forward tracking number to customer via Etsy messaging

---

## Phase 7 — Automate (after first 5 orders)

- [ ] Build `prodigi_client.py` in `src/` — Python wrapper around Prodigi API
- [ ] Add asset upload step (S3 / Cloudflare R2 / imgbb)
- [ ] Auto-submit order after user picks best composite in wizard Step 5
- [ ] Webhook → update job status in `web/jobs.py` with Prodigi order ID + tracking

---

## Key Numbers to Have Ready

| Item | Value |
|------|-------|
| Prodigi API key | (from dashboard) |
| 110pc SKU | (confirm from dashboard) |
| 252pc SKU | (confirm from dashboard) |
| 110pc unit cost GBP | (from price sheet) |
| 252pc unit cost GBP | (from price sheet) |
| UK standard shipping cost | (from price sheet) |
| Prodigi support email | support@prodigi.com |
