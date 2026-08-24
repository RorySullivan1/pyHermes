"""
Gmail send adapter.

Consumes what :mod:`svc.delivery` assembles and puts it on the wire. It owns
Gmail's wire contract and error semantics; authentication stays with the
caller, so this package imports nothing from Google and pyHermes gains no
dependency. See :mod:`svc.gmail.sender` for the reasoning and setup.

    from svc.delivery import build_message
    from svc.gmail import GoogleApiTransport, send_message

    message = build_message(email, subject=..., sender=..., to=[...])
    message_id = send_message(message, transport=GoogleApiTransport(service))
"""

from .sender import (
    TRANSIENT_STATUSES,
    GmailTransport,
    GoogleApiTransport,
    is_transient,
    send_message,
)

__all__ = [
    "TRANSIENT_STATUSES",
    "GmailTransport",
    "GoogleApiTransport",
    "is_transient",
    "send_message",
]
