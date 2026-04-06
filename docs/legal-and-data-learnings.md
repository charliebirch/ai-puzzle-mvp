# AI Puzzle — Legal, Data & AI Image Learnings

**Compiled: April 2026**
**For:** Business partner reference — everything we've figured out so far on T&Cs, privacy, consent, and AI image handling.

---

## 1. The Core Legal Challenge

We're taking customer photos, running them through AI models (hosted by Replicate), and producing Pixar-style cartoon puzzle artwork. This means we need to handle:

- **Photo consent** — permission to process someone's likeness through AI
- **Data retention** — how long we keep photos and intermediates
- **Third-party processing** — photos leave our systems and hit Replicate's API
- **Children's images** — puzzles are a kids' product, so minors' photos are likely
- **IP ownership** — who owns the AI-generated artwork
- **GDPR/CCPA** — we'll sell internationally via Etsy

---

## 2. Consent Flow

### How It Works (Etsy)

1. **Etsy listing** includes a clear disclaimer: "By submitting a photo, you confirm you have the right to use it and consent to AI processing"
2. Customer sends photo via Etsy message (implicit consent)
3. We send an **explicit confirmation message** before processing:
   > "Thanks for your photo! Just to confirm: by proceeding, you agree that this photo will be processed through AI art tools to create your custom puzzle. The original photo will be deleted within 30 days of order completion. Shall I proceed?"
4. Customer confirms → we log it and start processing

### How It Works (Web Interface)

- Upload form has a **mandatory checkbox**: "I confirm I have the right to submit this photo and consent to AI processing for puzzle creation"
- Can't upload without checking it
- Consent logged automatically on submission

### What We Log

Every consent event records:
- Timestamp, order ID, photo path
- Whether consent was given (boolean)
- How it was obtained ("etsy_message" or "web_checkbox")
- Customer name (optional)
- Data retention period (30 days)

### Minors

- If the photo is of someone under 18, the ordering adult must be the parent/legal guardian (or have their consent)
- Confirmed as part of the standard consent message

### Revoking Consent

Customers can revoke at any time:
- All photos and AI intermediates deleted immediately
- Order cancelled + refunded if not yet printed
- If already printed, digital files still deleted

---

## 3. Data Retention

| Data | Kept For | Notes |
|------|----------|-------|
| Customer photos | 30 days after order completion | Then permanently deleted |
| AI intermediates (bg removal, character, scene, etc.) | 30 days after order completion | Deleted with photos |
| Final puzzle design | Duration of business | Kept for order records |
| Consent logs | 3 years | Legal best practice |
| Order metadata | Duration of business | Standard business records |

---

## 4. Third-Party Data Sharing

Photos are sent to **two** external parties only:

1. **Replicate** (replicate.com) — hosts the AI models. Photos hit their API for processing. Their privacy policy: replicate.com/privacy
2. **Print supplier** (e.g. createjigsawpuzzles.com) — receives the final print-ready image only (not the original photo)

We do **not** sell, share, or use photos for anything beyond fulfilling the specific order.

---

## 5. Customer Rights (Privacy)

We've drafted a privacy policy covering:

- **Access** — customers can request a copy of all data we hold
- **Deletion** — request deletion anytime, we action within 7 business days
- **Rectification** — request correction of inaccurate data
- **Data portability** — request data in machine-readable format

### GDPR (EU Customers)
- Legal basis: performance of a contract (fulfilling the order) + legitimate interest (quality assurance)
- Data transfers outside EU covered by standard contractual clauses
- Right to complain to local data protection authority

### CCPA (California Customers)
- We do not sell personal information
- Right to know what we collect + right to request deletion
- No discrimination for exercising rights

---

## 6. Terms of Service — Key Points

### Photo License
- Customer grants us a **limited, non-exclusive license** to process the image — solely for puzzle creation
- Customer warrants they have the right to submit the photo

### AI Disclaimer
- We explicitly state: AI outputs are **artistic interpretations** and may not perfectly represent the original
- "We make reasonable efforts to preserve facial identity but cannot guarantee exact likeness"
- This is important — the AI does change features, especially across ethnicities/skin tones (see section 8)

### IP / Ownership
- Customer gets a **personal, non-commercial use license** for the final puzzle
- They may **not** resell, commercially redistribute, or mass-produce the designs

### Refunds
- Up to 2 free regenerations if unsatisfied
- Full refund available before printing
- Case-by-case after printing

### Liability
- Capped at the purchase price of the puzzle

---

## 7. Security

- Photos stored on encrypted storage during processing
- All API calls over HTTPS
- Access limited to business operator(s)
- No persistent cloud storage of customer photos (processing is ephemeral)

---

## 8. AI-Specific Learnings (Important Context)

These are things we've discovered through testing that have legal/ethical implications:

### Identity Preservation is Hard
- AI models **will change ethnicity, skin tone, and hair** unless you explicitly reinforce these in the text prompt
- e.g. a Black man with an afro can come back as lighter-skinned with different hair if the prompt doesn't say "Black man with dark skin and natural afro"
- This is why our "artistic interpretation" disclaimer matters — and why we ask customers to describe themselves

### AI Safety Filters
- FLUX 2 Pro's safety filter occasionally **rejects completely benign photos** (e.g. a child in normal clothing)
- We retry with a different seed — usually works on second attempt
- No way to appeal or understand why it triggers

### No Face-Swap — Intentional Choice
- We considered face-swap (InstantID) but rejected it — it discards hair (technical limitation of ArcFace) and feels more "deepfake-y"
- Our approach is full character re-generation, which feels more like commissioning a portrait artist
- This distinction may matter for marketing and customer comfort

### Replicate's Role
- Photos are sent to Replicate's API, processed, and results returned
- Replicate's own policies govern what happens on their infrastructure
- We should stay current with their privacy policy as it evolves

---

## 9. What's Still TODO

- [ ] **Formal legal review** — these docs are our best effort, not lawyer-reviewed
- [ ] **Cookie/analytics policy** — if we add tracking to the web interface
- [ ] **Print supplier DPA** — data processing agreement with whoever prints the puzzles
- [ ] **Replicate DPA** — check if Replicate offers a data processing agreement for GDPR compliance
- [ ] **Age verification** — currently honour-system for confirming parental consent
- [ ] **Automated deletion** — the 30-day retention is policy but not yet automated
- [ ] **Insurance** — product liability for a physical product sold internationally

---

## 10. Where the Source Documents Live

All in the repo under `docs/`:
- `consent-flow.md` — detailed consent mechanism and logging
- `privacy-policy.md` — full privacy policy (customer-facing)
- `terms-of-service.md` — full terms of service (customer-facing)
- `etsy-listing-template.md` — Etsy listing text including disclaimers

---

*This is a living document. Update as we learn more or get legal review.*
