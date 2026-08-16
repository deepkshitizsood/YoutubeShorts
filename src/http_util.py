"""Retry helper for provider API calls.

Every external call in this pipeline is a single point of failure for the whole
daily run - the Aug 15 2026 run was lost entirely to one transient 503 from the
image API, mid-way through a 6-9 call loop. Anything hitting a provider should
go through retry_call().
"""
from __future__ import annotations

import random
import sys
import time
from typing import Callable, TypeVar

import requests

T = TypeVar("T")

# Status codes worth retrying: rate limits and transient server-side failures.
RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}

DEFAULT_ATTEMPTS = 4
DEFAULT_BASE_DELAY = 2.0


class RetryableError(RuntimeError):
    """Raised by callers to explicitly mark a failure as worth retrying."""


def retry_call(
    fn: Callable[[], T],
    *,
    description: str,
    attempts: int = DEFAULT_ATTEMPTS,
    base_delay: float = DEFAULT_BASE_DELAY,
) -> T:
    """Calls fn(), retrying transient failures with exponential backoff + jitter.

    Retries on RetryableError, requests timeouts/connection errors, and
    requests.HTTPError whose response status is in RETRYABLE_STATUS. Anything
    else (a 400 from a malformed payload, a safety refusal) is a real bug or a
    permanent rejection, so it propagates immediately rather than burning
    minutes retrying something that cannot succeed.
    """
    last_exc: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except (RetryableError, requests.Timeout, requests.ConnectionError) as e:
            last_exc = e
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status not in RETRYABLE_STATUS:
                raise
            last_exc = e

        if attempt == attempts:
            break

        delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
        print(
            f"[retry] {description} failed (attempt {attempt}/{attempts}): {last_exc}. "
            f"Retrying in {delay:.1f}s.",
            file=sys.stderr,
        )
        time.sleep(delay)

    raise RuntimeError(f"{description} failed after {attempts} attempts: {last_exc}") from last_exc


def raise_for_retryable_status(resp: requests.Response, description: str) -> None:
    """Turns a non-OK response into the right exception type for retry_call().

    Retryable statuses become requests.HTTPError (which retry_call retries);
    everything else becomes a RuntimeError carrying the response body, since
    the body is usually the only thing that explains a 4xx.
    """
    if resp.ok:
        return
    if resp.status_code in RETRYABLE_STATUS:
        raise requests.HTTPError(
            f"{description} returned {resp.status_code}: {resp.text[:500]}", response=resp
        )
    raise RuntimeError(f"{description} failed ({resp.status_code}): {resp.text}")
