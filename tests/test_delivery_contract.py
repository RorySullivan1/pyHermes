"""
Epic #418: a host catching ``DeliveryError`` sees every send failure, from either adapter.

Each case runs through both ``send_message`` functions against a fake transport: a transport
raising a ``ValueError`` (#420), a negative or NaN ``Retry-After`` (#421), and a certificate
failure that must not be retried (#425).
"""

from __future__ import annotations

import math
import ssl
from collections.abc import Callable

import pytest
import requests

from octavo.builder import EmailBuilder, FullWidth, TextBlock
from octavo.delivery import build_message
from octavo.delivery.exceptions import DeliveryError, TransportError
from octavo.delivery.retry import PERMANENT_ERROR_NAMES, is_permanent_failure, retry_with_backoff
from octavo.gmail import is_transient as gmail_is_transient
from octavo.gmail import send_message as gmail_send
from octavo.outlook import GraphApiError
from octavo.outlook import is_transient as outlook_is_transient
from octavo.outlook import send_message as outlook_send

ENVELOPE = {"subject": "Weekly", "sender": "research@example.com", "to": "reader@example.com"}


class _Failing:
    """Raises ``error`` on every call, through either adapter's one method."""

    def __init__(self, error: BaseException) -> None:
        self.error = error
        self.calls = 0

    def _fail(self, *args: object, **kwargs: object) -> dict:
        self.calls += 1
        raise self.error

    send_raw = _fail
    send_mime = _fail


#: The two adapters' send functions, by name, for parametrising.
ADAPTERS: dict[str, Callable[..., object]] = {"gmail": gmail_send, "outlook": outlook_send}


@pytest.fixture
def message(valid_metadata):
    email = EmailBuilder().metadata(valid_metadata).section(FullWidth(TextBlock("Hi"))).build()
    return build_message(email, **ENVELOPE)


def _send(adapter: str, message, transport: _Failing, waits: list[float], attempts: int = 3):
    ADAPTERS[adapter](message, transport=transport, max_attempts=attempts, sleep=waits.append)


# Named like requests' own classes, which the adapters never import: matched by name.
class SSLError(requests.exceptions.ConnectionError):
    """A stand-in with requests' name and its place under ``OSError``."""


class ConnectionError(OSError):  # noqa: A001 — the name is the point
    """A network blip under a name that is not the builtin's."""


@pytest.mark.parametrize("adapter", ADAPTERS)
class TestEveryFailureIsADeliveryError:
    def test_a_transport_value_error_is_a_transport_error(self, adapter, message):
        # #420: requests' MissingSchema for base_url="graph.microsoft.com" is a ValueError.
        cause = requests.exceptions.MissingSchema("Invalid URL: No scheme supplied")
        transport = _Failing(cause)
        with pytest.raises(TransportError) as raised:
            _send(adapter, message, transport, [])
        assert raised.value.__cause__ is cause
        assert transport.calls == 1

    def test_a_plain_value_error_is_caught_by_delivery_error(self, adapter, message):
        with pytest.raises(DeliveryError):
            _send(adapter, message, _Failing(ValueError("anything")), [])

    def test_max_attempts_below_one_is_a_value_error_before_any_call(self, adapter, message):
        transport = _Failing(RuntimeError("never raised"))
        with pytest.raises(ValueError, match="max_attempts") as raised:
            _send(adapter, message, transport, [], attempts=0)
        assert not isinstance(raised.value, DeliveryError)
        assert transport.calls == 0

    @pytest.mark.parametrize("hint", [-1.0, math.nan])
    def test_an_unreadable_retry_after_runs_every_attempt(self, adapter, message, hint):
        # #421: a proxy-rewritten Retry-After of -1 reached time.sleep and raised.
        waits: list[float] = []
        transport = _Failing(GraphApiError(429, "throttled", retry_after=hint))
        with pytest.raises(TransportError):
            _send(adapter, message, transport, waits)
        assert transport.calls == 3
        assert waits == [1.0, 2.0]

    def test_a_certificate_failure_is_reported_on_the_first_attempt(self, adapter, message):
        # #425: requests' SSLError is an OSError, which read as a network blip.
        cause = SSLError("certificate verify failed")
        transport = _Failing(cause)
        waits: list[float] = []
        with pytest.raises(TransportError) as raised:
            _send(adapter, message, transport, waits)
        assert raised.value.__cause__ is cause
        assert (transport.calls, waits) == (1, [])

    def test_a_network_blip_is_still_retried(self, adapter, message):
        transport = _Failing(ConnectionError("reset"))
        with pytest.raises(TransportError):
            _send(adapter, message, transport, [])
        assert transport.calls == 3


class TestPermanentFailuresAreNamed:
    @pytest.mark.parametrize(
        "error",
        [
            requests.exceptions.SSLError("bad certificate"),
            requests.exceptions.MissingSchema("no scheme"),
            requests.exceptions.InvalidSchema("ftp"),
            requests.exceptions.InvalidURL("bad host"),
            ssl.SSLCertVerificationError("certificate verify failed"),
        ],
    )
    def test_each_is_permanent_and_neither_adapter_retries_it(self, error):
        assert is_permanent_failure(error)
        assert not gmail_is_transient(error)
        assert not outlook_is_transient(error)

    @pytest.mark.parametrize(
        "error",
        [requests.exceptions.ConnectionError("reset"), requests.exceptions.Timeout("slow")],
    )
    def test_a_network_failure_is_not(self, error):
        assert not is_permanent_failure(error)
        assert gmail_is_transient(error) and outlook_is_transient(error)

    def test_a_status_still_wins(self):
        # An exception carrying a status is classified by it, whatever its name.
        throttled = SSLError("odd")
        throttled.status_code = 503  # type: ignore[attr-defined]
        assert outlook_is_transient(throttled)

    def test_the_names_are_the_documented_five(self):
        assert PERMANENT_ERROR_NAMES == {
            "SSLError",
            "SSLCertVerificationError",
            "InvalidURL",
            "MissingSchema",
            "InvalidSchema",
        }


class TestAHintTheLadderCannotUse:
    @pytest.mark.parametrize("hint", [-1.0, math.nan, -0.5])
    def test_it_is_ignored_and_the_ladder_runs(self, hint):
        waits: list[float] = []
        calls: list[int] = []

        def operation() -> str:
            calls.append(1)
            raise TimeoutError

        with pytest.raises(TimeoutError):
            retry_with_backoff(
                operation,
                is_transient=lambda exc: True,
                max_attempts=3,
                initial_delay=1.0,
                backoff_factor=2.0,
                delay_hint=lambda exc: hint,
                sleep=waits.append,
            )
        assert len(calls) == 3
        assert waits == [1.0, 2.0]

    def test_a_hint_of_zero_is_honoured(self):
        waits: list[float] = []
        with pytest.raises(TimeoutError):
            retry_with_backoff(
                lambda: (_ for _ in ()).throw(TimeoutError()),
                is_transient=lambda exc: True,
                max_attempts=2,
                delay_hint=lambda exc: 0.0,
                sleep=waits.append,
            )
        assert waits == [0.0]
