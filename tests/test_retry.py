"""
Tests for the shared retry policy.

The policy is transport-neutral; every adapter supplies its own notion of
what counts as transient. These tests pin the parts that must not vary:
the backoff sequence, the attempt ceiling, and the refusal to retry
anything the caller has not positively classified as worth retrying.
"""

import pytest

from pyhermes.delivery.retry import retry_with_backoff

TRANSIENT = TimeoutError
PERMANENT = PermissionError


def _always_transient(exc: BaseException) -> bool:
    return isinstance(exc, TRANSIENT)


class _Flaky:
    """Fails `failures` times, then returns a sentinel."""

    def __init__(self, failures: int, error: BaseException | None = None):
        self.failures = failures
        self.error = error or TRANSIENT("temporary")
        self.calls = 0

    def __call__(self) -> str:
        self.calls += 1
        if self.calls <= self.failures:
            raise self.error
        return "sent"


class TestSuccessPath:
    def test_returns_immediately_without_sleeping(self):
        waits: list[float] = []
        assert (
            retry_with_backoff(_Flaky(0), is_transient=_always_transient, sleep=waits.append)
            == "sent"
        )
        assert waits == []

    def test_retries_a_transient_failure_then_succeeds(self):
        waits: list[float] = []
        operation = _Flaky(2)
        assert (
            retry_with_backoff(operation, is_transient=_always_transient, sleep=waits.append)
            == "sent"
        )
        assert operation.calls == 3


class TestBackoff:
    def test_delay_grows_by_the_backoff_factor(self):
        waits: list[float] = []
        with pytest.raises(TRANSIENT):
            retry_with_backoff(
                _Flaky(99),
                is_transient=_always_transient,
                max_attempts=4,
                initial_delay=1.0,
                backoff_factor=2.0,
                sleep=waits.append,
            )
        # Three waits for four attempts -- nothing is slept after the last.
        assert waits == [1.0, 2.0, 4.0]

    def test_delay_is_capped_by_max_delay(self):
        waits: list[float] = []
        with pytest.raises(TRANSIENT):
            retry_with_backoff(
                _Flaky(99),
                is_transient=_always_transient,
                max_attempts=5,
                initial_delay=10.0,
                backoff_factor=10.0,
                max_delay=25.0,
                sleep=waits.append,
            )
        assert waits == [10.0, 25.0, 25.0, 25.0]
        assert max(waits) <= 25.0


class TestDelayHint:
    def test_a_hint_above_max_delay_is_honoured_in_full(self):
        # This is the case test_delay_is_capped_by_max_delay cannot catch: a
        # server-supplied hint (Microsoft Graph commonly asks for 60s or
        # more) must not be clamped by the client's own backoff ceiling.
        waits: list[float] = []
        with pytest.raises(TRANSIENT):
            retry_with_backoff(
                _Flaky(99),
                is_transient=_always_transient,
                max_attempts=3,
                max_delay=30.0,
                delay_hint=lambda exc: 60.0,
                sleep=waits.append,
            )
        assert waits == [60.0, 60.0]

    def test_a_hint_above_max_hint_delay_is_still_bounded(self):
        # A hint is data the caller does not control -- a malformed or
        # hostile value (a day, say) must not hang the caller indefinitely.
        waits: list[float] = []
        with pytest.raises(TRANSIENT):
            retry_with_backoff(
                _Flaky(99),
                is_transient=_always_transient,
                max_attempts=3,
                delay_hint=lambda exc: 86400.0,
                max_hint_delay=300.0,
                sleep=waits.append,
            )
        assert waits == [300.0, 300.0]

    def test_the_computed_ladder_still_advances_while_a_hint_is_used(self):
        # A provider that hints once and then goes quiet should resume from
        # the right rung, not restart at initial_delay.
        waits: list[float] = []
        hints = iter([60.0, None])
        with pytest.raises(TRANSIENT):
            retry_with_backoff(
                _Flaky(99),
                is_transient=_always_transient,
                max_attempts=3,
                initial_delay=1.0,
                backoff_factor=2.0,
                delay_hint=lambda exc: next(hints),
                sleep=waits.append,
            )
        assert waits == [60.0, 2.0]


class TestGivingUp:
    def test_exhausting_attempts_reraises_the_original_error(self):
        operation = _Flaky(99)
        with pytest.raises(TRANSIENT, match="temporary"):
            retry_with_backoff(
                operation, is_transient=_always_transient, max_attempts=3, sleep=lambda _: None
            )
        assert operation.calls == 3

    def test_a_permanent_failure_is_not_retried(self):
        # Retrying a revoked credential only turns a fast error into a slow
        # one -- and on a send path risks delivering twice.
        waits: list[float] = []
        operation = _Flaky(99, error=PERMANENT("revoked"))
        with pytest.raises(PERMANENT):
            retry_with_backoff(operation, is_transient=_always_transient, sleep=waits.append)
        assert operation.calls == 1
        assert waits == []

    def test_max_attempts_of_one_disables_retrying(self):
        operation = _Flaky(99)
        with pytest.raises(TRANSIENT):
            retry_with_backoff(
                operation, is_transient=_always_transient, max_attempts=1, sleep=lambda _: None
            )
        assert operation.calls == 1

    @pytest.mark.parametrize("attempts", [0, -1])
    def test_non_positive_max_attempts_is_a_programming_error(self, attempts):
        with pytest.raises(ValueError, match="max_attempts"):
            retry_with_backoff(_Flaky(0), is_transient=_always_transient, max_attempts=attempts)
