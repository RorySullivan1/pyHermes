"""
Tests for the Outlook send adapter (Microsoft Graph).

Like the Gmail suite, everything runs against fakes: no tenant, no network,
no recorded HTTP fixtures. The adapter takes an authorized session rather
than owning authentication, which is what makes that possible.

Several tests pin differences from the Gmail adapter that would otherwise be
easy to "harmonise" away by mistake -- standard vs URL-safe base64, and the
absence of a returned message id.
"""

import base64

import pytest

from svc.builder import EmailBuilder, FullWidth, ImageBlock
from svc.builder.images import EmailImage
from svc.delivery import build_message, save_eml
from svc.delivery.exceptions import DeliveryError, TransportError
from svc.outlook import (
    ACCEPTED,
    GraphApiError,
    GraphApiTransport,
    is_transient,
    retry_after_seconds,
    send_message,
)

ENVELOPE = {
    "subject": "Weekly Market Wrap",
    "sender": "research@example.com",
    "to": "reader@example.com",
}


class _Response:
    """Minimal stand-in for a requests/httpx response."""

    def __init__(self, status_code: int, headers: dict | None = None, text: str = ""):
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text


class _RecordingSession:
    """Accepts every post, remembering url, body and headers."""

    def __init__(self, status_code: int = ACCEPTED, headers: dict | None = None):
        self.status_code = status_code
        self.headers = headers
        self.posts: list[tuple[str, str, dict]] = []

    def post(self, url: str, *, data: str, headers: dict) -> _Response:
        self.posts.append((url, data, headers))
        return _Response(self.status_code, self.headers)


class _RecordingTransport:
    """Accepts every send, remembering the encoded payload and mailbox."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def send_mime(self, encoded_message: str, *, user_id: str = "me") -> None:
        self.calls.append((encoded_message, user_id))


class _FailingTransport:
    """Raises `error` for the first `failures` calls, then accepts."""

    def __init__(self, error: BaseException, failures: int = 99):
        self.error = error
        self.failures = failures
        self.calls = 0

    def send_mime(self, encoded_message: str, *, user_id: str = "me") -> None:
        self.calls += 1
        if self.calls <= self.failures:
            raise self.error


@pytest.fixture
def message(valid_metadata, png_bytes):
    """An assembled message carrying one CID image."""
    email = (
        EmailBuilder()
        .metadata(valid_metadata)
        .section(
            FullWidth(
                content=ImageBlock(EmailImage.attached(png_bytes, alt="Chart", width=300)),
                title="Chart",
            )
        )
        .build()
    )
    return build_message(email, **ENVELOPE)


class TestSending:
    def test_returns_none_because_graph_returns_no_message_id(self, message):
        # Graph answers 202 Accepted with an empty body. Inventing an id
        # would be a lie; the Gmail adapter's return type is not copied here.
        assert send_message(message, transport=_RecordingTransport()) is None

    def test_defaults_to_the_signed_in_mailbox(self, message):
        transport = _RecordingTransport()
        send_message(message, transport=transport)
        assert transport.calls[0][1] == "me"

    def test_user_id_is_passed_through(self, message):
        transport = _RecordingTransport()
        send_message(message, transport=transport, user_id="ops@example.com")
        assert transport.calls[0][1] == "ops@example.com"

    def test_payload_is_exactly_what_save_eml_would_write(self, message, tmp_path):
        transport = _RecordingTransport()
        send_message(message, transport=transport)
        sent = base64.b64decode(transport.calls[0][0])
        assert sent == save_eml(message, tmp_path / "preview.eml").read_bytes()

    def test_payload_uses_standard_base64_not_url_safe(self, message):
        # Graph rejects the URL-safe alphabet Gmail requires, with
        # ErrorMimeContentInvalidBase64String. Decoding with the URL-safe
        # decoder must not be how this payload round-trips.
        transport = _RecordingTransport()
        send_message(message, transport=transport)
        encoded = transport.calls[0][0]
        assert "-" not in encoded and "_" not in encoded
        assert base64.b64decode(encoded)


class TestGraphApiTransport:
    def test_posts_mime_to_the_me_endpoint(self):
        session = _RecordingSession()
        GraphApiTransport(session).send_mime("Zm9v", user_id="me")
        url, data, headers = session.posts[0]
        assert url == "https://graph.microsoft.com/v1.0/me/sendMail"
        assert data == "Zm9v"
        # text/plain is what selects MIME mode over Graph's JSON schema.
        assert headers["Content-Type"] == "text/plain"

    def test_a_named_mailbox_uses_the_users_endpoint(self):
        session = _RecordingSession()
        GraphApiTransport(session).send_mime("Zm9v", user_id="ops@example.com")
        assert session.posts[0][0].endswith("/users/ops@example.com/sendMail")

    def test_base_url_is_overridable_for_sovereign_clouds(self):
        session = _RecordingSession()
        GraphApiTransport(session, base_url="https://graph.example.cn/v1.0/").send_mime("Zm9v")
        assert session.posts[0][0] == "https://graph.example.cn/v1.0/me/sendMail"

    def test_a_non_202_response_raises_with_its_status(self):
        session = _RecordingSession(status_code=400, headers={})
        with pytest.raises(GraphApiError) as caught:
            GraphApiTransport(session).send_mime("Zm9v")
        assert caught.value.status_code == 400

    def test_retry_after_is_captured_from_the_response(self):
        session = _RecordingSession(status_code=429, headers={"Retry-After": "42"})
        with pytest.raises(GraphApiError) as caught:
            GraphApiTransport(session).send_mime("Zm9v")
        assert caught.value.retry_after == 42.0

    def test_imports_nothing_from_an_http_library(self):
        # Parsed, not grepped: the module docstring shows `import requests`
        # as a usage example and a substring check would flag it.
        import ast
        import pathlib

        import svc.outlook.sender as sender

        tree = ast.parse(pathlib.Path(sender.__file__).read_text())
        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
        roots = {name.split(".")[0] for name in imported}
        assert not roots & {"requests", "httpx", "urllib3", "msal", "msgraph", "azure"}


class TestTransientFailures:
    @pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
    def test_transient_status_is_retried_then_accepted(self, message, status):
        transport = _FailingTransport(GraphApiError(status, "busy"), failures=2)
        assert send_message(message, transport=transport, sleep=lambda _: None) is None
        assert transport.calls == 3

    @pytest.mark.parametrize("error", [TimeoutError("slow"), ConnectionError("reset")])
    def test_network_interruptions_are_retried(self, message, error):
        transport = _FailingTransport(error, failures=1)
        send_message(message, transport=transport, sleep=lambda _: None)
        assert transport.calls == 2

    def test_exhausted_retries_surface_as_transport_error(self, message):
        transport = _FailingTransport(GraphApiError(503, "unavailable"))
        with pytest.raises(TransportError, match="503"):
            send_message(message, transport=transport, max_attempts=3, sleep=lambda _: None)
        assert transport.calls == 3


class TestThrottling:
    def test_retry_after_overrides_the_computed_backoff(self, message):
        # Microsoft keeps counting throttled requests against the quota, so
        # guessing a shorter delay prolongs the throttling.
        waits: list[float] = []
        transport = _FailingTransport(GraphApiError(429, "throttled", retry_after=12.0))
        with pytest.raises(TransportError):
            send_message(message, transport=transport, max_attempts=3, sleep=waits.append)
        assert waits == [12.0, 12.0]

    def test_without_a_hint_the_computed_ladder_is_used(self, message):
        waits: list[float] = []
        transport = _FailingTransport(GraphApiError(503, "unavailable"))
        with pytest.raises(TransportError):
            send_message(message, transport=transport, max_attempts=3, sleep=waits.append)
        assert waits == [1.0, 2.0]

    def test_hint_is_read_from_an_attached_response_too(self):
        error = RuntimeError("throttled")
        error.response = _Response(429, {"Retry-After": "7"})  # type: ignore[attr-defined]
        assert retry_after_seconds(error) == 7.0

    def test_an_http_date_retry_after_falls_back_to_the_ladder(self):
        # Retry-After may legally be an HTTP-date; parsing it is out of scope,
        # so it must degrade to the computed backoff rather than crash.
        error = GraphApiError(429, "throttled")
        error.retry_after = "Wed, 21 Oct 2026 07:28:00 GMT"  # type: ignore[assignment]
        assert retry_after_seconds(error) is None


class TestPermanentFailures:
    @pytest.mark.parametrize("status", [400, 401, 403, 404])
    def test_permanent_status_fails_immediately_without_retrying(self, message, status):
        waits: list[float] = []
        transport = _FailingTransport(GraphApiError(status, "refused"))
        with pytest.raises(TransportError, match=str(status)):
            send_message(message, transport=transport, sleep=waits.append)
        assert transport.calls == 1
        assert waits == []

    def test_unrecognised_failure_is_not_retried(self, message):
        transport = _FailingTransport(RuntimeError("something odd"))
        with pytest.raises(TransportError):
            send_message(message, transport=transport, sleep=lambda _: None)
        assert transport.calls == 1

    def test_the_underlying_exception_is_chained(self, message):
        original = GraphApiError(403, "missing Mail.Send")
        transport = _FailingTransport(original)
        with pytest.raises(TransportError) as caught:
            send_message(message, transport=transport, sleep=lambda _: None)
        assert caught.value.__cause__ is original

    def test_transport_error_is_a_delivery_error(self):
        assert issubclass(TransportError, DeliveryError)


class TestClassification:
    @pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
    def test_transient_statuses(self, status):
        assert is_transient(GraphApiError(status, "x"))

    @pytest.mark.parametrize("status", [400, 401, 403, 404, 422])
    def test_permanent_statuses(self, status):
        assert not is_transient(GraphApiError(status, "x"))

    def test_status_is_read_from_an_attached_response(self):
        error = RuntimeError("busy")
        error.response = _Response(503)  # type: ignore[attr-defined]
        assert is_transient(error)

    def test_an_exception_with_no_status_is_permanent(self):
        assert not is_transient(RuntimeError("no status here"))
