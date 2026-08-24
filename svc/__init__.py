"""
pyHermes Service Layer
======================

svc/
├── builder/     — OO email assembly (Jinja2): HTML + an asset manifest.
└── delivery/    — transport-neutral MIME assembly: HTML + manifest → message.

The seam between them: the builder *declares* CID embeds (for every
``src="cid:X"`` in the HTML, ``Email.assets()`` has the entry describing what
to attach as ``X``), and delivery *performs* them.

Per-service send adapters (``gmail/``, ``outlook/``) are **planned, not
built** — those subpackages do not exist yet. Don't import them.

Usage::

    from svc.builder import CardGroup, EmailBuilder, FullWidth
    from svc.builder.models import Card, KpiItem
    from svc.delivery import build_message, save_eml
"""
