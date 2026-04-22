"""
Custom exceptions for the email builder service.
"""


class EmailBuilderError(Exception):
    """Base exception for all email builder errors."""
    pass


class TemplateError(EmailBuilderError):
    """Raised when a template cannot be loaded or rendered."""
    pass


class ValidationError(EmailBuilderError):
    """Raised when configuration data fails validation."""
    pass


class SizeError(EmailBuilderError):
    """Raised when the rendered email exceeds the size limit."""
    pass
