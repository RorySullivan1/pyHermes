"""
The shared retry ladder: policy here, classification with the adapter.

**Policy** — how many attempts and how long to wait — is transport-neutral
and lives here. **Classification** — which failures are worth retrying at all
— is supplied by the caller, because only an adapter knows what its own
provider's rate-limit error looks like.

The default is to give up. Retrying a *permanent* failure is not merely
useless but harmful: it turns a fast, clear error (a revoked credential) into
a slow one, and on a send path a blind retry risks delivering twice. Only a
failure the adapter positively identifies as transient is retried.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from svc.config import get_config

__all__ = ["retry_with_backoff"]

T = TypeVar("T")


def retry_with_backoff(
    operation: Callable[[], T],
    *,
    is_transient: Callable[[BaseException], bool],
    max_attempts: int | None = None,
    initial_delay: float | None = None,
    backoff_factor: float | None = None,
    max_delay: float | None = None,
    delay_hint: Callable[[BaseException], float | None] | None = None,
    max_hint_delay: float | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """
    Call ``operation``, retrying only failures ``is_transient`` accepts.

    Args:
        operation:      The zero-argument call to attempt.
        is_transient:   Predicate deciding whether a raised exception is worth
            retrying. Anything it rejects propagates immediately.
        max_attempts:   Total attempts including the first; ``1`` disables
            retrying. ``None`` — like every numeric argument here — takes the
            value from :func:`svc.config.get_config`.
        initial_delay:  Seconds to wait after the first failure.
        backoff_factor: Multiplier applied to the delay after each failure.
        max_delay:      Ceiling on a *computed* wait.
        delay_hint:     Optional reader extracting a server-specified wait (a
            ``Retry-After``). A hint wins over the computed backoff and is
            clamped by ``max_hint_delay``, not ``max_delay``.
        max_hint_delay: Ceiling on a *hinted* wait, far above ``max_delay`` so a
            legitimate hint is honoured in full but never unbounded.
        sleep:          Injected so tests run the real sequence without the
            wall-clock time; pass a recorder to assert the delays.

    Returns:
        Whatever ``operation`` returns on its first success.

    Raises:
        ValueError: If ``max_attempts`` is below 1 — a programming error, so
            not a ``DeliveryError``.
        BaseException: The last exception from ``operation``, re-raised
            unchanged. Wrapping it is the adapter's job.
    """
    # Every numeric knob defaults to the active configuration rather than a
    # literal, so a deployment can retune the ladder without editing the
    # library -- while an explicit argument still wins, which is what the
    # adapters and their tests rely on.
    config = get_config()
    if max_attempts is None:
        max_attempts = config.retry_max_attempts
    if initial_delay is None:
        initial_delay = config.retry_initial_delay
    if backoff_factor is None:
        backoff_factor = config.retry_backoff_factor
    if max_delay is None:
        max_delay = config.retry_max_delay
    if max_hint_delay is None:
        max_hint_delay = config.retry_max_hint_delay

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
            hinted = delay_hint(exc) if delay_hint is not None else None
            if hinted is not None:
                sleep(min(hinted, max_hint_delay))
            else:
                sleep(min(delay, max_delay))
            # The computed ladder advances either way, so a provider that
            # hints once and then goes quiet resumes from the right rung
            # rather than restarting at initial_delay.
            delay *= backoff_factor

    # Unreachable: the loop either returns or raises on its final attempt.
    raise AssertionError("retry_with_backoff exited its loop without a result")
