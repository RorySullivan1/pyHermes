"""
The closed string vocabularies the builder accepts, in one place.

Column ratios, card orientation, embed strategy, image and text alignment,
row kind, and the theme names — so the allowed values live here rather than
as bare literals across containers and components.

Every enum is a :class:`~enum.StrEnum`, so a member *is* its wire string and
a caller may pass either interchangeably. That keeps them purely additive:
existing ``ratio="50-50"`` calls are unaffected even where a container now
stores the member.

**Vocabulary only.** A ratio's template path stays with the container that
owns it — a template path is a rendering detail, not part of the type.
"""

from __future__ import annotations

from enum import StrEnum


class TwoColumnRatio(StrEnum):
    """Column-width splits supported by :class:`~svc.builder.containers.TwoColumn`."""

    EQUAL = "50-50"
    NARROW_WIDE = "30-70"
    WIDE_NARROW = "70-30"


class ThreeColumnRatio(StrEnum):
    """Column-width splits supported by :class:`~svc.builder.containers.ThreeColumn`."""

    EQUAL = "33-33-33"
    WIDE_LEFT = "50-25-25"
    WIDE_CENTER = "25-50-25"
    WIDE_RIGHT = "25-25-50"


class CardOrientation(StrEnum):
    """Layout direction for a :class:`~svc.builder.components.CardGroup`."""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class SizeTheme(StrEnum):
    """
    Density presets for the whole email.

    The *entire* caller-facing sizing surface: ``EmailMetadata(size_theme=…)``
    takes a member here or its bare string, and there is deliberately no
    per-email or per-component px override anywhere in the builder. The
    theme-to-values mapping lives in :mod:`svc.builder.sizing`, not here —
    this enum holds only the vocabulary, per the note above.
    """

    COMPACT = "compact"
    STANDARD = "standard"
    SPACIOUS = "spacious"


class EmbedStrategy(StrEnum):
    """
    How an image's bytes reach the reader.

    The three options are not interchangeable — each trades hosting,
    message size, and client support differently. See
    :mod:`svc.builder.images` for the full comparison.
    """

    #: Reference a publicly hosted URL. No size cost; Outlook desktop
    #: blocks it until the reader clicks "download images".
    REMOTE = "remote"
    #: Attach the bytes as a MIME part and point at it with ``cid:``.
    #: Renders without a prompt in Outlook; costs *message* size, not HTML
    #: size, so it does not count against the 102 KB Gmail clipping limit.
    #: Requires the delivery layer to attach the parts the builder lists.
    CID = "cid"
    #: Inline the bytes as a base64 ``data:`` URI. Needs no host and no
    #: attachment, but Gmail strips it and Outlook's Word engine will not
    #: render it — and base64 costs +33% straight out of the 102 KB budget.
    DATA_URI = "data_uri"


class ImageAlign(StrEnum):
    """Horizontal placement for a :class:`~svc.builder.components.ImageBlock`."""

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class ColumnAlign(StrEnum):
    """
    Horizontal text alignment inside a :class:`~svc.builder.models.Column`.

    Deliberately separate from :class:`ImageAlign` despite sharing member
    names: that one places a *block* within its container, this one aligns
    *text* within cells. Two concepts that happen to agree today, and would
    stop agreeing the moment either grew a member the other has no meaning
    for.
    """

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class TextAlign(StrEnum):
    """
    Horizontal alignment of a *band of copy* — a region's box, a section.

    A third alignment vocabulary rather than a shared one, which is the
    convention :class:`ColumnAlign` already set and explained: alignments
    that agree today stop agreeing the moment one grows a member the other
    has no meaning for. What distinguishes this one is the thing being
    aligned. :class:`ImageAlign` places a *block* within its container and
    :class:`ColumnAlign` aligns *text within table cells*; this aligns the
    prose of a whole band, and it is genuinely one concept across the two
    places that band appears — the header and footer boxes (through
    ``BoxSurface``) and the body's containers (#126), which both read it
    from here.

    ``justify`` is absent deliberately: it does nothing to a single short
    line, and the rest of the CSS vocabulary is inline-level.
    """

    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class ColumnKind(StrEnum):
    """
    What a table column holds, which decides how it is set.

    The vocabulary that replaces ``loop.first`` (#117). A column's kind
    drives its typeface, its weight and — unless the caller says otherwise —
    its alignment, so one word carries what four separate template
    conditionals used to.
    """

    #: Labels and prose. Set in the label face, unemphasised, aligned left.
    TEXT = "text"
    #: Figures. Set in the numeric face, bold, aligned right.
    NUMERIC = "numeric"


class RowKind(StrEnum):
    """
    What a row of a :class:`~svc.builder.components.DataTable` *is*.

    A financial table is rarely uniform: it carries figures, the subtotals
    that summarise them, and the headings that group them. Before #119 all
    three rendered identically and the only way to signal a total was to put
    the word in a cell and hope.

    This is deliberately **not** the same axis as a cell's colour. A cell's
    colour is the caller's claim about a *figure*; a row's kind is a
    statement about the row's role in the table, so it renders from theme
    tokens and takes no caller colours at all.
    """

    #: An ordinary row of figures. Stripes with its neighbours.
    DATA = "data"
    #: A total or subtotal. Ruled off above, bold across, and never striped —
    #: a reader should find it without counting rows.
    TOTAL = "total"
    #: A heading that groups the rows beneath it. Its first cell carries the
    #: label; the rest render empty, because a merged cell has no honest
    #: plain-text projection.
    SUBHEAD = "subhead"
