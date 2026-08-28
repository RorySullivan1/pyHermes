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

The formatting policy
---------------------

Decided **once, here** (#109), rather than per component — the alternative is
a house format that drifts one projection at a time. Every ``text()`` in the
package composes these helpers instead of spelling their decisions itself:

``LINE_WIDTH = 78``
    Prose wraps here, one column under RFC 5322's 78-character soft limit for
    a line of a message. **Tables never wrap** — see :func:`table`.

*One* blank line between blocks, *two* between sections
    :func:`join_blocks` and :func:`join_sections`. The rhythm is what gives a
    plain-text email its structure, since it has no other typography.

Links: :func:`format_link` inline, :func:`link_line` on a line of its own
    Parentheses read better inside a sentence, a colon better in a list of
    destinations. A link with no URL emits its label alone, because an email
    is free to carry none.

A section title sits over a rule of its own length
    :func:`underline` — ``-`` for a section, ``=`` for the masthead, so the
    email's one top-level heading reads as one. Nothing else is decorated.

Chrome images project to nothing; content images project their alt text
    A logo, a masthead background and a footer sign-off mark are decoration a
    text reader loses nothing by missing. An ``ImageBlock`` or a
    ``ChartBlock`` is the section's *content*, and its ``alt`` is required at
    construction precisely so this projection is never empty.
"""

from __future__ import annotations

import re
import textwrap
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


def link_line(label: str, url: str) -> str:
    """
    Spell one link that stands on a line of its own.

    The list form, where :func:`format_link` is the inline one — a footer's
    link row and a call-to-action are lists of destinations, and a colon reads
    better there than the parentheses that suit a link inside a sentence.
    Both spellings live here so the house format stays in one module.

    A label with no URL emits the label alone. pyHermes does not require an
    unsubscribe destination or any other link (#100), so an email that
    supplies none must not project a dangling ``Unsubscribe:``.
    """
    return f"{label}: {url}" if url else label


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


#: Where prose wraps: one column under RFC 5322's 78-character soft limit.
LINE_WIDTH = 78


def wrap(text: str) -> str:
    """
    Wrap prose to :data:`LINE_WIDTH`, line by line.

    Each line is wrapped on its own rather than the whole block being reflowed,
    because the breaks already in it are meaningful — a ``br`` the caller
    wrote, or one list item per line — and reflowing would run them together.

    A ``- `` item keeps a hanging indent, so a wrapped bullet stays visibly
    one item instead of looking like the start of the next.
    """
    out: list[str] = []
    for line in text.split("\n"):
        if not line:
            out.append("")
        elif line.startswith("- "):
            out.extend(textwrap.wrap(line, LINE_WIDTH, subsequent_indent="  ") or [line])
        else:
            out.extend(textwrap.wrap(line, LINE_WIDTH) or [line])
    return "\n".join(out)


def underline(title: str, rule: str = "-") -> str:
    """
    A heading over a rule of its own length.

    ``-`` for a section and ``=`` for the masthead, so the email's single
    top-level heading reads as one. A plain-text email has no other
    typography, so this and the blank-line rhythm carry all of its structure.
    """
    return f"{title}\n{rule * len(title)}" if title else ""


def join_blocks(*blocks: str) -> str:
    """Join blocks with one blank line, dropping the empty ones."""
    return "\n\n".join(block for block in blocks if block)


def join_sections(*sections: str) -> str:
    """Join sections with two blank lines, dropping the empty ones."""
    return "\n\n\n".join(section for section in sections if section)


def table(headers: list[str], rows: list[list[str]]) -> str:
    """
    Aligned monospace columns: the epic's named fiddly spot.

    Three decisions, and the third is the one worth stating:

    * **Width comes from the widest cell in each column**, header included.
    * **The first column is left-aligned and the rest are right-aligned.**
      That is not a guess about the data — it is the convention the HTML
      template already encodes, where ``loop.first`` picks the label face for
      column one and the numeric face for the others. Reading the alignment
      off the same rule is what keeps the two projections agreeing.
    * **Nothing wraps inside a cell.** A table wider than
      :data:`LINE_WIDTH` overflows the line-width policy rather than
      corrupting its own alignment — a wrapped cell destroys the column that
      is the entire reason to render a table as text at all. The policy
      yields to the alignment here, deliberately, and this is where it says so.

    Args:
        headers: One label per column.
        rows:    Cells per row, each row the same length as ``headers``.

    Returns:
        The header row, a rule, and one line per row. Empty if there are no
        headers.
    """
    if not headers:
        return ""
    widths = [
        max(len(headers[i]), *(len(row[i]) for row in rows)) if rows else len(headers[i])
        for i in range(len(headers))
    ]

    def line(cells: list[str]) -> str:
        first, *rest = (
            cell.ljust(widths[i]) if i == 0 else cell.rjust(widths[i])
            for i, cell in enumerate(cells)
        )
        return "  ".join([first, *rest]).rstrip()

    rule = "  ".join("-" * width for width in widths)
    return "\n".join([line(headers), rule, *(line(row) for row in rows)])


__all__ = [
    "LINE_WIDTH",
    "format_link",
    "html_to_text",
    "join_blocks",
    "join_sections",
    "link_line",
    "table",
    "underline",
    "wrap",
]
