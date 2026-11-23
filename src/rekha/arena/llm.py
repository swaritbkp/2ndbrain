"""One chat-completion call with an RPM limiter and exponential backoff (429 / 5xx / network / malformed responses)."""
from __future__ import annotations

import os
import random
import time
from collections import deque

TRANSIENT_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 520, 522, 524, 529}


class TransientLLMError(RuntimeError):
    """A 200 response that is unusable (no choices, provider error body). Retried like a 5xx."""


class RateLimiter:
    def __init__(self, rpm: int):
        self.rpm = max(int(rpm), 1)
        self.stamps: deque[float] = deque()

    def wait(self) -> None:
        now = time.monotonic()
        while self.stamps and now - self.stamps[0] > 60:
            self.stamps.popleft()
        if len(self.stamps) >= self.rpm:
            time.sleep(max(60 - (now - self.stamps[0]), 0))
        self.stamps.append(time.monotonic())


def _retry_after(e: Exception) -> float | None:
    resp = getattr(e, "response", None)
    headers = getattr(resp, "headers", None) or {}
    try:
        v = headers.get("retry-after") or headers.get("Retry-After")
        return float(v) if v else None
    except (TypeError, ValueError):
        return None


def is_transient(e: Exception) -> bool:
    if isinstance(e, TransientLLMError):
        return True
    status = getattr(e, "status_code", None)
    if status in TRANSIENT_STATUS:
        return True
    name = type(e).__name__
    return name in {"APIConnectionError", "APITimeoutError", "RateLimitError", "InternalServerError", "JSONDecodeError"}


def chat(client, limiter: RateLimiter | None, max_retries: int | None = None, **kwargs):
    """Returns the completion. Raises the last error once retries are exhausted or the error is permanent."""
    retries = int(os.environ.get("ARENA_MAX_RETRIES", "6")) if max_retries is None else max_retries
    base = float(os.environ.get("ARENA_BACKOFF_BASE", "2"))
    for attempt in range(retries + 1):
        if limiter:
            limiter.wait()
        try:
            r = client.chat.completions.create(**kwargs)
            if not getattr(r, "choices", None):
                raise TransientLLMError(f"no choices in response: {str(getattr(r, 'error', ''))[:200]}")
            return r
        except Exception as e:  # noqa: BLE001 (classified below)
            if attempt >= retries or not is_transient(e):
                raise
            delay = _retry_after(e) or base * (2 ** attempt) + random.uniform(0, base)
            time.sleep(min(delay, 120))
    raise RuntimeError("unreachable")
