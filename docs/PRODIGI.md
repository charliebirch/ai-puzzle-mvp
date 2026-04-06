# Prodigi — Fulfillment Partner Reference

**Selected:** 2026-04-06  
**Primary market:** UK (Prodigi UK fulfillment, 2-5 day domestic)  
**Launch sizes:** 110pc (kids entry) + 252pc (kids standard)  
**Integration method:** Prodigi Print API v4 (REST)

> **Consultant note:** Prodigi is a solid UK-centric POD partner with a mature API and no minimums. The main gotchas are resolution requirements (your pipeline must output at 300 DPI), landscape orientation (all puzzles are landscape — pipeline redesign needed), and margin pressure (costs are real, pricing strategy matters).

---

## Product Range

### Jigsaw Puzzles

All puzzles include a **premium metal presentation tin** with a custom-printed lid. Pieces are 1mm pressed paperboard with high-gloss varnish, printed using dye-sublimation.

| Name | Pieces | Completed Size | Tin Size | Our Use |
|------|--------|---------------|----------|---------|
| Mini | 30pc | 250×200mm | Small (130×85×50mm) | – |
| Kids | 110pc | 250×200mm | Small (130×85×50mm) | **Launch** |
| Standard | 252pc | 375×285mm | Small (130×85×50mm) | **Launch** |
| Classic | 500pc | 530×390mm | Large (202×167×63mm) | Future |
| Premium | 1000pc | 765×525mm | Large (202×167×63mm) | Future |

**Materials:**
- Pieces: 1mm pressed paperboard
- Print: Dye-sublimation, edge-to-edge, high-gloss varnish
- Box: Recycled corrugated cardboard
- Tin: Premium metal, full custom lid print (separate from puzzle surface)

---

## File Requirements

### Puzzle Surface

| Size | Completed mm | Required px @ 300 DPI | Aspect |
|------|-------------|----------------------|--------|
| 110pc | 250×200mm | **2953×2362px** | ~5:4 landscape |
| 252pc | 375×285mm | **4429×3366px** | ~4:3 landscape |
| 500pc | 530×390mm | **6260×4606px** | ~4:3 landscape |
| 1000pc | 765×525mm | **9035×6165px** | ~3:2 landscape |

> **All puzzles are landscape orientation.** Current pipeline generates portrait — this requires a redesign (see Pipeline Gaps below).

- **Format:** JPG (preferred) or PDF
- **Color space:** sRGB
- **DPI:** 300 minimum — below this is unacceptable for print
- **Bleed:** Handled automatically by Prodigi API — do not manually add bleed

### Tin Lid (separate asset)

The tin lid requires a **separate image** at its own dimensions:

| Tin | Applies to | Lid px @ 300 DPI |
|-----|-----------|------------------|
| Small | 30/110/252pc | **869×674px** |
| Large | 500/1000pc | **1724×1169px** |

**Current approach:** Auto-crop/resize the final puzzle image to the lid dimensions. No separate design needed at launch — revisit if branding becomes a priority.

---

## Prodigi SKU Reference

SKUs confirmed from `prodigi-jigsaws-gb-pricing.csv` (2026-04-06).

| Our Name | Prodigi SKU | Pieces | Size | Unit Cost (GBP) | Print Assets Needed |
|----------|------------|--------|------|-----------------|---------------------|
| Starter | `JIGSAW-PUZZLE-30` | 30 | 250×200mm | £10.00 | Puzzle surface + small tin lid |
| Kids | `JIGSAW-PUZZLE-110` | 110 | 250×200mm | £12.00 | Puzzle surface + small tin lid |
| Standard | `JIGSAW-PUZZLE-252` | 252 | 375×285mm | £13.00 | Puzzle surface + small tin lid |
| Classic | `JIGSAW-PUZZLE-500` | 500 | 530×390mm | £16.00 | Puzzle surface + large tin lid |
| Premium | `JIGSAW-PUZZLE-1000` | 1000 | 765×525mm | £20.00 | Puzzle surface + large tin lid |

---

## API Integration

### Authentication

```http
X-API-Key: <your-api-key>
```

Get your key: Prodigi dashboard → Settings → Integrations → API → Show API Key

### Environments

| Environment | Base URL | When to use |
|-------------|----------|-------------|
| Sandbox | `https://api.sandbox.prodigi.com` | All development + testing (no charge) |
| Live | `https://api.prodigi.com` | Production orders only |

**Always test in sandbox first.** The sandbox is fully functional — it simulates the full order flow without billing.

### Key Endpoints

```
POST   /v4.0/orders                            Create order
GET    /v4.0/orders/{id}                       Get order status
GET    /v4.0/orders                            List orders
POST   /v4.0/quotes                            Get price quote
POST   /v4.0/orders/{id}/actions/cancel        Cancel order
POST   /v4.0/orders/{id}/actions/updateShippingMethod
POST   /v4.0/orders/{id}/actions/updateRecipient
```

### Create Order — Minimal Example

```json
POST /v4.0/orders
{
  "merchantReference": "etsy-order-12345",
  "idempotencyKey": "etsy-order-12345",
  "shippingMethod": "Standard",
  "recipient": {
    "name": "Jane Smith",
    "address": {
      "line1": "14 High Street",
      "town": "London",
      "postcode": "SW1A 1AA",
      "countryCode": "GB"
    }
  },
  "items": [
    {
      "merchantReference": "etsy-order-12345-item-1",
      "sku": "JIGSAW-PUZZLE-252",
      "copies": 1,
      "sizing": "fillPrintArea",
      "assets": [
        {
          "printArea": "default",
          "url": "https://your-cdn.com/puzzle-surface.jpg"
        },
        {
          "printArea": "lid",
          "url": "https://your-cdn.com/tin-lid.jpg"
        }
      ]
    }
  ]
}
```

**Important:**
- `idempotencyKey`: Set to your order ID — prevents duplicate orders if the request is retried
- `sizing`: Use `fillPrintArea` — fills the print area, may crop edges slightly. Alternative: `fitPrintArea` (adds white borders)
- Assets must be **publicly accessible URLs** — Prodigi downloads the images directly
- Images are deleted from Prodigi servers ~2 weeks after fulfillment — keep your own copies

### Order Status

| Status | Meaning |
|--------|---------|
| `InProgress` | Order submitted, processing |
| `Complete` | All items dispatched |
| `Cancelled` | Order cancelled |

Detailed sub-stages: asset download → lab allocation → asset preparation → production → shipping.

### Webhooks

Configure in Prodigi dashboard (global) or per-order via `callbackUrl` field. Events follow the [CloudEvents spec](https://cloudevents.io/).

Events include: stage changes, shipment notifications, tracking numbers.

**Recommendation:** Set up webhooks to push order status back to your job tracking system (`web/jobs.py`) so the wizard can show fulfillment progress.

### Error Handling

Prodigi has **174+ API outages** recorded — build retry logic for order creation. Use `idempotencyKey` to safely retry without duplicate orders.

```python
# Pseudocode — safe retry pattern
for attempt in range(3):
    response = prodigi.create_order(idempotency_key=order_id, ...)
    if response.outcome in ("created", "ok"):
        break
    if response.outcome == "validationFailed":
        raise  # don't retry validation errors
    time.sleep(2 ** attempt)  # exponential backoff
```

---

## Order Flow (End-to-End)

```
1. Customer places Etsy order → selects 110pc or 252pc + uploads photo
2. Charlie receives Etsy order notification
3. Run wizard pipeline (~£0.38, ~12 min):
   - Step 1: Background removal
   - Step 2: Character generation (Pixar-style)
   - Step 3: Costume selection
   - Step 4: Scene generation (landscape)
   - Step 5: Composite + quality score + pick best
4. Export final image at target resolution:
   - 110pc → 2953×2362px JPG @ 300 DPI
   - 252pc → 4429×3366px JPG @ 300 DPI
   + Auto-crop tin lid image (869×674px)
5. Upload both assets to publicly accessible URL (e.g. S3, Cloudflare R2)
6. POST to Prodigi API (sandbox first to verify)
7. Prodigi produces puzzle (72h) + dispatches
8. UK domestic delivery: 2-5 working days
9. Customer receives puzzle
```

**Total customer timeline:** ~4-8 working days from order to delivery (UK).

---

## Shipping

### UK Customers (Primary Market)

Prices from `prodigi-jigsaws-gb-pricing.csv`. All are GB→GB rates.

| Tier | First item | +1 item | Tracked | Days |
|------|-----------|---------|---------|------|
| Budget | £3.95 | £0.25 | No | 2-3 |
| Standard | £5.25 | £0.25 | No | 2-3 |
| Express | £6.25 | £0.00 | Yes | 1-2 |
| Overnight | £9.95 | £0.00 | Yes | 1 |

**Recommendation:** Launch with Standard (£5.25, 2-3 days). Budget saves £1.30 but is untracked — not worth the customer service risk on a £25-35 gift. Express at £6.25 is a reasonable premium upsell.

### Other Markets (Future)

| Destination | Typical Time |
|-------------|-------------|
| UK to EU | 5-7 working days |
| UK to US/Canada | 10-15 working days |
| Australia domestic | 2-5 working days (if AU fulfillment used later) |
| AU to NZ | 7-10 working days |
| International | 10-30 working days |

---

## Pricing & Margin (UK Market)

All costs confirmed from `prodigi-jigsaws-gb-pricing.csv`. Standard shipping (£5.25). Etsy fees: 6.5% transaction + £0.20 listing fee.

| Size | Prodigi unit | Standard shipping | Pipeline | Etsy (6.5%+£0.20) | **Total cost** | Suggested list | **Margin** |
|------|-------------|------------------|----------|-------------------|----------------|----------------|------------|
| 110pc | £12.00 | £5.25 | £0.38 | £1.83 at £25 | **£19.46** | **£25** | **£5.54** |
| 110pc | £12.00 | £5.25 | £0.38 | £2.02 at £28 | **£19.65** | **£28** | **£8.35** |
| 252pc | £13.00 | £5.25 | £0.38 | £2.28 at £32 | **£20.91** | **£32** | **£9.09** |
| 252pc | £13.00 | £5.25 | £0.38 | £2.68 at £35 | **£21.31** | **£35** | **£13.69** |

**Margin verdict:** Viable. £28 for 110pc and £35 for 252pc are the sweet spots — ~30-40% margin. The 252pc at £35 is the better product to push.

**Key levers to improve margin:**
1. Prodigi Pro tier: 15% off unit costs (£12→£10.20, £13→£11.05) — worthwhile after ~20 orders/month
2. Free shipping model: Build £5.25 into list price — Etsy favours free-shipping listings in search
3. 30pc puzzle (£10 unit): cheapest entry point, same small tin — could be £18-20 for a "pocket money" gift tier

**Note on free shipping:** If you offer "free shipping" on Etsy by building the cost in, the maths shifts slightly (Etsy takes 6.5% of shipping too if you charge it separately, so the difference is minimal).

---

## Quality Considerations

### Known Issues from Reviews
- **Color accuracy inconsistency** — some batches have noticeably different colors vs your sRGB file. Mitigate by ordering samples and calibrating.
- **Print clarity** — "can be poor at times" per independent reviews. Dye-sublimation is generally excellent; inconsistency likely lab-dependent.
- **Customer support shift** — Prodigi recently moved to AI support. May be slower for complex issues.

### Pre-launch Checklist
- [ ] Order at least 1 sample of each size with a real pipeline output
- [ ] Check: color accuracy (compare screen vs print)
- [ ] Check: piece cut quality (no rough edges, pieces interlock firmly)
- [ ] Check: tin lid alignment and print quality
- [ ] Check: box packaging condition

### Image Retention
Prodigi auto-deletes uploaded images ~2 weeks post-fulfillment. Always keep your own copies in `orders/<order_id>/` and back up to cloud storage before fulfillment.

---

## Pipeline Gaps to Fix Before Launch

These are **blockers** — the current pipeline cannot produce print-ready files without these changes.

### 🔴 GAP 1 — Resolution (Blocker)

Current pipeline outputs ~1024px from Kontext Max. Real-ESRGAN at 2x → ~2048px.

**Required:**
- 110pc: **2953px** (achievable with 4x upscale from 1024px = 4096px ✓)
- 252pc: **4429px** (achievable with 4x upscale ✓)
- 500pc: **6260px** (needs 4x from 1536px output, or chain 2x→2x)
- 1000pc: **9035px** (needs 4x from 2048px output ✓)

**Fix:** Change `pipeline_steps.py` to use Real-ESRGAN 4x scale instead of 2x. This is a one-line change in `step_upscale()`.

**Note:** CLAUDE.md already flagged this as "upscale 4x for actual puzzle printing (currently 2x for preview)."

### 🔴 GAP 2 — Landscape Orientation (Blocker)

All Prodigi puzzles are landscape. Current pipeline generates portrait/square images.

**Required changes:**
1. **FLUX 2 Pro scene gen**: Add `width`/`height` params to force landscape aspect (e.g. `width=1344, height=1008` for 4:3). Verify FLUX 2 Pro supports this via Replicate API.
2. **Scene prompt** (`scene_prompts.py`): Update village prompt to describe a wider scene. Add horizontal elements — cobblestone path stretching wide, market stalls on both sides, clock tower on right edge, tree arch on left.
3. **Compositing** (`composite_pil.py`): Adjust character positioning for landscape canvas. Character off-center left; more scene visible on right.
4. **Quality scorer** (`puzzle_scorer.py`): Verify no metrics assume portrait aspect ratio.

### 🟡 GAP 3 — Export Step (Pre-launch)

No current pipeline step generates the final print-ready files at the correct DPI/dimensions. Need:
- A `step_export_for_print()` function in `pipeline_steps.py` that:
  - Takes the upscaled image + target size (110pc, 252pc, etc.)
  - Outputs puzzle surface JPG at exact pixel dimensions
  - Generates tin lid JPG via center-crop of puzzle surface
  - Returns both file paths

### 🟡 GAP 4 — Asset Hosting (Pre-launch)

Prodigi API requires **publicly accessible image URLs** — it downloads the images directly. The current pipeline saves files locally.

Options:
- Simple: Upload to a temporary public URL (e.g. Cloudflare R2, S3, imgbb)
- Integrated: Add a `step_upload_assets()` step that uploads and returns URLs
- Manual for now: Charlie manually uploads to a hosting URL per order

For v1 manual fulfillment, manual hosting is fine. Build automation when order volume justifies it.

---

## Integration with Etsy

Prodigi has a native Etsy integration (connect store in Prodigi dashboard). However, for this business the pipeline is **custom** — standard Etsy integration won't work because the image is generated per-order.

**Recommended approach (v1):**
1. Etsy listing is standard (static photos of sample output)
2. Customer orders via Etsy → Charlie gets notified
3. Charlie runs wizard pipeline manually
4. Charlie places Prodigi order manually (dashboard or API)

**Future (API-driven):**
- Etsy webhook → trigger pipeline → auto-submit to Prodigi API
- Requires Etsy Seller API + Prodigi API integration

---

## Resources

| Resource | URL |
|----------|-----|
| Prodigi puzzle product page | https://www.prodigi.com/products/sport-and-games/jigsaw-puzzles/ |
| Prodigi Print API docs | https://www.prodigi.com/print-api/docs/reference/ |
| Prodigi Postman collection | https://postman.prodigi.com/ |
| Prodigi dashboard | https://dashboard.prodigi.com |
| Prodigi sandbox API | https://api.sandbox.prodigi.com |
| Prodigi support | support@prodigi.com |

---

## Decision Log

| Decision | Choice | Rationale | Date |
|----------|--------|-----------|------|
| Fulfillment partner | Prodigi | Strong UK fulfillment, mature API, no minimums, premium tin packaging | 2026-04-06 |
| Launch market | UK | Business partner in UK, fast Prodigi UK domestic shipping | 2026-04-06 |
| Launch sizes | 110pc + 252pc | Kids gifting focus, lower unit cost, smaller tin easier to ship | 2026-04-06 |
| Tin lid design | Auto-crop puzzle image | Zero extra work, consistent look, revisit if branding needed | 2026-04-06 |
| Orientation | Landscape | All Prodigi puzzles are landscape — pipeline must be redesigned | 2026-04-06 |
| Integration method | Manual v1 → API v2 | Custom pipeline can't use Prodigi's Etsy auto-sync | 2026-04-06 |
