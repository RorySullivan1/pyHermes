"""
Exceptions for the delivery layer.

:class:`DeliveryError` is deliberately a **sibling** of
:class:`~svc.builder.exceptions.EmailBuilderError`, not a child. A message
that fails to assemble or send is not a build failure, and a caller must be
able to tell the two apart::

    try:
        message = build_message(email, subject=..., sender=..., to=...)
    except EmailBuilderError:
        ...  # the email itself is wrong -- bad data, oversized, bad template
    except DeliveryError:
        ...  # the email is fine; the envelope or the transport is not

Catch :class:`DeliveryError` for "anything the delivery layer rejected".
"""


class DeliveryError(Exception):
    """Base exception for everything the delivery layer rejects."""


class MessageError(DeliveryError):
    """Raised when an outgoing message cannot be assembled.

    Covers a missing envelope field (no subject, sender or recipient) and a
    mismatch between the HTML's ``cid:`` references and the asset manifest.
    """
