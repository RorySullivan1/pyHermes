"""
Tests for the Gmail send adapter.

Every test here runs against a fake transport: no account, no network, no
recorded HTTP fixtures to drift out of date. That is possible because the
adapter takes an already-authorized transport rather than owning
authentication, which is the whole point of that boundary.
"""

import base64
import json

import httplib2
import pytest
import requests

from svc.builder import EmailBuilder, FullWidth, ImageBlock
from svc.builder.images import EmailImage
from svc.delivery import build_message, save_eml
from svc.delivery.exceptions import DeliveryError, TransportError
from svc.gmail import GoogleApiTransport, is_transient, send_message

ENVELOPE = {
    "subject": "Weekly Market Wrap",
    "sender": "research@example.com",
    "to": "reader@example.com",
}


class _FakeResponse:
    """Mimics the ``resp`` attribute googleapiclient's HttpError carries."""

    def __init__(self, status: int):
        self.status = status


class _ApiError(Exception):
    """Stands in for googleapiclient.errors.HttpError, duck-typed the same."""

    def __init__(self, status: int, message: str = "api failure", reason: str | None = None):
        super().__init__(message)
        self.resp = _FakeResponse(status)
        if reason is not None:
            # Gmail's documented error body shape: {"error": {"errors":
            # [{"reason": ..., ...}], "code": ..., "message": ...}}.
            body = {
                "error": {
                    "errors": [{"domain": "usageLimits", "reason": reason, "message": message}],
                    "code": status,
                    "message": message,
                }
            }
            self.content = json.dumps(body).encode()


class _RecordingTransport:
    """Succeeds, remembering what it was handed."""

    def __init__(self, message_id: str = "msg-1"):
        self.message_id = message_id
        self.calls: list[tuple[str, str]] = []

    def send_raw(self, raw_message: str, *, user_id: str = "me") -> dict:
        self.calls.append((raw_message, user_id))
        return {"id": self.message_id, "threadId": "thr-1"}


class _FailingTransport:
    """Raises `error` for the first `failures` calls, then succeeds."""

    def __init__(self, error: BaseException, failures: int = 99):
        self.error = error
        self.failures = failures
        self.calls = 0

    def send_raw(self, raw_message: str, *, user_id: str = "me") -> dict:
        self.calls += 1
        if self.calls <= self.failures:
            raise self.error
        return {"id": "msg-after-retry"}


@pytest.fixture
def message(valid_metadata, png_bytes):
    """An assembled message carrying one CID image."""
    email = (
        EmailBuilder()
        .metadata(valid_metadata)
        .section(
            content := FullWidth(
                content=ImageBlock(EmailImage.attached(png_bytes, alt="Chart", width=300)),
                title="Chart",
            )
        )
        .build()
    )
    assert content is not None
    return build_message(email, **ENVELOPE)


class TestSending:
    def test_returns_the_gmail_message_id(self, message):
        transport = _RecordingTransport(message_id="abc123")
        assert send_message(message, transport=transport) == "abc123"

    def test_defaults_to_the_authenticated_mailbox(self, message):
        transport = _RecordingTransport()
        send_message(message, transport=transport)
        assert transport.calls[0][1] == "me"

    def test_user_id_is_passed_through(self, message):
        transport = _RecordingTransport()
        send_message(message, transport=transport, user_id="ops@example.com")
        assert transport.calls[0][1] == "ops@example.com"

    def test_raw_payload_is_exactly_what_save_eml_would_write(self, message, tmp_path):
        # The dry run is only a faithful preview if the bytes match; this is
        # the assertion that keeps save_eml honest as a preview mechanism.
        transport = _RecordingTransport()
        send_message(message, transport=transport)
        sent = base64.urlsafe_b64decode(transport.calls[0][0])
        on_disk = save_eml(message, tmp_path / "preview.eml").read_bytes()
        assert sent == on_disk

    def test_raw_payload_is_base64url_not_standard_base64(self, message):
        # Gmail requires the URL-safe alphabet; standard base64 '+' and '/'
        # would be rejected or silently corrupt the message.
        transport = _RecordingTransport()
        send_message(message, transport=transport)
        raw = transport.calls[0][0]
        assert "+" not in raw and "/" not in raw
        base64.urlsafe_b64decode(raw)  # round-trips without padding errors


class TestTransientFailures:
    @pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
    def test_transient_status_is_retried_then_succeeds(self, message, status):
        transport = _FailingTransport(_ApiError(status), failures=2)
        assert send_message(message, transport=transport, sleep=lambda _: None) == "msg-after-retry"
        assert transport.calls == 3

    @pytest.mark.parametrize("error", [TimeoutError("slow"), ConnectionError("reset")])
    def test_network_interruptions_are_retried(self, message, error):
        transport = _FailingTransport(error, failures=1)
        assert send_message(message, transport=transport, sleep=lambda _: None) == "msg-after-retry"
        assert transport.calls == 2

    def test_exhausted_retries_surface_as_transport_error(self, message):
        transport = _FailingTransport(_ApiError(503))
        with pytest.raises(TransportError, match="503"):
            send_message(message, transport=transport, max_attempts=3, sleep=lambda _: None)
        assert transport.calls == 3

    def test_backoff_is_actually_applied_between_attempts(self, message):
        waits: list[float] = []
        transport = _FailingTransport(_ApiError(429))
        with pytest.raises(TransportError):
            send_message(message, transport=transport, max_attempts=3, sleep=waits.append)
        assert waits == [1.0, 2.0]


class TestPermanentFailures:
    @pytest.mark.parametrize("status", [400, 401, 403, 404])
    def test_permanent_status_fails_immediately_without_retrying(self, message, status):
        waits: list[float] = []
        transport = _FailingTransport(_ApiError(status))
        with pytest.raises(TransportError, match=str(status)):
            send_message(message, transport=transport, sleep=waits.append)
        assert transport.calls == 1, "a permanent failure must not be retried"
        assert waits == []

    def test_unrecognised_failure_is_not_retried(self, message):
        # An unknown failure may already have delivered the message; retrying
        # blind risks a duplicate, so the safe default is to surface it.
        transport = _FailingTransport(RuntimeError("something odd"))
        with pytest.raises(TransportError):
            send_message(message, transport=transport, sleep=lambda _: None)
        assert transport.calls == 1

    def test_the_providers_exception_is_chained(self, message):
        original = _ApiError(403, "insufficient scope")
        transport = _FailingTransport(original)
        with pytest.raises(TransportError) as caught:
            send_message(message, transport=transport, sleep=lambda _: None)
        assert caught.value.__cause__ is original

    def test_transport_error_is_a_delivery_error(self):
        assert issubclass(TransportError, DeliveryError)

    def test_a_response_without_an_id_is_not_treated_as_success(self, message):
        class _Silent:
            def send_raw(self, raw_message: str, *, user_id: str = "me") -> dict:
                return {"threadId": "thr-1"}

        with pytest.raises(TransportError, match="no message id"):
            send_message(message, transport=_Silent())


class TestNetworkFailureClassification:
    """
    F1: real network exceptions, not just the builtins.

    A prior version of ``is_transient`` checked only the builtin
    ``TimeoutError``/``ConnectionError``, which hid this bug because none of
    the transports this module documents actually raise those builtins.
    """

    def test_requests_connection_error_is_retried(self, message):
        # requests.exceptions.ConnectionError is an OSError subclass, but
        # NOT an instance of the builtin ConnectionError -- the gap F1 found.
        assert not isinstance(requests.exceptions.ConnectionError(), ConnectionError)
        transport = _FailingTransport(requests.exceptions.ConnectionError("reset"), failures=1)
        assert send_message(message, transport=transport, sleep=lambda _: None) == "msg-after-retry"
        assert transport.calls == 2

    def test_requests_timeout_is_retried(self, message):
        assert not isinstance(requests.exceptions.Timeout(), TimeoutError)
        transport = _FailingTransport(requests.exceptions.Timeout("slow"), failures=1)
        assert send_message(message, transport=transport, sleep=lambda _: None) == "msg-after-retry"
        assert transport.calls == 2

    def test_requests_http_error_with_a_permanent_status_is_not_retried(self, message):
        # The trap a naive `isinstance(exc, OSError)` fix falls into:
        # HTTPError is an OSError too, so without status-first classification
        # a 400 would be misread as a network blip and retried.
        response = requests.Response()
        response.status_code = 400
        error = requests.exceptions.HTTPError("bad request", response=response)
        assert isinstance(error, OSError)
        transport = _FailingTransport(error)
        with pytest.raises(TransportError, match="400"):
            send_message(message, transport=transport, sleep=lambda _: None)
        assert transport.calls == 1

    def test_requests_http_error_with_a_transient_status_is_retried(self, message):
        response = requests.Response()
        response.status_code = 503
        error = requests.exceptions.HTTPError("unavailable", response=response)
        transport = _FailingTransport(error, failures=1)
        assert send_message(message, transport=transport, sleep=lambda _: None) == "msg-after-retry"
        assert transport.calls == 2

    def test_httplib2_server_not_found_is_retried(self, message):
        # httplib2 -- what googleapiclient itself is built on -- raises its
        # own hierarchy rooted at HttpLib2Error rather than OSError, so this
        # would be missed by an isinstance(exc, OSError) check alone too.
        error = httplib2.ServerNotFoundError("Unable to find the server")
        assert not isinstance(error, OSError)
        transport = _FailingTransport(error, failures=1)
        assert send_message(message, transport=transport, sleep=lambda _: None) == "msg-after-retry"
        assert transport.calls == 2

    def test_is_transient_agrees_directly(self):
        assert is_transient(requests.exceptions.ConnectionError())
        assert is_transient(requests.exceptions.Timeout())
        assert is_transient(httplib2.ServerNotFoundError())
        response = requests.Response()
        response.status_code = 400
        assert not is_transient(requests.exceptions.HTTPError(response=response))


class TestMaxAttemptsIsACallerBug:
    """F2: a bad max_attempts is a programming error, not a send failure."""

    def test_zero_max_attempts_raises_value_error_not_transport_error(self, message):
        transport = _RecordingTransport()
        with pytest.raises(ValueError, match="max_attempts"):
            send_message(message, transport=transport, max_attempts=0)

    def test_zero_max_attempts_never_calls_the_transport(self, message):
        # The bug: today this reports "Gmail refused the message" for a
        # message that was never handed to the transport at all.
        transport = _RecordingTransport()
        with pytest.raises(ValueError):
            send_message(message, transport=transport, max_attempts=0)
        assert transport.calls == []

    def test_negative_max_attempts_also_raises_value_error(self, message):
        transport = _RecordingTransport()
        with pytest.raises(ValueError):
            send_message(message, transport=transport, max_attempts=-1)


class TestForbiddenRateLimiting:
    """
    F3: Gmail overloads 403 for both rate limiting and real authorization
    failures. Confirmed from Gmail's own error-handling guide
    (https://developers.google.com/gmail/api/guides/handle-errors): the
    documented JSON bodies for ``reason: rateLimitExceeded`` and
    ``reason: userRateLimitExceeded`` both carry ``"code": 403`` and the
    guide's fix for both is "Use exponential backoff to retry the request" --
    contrasted with sibling 403 reasons (``dailyLimitExceeded``, told to
    raise its quota; ``domainPolicy``, a real authorization failure) that
    are not told to retry. So 403 is retried only when the reason names
    rate limiting, keyed on the payload rather than the bare status.
    """

    @pytest.mark.parametrize("reason", ["rateLimitExceeded", "userRateLimitExceeded"])
    def test_403_with_a_rate_limit_reason_is_retried(self, message, reason):
        transport = _FailingTransport(_ApiError(403, reason=reason), failures=1)
        assert send_message(message, transport=transport, sleep=lambda _: None) == "msg-after-retry"
        assert transport.calls == 2

    @pytest.mark.parametrize("reason", ["dailyLimitExceeded", "domainPolicy", "forbidden"])
    def test_403_with_a_non_rate_limit_reason_is_not_retried(self, message, reason):
        transport = _FailingTransport(_ApiError(403, reason=reason))
        with pytest.raises(TransportError, match="403"):
            send_message(message, transport=transport, sleep=lambda _: None)
        assert transport.calls == 1

    def test_403_with_no_body_at_all_is_not_retried(self, message):
        # No content to read a reason from -- stay conservative rather than
        # guess, per the finding: an unproven claim must not make bare 403
        # transient.
        transport = _FailingTransport(_ApiError(403))
        with pytest.raises(TransportError, match="403"):
            send_message(message, transport=transport, sleep=lambda _: None)
        assert transport.calls == 1

    def test_is_transient_reads_the_reason_directly(self):
        assert is_transient(_ApiError(403, reason="rateLimitExceeded"))
        assert is_transient(_ApiError(403, reason="userRateLimitExceeded"))
        assert not is_transient(_ApiError(403, reason="dailyLimitExceeded"))
        assert not is_transient(_ApiError(403))


class TestClassification:
    @pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
    def test_transient_statuses(self, status):
        assert is_transient(_ApiError(status))

    @pytest.mark.parametrize("status", [400, 401, 404, 422])
    def test_permanent_statuses(self, status):
        assert not is_transient(_ApiError(status))

    def test_bare_403_is_permanent(self):
        # No body to read a reason from -- stays permanent rather than
        # guessing. See TestForbiddenRateLimiting for the reason-based cases.
        assert not is_transient(_ApiError(403))

    def test_status_code_attribute_is_also_read(self):
        # Newer googleapiclient releases expose status_code instead of resp.
        error = RuntimeError("rate limited")
        error.status_code = 429  # type: ignore[attr-defined]
        assert is_transient(error)

    def test_an_exception_with_no_status_is_permanent(self):
        assert not is_transient(RuntimeError("no status here"))


class TestGoogleApiTransport:
    def test_calls_the_gmail_service_chain_and_returns_its_result(self):
        recorded = {}

        class _Request:
            def execute(self):
                return {"id": "msg-9"}

        class _Messages:
            def send(self, *, userId, body):  # noqa: N803 - Google's own spelling
                recorded["userId"] = userId
                recorded["body"] = body
                return _Request()

        class _Users:
            def messages(self):
                return _Messages()

        class _Service:
            def users(self):
                return _Users()

        transport = GoogleApiTransport(_Service())
        assert transport.send_raw("cmF3", user_id="me") == {"id": "msg-9"}
        assert recorded == {"userId": "me", "body": {"raw": "cmF3"}}

    def test_imports_nothing_from_google(self):
        # The adapter must stay dependency-free: it duck-types the service.
        # Parsed, not grepped -- the module docstring shows a googleapiclient
        # import as a *usage example*, and a substring check would flag it.
        import ast
        import pathlib

        import svc.gmail.sender as sender

        tree = ast.parse(pathlib.Path(sender.__file__).read_text())
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        assert not [name for name in imported if name.split(".")[0] == "googleapiclient"]
        assert not [name for name in imported if name.split(".")[0] == "google"]
