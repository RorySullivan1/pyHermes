"""
The theme's styles on the closed set of tags a raw-HTML prose field carries (#280).

The same closed-tag idea as #108's degrader: a fixed set of tags is styled,
every other tag passes through as written, and a tag that already has a
``style`` is the author's. ``h1`` and ``h2`` are refused rather than demoted,
because the section title owns those levels and a silent rewrite would hide
that from the author; accepting them later is additive, refusing them later
would not be.
"""

from __future__ import annotations

import re

import jinja2

from .exceptions import TemplateError, ValidationError

#: The tags :func:`prose` styles, in the order the styles template lists them.
STYLED_TAGS = ("h3", "h4", "ul", "ol", "li", "blockquote", "a", "hr")

#: The spacing the styles read, so each block that styles prose declares them.
PROSE_TOKENS = ("prose_gap", "prose_indent", "prose_item_gap")

#: Where each tag's declarations live, so an overlay can restyle one.
STYLES_TEMPLATE = "text/prose-styles.html"

_TOP_HEADING = re.compile(r"<(h[12])[\s/>]", re.IGNORECASE)
_START_TAG = re.compile(
    r"<(" + "|".join(STYLED_TAGS) + r")\b((?:[^>\"']|\"[^\"]*\"|'[^']*')*)>",
    re.IGNORECASE,
)
_STYLE_ATTR = re.compile(r"\sstyle\s*=", re.IGNORECASE)


def refuse_top_headings(html: str, field: str) -> None:
    """
    Raise if ``html`` holds an ``h1`` or ``h2``.

    Raises:
        ValidationError: Naming ``field`` and the tag found.
    """
    found = _TOP_HEADING.search(html)
    if found:
        raise ValidationError(
            f"{field} holds an <{found.group(1).lower()}>; the section title owns that "
            "level. Use <h3> for a subheading, or <h4> beneath it."
        )


@jinja2.pass_context
def prose(context: jinja2.runtime.Context, html: str) -> str:
    """``html`` with each styled tag that has no ``style`` given the theme's."""
    if not _START_TAG.search(html):
        return html
    styles = _styles(context)

    def styled(match: re.Match[str]) -> str:
        tag, attrs = match.group(1), match.group(2)
        if _STYLE_ATTR.search(attrs):
            return match.group(0)
        attrs = attrs.rstrip()
        close = ""
        if attrs.endswith("/"):
            attrs, close = attrs[:-1].rstrip(), " /"
        return f'<{tag}{attrs} style="{styles[tag.lower()]}"{close}>'

    return _START_TAG.sub(styled, html)


def _styles(context: jinja2.runtime.Context) -> dict[str, str]:
    """Each styled tag's declarations, rendered with the caller's namespaces."""
    source = context.environment.get_template(STYLES_TEMPLATE).render(context.get_all())
    styles = {}
    for line in source.splitlines():
        tag, sep, declarations = line.partition(":")
        if sep and tag.strip() in STYLED_TAGS:
            styles[tag.strip()] = " ".join(declarations.split())
    missing = [tag for tag in STYLED_TAGS if tag not in styles]
    if missing:
        raise TemplateError(f"{STYLES_TEMPLATE} styles no {', '.join(missing)}")
    return styles
