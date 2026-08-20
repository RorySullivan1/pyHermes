"""
pyHermes Service Layer
======================

svc/
└── builder/     — OO email assembly (Jinja2).  The entire current product.

Delivery (``gmail/``, ``outlook/``) is **planned, not built** — those
subpackages do not exist yet.  Don't import them.

Usage::

    from svc.builder import EmailBuilder, KpiStrip, FullWidth, Highlight
    from svc.builder.models import KpiItem
"""
