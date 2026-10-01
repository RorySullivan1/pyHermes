"""
Email-client lint pass (#60): portability checks over rendered HTML.

The constraints that break emails were documented prose, not checks —
Outlook's Word engine ignores ``max-width`` so every ``img`` needs a
``width=`` attribute; ``alt`` was required at construction but nothing
asserted it survived into the markup. This turns those into findings::

    findings = lint_email(email)     # the rules, plus the size breakdown
    errors = [f for f in findings if f.severity is Severity.ERROR]

Every rule cites its source in ``SOURCES``; ``DEFERRED_RULES`` names any that
are real but not yet shipped. `.claude/rules/qa-harness.md` carries both. It ships in the
package since #278, so an installed copy can check an email; ``qa.lint`` re-exports it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from html.parser import HTMLParser

from pyhermes.builder import Email
from pyhermes.builder.document import Document
from pyhermes.builder.exceptions import SizeError
from pyhermes.config import get_config

__all__ = [
    "DEFERRED_RULES",
    "RULE_MEDIA",
    "SOURCES",
    "UNSUPPORTED_DECLARATIONS",
    "Finding",
    "RegionSize",
    "Severity",
    "SizeReport",
    "errors",
    "format_findings",
    "layout_findings",
    "lint_document",
    "lint_email",
    "lint_html",
    "render_for_check",
    "rules_for",
    "size_report",
]

#: Where each rule's claim about a mail client comes from. Prose that cannot be
#: traced is a preference wearing a rule's clothes.
SOURCES: dict[str, str] = {
    "img-width-attr": (
        "Outlook's Word rendering engine ignores CSS max-width, so a display "
        "width must travel as the HTML attribute. This repo already builds on "
        "that (pyhermes/builder/images.py's `width`, and CLAUDE.md's images "
        "section); the rule checks it survives into the markup."
    ),
    "img-alt": (
        "Alt text is what the reader sees whenever images are blocked, which "
        "for Outlook desktop is the default state (pyhermes/builder/images.py). "
        "EmailImage requires it at construction; this checks the render. The "
        'exception is a decorative image, which takes alt="" so a screen '
        "reader skips it — indistinguishable in the render from a forgotten "
        'alt, so it must say so with role="presentation", the same annotation '
        "table-role asks of a layout table. W3C WAI, Decorative Images. "
        "w3.org/WAI/tutorials/images/decorative"
    ),
    "table-role": (
        "A table with no role is exposed to assistive technology as a data "
        "table, so a screen reader announces its dimensions before any "
        "content. Table-based layout is mandatory in email — this repo's own "
        "outlook-unsupported-css rule denies the alternatives — so the markup "
        'is right and only the annotation is missing. role="presentation" '
        "removes the table semantics without changing a pixel; the mirror "
        "case is a real data table, which must NOT carry it. W3C WAI, "
        "Tables Tutorial: Layout Tables. w3.org/WAI/tutorials/tables/layout"
    ),
    "vml-fill-empty-src": (
        "An empty src is not inert: #78 established that url('') may be "
        "resolved against the current document and issue a spurious request, "
        "and gated the CSS background-image on that. The VML half two lines "
        "above was missed, so a banner with no backdrop shipped "
        'src="" to Outlook for the life of the package (#150). Reached by '
        "inspecting conditional-comment text, the exception no-external-css "
        "already makes: markup inside [if mso] is otherwise not linted, "
        "because judging VML by standard-HTML rules fires on markup that is "
        "correct precisely because it is non-standard."
    ),
    "vml-fill-frame-without-src": (
        'type="frame" tells the Word engine the fill *is* an image. With no '
        "src to frame it does not fall back to color/opacity -- it paints a "
        "broken-image placeholder across the whole shape, which on the "
        "masthead means no band, no scrim, and dark title text on white. "
        "Verified by rendering both forms through the Word engine, which is "
        "what Outlook Classic uses for HTML mail; gating src alone was the "
        "first attempt at #150 and this is the defect it left behind. "
        "Microsoft, VML Fill Element: the type attribute selects the fill "
        "style, and frame is the one that requires a source image."
    ),
    "no-external-css": (
        "Microsoft, on Outlook Classic: styles that are not fully inline "
        "'may be stripped or misapplied'. learn.microsoft.com/troubleshoot/"
        "dynamics-365/customer-insights/journeys/email/"
        "email-troubleshoot-rendering"
    ),
    "outlook-unsupported-css": (
        "Outlook Classic renders through a Word-based HTML processing engine "
        "with no support for modern layout CSS; Microsoft's guidance is to "
        "build layout from <table> structures. learn.microsoft.com/"
        "troubleshoot/dynamics-365/customer-insights/journeys/email/"
        "email-troubleshoot-rendering"
    ),
    "outlook-line-height": (
        "Microsoft, on Outlook Classic: 'numeric line-height values, such as "
        "line-height: 1.5, aren't supported […] use percentage values for "
        "line height'. learn.microsoft.com/troubleshoot/dynamics-365/"
        "customer-insights/journeys/email/email-troubleshoot-rendering"
        "#outlook-classic"
    ),
    "outlook-transparent-background": (
        "Microsoft, on Outlook Classic: 'background colors that use "
        "transparency' are treated 'as background images, so they're subject "
        "to the same rendering limitations […] use a fully opaque color'. "
        "Same source. The masthead scrim satisfies this by being hidden from "
        "Outlook entirely, which already draws it through VML."
    ),
    "empty-url": (
        "An empty url() is not inert: a client may resolve it against the "
        "current document and issue a spurious request for the message body "
        "itself. Templates guard the declaration on the value instead. The "
        "same rule covers an empty `img src`, which adds a visible "
        "broken-image icon to that cost — the form the banner shipped for "
        "nine of fourteen fixtures until a real report was built against it."
    ),
    "page-size-declared": (
        "A paged document that declares no @page size is laid out on the "
        "engine's default page, silently: WeasyPrint falls back to A4, so a "
        "Letter document renders 8mm too tall and nothing says so. CSS Paged "
        "Media Level 3, section 3.1 (the page size property). The skeleton "
        "takes it from the medium's PageFormat, so an absent one means the "
        "page never reached the render."
    ),
    "paged-table-width": (
        "A print engine honours the CSS width property and does not map the "
        "`width` HTML attribute on a table, where a browser does. The "
        "component templates carry widths as attributes because Outlook's "
        "Word engine reads nothing else, so a paged skeleton that does not "
        "map them back renders every table shrink-wrapped to its content -- "
        "measured at 188px inside a 794px page in #164, correct markup and a "
        "different document."
    ),
    "print-marks": (
        "A print house trims a sheet by its crop marks and needs the ground "
        "colours to run past the trim, or a cut that lands a hair outside it "
        "leaves a white sliver. CSS Paged Media Level 3, section 7.2 (`bleed`) "
        "and 7.3 (`marks`), which WeasyPrint implements (#188). The brochure "
        "skeleton declares both from the fold, so an absent one means the fold "
        "never reached the render."
    ),
    "rgb-only": (
        "WeasyPrint writes RGB PDFs with no ICC profile and no PDF/X "
        "conformance, and pyHermes converts no colour: separation for a press "
        "is the print house's step (#172's recorded non-goal). Stated once per "
        "brochure so it is never mistaken for an oversight, and never an error, "
        "because no edit to the document can change it."
    ),
    "table-structure": (
        "A print engine repeats a table's header on every sheet the table "
        "crosses only when the header row sits in a `thead`; CSS 2.1, section "
        "17.2 (table-header-group), which WeasyPrint implements. The shared "
        "data table emitted a bare header row until #173, so a holdings table "
        "lost its column headers after sheet one. No golden or browser "
        "screenshot could see it, because an email has no sheets. This rule "
        "reads the markup, so it holds without a PDF backend installed."
    ),
    "table-header-tier": (
        "A span is admitted in a table's header tier and nowhere else (#223). "
        "A merged body cell splits badly across sheets and has no honest "
        "plain-text projection (data-table.md). A spanning header cell names "
        'its columns only with scope="colgroup" (W3C WAI, Tables Tutorial: '
        "Multi-level Headers, w3.org/WAI/tutorials/tables/multi-level), and a "
        "tier whose spans miscount the columns misplaces every head under it. "
        "Outlook's handling of colspan is unverified in this repo; this rule "
        "keeps the span where a render has been reasoned about."
    ),
    "slide-overflow": (
        "A slide is one sheet with a fixed body (#296), so copy that does not fit "
        "is clipped at the footer band rather than carried onto a second sheet, "
        "and the clip is silent in the PDF. The brochure's panels clip the same "
        "way (#186). This lays the deck out through the PDF exporter and reads "
        "back where each slide's closing sentinel landed; without the [pdf] "
        "extra it says it could not measure rather than passing."
    ),
    "size-budget": (
        "Gmail clips a message above ~102 KB behind a 'View entire message' "
        "link. pyhermes/config.Config.size_limit_kb; Email._validate_size enforces "
        "the total, this attributes it."
    ),
}

#: Rules that are real and sourced but do **not** ship, because the current
#: templates violate them and the fix moves surfaces several epics contend on.
#: Filed instead, so the omission is a recorded decision rather than an
#: oversight, and so whoever fixes the finding knows a rule is waiting.
#:
#: **Empty, and that is the point.** The three entries this held — unitless
#: ``line-height``, the masthead's ``rgba()`` scrim, and ``background-image:
#: url('')`` — were #78, and all three are fixed, so all three rules moved
#: into ``SOURCES`` and now report. The mechanism stays because the next
#: sourced finding the templates violate should be recorded here rather than
#: shipped red or silently dropped.
DEFERRED_RULES: dict[str, str] = {}

#: Inline-style declarations Outlook's Word engine cannot lay out. Deliberately
#: tiny and deliberately absent of `max-width`: the repo pairs `max-width` with
#: a `width=` attribute on purpose, so denying it would fire on correct code —
#: and a noisy rule gets switched off, which is worse than no rule. The
#: `img-width-attr` rule covers the case that actually matters.
UNSUPPORTED_DECLARATIONS: dict[str, frozenset[str]] = {
    "display": frozenset({"flex", "inline-flex", "grid", "inline-grid"}),
    "position": frozenset({"absolute", "fixed"}),
}


@dataclass
class _OpenTable:
    """One ``table`` the parser is currently inside.

    Held on a stack because the discriminator — does this table contain a
    header cell? — is only known once the closing tag is reached, and because
    a ``th`` belongs to the innermost open table. That nesting is not
    hypothetical: the gallery's one real data table renders inside two layout
    tables, and a flat flag would mark all three as data.
    """

    where: str
    role: str
    has_header: bool = False
    has_thead: bool = False
    in_thead: bool = False
    row_widths: list[int] = field(default_factory=list)
    head_rows: int = 0


#: Which media each rule applies to, by ``Medium.name``.
#:
#: **Every rule in SOURCES needs an entry, and a test enforces it**, so a rule
#: added later cannot quietly apply everywhere or nowhere. The question each
#: entry answers is not "could this fire here" but "is the claim behind it
#: true here" — a rule about Outlook's Word engine says nothing about a sheet
#: of paper, and running it there produces findings a reader has to learn to
#: ignore, which is how a lint pass dies.
#:
#: The paged column was **measured, not predicted** (#162): a realistic paged
#: render is clean against all ten email rules, and exactly one of them —
#: ``size-budget``, which is Gmail's 102 KB — is wrong there rather than
#: merely quiet. Nothing clips a PDF.
RULE_MEDIA: dict[str, frozenset[str]] = {
    # Accessibility, not client compatibility: a screen reader reads a PDF
    # too, and neither rule mentions a mail client in its source.
    "img-alt": frozenset({"email", "document", "brochure", "deck", "html"}),
    "table-role": frozenset({"email", "document", "brochure", "deck", "html"}),
    # A URL that cannot resolve is a defect in any medium, and #164 made it a
    # harder one for paged output than for email: the PDF exporter refuses
    # every URL it cannot serve from the manifest, so an empty or external
    # one stops the render rather than merely wasting a request.
    "empty-url": frozenset({"email", "document", "brochure", "deck", "html"}),
    "no-external-css": frozenset({"email", "document", "brochure", "deck", "html"}),
    # Outlook's Word engine, and the markup written for it. None of this is
    # true of a print engine -- #164 measured the reverse for the width
    # attribute, which a print engine ignores where Outlook needs it.
    "img-width-attr": frozenset({"email"}),
    "outlook-unsupported-css": frozenset({"email"}),
    "outlook-line-height": frozenset({"email"}),
    "outlook-transparent-background": frozenset({"email"}),
    "vml-fill-empty-src": frozenset({"email"}),
    "vml-fill-frame-without-src": frozenset({"email"}),
    # Gmail's clipping limit. The size *report* stays available everywhere --
    # knowing where the bytes went is useful for any document -- but the
    # threshold is a fact about one mail client.
    "size-budget": frozenset({"email"}),
    # Paged-only, and each comes from a defect a real PDF produced (#164, #173).
    # A brochure and a deck are laid out by the same engine, so each is as true of them.
    "page-size-declared": frozenset({"document", "brochure", "deck"}),
    "paged-table-width": frozenset({"document", "brochure", "deck"}),
    "table-structure": frozenset({"document", "brochure", "deck"}),
    # Structure and accessibility, true of the markup in every medium (#223).
    "table-header-tier": frozenset({"email", "document", "brochure", "deck", "html"}),
    # A folded sheet going to a press: true of nothing else this package builds.
    "print-marks": frozenset({"brochure"}),
    "rgb-only": frozenset({"brochure"}),
    # One slide is one sheet, so overflow is clipped copy (#297). A deck is
    # projected or sent, never pressed, so the two print rules stay off it.
    "slide-overflow": frozenset({"deck"}),
}


def rules_for(medium: str) -> frozenset[str]:
    """Every rule that applies to the medium named ``medium``."""
    return frozenset(rule for rule, media in RULE_MEDIA.items() if medium in media)


#: Claims about Outlook, suppressed inside ``<!--[if !mso]><!-->``; named, not prefix-matched.
#: `qa-harness.md` records why ``img-width-attr`` keeps firing there.
_OUTLOOK_ONLY_RULES = frozenset(
    {"outlook-line-height", "outlook-transparent-background", "outlook-unsupported-css"}
)

#: A ``line-height`` with no unit — the form Outlook Classic ignores. ``0`` is
#: excluded deliberately: it is the accent rule's spacer cell collapsing a row
#: to nothing, it is unambiguous without a unit, and ``0%`` would say the same
#: thing less clearly. ``normal`` and the CSS-wide keywords are not numbers and
#: never match.
_UNITLESS_LINE_HEIGHT = re.compile(r"0*\.\d+|[1-9]\d*(?:\.\d+)?")

#: A colour carrying an alpha channel. Outlook treats any of these as a
#: background image rather than a fill.
_TRANSPARENT_COLOR = re.compile(r"\b(?:rgba|hsla)\s*\(|#[0-9a-f]{8}\b")

#: ``url()`` with nothing in it, quoted or not.
_EMPTY_URL = re.compile(r"""url\(\s*(?:''|""|)\s*\)""")

#: A ``v:fill`` carrying an empty ``src``. Matched over conditional-comment
#: text, where the VML lives; see ``_check_vml_fill``.
_VML_EMPTY_SRC = re.compile(r"""<v:fill\b[^>]*\bsrc\s*=\s*(?:''|"")""", re.IGNORECASE)

#: Any ``v:fill`` tag, so the frame-without-a-source case can be judged on
#: the tag's whole attribute set rather than by a single lookahead.
_VML_FILL_TAG = re.compile(r"<v:fill\b[^>]*>", re.IGNORECASE)
_VML_TYPE_FRAME = re.compile(r"""\btype\s*=\s*['"]?frame\b""", re.IGNORECASE)
_VML_HAS_SRC = re.compile(r"\bsrc\s*=", re.IGNORECASE)

#: How many regions the size breakdown names. Enough to point at the culprit,
#: short enough to read in a failure message.
_HEAVIEST_REGIONS = 5


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    #: A fact the reader should know that no edit can change. It never fails
    #: a build, and says so once per document rather than per element.
    INFO = "info"


@dataclass(frozen=True)
class Finding:
    """One portability problem, located precisely enough to act on."""

    rule_id: str
    severity: Severity
    location: str
    message: str

    @property
    def source(self) -> str:
        """Where this rule's claim about a mail client comes from."""
        return SOURCES.get(self.rule_id, "")

    def __str__(self) -> str:
        return f"{self.severity.value}: {self.rule_id} at {self.location} — {self.message}"


# ──────────────────────────────────────────────────────────────────────
# The parser
# ──────────────────────────────────────────────────────────────────────


class _Linter(HTMLParser):
    """
    Walks the document once, collecting findings.

    Markup inside ``<!--[if mso]>`` conditional comments is deliberately not
    linted. ``HTMLParser`` hands a conditional comment over as comment text
    rather than tags, and that is the behaviour we want: the block exists to
    carry Outlook-only VML (``v:roundrect`` and friends), so judging it by the
    standard-HTML rules would fire on markup that is correct *because* it is
    non-standard. ``no-external-css`` still inspects comment text, since an
    ``@import`` hidden in a conditional is a real problem.

    The mirror case is ``<!--[if !mso]><!-->``, which is *downlevel-revealed*:
    the comment ends immediately, so the markup after it is real HTML to every
    parser including this one — which is exactly right, since every client but
    Outlook renders it. What that markup cannot be is an *Outlook* problem, so
    the rules in ``_OUTLOOK_ONLY_RULES`` are suppressed between such a
    conditional and its ``<![endif]``. Everything else still applies: a
    missing ``alt`` is a missing ``alt`` wherever it sits.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.findings: list[Finding] = []
        self._in_style = False
        self._hidden_from_outlook = False
        self._tables: list[_OpenTable] = []

    # -- helpers ------------------------------------------------------

    def _where(self, detail: str = "") -> str:
        line, column = self.getpos()
        return f"line {line}, col {column}{f' ({detail})' if detail else ''}"

    def _report(self, rule_id: str, severity: Severity, message: str, detail: str = "") -> None:
        if self._hidden_from_outlook and rule_id in _OUTLOOK_ONLY_RULES:
            return
        self.findings.append(
            Finding(
                rule_id=rule_id,
                severity=severity,
                location=self._where(detail),
                message=message,
            )
        )

    # -- handlers -----------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name.lower(): (value or "") for name, value in attrs}

        if tag == "style":
            self._in_style = True
        if tag == "table":
            self._tables.append(
                _OpenTable(where=self._where(), role=attributes.get("role", "").strip().lower())
            )
        if tag in ("th", "td") and self._tables:
            # A header cell belongs to the *innermost* open table, which is
            # what makes a data table nested inside layout tables classify
            # correctly rather than marking its ancestors as data too.
            if tag == "th":
                self._tables[-1].has_header = True
            self._check_span(tag, attributes)
        if tag == "thead" and self._tables:
            self._tables[-1].has_thead = True
            self._tables[-1].in_thead = True
        if tag == "tr" and self._tables:
            self._tables[-1].row_widths.append(0)
            self._tables[-1].head_rows += self._tables[-1].in_thead
        if tag == "img":
            self._check_image(attributes)
        if tag == "link":
            self._check_link(attributes)
        if "style" in attributes:
            self._check_inline_style(tag, attributes["style"])

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag == "style":
            self._in_style = False

    def handle_endtag(self, tag: str) -> None:
        if tag == "style":
            self._in_style = False
        if tag == "thead" and self._tables:
            self._tables[-1].in_thead = False
        if tag == "table" and self._tables:
            table = self._tables.pop()
            self._check_table(table)
            self._check_tier(table)

    def handle_data(self, data: str) -> None:
        if self._in_style:
            self._check_at_import(data)

    def handle_comment(self, data: str) -> None:
        # A downlevel-revealed conditional opens as `[if !mso]><!` and closes
        # as `<![endif]`; what sits between is markup Outlook never sees.
        stripped = data.strip()
        if stripped.startswith("[if !mso]"):
            self._hidden_from_outlook = True
        elif stripped == "<![endif]":
            self._hidden_from_outlook = False

        # Conditional comments carry real CSS for Outlook; an @import there
        # would be just as external as one in a <style> block.
        self._check_at_import(data)
        self._check_vml_fill(data)

    # -- rules --------------------------------------------------------

    def _check_vml_fill(self, data: str) -> None:
        """
        A ``v:fill`` may not carry an empty ``src``.

        The one VML rule, and it reaches into comment text rather than tags
        because ``[if mso]`` markup never reaches the tag handlers. Narrow on
        purpose: this is not a foothold for linting VML generally, which the
        class docstring argues against. It exists because the identical
        defect in the CSS half was worth fixing and this half was missed.
        """
        for match in _VML_EMPTY_SRC.finditer(data):
            self._report(
                "vml-fill-empty-src",
                Severity.ERROR,
                "<v:fill> has an empty src; an empty URL may resolve against the "
                "current document and issue a spurious request. Gate the attribute "
                "on the value, as the CSS background-image is gated.",
                match.group(0)[:60],
            )

        for match in _VML_FILL_TAG.finditer(data):
            tag = match.group(0)
            if _VML_TYPE_FRAME.search(tag) and not _VML_HAS_SRC.search(tag):
                self._report(
                    "vml-fill-frame-without-src",
                    Severity.ERROR,
                    '<v:fill> declares type="frame" with no src. The Word engine '
                    "then paints a broken-image placeholder over the shape rather "
                    "than falling back to color/opacity. Gate type with the src.",
                    tag[:60],
                )

    def _check_span(self, tag: str, attributes: dict[str, str]) -> None:
        """A span sits in the header tier only, and a spanning head says so."""
        table = self._tables[-1]
        span = int(attributes["colspan"]) if attributes.get("colspan", "").isdigit() else 1
        if table.row_widths:
            table.row_widths[-1] += span
        if "colspan" not in attributes:
            return
        if not table.in_thead:
            self._report(
                "table-header-tier",
                Severity.ERROR,
                f"<{tag} colspan> outside a <thead>; a merged body cell splits badly "
                "across sheets and has no plain-text projection.",
            )
        elif span > 1 and attributes.get("scope", "") != "colgroup":
            self._report(
                "table-header-tier",
                Severity.ERROR,
                '<th colspan> without scope="colgroup", so its columns are not associated with it.',
            )

    def _check_tier(self, table: _OpenTable) -> None:
        """Every header row covers the same columns as the body."""
        widths = table.row_widths
        if table.head_rows > 1 and len(set(widths)) > 1:
            self.findings.append(
                Finding(
                    rule_id="table-header-tier",
                    severity=Severity.ERROR,
                    location=table.where,
                    message=(
                        f"the header tier covers {widths[: table.head_rows]} columns per row "
                        f"but the table's rows are {sorted(set(widths))} wide; every head "
                        "sits over the wrong columns."
                    ),
                )
            )

    def _check_table(self, table: _OpenTable) -> None:
        """
        A layout table must be presentational; a data table must not be.

        Both directions, because only checking the first would be satisfied
        by marking *every* table — which silently strips the semantics from
        the one table a screen reader should actually navigate.

        ``th`` is the discriminator. It is what distinguishes the two kinds
        in this codebase exactly today, and it is the same signal a screen
        reader itself uses: a table whose cells are all ``td`` announces
        dimensions and nothing else, which is precisely the noise the
        presentational role removes.
        """
        presentational = table.role in ("presentation", "none")

        if table.has_header and presentational:
            self.findings.append(
                Finding(
                    rule_id="table-role",
                    severity=Severity.ERROR,
                    location=table.where,
                    message=(
                        f'<table role="{table.role}"> contains <th> header cells, so it is '
                        "a data table; the presentational role strips the semantics a "
                        "screen reader needs to associate each cell with its column."
                    ),
                )
            )
        elif table.has_header and not table.has_thead:
            # Paged only, by RULE_MEDIA: the header repeats per sheet only
            # from a thead, and an email has no sheets.
            self.findings.append(
                Finding(
                    rule_id="table-structure",
                    severity=Severity.ERROR,
                    location=table.where,
                    message=(
                        "data <table> has no <thead>, so a print engine shows its "
                        "column headers on the first sheet only. Put the header row "
                        "in a <thead> and the data rows in a <tbody>."
                    ),
                )
            )
        if not table.has_header and not presentational:
            self.findings.append(
                Finding(
                    rule_id="table-role",
                    severity=Severity.ERROR,
                    location=table.where,
                    message=(
                        "<table> has no header cells and no role, so assistive technology "
                        "announces this layout scaffolding as a data table. Add "
                        'role="presentation".'
                    ),
                )
            )

    def _check_image(self, attributes: dict[str, str]) -> None:
        source = attributes.get("src", "")[:60]

        if not source.strip():
            self._report(
                "empty-url",
                Severity.ERROR,
                "<img> has an empty or missing src; it renders as a broken-image "
                "icon in every client, and the empty value may resolve against "
                "the current document. Guard the tag on the value.",
                'src=""',
            )

        width = attributes.get("width", "").strip()
        if not width:
            self._report(
                "img-width-attr",
                Severity.ERROR,
                "<img> has no width attribute; Outlook's Word engine ignores CSS "
                "max-width, so the display width must be an HTML attribute.",
                source,
            )
        elif not width.isdigit():
            self._report(
                "img-width-attr",
                Severity.ERROR,
                f'<img width="{width}" is not an integer of pixels; Outlook '
                "reads the attribute, not a CSS length.",
                source,
            )

        decorative = attributes.get("role", "").strip().lower() == "presentation"
        alt = attributes.get("alt", "").strip()
        if not alt and not decorative:
            self._report(
                "img-alt",
                Severity.ERROR,
                "<img> has empty or missing alt text; with images blocked — "
                "Outlook desktop's default — this is all the reader gets. If the "
                'image is decorative, say so with role="presentation".',
                source,
            )
        elif alt and decorative:
            self._report(
                "img-alt",
                Severity.ERROR,
                '<img role="presentation"> carries alt text; the annotation says a '
                "screen reader should skip it and the text says it has something "
                "to say. Drop one.",
                source,
            )

    def _check_link(self, attributes: dict[str, str]) -> None:
        if "stylesheet" in attributes.get("rel", "").lower():
            self._report(
                "no-external-css",
                Severity.ERROR,
                "<link rel=stylesheet> will not be fetched; email CSS must be inline.",
                attributes.get("href", "")[:60],
            )

    def _check_at_import(self, css: str) -> None:
        if "@import" in css:
            self._report(
                "no-external-css",
                Severity.ERROR,
                "@import will not be fetched; email CSS must be inline.",
            )

    def _check_inline_style(self, tag: str, style: str) -> None:
        for prop, value in _declarations(style):
            unsupported = UNSUPPORTED_DECLARATIONS.get(prop)
            if unsupported and value in unsupported:
                self._report(
                    "outlook-unsupported-css",
                    Severity.ERROR,
                    f'<{tag} style="{prop}:{value}"> — Outlook\'s Word engine '
                    "cannot lay this out; build layout from tables.",
                    f"{prop}:{value}",
                )
            if prop == "line-height" and _UNITLESS_LINE_HEIGHT.fullmatch(value):
                self._report(
                    "outlook-line-height",
                    Severity.ERROR,
                    f'<{tag} style="line-height:{value}"> — Outlook\'s Word '
                    f"engine ignores a unitless line-height; use "
                    f"{float(value) * 100:.10g}% instead.",
                    f"line-height:{value}",
                )
            if prop.endswith("background-color") and _TRANSPARENT_COLOR.search(value):
                self._report(
                    "outlook-transparent-background",
                    Severity.ERROR,
                    f'<{tag} style="{prop}:{value}"> — Outlook demotes a '
                    "transparent background-color to a background image; use "
                    "an opaque colour, or keep the declaration away from "
                    "Outlook.",
                    f"{prop}:{value}",
                )
            if _EMPTY_URL.search(value):
                self._report(
                    "empty-url",
                    Severity.ERROR,
                    f'<{tag} style="{prop}:{value}"> — an empty url() may '
                    "resolve against the current document and fetch the "
                    "message body; guard the declaration on the value.",
                    f"{prop}:{value}",
                )


def _declarations(style: str) -> list[tuple[str, str]]:
    """Split an inline style into ``(property, value)``, lowercased."""
    parsed = []
    for declaration in style.split(";"):
        prop, separator, value = declaration.partition(":")
        if separator:
            parsed.append((prop.strip().lower(), value.strip().lower()))
    return parsed


# ──────────────────────────────────────────────────────────────────────
# The size breakdown
# ──────────────────────────────────────────────────────────────────────

#: A section marker is a short comment carrying an actual name. The templates
#: also use decorative rules (``<!-- ══════ -->``); those are not sections, and
#: treating them as such made the heaviest "region" a row of box-drawing
#: characters — a breakdown that names nothing is no better than the total it
#: was meant to explain. Requiring a letter is what tells the two apart.
_MARKER = re.compile(r"<!--\s*(?!\[if)(?=[^>]*[A-Za-z])([^>]{1,60}?)\s*-->")


@dataclass(frozen=True)
class RegionSize:
    """Bytes attributable to one section-marker region."""

    name: str
    bytes: int

    @property
    def kb(self) -> float:
        return self.bytes / 1024


@dataclass(frozen=True)
class SizeReport:
    """Where the 102 KB budget went."""

    total_bytes: int
    regions: list[RegionSize] = field(default_factory=list)

    @property
    def total_kb(self) -> float:
        return self.total_bytes / 1024

    def heaviest(self, count: int = _HEAVIEST_REGIONS) -> list[RegionSize]:
        return sorted(self.regions, key=lambda region: region.bytes, reverse=True)[:count]

    def summary(self) -> str:
        lines = [f"{self.total_kb:.1f} KB total; heaviest regions:"]
        lines += [f"  {region.kb:7.1f} KB  {region.name}" for region in self.heaviest()]
        return "\n".join(lines)


def size_report(html: str, sections: list[tuple[str, str]] | None = None) -> SizeReport:
    """
    Attribute the rendered bytes to the section markers that delimit them.

    ``Email._validate_size`` reports a total and stops there, which tells you
    an email is too big without telling you what to cut. This says which
    region spent it. It *extends* that check rather than reshaping it — the
    static method and its message text are asserted by existing tests.

    Regions run from one ``<!-- marker -->`` to the next; bytes before the
    first marker are attributed to ``"(document head)"``. ``<!--[if ...]>``
    conditional comments are not markers.

    ``sections`` is ``(label, markup)`` per body section, as
    :meth:`Document.rendered_sections` gives it. Each one found in ``html``
    becomes its own region, and its bytes leave the marker region around it,
    so the regions still sum to the total. One not found is left where it was.
    """
    spans = _section_spans(html, sections or [])
    markers = [m for m in _MARKER.finditer(html) if not _inside(m.start(), spans)]
    bounds = [(m.start(), m[1]) for m in markers]
    if markers and markers[0].start():
        bounds.insert(0, (0, "(document head)"))
    elif spans and not markers:
        # A paged document carries no markers; what its sections leave is one region.
        bounds = [(0, "(rest of document)")]
    regions: list[RegionSize] = []
    if bounds:
        for index, (start, name) in enumerate(bounds):
            end = bounds[index + 1][0] if index + 1 < len(bounds) else len(html)
            inner = sum(_size(html[a:b]) for a, b, _ in spans if start <= a and b <= end)
            regions.append(RegionSize(name, _size(html[start:end]) - inner))
    regions += [RegionSize(label, _size(html[a:b])) for a, b, label in spans]
    return SizeReport(total_bytes=_size(html), regions=regions)


def _size(text: str) -> int:
    return len(text.encode("utf-8"))


def _section_spans(html: str, sections: list[tuple[str, str]]) -> list[tuple[int, int, str]]:
    """Where each section's markup sits in ``html``, searched in order."""
    spans, cursor = [], 0
    for label, markup in sections:
        start = html.find(markup, cursor) if markup else -1
        if start >= 0:
            cursor = start + len(markup)
            spans.append((start, cursor, label))
    return spans


def _inside(offset: int, spans: list[tuple[int, int, str]]) -> bool:
    return any(start <= offset < end for start, end, _ in spans)


def _budget_findings(html: str, sections: list[tuple[str, str]] | None = None) -> list[Finding]:
    """Warn or fail on the size budget, naming where the bytes went."""
    config = get_config()
    report = size_report(html, sections)
    if report.total_kb > config.size_limit_kb:
        severity, threshold = Severity.ERROR, config.size_limit_kb
    elif report.total_kb > config.size_warn_kb:
        severity, threshold = Severity.WARNING, config.size_warn_kb
    else:
        return []
    return [
        Finding(
            rule_id="size-budget",
            severity=severity,
            location="whole document",
            message=f"over {threshold} KB. {report.summary()}",
        )
    ]


#: A ``@page`` rule declaring a size. Matched over the whole document rather
#: than parsed: it lives in a ``style`` element, which HTMLParser hands over
#: as text.
_PAGE_SIZE = re.compile(r"@page\b[^{]*\{[^}]*\bsize\s*:", re.IGNORECASE | re.DOTALL)

#: A table carrying a percentage width as an attribute, and the CSS rule that
#: maps it back for an engine that ignores attributes.
_TABLE_PCT_ATTR = re.compile(r"""<table\b[^>]*\bwidth\s*=\s*['"]?100%""", re.IGNORECASE)
_TABLE_PCT_RULE = re.compile(r"""table\s*\[\s*width\s*=\s*['"]?100%['"]?\s*\]""", re.IGNORECASE)


def _paged_findings(html: str) -> list[Finding]:
    """
    The two checks that are about a *page* rather than about a client.

    Both are document-level rather than per-element, because both are about
    something the skeleton must declare once. Both come from a defect a real
    PDF produced in #164 rather than from reading a specification and
    imagining one.
    """
    findings = []
    if not _PAGE_SIZE.search(html):
        findings.append(
            Finding(
                rule_id="page-size-declared",
                severity=Severity.ERROR,
                location="the document's stylesheet",
                message=(
                    "no @page rule declares a size, so the engine lays this out on "
                    "its own default page and says nothing"
                ),
            )
        )
    if _TABLE_PCT_ATTR.search(html) and not _TABLE_PCT_RULE.search(html):
        findings.append(
            Finding(
                rule_id="paged-table-width",
                severity=Severity.ERROR,
                location="the document's stylesheet",
                message=(
                    'a table carries width="100%" as an attribute and nothing maps it '
                    "to CSS, so a print engine shrink-wraps it to its content"
                ),
            )
        )
    return findings


#: A ``@page`` rule declaring both a bleed and marks.
_PAGE_BLEED = re.compile(r"@page\b[^{]*\{[^}]*\bbleed\s*:", re.IGNORECASE | re.DOTALL)
_PAGE_MARKS = re.compile(r"@page\b[^{]*\{[^}]*\bmarks\s*:\s*(?!none)", re.IGNORECASE | re.DOTALL)


def _print_findings(html: str) -> list[Finding]:
    """The two checks about a sheet going to a press, both document-level."""
    findings = []
    if not (_PAGE_BLEED.search(html) and _PAGE_MARKS.search(html)):
        findings.append(
            Finding(
                rule_id="print-marks",
                severity=Severity.ERROR,
                location="the document's stylesheet",
                message=(
                    "no @page rule declares both a bleed and crop marks, so a print "
                    "house has nothing to trim by and no ground past the trim"
                ),
            )
        )
    findings.append(
        Finding(
            rule_id="rgb-only",
            severity=Severity.INFO,
            location="whole document",
            message=(
                "this PDF is RGB, with no colour profile; converting it for a press "
                "is the print house's step"
            ),
        )
    )
    return findings


# ──────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────


def lint_html(
    html: str, medium: str = "email", sections: list[tuple[str, str]] | None = None
) -> list[Finding]:
    """
    Lint rendered HTML for the medium named ``medium``.

    Takes a string rather than a document so it works on markup from anywhere
    — a saved file, a paste, another builder — and a medium *name* rather than
    a ``Medium`` for the same reason: this module imports nothing from
    ``pyhermes`` beyond what it already needs, and a name is what the rule table
    is keyed by.

    Defaults to ``"email"`` so every pre-#165 caller keeps its exact
    behaviour; :func:`lint_document` is what reads the medium off a document.
    ``sections`` names the body sections in the size breakdown; see
    :func:`size_report`.
    """
    linter = _Linter()
    linter.feed(html)
    linter.close()
    applicable = rules_for(medium)
    found = (
        linter.findings
        + _budget_findings(html, sections)
        + _paged_findings(html)
        + _print_findings(html)
    )
    return [finding for finding in found if finding.rule_id in applicable]


def lint_document(document: Document) -> list[Finding]:
    """
    Lint a built document under the rules its own medium answers to.

    This is the entry point that makes the rule table mean anything: an
    email is judged by the ten rules about mail clients, and a paged document
    by the six that are true of a page. A document over its size limit is
    still linted: the refused markup is what the breakdown is for. The rules
    only a layout can answer follow, from :func:`layout_findings`.
    """
    html = render_for_check(document)
    return lint_html(html, document.medium.name, document.rendered_sections()) + layout_findings(
        document
    )


def layout_findings(document: Document) -> list[Finding]:
    """
    The findings only the print engine can answer: today, a slide whose copy overflows (#297).

    Each overflowing slide is an error. Without the ``[pdf]`` extra it is one
    warning saying the deck was not measured, so a check never passes a
    deck it could not see. Empty for any medium the rule does not apply to.
    """
    from pyhermes.deck import Deck, overflowing_slides
    from pyhermes.pdf import BackendMissingError

    if "slide-overflow" not in rules_for(document.medium.name) or not isinstance(document, Deck):
        return []
    try:
        overflowing = overflowing_slides(document)
    except BackendMissingError:
        return [
            Finding(
                rule_id="slide-overflow",
                severity=Severity.WARNING,
                location="whole deck",
                message=(
                    "not measured: finding a slide that overflows needs a layout, "
                    'and the PDF backend is missing. Install "pyhermes[pdf]".'
                ),
            )
        ]
    return [
        Finding(
            rule_id="slide-overflow",
            severity=Severity.ERROR,
            location=name,
            message="its copy runs past the footer band and is clipped; trim it or split the slide",
        )
        for name in overflowing
    ]


def render_for_check(document: Document) -> str:
    """``document.render()``, or the markup a size constraint refused, so it can be measured."""
    try:
        return document.render()
    except SizeError as exc:
        if exc.html is None:
            raise
        return exc.html


def lint_email(email: Email) -> list[Finding]:
    """Lint a built email. Kept as the name every existing caller uses."""
    return lint_document(email)


def errors(findings: list[Finding]) -> list[Finding]:
    """The findings that should fail a build."""
    return [finding for finding in findings if finding.severity is Severity.ERROR]


def format_findings(findings: list[Finding]) -> str:
    """A report a human can act on, sources included."""
    if not findings:
        return "No findings."
    lines = []
    for finding in findings:
        lines.append(str(finding))
        if finding.source:
            lines.append(f"    source: {finding.source}")
    return "\n".join(lines)


__all__ = [
    "DEFERRED_RULES",
    "RULE_MEDIA",
    "SOURCES",
    "UNSUPPORTED_DECLARATIONS",
    "Finding",
    "RegionSize",
    "Severity",
    "SizeReport",
    "errors",
    "format_findings",
    "layout_findings",
    "lint_document",
    "lint_email",
    "lint_html",
    "render_for_check",
    "rules_for",
    "size_report",
]
