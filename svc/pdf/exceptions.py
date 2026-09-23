"""
Exceptions for the PDF exporter.

:class:`PdfError` is a **sibling** of ``EmailBuilderError`` and
``DeliveryError`` rather than a child of either, for the reason delivery
gives: a document that will not print is neither a build failure nor a
transport failure, and a caller must tell the three apart::

    try:
        pdf = render_pdf(document)
    except EmailBuilderError:
        ...  # the document itself is wrong
    except PdfError:
        ...  # the document is fine; the backend or a resource is not
"""


class PdfError(Exception):
    """Base exception for everything the PDF exporter rejects."""


class BackendMissingError(PdfError):
    """Raised when WeasyPrint is not installed.

    The exporter is an optional extra, so this is a setup problem rather than
    a data problem, and the message names the install that fixes it.
    """


class UnreachableResourceError(PdfError):
    """Raised when the document references something the exporter will not fetch.

    The exporter makes **no network requests**, so a hosted image is not
    slow — it is refused, by URL. Attach the bytes
    (:meth:`~svc.builder.images.EmailImage.attached`) or inline them
    (:meth:`~svc.builder.images.EmailImage.inline`) and they travel with the
    document instead.
    """


class ProfileError(PdfError, ValueError):
    """Raised when a :class:`~svc.pdf.profile.PdfProfile` is constructed wrong.

    Also a ``ValueError``, as a bad ``Config`` field is: a profile is setup,
    and a caller validating setup catches that.
    """
