"""
The email medium, and what will become the email-only half of the builder.

Today this package owns the medium alone: ``Email``, the four regions and
``base.html`` still live in ``svc.builder``. Epic #157's later phases move
them here, which is why the import path exists from the start — a caller who
writes ``from svc.email import EMAIL_MEDIUM`` now keeps working through
every one of them.
"""

from .medium import EMAIL_MEDIUM, validate_gmail_size

__all__ = ["EMAIL_MEDIUM", "validate_gmail_size"]
