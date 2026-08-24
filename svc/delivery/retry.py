"""
Bounded retry with exponential backoff, shared by every send adapter.

The split here is deliberate and is what lets the second adapter reuse the
first one's work:

- The **policy** — how many attempts, how long to wait between them — is
  transport-neutral and lives here.
- The **classification** — which failures are worth retrying at all — is
  transport-specific and is supplied by the caller, because only the adapter
  knows what its own provider's rate-limit error looks like.

Retrying a *permanent* failure is not merely useless, it is harmful: it turns
a fast, clear error (a revoked credential) into a slow one, and on a send
path a blind retry risks delivering the same message twice. So the default is
to give up, and only a failure the adapter positively identifies as transient
is retried.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

__all__ = ["retry_with_backoff"]

T = TypeVar("T")


def retry_with_backoff(
    operation: Callable[[], T],
    *,
    is_transient: Callable[[BaseException], bool],
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 30.0,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """
    Call ``operation``, retrying only failures ``is_transient`` accepts.

    Args:
        operation:      The zero-argument call to attempt.
        is_transient:   Predicate deciding whether a raised exception is
            worth retrying. Anything it rejects propagates immediately.
        max_attempts:   Total attempts including the first. ``1`` disables
            retrying without needing a separate code path.
        initial_delay:  Seconds to wait after the first failure.
        backoff_factor: Multiplier applied to the delay after each failure.
        max_delay:      Ceiling on any single wait, so a long retry chain
            cannot stall a caller indefinitely.
        sleep:          Injected so tests can run the real backoff sequence
            without spending the wall-clock time it describes. Pass a
            recorder to assert the delays.

    Returns:
        Whatever ``operation`` returns on its first success.

    Raises:
        ValueError: If ``max_attempts`` is below 1 — a programming error in
            the call, not rejected data, so it is not a ``DeliveryError``.
        BaseException: The last exception raised by ``operation``, re-raised
            unchanged once attempts are exhausted or the failure is not
            transient. Wrapping it is the adapter's job, which has the
            context to say what it means.
    """
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be at least 1, got {max_attempts}")

    delay = initial_delay
    for attempt in range(1, max_attempts + 1):
        try:
            return operation()
        except BaseException as exc:
            # The last attempt gets no special classification: whether it was
            # transient or not, there is nothing left to try.
            if attempt == max_attempts or not is_transient(exc):
                raise
            sleep(min(delay, max_delay))
            delay *= backoff_factor

    # Unreachable: the loop either returns or raises on its final attempt.
    raise AssertionError("retry_with_backoff exited its loop without a result")
