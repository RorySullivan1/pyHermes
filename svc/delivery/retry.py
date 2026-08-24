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
    delay_hint: Callable[[BaseException], float | None] | None = None,
    max_hint_delay: float = 300.0,
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
        max_delay:      Ceiling on a *computed* wait — the client's own
            backoff guess — so a long retry chain cannot stall a caller
            indefinitely.
        delay_hint:     Optional reader that extracts a server-specified wait
            from the exception — a ``Retry-After`` header, typically. When it
            returns a value, that wins over the computed backoff, because a
            server saying *how long* to wait knows better than a client
            guessing. Some providers count ignored — or under-honoured —
            hints against a quota, so guessing short is not merely impolite,
            it prolongs the throttling. A hint is clamped by
            ``max_hint_delay``, not ``max_delay``: real providers routinely
            ask for more than a client's own backoff ceiling (Microsoft Graph
            commonly hints 60 seconds or more), so honouring it needs the
            larger bound.
        max_hint_delay: Ceiling on a *hinted* wait specifically. Deliberately
            far above ``max_delay`` so a legitimate hint is always honoured
            in full, but still finite: the hint comes from response data the
            caller does not control, and an unbounded wait on a malformed or
            hostile value would hang the caller indefinitely.
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
