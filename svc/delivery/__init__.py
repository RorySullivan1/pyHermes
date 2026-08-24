"""
pyHermes delivery layer — transport-neutral MIME assembly.

The builder declares a CID embed; it never performs one. Attaching a MIME
part is a transport act, so ``svc.builder`` emits two things and this package
consumes both::

    from svc.delivery import build_message, save_eml

    message = build_message(
        email,
        subject="Weekly Market Wrap",
        sender="research@example.com",
        to=["reader@example.com"],
    )
    save_eml(message, "output/weekly-wrap.eml")   # dry run, no transport

:func:`~svc.delivery.message.build_message` is pure — no credentials, no
network, no clock — so it is fully testable on its own. Sending is the job of
the per-service adapters (``svc.gmail``, ``svc.outlook``), which consume the
message this package builds.
"""

from .exceptions import DeliveryError, MessageError
from .message import RenderableEmail, build_message, collect_cid_references, save_eml

__all__ = [
    "DeliveryError",
    "MessageError",
    "RenderableEmail",
    "build_message",
    "collect_cid_references",
    "save_eml",
]
