"""
pyHermes service layer: ``builder`` -> ``delivery`` -> ``gmail`` / ``outlook``.

Two seams hold the chain apart, and both are load-bearing:

**Builder to delivery** — the builder *declares* CID embeds. For every
``src="cid:X"`` in the HTML, :meth:`Email.assets` has the entry describing
what to attach as ``X``; delivery *performs* the attachment.

**Delivery to an adapter** — delivery assembles bytes, an adapter transmits
them. Adapters own their provider's wire contract and error semantics and
**never** authentication, so pyHermes depends on no provider SDK.

This package re-exports nothing: import from ``svc.builder``,
``svc.delivery``, ``svc.gmail`` or ``svc.outlook`` directly.
"""
