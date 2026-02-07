"""
Consent event logging for photo processing.

Logs consent events to consent_log.jsonl for legal compliance.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

CONSENT_LOG = Path("consent_log.jsonl")


def log_consent(
    order_id: str,
    photo_path: str,
    consent_given: bool = True,
    consent_method: str = "etsy_message",
    customer_name: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """Log a consent event for photo processing.

    Args:
        order_id: Order identifier (e.g., ETSY-12345).
        photo_path: Path to the customer's photo.
        consent_given: Whether consent was given.
        consent_method: How consent was obtained.
        customer_name: Optional customer name.
        notes: Optional notes about the consent.

    Returns:
        The logged consent record.
    """
    record = {
        "timestamp": datetime.now().isoformat(),
        "order_id": order_id,
        "photo_path": photo_path,
        "consent_given": consent_given,
        "consent_method": consent_method,
        "customer_name": customer_name,
        "notes": notes,
        "data_retention_days": 30,
    }

    CONSENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with CONSENT_LOG.open("a") as f:
        f.write(json.dumps(record) + "\n")

    return record


def check_consent(order_id: str) -> Optional[dict]:
    """Check if consent exists for an order.

    Returns:
        Most recent consent record for the order, or None.
    """
    if not CONSENT_LOG.exists():
        return None

    latest = None
    with CONSENT_LOG.open() as f:
        for line in f:
            if line.strip():
                record = json.loads(line)
                if record.get("order_id") == order_id:
                    latest = record

    return latest
