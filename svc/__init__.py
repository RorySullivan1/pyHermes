"""
pyHermes Service Layer
======================

svc/
├── builder/     — OO email assembly (Jinja2)
├── gmail/       — Gmail delivery
├── outlook/     — Outlook delivery
└── assembler.py — Legacy flat assembler

Usage::

    from svc.builder import EmailBuilder, KpiStrip, FullWidth, Highlight
    from svc.builder.models import KpiItem
"""
