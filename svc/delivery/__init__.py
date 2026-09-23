"""
Transport-neutral MIME assembly: the builder's output, as a sendable message.

The builder *declares* a CID embed; this package *performs* it. Attaching a
MIME part is a transport act, so ``svc.builder`` emits HTML plus a manifest
and this package consumes both::

    message = build_message(email, subject=..., sender=..., to=[...])
    save_eml(message, "output/weekly-wrap.eml")   # dry run, no transport

:func:`~svc.delivery.message.build_message` is pure — no credentials, no
network, no clock — so it is testable on its own. Sending belongs to the
adapters (``svc.gmail``, ``svc.outlook``) that consume this message.
"""

from .exceptions import DeliveryError, MessageError
from .message import (
    Attachment,
    RenderableEmail,
    build_message,
    collect_cid_references,
    save_eml,
)

__all__ = [
    "Attachment",
    "DeliveryError",
    "MessageError",
    "RenderableEmail",
    "build_message",
    "collect_cid_references",
    "save_eml",
]
