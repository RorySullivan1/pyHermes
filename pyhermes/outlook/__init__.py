"""
Outlook send adapter, over Microsoft Graph.

Consumes what :mod:`pyhermes.delivery` assembles and puts it on the wire. It owns
Graph's wire contract and error semantics; authentication stays with the
caller, so this package imports nothing from Microsoft and pyHermes gains no
dependency. See :mod:`pyhermes.outlook.sender` for the transport choice and the
ways Graph differs from Gmail.

    from pyhermes.delivery import build_message
    from pyhermes.outlook import GraphApiTransport, send_message

    message = build_message(email, subject=..., sender=..., to=[...])
    send_message(message, transport=GraphApiTransport(session))
"""

from .sender import (
    ACCEPTED,
    GRAPH_BASE_URL,
    TRANSIENT_STATUSES,
    GraphApiError,
    GraphApiTransport,
    OutlookTransport,
    is_transient,
    retry_after_seconds,
    send_message,
)

__all__ = [
    "ACCEPTED",
    "GRAPH_BASE_URL",
    "TRANSIENT_STATUSES",
    "GraphApiError",
    "GraphApiTransport",
    "OutlookTransport",
    "is_transient",
    "retry_after_seconds",
    "send_message",
]
