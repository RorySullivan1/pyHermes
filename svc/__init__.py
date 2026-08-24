"""
pyHermes Service Layer
======================

svc/
├── builder/     — OO email assembly (Jinja2): HTML + an asset manifest.
├── delivery/    — transport-neutral MIME assembly: HTML + manifest → message.
├── gmail/       — Gmail send adapter: message → the wire.
└── outlook/     — Outlook send adapter, over Microsoft Graph.

The seam between builder and delivery: the builder *declares* CID embeds
(for every ``src="cid:X"`` in the HTML, ``Email.assets()`` has the entry
describing what to attach as ``X``), and delivery *performs* them.

The seam between delivery and an adapter: delivery assembles bytes, an
adapter transmits them. Adapters own their provider's wire contract and
error semantics; they never own authentication, so pyHermes has no
dependency on any provider SDK.

Usage::

    from svc.builder import CardGroup, EmailBuilder, FullWidth
    from svc.builder.models import Card, KpiItem
    from svc.delivery import build_message, save_eml
    from svc.gmail import GoogleApiTransport, send_message
"""
