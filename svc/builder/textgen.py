"""
The HTML-subset degrader (#108): the builder's blessed raw HTML, as plain text.

Five surfaces in this package are raw caller HTML by documented contract —
``TextBlock.content``, ``Card.body``, ``NumberedItem.body``,
``Footer.disclaimer`` and ``header_disclaimer``. Every other value reaches a
template through ``escape_html``. The plain-text part (#53) therefore needs
exactly one converter, and only for those five::

    from svc.builder.textgen import html_to_text

    html_to_text("<p>Past performance is <strong>not</strong> a guide.</p>")
    # 'Past performance is not a guide.'

**It parses; it never greps.** ``qa/lint.py`` records what a regex costs here:
a ``grep`` for ``Contact Us`` matched inside an HTML comment and produced a
confident, wrong answer. :class:`html.parser.HTMLParser` is stdlib, so the
conversion costs no dependency — the same foundation and the same reason.

**The blessed set is closed, and that is a decision rather than a to-do.**
Epic #53 names this converter as its scope magnet, so the set is written down
here and refuses to grow:

===================  =========================================================
element              projection
===================  =========================================================
``p``                a paragraph break
``br``               a line break
``a``                carries its URL — see ``format_link``
``strong`` ``b``     markers **dropped**; plain text has no emphasis, and
``em`` ``i``         ``*stars*`` are a Markdown affectation, not house style
``ul`` ``ol`` ``li`` one ``- `` item per line
===================  =========================================================

An element outside that set **contributes its text and vanishes as markup**.
So a table pasted into a disclaimer degrades to its cell text run together —
imperfect, acceptable, and documented. The two exceptions are ``script`` and
``style``, whose content is dropped whole: a browser renders no text for
either, so keeping it would be *less* faithful rather than more, and a script
body reaching a plain-text reader is a defect rather than a degradation.

The alternative to a closed set is a converter that grows one caller's tag at
a time until it is a second rendering engine, which is the failure the set
exists to prevent. The one surface that *does*
carry ordinals — ``NumberedList`` — never routes through here: it holds them
as data and projects them itself (#109), which is why ``ol`` can take the same
``- `` as ``ul`` without losing anything a caller expressed.

**Character references decode to the characters themselves**, and this is
#100's decision deliberately inverted. That issue kept ``&copy;`` as an entity
in the HTML because U+00A9 mis-decoded as latin-1 renders as a mojibake pair.
The text part travels as a MIME part whose charset ``EmailMessage`` declares,
so the real character is correct there — and an undecoded ``&copy;`` reaching
a plain-text reader would be the actual bug. ``convert_charrefs=True`` does
this in the parser, before any of this module's logic sees the text.

**Output is deterministic**, byte for byte, for identical input. #110's text
goldens depend on it, and so does the whole golden discipline behind them.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from html.parser import HTMLParser

#: Elements whose markers are dropped but whose text is kept inline.
_INLINE_PASSTHROUGH = frozenset({"strong", "b", "em", "i"})

#: Elements that open and close a block of their own.
_BLOCK = frozenset({"p", "ul", "ol"})

#: Elements whose content is code rather than copy, and is dropped whole.
#:
#: Not an exception to the closed set — the set governs which elements get a
#: *projection*, and these get none. A browser renders no text for either, so
#: keeping their content would be less faithful, not more: a stylesheet or a
#: script body reaching a plain-text reader is a defect, where a stray table's
#: cell text running together is the documented imperfect degradation.
_NOT_TEXT = frozenset({"script", "style"})

#: A structural line break, held apart from any whitespace the source carries.
#:
#: The distinction is the whole of the whitespace model. Only ``br`` and ``li``
#: break a line; a newline inside the *source* is layout, and a browser
#: collapses it to a space. Marking the real breaks with a character that
#: cannot appear in the copy is what lets one collapse pass handle both.
_BREAK = "\x00"

#: Any run of whitespace, collapsed to one space.
_SPACE_RUN = re.compile(r"\s+")


def format_link(label: str, url: str) -> str:
    """
    Spell one link in plain text.

    The seam #108 leaves for #109: the formatting policy owns the final
    spelling, and it can move without reopening the parser. A link whose
    label *is* its URL emits once rather than saying the same thing twice.

    Args:
        label: The link's visible text, already degraded and collapsed.
        url:   The ``href``, or the empty string if there was none.

    Returns:
        The text to emit in place of the link.
    """
    if not url:
        return label
    if not label or label == url:
        return url
    return f"{label} ({url})"


class _Degrader(HTMLParser):
    """
    Walks the fragment once, building blocks of lines.

    Two buffers rather than one: ``_current`` accumulates the block being
    built, and ``_link`` diverts text while an anchor is open so its label can
    be handed to :func:`format_link` whole. An anchor left unclosed by
    malformed input is flushed at :meth:`close`, because this module's callers
    pass arbitrary caller HTML and a converter that raises on a stray tag
    would fail the render of an otherwise valid email.
    """

    def __init__(self, link_format: Callable[[str, str], str]) -> None:
        super().__init__(convert_charrefs=True)
        self._link_format = link_format
        self._blocks: list[str] = []
        self._current: list[str] = []
        self._link: list[str] | None = None
        self._href = ""
        self._muted = 0

    # -- buffers ------------------------------------------------------

    def _emit(self, text: str) -> None:
        if self._link is not None:
            self._link.append(text)
        else:
            self._current.append(text)

    def _flush_block(self) -> None:
        """Close the current block, normalising and keeping it if it has text."""
        self._close_link()
        block = _normalise_block("".join(self._current))
        self._current = []
        if block:
            self._blocks.append(block)

    def _close_link(self) -> None:
        if self._link is None:
            return
        label = _SPACE_RUN.sub(" ", "".join(self._link)).strip()
        href, self._href = self._href, ""
        self._link = None
        self._current.append(self._link_format(label, href))

    # -- parser hooks -------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _NOT_TEXT:
            self._muted += 1
        elif tag in _BLOCK:
            self._flush_block()
        elif tag == "li":
            self._close_link()
            self._current.append(f"{_BREAK}- ")
        elif tag == "br":
            self._emit(_BREAK)
        elif tag == "a":
            self._close_link()
            self._href = dict(attrs).get("href") or ""
            self._link = []
        elif tag in _INLINE_PASSTHROUGH:
            pass  # markers dropped; the text arrives through handle_data

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # ``<br/>`` and friends: HTMLParser routes the XHTML spelling here
        # instead of through start-then-end, so a self-closed break would
        # otherwise be silently dropped.
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag in _NOT_TEXT:
            self._muted = max(0, self._muted - 1)
        elif tag in _BLOCK:
            self._flush_block()
        elif tag == "a":
            self._close_link()

    def handle_data(self, data: str) -> None:
        if self._muted:
            return
        # A literal break marker in caller copy would be indistinguishable
        # from a structural one, so it never survives the door.
        self._emit(data.replace(_BREAK, ""))

    # -- result -------------------------------------------------------

    def text(self) -> str:
        self._flush_block()
        return "\n\n".join(self._blocks)


def _normalise_block(raw: str) -> str:
    """
    Collapse one block's whitespace the way a browser would.

    Every run of whitespace becomes one space — **including a newline**, which
    is the part that is easy to get wrong: a paragraph written across three
    indented source lines is one line of copy to a reader, and only ``br`` and
    ``li`` actually break one. Those arrive as ``_BREAK`` markers, held apart
    from the source's own whitespace precisely so this single pass can tell
    them apart.

    Blank lines *inside* a block survive — two consecutive breaks are a gap
    the caller asked for — but leading and trailing ones are dropped, because
    those come from the markup's layout rather than from the copy.
    """
    lines = [_SPACE_RUN.sub(" ", line).strip() for line in raw.split(_BREAK)]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def html_to_text(html: str, link_format: Callable[[str, str], str] = format_link) -> str:
    """
    Degrade one blessed raw-HTML field to plain text.

    Args:
        html:        The caller's HTML. Arbitrary input is accepted: an
                     unknown element contributes its text, and malformed
                     markup degrades rather than raising.
        link_format: How to spell a link, defaulting to :func:`format_link`.
                     The seam #109's formatting policy moves.

    Returns:
        Plain text: paragraphs separated by a blank line, list items one per
        line behind ``- ``, no leading or trailing whitespace. Deterministic
        for identical input.
    """
    degrader = _Degrader(link_format)
    degrader.feed(html)
    degrader.close()
    return degrader.text()


__all__ = ["format_link", "html_to_text"]
