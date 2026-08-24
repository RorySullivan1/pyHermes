"""
Gmail send adapter: puts an assembled message on the wire.

What this module owns is Gmail's *wire contract* — the base64url ``raw``
encoding, the ``users.messages.send`` shape, which of Gmail's failures are
worth retrying, and how they map onto this package's exception hierarchy.

What it deliberately does **not** own is authentication. It takes an already
authorized transport and calls it. That boundary buys three things:

1. **pyHermes gains no dependency.** Nothing here imports Google's client
   libraries — the transport is a structural type, so a real
   ``googleapiclient`` service, a stub, or anything else with the right
   method all satisfy it. The project's only runtime dependency stays Jinja2.
2. **No credential ever touches this package.** Token acquisition, storage,
   refresh and revocation stay with the caller, which is where an
   application's secret handling already lives. OAuth token lifecycle is
   where naive adapters rot, and the cheapest way not to rot is not to own it.
3. **Tests need no mailbox.** A fake transport is a class with one method, so
   the whole send path — including the retry ladder — is exercised in CI with
   no account, no network, and no recorded fixtures to drift.

Usage::

    from googleapiclient.discovery import build      # caller's dependency
    from svc.delivery import build_message
    from svc.gmail import GoogleApiTransport, send_message

    service = build("gmail", "v1", credentials=creds)   # caller authenticates
    message = build_message(email, subject=..., sender=..., to=[...])
    message_id = send_message(message, transport=GoogleApiTransport(service))
"""

from __future__ import annotations

import base64
import time
from collections.abc import Callable
from email.message import EmailMessage
from typing import Any, Protocol

from svc.delivery.exceptions import TransportError
from svc.delivery.message import to_wire_bytes
from svc.delivery.retry import retry_with_backoff

__all__ = ["GmailTransport", "GoogleApiTransport", "send_message"]

#: Gmail statuses worth a second attempt: rate limiting and the 5xx family.
#: Everything else — 400 malformed, 401 unauthenticated, 403 forbidden or
#: over-quota-for-good, 404 unknown user — is a condition that will not fix
#: itself, and retrying it only delays a clear error.
TRANSIENT_STATUSES = frozenset({429, 500, 502, 503, 504})


class GmailTransport(Protocol):
    """The one call this adapter needs from an authorized Gmail client."""

    def send_raw(self, raw_message: str, *, user_id: str = "me") -> dict[str, Any]: ...


class GoogleApiTransport:
    """
    Adapts a ``googleapiclient`` Gmail service to :class:`GmailTransport`.

    Duck-typed on purpose: this class imports nothing from Google and merely
    calls the method chain a Gmail service exposes, so it costs the project
    no dependency while sparing every caller from rewriting the same three
    lines. Build the service yourself and hand it over::

        service = build("gmail", "v1", credentials=creds)
        transport = GoogleApiTransport(service)

    Args:
        service: An authorized Gmail API service resource.
    """

    def __init__(self, service: Any) -> None:
        self._service = service

    def send_raw(self, raw_message: str, *, user_id: str = "me") -> dict[str, Any]:
        request = self._service.users().messages().send(userId=user_id, body={"raw": raw_message})
        result: dict[str, Any] = request.execute()
        return result


def _status_of(exc: BaseException) -> int | None:
    """
    The HTTP status behind a client-library exception, if it carries one.

    Read by duck-typing rather than by catching ``HttpError``, so this module
    needs no Google import: ``googleapiclient.errors.HttpError`` exposes
    ``resp.status``, and newer releases also expose ``status_code``. An
    exception with neither returns ``None`` and is treated as permanent.
    """
    response = getattr(exc, "resp", None)
    status = getattr(response, "status", None)
    if status is None:
        status = getattr(exc, "status_code", None)
    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


def is_transient(exc: BaseException) -> bool:
    """
    Whether a failure is worth retrying.

    Network-level interruptions and the transient status family qualify.
    Anything unrecognised does **not**: on a send path an unknown failure may
    have already delivered the message, so the safe default is to surface it
    rather than risk a duplicate.
    """
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    status = _status_of(exc)
    return status in TRANSIENT_STATUSES if status is not None else False


def send_message(
    message: EmailMessage,
    *,
    transport: GmailTransport,
    user_id: str = "me",
    max_attempts: int = 3,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    """
    Send an assembled message through an authorized Gmail transport.

    Args:
        message:      An assembled message from
            :func:`svc.delivery.build_message`. It is sent as-is — this
            function never rebuilds or mutates MIME structure.
        transport:    An authorized client satisfying :class:`GmailTransport`.
        user_id:      Gmail's mailbox selector; ``"me"`` is the authenticated
            user and is almost always what you want.
        max_attempts: Total attempts including the first. ``1`` disables
            retrying.
        sleep:        Injected for tests, so the retry ladder can be exercised
            without spending the backoff in real time.

    Returns:
        The Gmail message id assigned to the sent message.

    Raises:
        TransportError: On any send failure — authentication refused, the API
            rejecting the request, the network failing, or a transient failure
            that outlived its retries. The provider's own exception is always
            chained.

    Note:
        The bytes sent are exactly what :func:`svc.delivery.save_eml` would
        write, so a dry run is a faithful preview of the real send.
    """
    raw = base64.urlsafe_b64encode(to_wire_bytes(message)).decode("ascii")

    try:
        response = retry_with_backoff(
            lambda: transport.send_raw(raw, user_id=user_id),
            is_transient=is_transient,
            max_attempts=max_attempts,
            sleep=sleep,
        )
    except Exception as exc:
        status = _status_of(exc)
        detail = f" (HTTP {status})" if status is not None else ""
        raise TransportError(f"Gmail refused the message{detail}: {exc}") from exc

    message_id = response.get("id") if isinstance(response, dict) else None
    if not message_id:
        # A send that reports no id is not a send we can claim succeeded --
        # better a loud failure than a caller recording a delivery that may
        # not have happened.
        raise TransportError(
            f"Gmail returned no message id for a send that reported success: {response!r}"
        )
    return str(message_id)
