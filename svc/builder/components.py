"""
Component classes for the email builder.

Each component represents a reusable content block (KPI strip, data table,
chart, text block, etc.). Components are constructed with their data and
render themselves via their Jinja2 template.

Usage:
    engine = TemplateEngine()
    kpi = KpiStrip(items=[KpiItem("S&P 500", "5,234", "#4A7C59", "+1.42%")])
    html = kpi.render(engine)
"""

from __future__ import annotations

from typing import Any

from .engine import TemplateEngine
from .exceptions import ValidationError
from .models import KpiItem, NumberedItem, TableRow, _validate_url


class Component:
    """
    Abstract base for all email components.

    Subclasses must set ``template_path`` and implement ``context()``.
    """

    template_path: str = ""  # e.g. "analysis/kpi-strip.html"

    def context(self) -> dict[str, Any]:
        """Return the template context dict for this component."""
        raise NotImplementedError

    def render(self, engine: TemplateEngine) -> str:
        """
        Render the component to an HTML string.

        Args:
            engine: Initialised TemplateEngine.

        Returns:
            Rendered HTML fragment.
        """
        if not self.template_path:
            raise ValidationError(f"{self.__class__.__name__} has no template_path set.")
        return engine.render(self.template_path, self.context())


# ──────────────────────────────────────────────────────────────────────
# Analysis components  (templates/analysis/)
# ──────────────────────────────────────────────────────────────────────


class KpiStrip(Component):
    """
    Row of key performance indicators.

    Accepts 2–4 KpiItem objects.  The template auto-adjusts column
    widths based on the number of items.

    Args:
        items:    List of KpiItem instances (2–4 items).
        subtitle: Optional sub-heading rendered above the strip.
    """

    template_path = "analysis/kpi-strip.html"

    def __init__(self, items: list[KpiItem], subtitle: str | None = None):
        if not 2 <= len(items) <= 4:
            raise ValidationError("KpiStrip requires 2–4 items.")
        for item in items:
            item.validate()
        self.items = items
        self.subtitle = subtitle

    def context(self) -> dict[str, Any]:
        return {
            "kpis": [
                {
                    "label": k.label,
                    "value": k.value,
                    "color": k.color,
                    "sublabel": k.sublabel,
                }
                for k in self.items
            ],
            "subtitle": self.subtitle,
        }


class DataTable(Component):
    """
    Financial data table with headers, alternating row colours, and
    colour-coded numeric cells.

    Args:
        headers:  List of column header strings.
        rows:     List of TableRow instances.
        source:   Attribution string (e.g. "Source: Bloomberg").
        as_of:    Date string (e.g. "March 28, 2026").
        subtitle: Optional sub-heading rendered above the table.
    """

    template_path = "analysis/data-table.html"

    def __init__(
        self,
        headers: list[str],
        rows: list[TableRow],
        source: str = "",
        as_of: str = "",
        subtitle: str | None = None,
    ):
        if not headers:
            raise ValidationError("DataTable requires at least one header.")
        if not rows:
            raise ValidationError("DataTable requires at least one row.")
        for i, row in enumerate(rows):
            row.validate()
            if len(row.cells) != len(headers):
                raise ValidationError(
                    f"DataTable row {i} has {len(row.cells)} cells but there are "
                    f"{len(headers)} headers; the table would render misaligned."
                )
        self.headers = headers
        self.rows = rows
        self.source = source
        self.as_of = as_of
        self.subtitle = subtitle

    def context(self) -> dict[str, Any]:
        return {
            "headers": self.headers,
            "rows": [
                {
                    "cells": r.cells,
                    "colors": r.colors,
                    "alt": i % 2 == 1,  # alternating row background
                }
                for i, r in enumerate(self.rows)
            ],
            "source": self.source,
            "as_of": self.as_of,
            "subtitle": self.subtitle,
        }


class ChartBlock(Component):
    """
    Image / chart placeholder with source attribution.

    Args:
        image_url: Full URL to the chart image.
        alt_text:  Accessibility alt text.
        source:    Attribution string.
        subtitle:  Optional sub-heading rendered above the chart.
    """

    template_path = "analysis/chart-block.html"

    def __init__(
        self,
        image_url: str,
        alt_text: str = "Chart",
        source: str = "",
        subtitle: str | None = None,
    ):
        if not image_url:
            raise ValidationError("ChartBlock requires an image_url.")
        _validate_url(image_url, "chart.image_url")
        self.image_url = image_url
        self.alt_text = alt_text
        self.source = source
        self.subtitle = subtitle

    def context(self) -> dict[str, Any]:
        return {
            "chart_image_url": self.image_url,
            "chart_alt_text": self.alt_text,
            "chart_source": self.source,
            "subtitle": self.subtitle,
        }


# ──────────────────────────────────────────────────────────────────────
# Text components  (templates/text/)
# ──────────────────────────────────────────────────────────────────────


class TextBlock(Component):
    """
    Simple narrative prose block.

    Args:
        content:  HTML or plain-text paragraph content.  May contain
                  multiple ``<p>`` tags for multi-paragraph blocks.
        subtitle: Optional sub-heading rendered above the prose.
    """

    template_path = "text/text-block.html"

    def __init__(self, content: str, subtitle: str | None = None):
        if not content:
            raise ValidationError("TextBlock requires content.")
        self.content = content
        self.subtitle = subtitle

    def context(self) -> dict[str, Any]:
        return {
            "text_content": self.content,
            "subtitle": self.subtitle,
        }


class NumberedList(Component):
    """
    Numbered theme / item list (e.g. "Key Themes" section).

    Args:
        items:    List of NumberedItem instances.
        subtitle: Optional sub-heading rendered above the list.
    """

    template_path = "text/numbered-list.html"

    def __init__(self, items: list[NumberedItem], subtitle: str | None = None):
        if not items:
            raise ValidationError("NumberedList requires at least one item.")
        for item in items:
            item.validate()
        self.items = items
        self.subtitle = subtitle

    def context(self) -> dict[str, Any]:
        return {
            "items": [
                {
                    "number": it.number,
                    "title": it.title,
                    "body": it.body,
                }
                for it in self.items
            ],
            "subtitle": self.subtitle,
        }


class AuthorBlock(Component):
    """
    Author attribution byline.

    Args:
        name:      Full name.
        job_title: Job title or role (e.g. "Chief Market Strategist").
        email:     Contact email address.
        subtitle:  Optional sub-heading rendered above the byline.
    """

    template_path = "text/author-block.html"

    def __init__(
        self,
        name: str,
        job_title: str = "",
        email: str = "",
        subtitle: str | None = None,
    ):
        if not name:
            raise ValidationError("AuthorBlock requires a name.")
        self.name = name
        self.job_title = job_title
        self.email = email
        self.subtitle = subtitle

    def context(self) -> dict[str, Any]:
        return {
            "author_name": self.name,
            "author_job_title": self.job_title,
            "author_email": self.email,
            "subtitle": self.subtitle,
        }
