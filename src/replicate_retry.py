"""Retry wrapper for Replicate API calls.

Handles 429 (rate limit) and transient connection errors with exponential backoff.
Drop-in replacement for replicate.run().
"""

import time

import replicate
from replicate.exceptions import ReplicateError

MAX_RETRIES = 3
BASE_DELAY = 5  # seconds

# Connection errors worth retrying
_TRANSIENT_ERRORS = (ConnectionError, OSError, TimeoutError)


def run_with_retry(model_id: str, input: dict, **kwargs) -> any:
    """Call replicate.run() with automatic retry on transient errors.

    Retries on:
    - 429 rate limit errors
    - Connection reset / broken pipe / timeout errors

    Args:
        model_id: Replicate model ID.
        input: Input dict for the model.
        **kwargs: Extra kwargs passed to replicate.run().

    Returns:
        The Replicate output (same as replicate.run()).

    Raises:
        ReplicateError: If all retries exhausted or non-retryable error.
    """
    for attempt in range(MAX_RETRIES + 1):
        try:
            return replicate.run(model_id, input=input, **kwargs)
        except ReplicateError as e:
            if e.status in (429, 502, 503) and attempt < MAX_RETRIES:
                delay = BASE_DELAY * (2 ** attempt)
                print(f"  Replicate error ({e.status}), retrying in {delay}s... (attempt {attempt + 1}/{MAX_RETRIES})")
                time.sleep(delay)
            else:
                raise
        except _TRANSIENT_ERRORS as e:
            if attempt < MAX_RETRIES:
                delay = BASE_DELAY * (2 ** attempt)
                print(f"  Connection error ({e}), retrying in {delay}s... (attempt {attempt + 1}/{MAX_RETRIES})")
                time.sleep(delay)
            else:
                raise
