# Consent Flow Documentation

## Overview

Every order requires documented consent before photos are processed through AI models.

## Consent Mechanism

### Current Flow (Etsy-based)

1. **Listing disclaimer:** Etsy listing includes a clear note that submitted photos will be processed using AI transformation tools.
2. **Message confirmation:** When a customer sends their photo via Etsy message, their message serves as implicit consent.
3. **Explicit confirmation:** Before processing, we send a message:
   > "Thanks for your photo! Just to confirm: by proceeding, you agree that this photo will be processed through AI art tools to create your custom puzzle. The original photo will be deleted within 30 days of order completion. Shall I proceed?"
4. **Customer responds** with confirmation.
5. **Consent logged** in `consent_log.jsonl` with timestamp, order ID, and method.

### Future Flow (Web Interface)

1. Upload form includes a **consent checkbox**: "I confirm I have the right to submit this photo and consent to AI processing for puzzle creation."
2. Checkbox must be checked before upload is accepted.
3. Consent event logged automatically on form submission.

## What's Logged

Each consent event records:
- `timestamp` - When consent was given
- `order_id` - Associated order
- `photo_path` - Which photo was consented for
- `consent_given` - Boolean
- `consent_method` - How consent was obtained ("etsy_message", "web_checkbox")
- `customer_name` - Optional
- `notes` - Any additional context
- `data_retention_days` - How long data will be retained (30)

## Consent for Minors

If the photo depicts a minor (under 18):
- The ordering adult must be the parent/legal guardian or have their explicit consent.
- This is confirmed as part of the standard consent message.

## Revoking Consent

Customers can revoke consent at any time by messaging us. Upon revocation:
1. All photos and AI intermediates are deleted immediately.
2. If the puzzle has not been sent to print, the order is cancelled and refunded.
3. If already printed, the digital files are still deleted.

## Data Retention Schedule

- **0-30 days:** All order files retained for potential regeneration/support.
- **30 days:** Photos and AI intermediates auto-flagged for deletion.
- **Consent logs:** Retained for 3 years per legal best practice.
