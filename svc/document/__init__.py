"""
The paged medium, and what will become the document-only half of the builder.

Today this package owns the medium and its page. Epic #157's #163 adds the
managed elements a paged document needs and an email never had: a ``Page``
with its breaks, a cover, running header and footer margin boxes, and a
back-matter disclaimer.
"""

from .medium import PAGED_MEDIUM, paged_medium

__all__ = ["PAGED_MEDIUM", "paged_medium"]
