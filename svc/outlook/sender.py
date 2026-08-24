"""
Outlook send adapter, over Microsoft Graph.

Transport choice
----------------
Outlook has three plausible transports, and picking by default is how a
delivery layer rots. This adapter uses **Microsoft Graph**:

- **Microsoft Graph** *(chosen)*. OAuth2, works for any Microsoft 365 tenant,
  needs nothing installed locally — and, decisively, ``sendMail`` accepts a
  whole RFC 822 message as base64 rather than making the caller decompose it
  into Graph's JSON ``message`` schema. That keeps the bytes we send
  identical to the bytes :func:`svc.delivery.save_eml` writes, so inline CID
  images and every header survive exactly as assembled. Re-encoding through
  a JSON schema would put that equality — and the dry run's usefulness —
  at risk.
- **SMTP.** Needs no SDK, but it is not *Outlook*: it is a generic protocol
  that happens to reach Microsoft 365, and Microsoft has been retiring basic
  auth for it. A generic SMTP adapter is a reasonable thing to want, and it
  could reuse :func:`~svc.delivery.retry.retry_with_backoff` unchanged — it
  is simply not this module.
- **``win32com`` / local Outlook automation.** Windows-only and requires a
  running Outlook install. Wrong for a library, ruled out.

*What would change the answer:* if pyHermes ever needed to send from a
desktop Outlook profile rather than a tenant identity, or a caller could not
obtain Graph ``Mail.Send`` permission, the SMTP path would be worth building
alongside this one rather than replacing it.

Where Graph differs from Gmail
------------------------------
Named here rather than quietly diverged from, because the two adapters look
alike and the differences bite:

1. **Standard base64, not URL-safe.** Gmail's ``raw`` field wants the
   URL-safe alphabet; Graph wants ordinary base64 and rejects the message
   with ``ErrorMimeContentInvalidBase64String`` otherwise.
2. **No message id comes back.** ``sendMail`` answers ``202 Accepted`` with
   an empty body, so :func:`send_message` returns ``None`` where the Gmail
   adapter returns an id. There is nothing to return, and inventing one
   would be a lie.
3. **202 means *accepted*, not *delivered*.** Microsoft is explicit that the
   status does not indicate processing has completed. A caller that needs
   proof of delivery must look elsewhere; this function returning cleanly is
   not it.
4. **``Retry-After`` is authoritative.** Microsoft's guidance is that
   throttled requests keep accruing against the quota, so ignoring the hint
   and guessing a backoff actively *prolongs* the throttling. This adapter
   reads the header and lets it override the computed ladder.

Authentication is not this module's job — see :mod:`svc.gmail.sender` for the
same boundary and the reasoning behind it. Bring an authorized session.

Usage::

    import requests                             # the caller's dependency
    from svc.delivery import build_message
    from svc.outlook import GraphApiTransport, send_message

    session = requests.Session()                # caller authenticates
    session.headers["Authorization"] = f"Bearer {token}"

    message = build_message(email, subject=..., sender=..., to=[...])
    send_message(message, transport=GraphApiTransport(session))
"""

from __future__ import annotations

import base64
import time
from collections.abc import Callable
from email.message import EmailMessage
from typing import Any, Protocol
from urllib.parse import quote

from svc.config import Config, get_config
from svc.delivery.exceptions import TransportError
from svc.delivery.message import to_wire_bytes
from svc.delivery.retry import retry_with_backoff

__all__ = [
    "TRANSIENT_STATUSES",
    "GraphApiError",
    "GraphApiTransport",
    "OutlookTransport",
    "is_transient",
    "retry_after_seconds",
    "send_message",
]

#: Graph's default service root. Passed to :class:`GraphApiTransport` so a
#: caller on a sovereign or national cloud can point elsewhere.
GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

#: The status Graph returns for an accepted send: queued, not yet delivered.
ACCEPTED = 202

#: Default request timeout, in seconds, for `GraphApiTransport.send_mime`.
#: `requests.Session` has no settable default of its own, so an unbounded
#: call to a blackholed connection hangs forever -- and because it never
#: raises, it never reaches the retry ladder either. `requests`/`httpx`
#: apply a timeout per socket operation (connect, then each read), not to
#: the whole request, so this bounds a stalled attachment upload without
#: penalising one that is merely large and still making progress.
DEFAULT_TIMEOUT_SECONDS = Config().request_timeout_seconds


class _UseConfigured:
    """Sentinel for "take this from the active config".

    Needed because ``None`` is already a meaningful timeout -- it means *no*
    timeout -- so it cannot double as "unspecified".
    """


_USE_CONFIGURED = _UseConfigured()

#: Worth a second attempt: throttling and the 5xx family. Everything else --
#: 400 malformed MIME, 401 unauthenticated, 403 missing Mail.Send, 404 unknown
#: mailbox -- will not fix itself, and retrying only delays a clear error.
TRANSIENT_STATUSES = frozenset({429, 500, 502, 503, 504})


class GraphApiError(Exception):
    """A non-success response from Graph's ``sendMail`` endpoint.

    Carries the pieces the retry policy needs to make a decision: the status
    and, when Graph supplied one, the ``Retry-After`` hint.
    """

    def __init__(self, status_code: int, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class OutlookTransport(Protocol):
    """The one call this adapter needs from an authorized Graph client."""

    def send_mime(self, encoded_message: str, *, user_id: str = "me") -> None: ...


class GraphApiTransport:
    """
    Adapts an authorized HTTP session to :class:`OutlookTransport`.

    Duck-typed on purpose: this class imports no HTTP library and only calls
    ``session.post(url, data=..., headers=..., timeout=...)``, so a
    ``requests.Session``, an ``httpx.Client``, or any authorized stand-in
    works and pyHermes gains no dependency. The session must already carry
    credentials — typically an ``Authorization: Bearer`` header — because
    this package never handles tokens.

    Args:
        session:  An authorized HTTP client exposing ``post``.
        base_url: Graph service root; override for a sovereign cloud.
        timeout:  Seconds passed through to ``session.post`` as ``timeout=``.
            See :data:`DEFAULT_TIMEOUT_SECONDS` for why a default exists at
            all. Override for a slower network or a deliberately-unbounded
            call (pass ``None`` if the session supports it).
    """

    def __init__(
        self,
        session: Any,
        *,
        base_url: str = GRAPH_BASE_URL,
        timeout: float | None | _UseConfigured = _USE_CONFIGURED,
    ) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")
        self._timeout: float | None = (
            get_config().request_timeout_seconds if isinstance(timeout, _UseConfigured) else timeout
        )

    def _endpoint(self, user_id: str) -> str:
        # "me" is our own sentinel, never caller data, so it needs no
        # encoding. Anything else is a caller-supplied mailbox id or UPN and
        # must be percent-encoded before it goes in a path segment: an Azure
        # AD B2B guest UPN legally contains '#' (e.g.
        # "alice_contoso.com#EXT#@tenant.onmicrosoft.com"), and everything
        # from '#' onward is a URL fragment -- stripped before the request
        # ever reaches the wire, taking "/sendMail" with it. quote(..., safe="")
        # also protects against '/', which would otherwise splice in extra
        # path segments.
        if user_id == "me":
            return f"{self._base_url}/me/sendMail"
        return f"{self._base_url}/users/{quote(user_id, safe='')}/sendMail"

    def send_mime(self, encoded_message: str, *, user_id: str = "me") -> None:
        response = self._session.post(
            self._endpoint(user_id),
            data=encoded_message,
            # text/plain is what selects MIME mode; application/json would
            # make Graph expect its own message schema instead.
            headers={"Content-Type": "text/plain"},
            timeout=self._timeout,
        )
        status = int(getattr(response, "status_code", 0))
        if status != ACCEPTED:
            raise GraphApiError(
                status,
                f"Graph sendMail returned {status}: {_body_of(response)}",
                retry_after=_retry_after_of(response),
            )


def _body_of(response: Any) -> str:
    """A short, safe rendering of a response body for an error message."""
    text = getattr(response, "text", None)
    if not isinstance(text, str):
        return "<no body>"
    return text[: get_config().error_body_excerpt_chars]


def _retry_after_of(response: Any) -> float | None:
    """The ``Retry-After`` value from a response, in seconds, if present."""
    headers = getattr(response, "headers", None)
    if headers is None:
        return None
    try:
        raw = headers.get("Retry-After") or headers.get("retry-after")
    except AttributeError:
        return None
    try:
        return float(raw) if raw is not None else None
    except (TypeError, ValueError):
        # Retry-After may legally be an HTTP-date rather than a delta of
        # seconds. Parsing that is not worth the surface area here -- falling
        # back to the computed ladder is a safe, if slower, answer.
        return None


def _status_of(exc: BaseException) -> int | None:
    """
    The HTTP status behind an exception, if it carries one.

    Read by duck-typing so a caller using an SDK we know nothing about still
    gets correct classification: ``GraphApiError`` and most HTTP libraries
    expose ``status_code``, and some attach the response instead.
    """
    status = getattr(exc, "status_code", None)
    if status is None:
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)
    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


#: Exception class names treated as network-level failures when nothing
#: carries a usable status. Matched by name, not `isinstance`, the same
#: duck-typing `_status_of` already relies on: a client this module has
#: never heard of (and, per the module docstring, never imports) can still
#: be recognised without pyHermes depending on it. `OSError` alone already
#: covers the stdlib builtins and every `requests` exception --
#: `ConnectionError`, `Timeout` and `HTTPError` are all `OSError`
#: subclasses -- so this name list exists only for a client whose network
#: exceptions do *not* derive from `OSError` (e.g. one built on plain
#: `Exception`, the way `httpx`'s hierarchy is commonly described, though
#: this module makes no assumption about a library it does not import).
_NETWORK_ERROR_NAMES = frozenset({"ConnectionError", "Timeout", "TimeoutError"})


def _is_network_failure(exc: BaseException) -> bool:
    """Best-effort recognition of a network-level failure, no status attached."""
    return isinstance(exc, OSError) or type(exc).__name__ in _NETWORK_ERROR_NAMES


def is_transient(exc: BaseException) -> bool:
    """
    Whether a failure is worth retrying.

    Status is checked *first*, and a network-level check is only the
    fallback for an exception that carries no status at all. The order is
    load-bearing, not stylistic: `requests.exceptions.HTTPError` (and
    `ConnectionError`, and `Timeout`) are all `OSError` subclasses, so a
    network-level check run *first* would misclassify a plain HTTP 400 --
    raised via `raise_for_status()` -- as a transient network blip. Checking
    status first means an exception that carries one is classified by it,
    full stop; the network fallback only ever sees exceptions Graph itself
    never produced a status for, i.e. the request never got a response at
    all. The transient status family and a recognised network interruption
    both qualify. Anything else does **not**: a send that failed in an
    unknown way may already have been accepted, and a blind retry risks a
    duplicate.
    """
    status = _status_of(exc)
    if status is not None:
        return status in TRANSIENT_STATUSES
    return _is_network_failure(exc)


def retry_after_seconds(exc: BaseException) -> float | None:
    """
    The server-specified wait attached to a throttling failure, if any.

    Handed to :func:`~svc.delivery.retry.retry_with_backoff` as its
    ``delay_hint``. Honouring it is not politeness: Microsoft keeps counting
    throttled requests against the quota, so a client that guesses shorter
    delays stays throttled longer than one that waits as asked.
    """
    retry_after = getattr(exc, "retry_after", None)
    if retry_after is None:
        response = getattr(exc, "response", None)
        if response is not None:
            retry_after = _retry_after_of(response)
    try:
        return float(retry_after) if retry_after is not None else None
    except (TypeError, ValueError):
        return None


def send_message(
    message: EmailMessage,
    *,
    transport: OutlookTransport,
    user_id: str = "me",
    max_attempts: int = 3,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """
    Send an assembled message through an authorized Graph transport.

    Args:
        message:      An assembled message from
            :func:`svc.delivery.build_message`. Sent as-is — this function
            never rebuilds or mutates MIME structure.
        transport:    An authorized client satisfying :class:`OutlookTransport`.
        user_id:      ``"me"`` for the signed-in user, or a mailbox id /
            userPrincipalName to send as a specific user.
        max_attempts: Total attempts including the first. ``1`` disables
            retrying.
        sleep:        Injected for tests, so the retry ladder runs without
            spending the backoff in real time.

    Returns:
        ``None``. Graph answers ``202 Accepted`` with an empty body, so unlike
        the Gmail adapter there is no message id to hand back — and a clean
        return means *accepted for processing*, not delivered.

    Raises:
        TransportError: On any send failure — authentication refused, Graph
            rejecting the request, the network failing, or throttling that
            outlived its retries. The underlying exception is always chained.
        ValueError: If ``max_attempts`` is below 1 — a bug in this call, not
            a send failure, so it is raised as itself rather than reported
            as a refused message.

    Note:
        The bytes sent are exactly what :func:`svc.delivery.save_eml` would
        write, so a dry run is a faithful preview of the real send.
    """
    # Standard base64, deliberately not URL-safe: Graph rejects the URL-safe
    # alphabet that Gmail's `raw` field requires.
    encoded = base64.b64encode(to_wire_bytes(message)).decode("ascii")

    try:
        retry_with_backoff(
            lambda: transport.send_mime(encoded, user_id=user_id),
            is_transient=is_transient,
            max_attempts=max_attempts,
            delay_hint=retry_after_seconds,
            sleep=sleep,
        )
    except ValueError:
        # retry_with_backoff's own contract: it raises ValueError only for
        # max_attempts < 1, validated before it ever calls the transport.
        # That is a bug in this call, not a message Graph rejected -- let it
        # surface as the ValueError it is instead of being reported as a
        # failed send that was, in fact, never attempted.
        raise
    except Exception as exc:
        status = _status_of(exc)
        detail = f" (HTTP {status})" if status is not None else ""
        raise TransportError(f"Microsoft Graph refused the message{detail}: {exc}") from exc
