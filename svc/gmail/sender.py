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
import json
import time
from collections.abc import Callable
from email.message import EmailMessage
from typing import Any, Protocol

from svc.delivery.exceptions import TransportError
from svc.delivery.message import to_wire_bytes
from svc.delivery.retry import retry_with_backoff

__all__ = ["GmailTransport", "GoogleApiTransport", "send_message"]

#: Gmail statuses worth a second attempt: rate limiting and the 5xx family.
#: Everything else — 400 malformed, 401 unauthenticated, 404 unknown user —
#: is a condition that will not fix itself, and retrying it only delays a
#: clear error. 403 is deliberately absent from this set: Gmail overloads it
#: for both rate limiting and outright authorization failures, so it is
#: classified separately, by ``reason``, in :func:`is_transient`.
TRANSIENT_STATUSES = frozenset({429, 500, 502, 503, 504})

#: The Gmail-documented ``reason`` values for a 403 that mean "you're
#: sending too fast", not "you may never do this". Per Gmail's own
#: error-handling guide[1], both are ``usageLimits`` errors and both are
#: told to retry with exponential backoff — unlike sibling 403 reasons such
#: as ``dailyLimitExceeded`` (told to raise its quota, not retry) or a
#: genuine ``domainPolicy``/authorization failure. This is why a bare 403
#: is *not* added to ``TRANSIENT_STATUSES``: only these two reasons are.
#: [1] https://developers.google.com/gmail/api/guides/handle-errors
#:     (confirmed against the live page while triaging this finding —
#:     the documented JSON samples for both reasons carry ``"code": 403``
#:     and the guide's fix is literally "Use exponential backoff to retry
#:     the request").
RATE_LIMIT_REASONS = frozenset({"rateLimitExceeded", "userRateLimitExceeded"})


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

    Read by duck-typing rather than by catching a library's own exception
    class, so this module needs no provider import. Three shapes are
    checked, in order: ``exc.resp.status`` (``googleapiclient.errors.
    HttpError``, the transport Gmail's own docs use), ``exc.status_code``
    (newer ``googleapiclient`` releases), and ``exc.response.status_code``
    (``requests``' ``HTTPError``, populated by ``raise_for_status()``).
    Checking the last of these matters beyond generality: without it, an
    ``HTTPError`` — which subclasses ``OSError`` — would carry no
    extractable status, fall through to the network-level check in
    :func:`is_transient`, and a plain 400 would be misread as a network
    blip and retried. An exception matching none of the three returns
    ``None`` and falls to that same network-level check on its own merits.
    """
    response = getattr(exc, "resp", None)
    status = getattr(response, "status", None)
    if status is None:
        status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(getattr(exc, "response", None), "status_code", None)
    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


def _reason_of(exc: BaseException) -> str | None:
    """
    The Gmail API's machine-readable ``reason`` for a 403, if present.

    ``googleapiclient.errors.HttpError`` carries the raw JSON response body
    as ``.content`` (bytes); Gmail's documented error shape nests the reason
    at ``error.errors[0].reason``. Read by duck-typing and best-effort
    parsing, matching :func:`_status_of`'s approach: any failure to find or
    parse it returns ``None`` rather than raising, since a malformed or
    absent body is not itself the failure being classified.
    """
    content = getattr(exc, "content", None)
    if content is None:
        return None
    try:
        errors = json.loads(content)["error"]["errors"]
        reason = errors[0]["reason"]
    except (TypeError, ValueError, LookupError):
        return None
    return str(reason) if reason is not None else None


#: Fully-qualified names of network-level failures that are neither the
#: builtin ``TimeoutError``/``ConnectionError`` nor an ``OSError`` subclass,
#: so an isinstance check alone would miss them. Matched by name rather
#: than imported, to keep this module free of a provider dependency (see
#: the module docstring). httplib2 -- the HTTP transport googleapiclient
#: itself is built on -- raises its own hierarchy rooted at
#: ``HttpLib2Error`` instead of reusing ``OSError``; ``ServerNotFoundError``
#: (DNS resolution failure) is the one named here because it is the
#: specific case this finding evidenced and the paradigmatic "network
#: blip" this list exists for. Deliberately not the whole ``HttpLib2Error``
#: family: some siblings (e.g. a certificate mismatch) are not transient.
_NETWORK_ERROR_TYPE_NAMES = frozenset({"httplib2.error.ServerNotFoundError"})


def _is_network_error(exc: BaseException) -> bool:
    """
    Whether ``exc`` is a transport-level failure rather than a server
    response — a DNS/socket/TLS blip worth a second attempt.

    Covers the builtin ``TimeoutError``/``ConnectionError`` and every
    ``OSError`` subclass. The latter matters beyond the builtins:
    ``requests.exceptions.ConnectionError`` and ``.Timeout`` are both
    ``OSError`` subclasses but are *not* instances of the builtins of the
    same name, so an isinstance check against only the builtins misses
    them — the bug this function exists to fix. It also covers the named
    non-``OSError`` exceptions above, matched structurally so this stays
    free of a network-library import.
    """
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return True
    exc_type = type(exc)
    qualified = f"{exc_type.__module__}.{exc_type.__qualname__}"
    return qualified in _NETWORK_ERROR_TYPE_NAMES


def is_transient(exc: BaseException) -> bool:
    """
    Whether a failure is worth retrying.

    Classification is status-first: anything carrying a readable HTTP
    status is judged on that status (403 specially, by ``reason`` — see
    ``RATE_LIMIT_REASONS`` — everything else against
    ``TRANSIENT_STATUSES``). Only when no status can be read does a
    network-level check apply, covering DNS/socket/TLS blips. Anything
    unrecognised by either path does **not** count as transient: on a send
    path an unknown failure may have already delivered the message, so the
    safe default is to surface it rather than risk a duplicate.
    """
    status = _status_of(exc)
    if status is None:
        return _is_network_error(exc)
    if status == 403:
        return _reason_of(exc) in RATE_LIMIT_REASONS
    return status in TRANSIENT_STATUSES


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
        ValueError: If ``max_attempts`` is below 1 — a caller-argument bug,
            not a send failure, so it is raised as itself rather than
            wrapped into a ``TransportError`` claiming Gmail refused a
            message that was never transmitted.
        TransportError: On any send failure — authentication refused, the API
            rejecting the request, the network failing, or a transient failure
            that outlived its retries. The provider's own exception is always
            chained.

    Note:
        The bytes sent are exactly what :func:`svc.delivery.save_eml` would
        write, so a dry run is a faithful preview of the real send.
    """
    # retry_with_backoff raises this same ValueError for the same reason,
    # but from inside the `except Exception` below it would be caught and
    # reported as "Gmail refused the message" -- a bad call is not a send
    # failure, so it is checked here, before any attempt, instead of
    # relying on that wrapping to let it through unwrapped.
    if max_attempts < 1:
        raise ValueError(f"max_attempts must be at least 1, got {max_attempts}")

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
