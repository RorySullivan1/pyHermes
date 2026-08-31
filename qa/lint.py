"""
Email-client lint pass (#60): portability checks over rendered HTML.

The constraints that break emails were documented prose, not checks —
Outlook's Word engine ignores ``max-width`` so every ``img`` needs a
``width=`` attribute; ``alt`` was required at construction but nothing
asserted it survived into the markup. This turns those into findings::

    findings = lint_email(email)     # the rules, plus the size breakdown
    errors = [f for f in findings if f.severity is Severity.ERROR]

Every rule cites its source in ``SOURCES``; ``DEFERRED_RULES`` names any that
are real but not yet shipped. `.claude/rules/qa-harness.md` carries both.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from html.parser import HTMLParser

from svc.builder import Email
from svc.config import get_config

#: Where each rule's claim about a mail client comes from. Prose that cannot be
#: traced is a preference wearing a rule's clothes.
SOURCES: dict[str, str] = {
    "img-width-attr": (
        "Outlook's Word rendering engine ignores CSS max-width, so a display "
        "width must travel as the HTML attribute. This repo already builds on "
        "that (svc/builder/images.py's `width`, and CLAUDE.md's images "
        "section); the rule checks it survives into the markup."
    ),
    "img-alt": (
        "Alt text is what the reader sees whenever images are blocked, which "
        "for Outlook desktop is the default state (svc/builder/images.py). "
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
    "size-budget": (
        "Gmail clips a message above ~102 KB behind a 'View entire message' "
        "link. svc/config.Config.size_limit_kb; Email._validate_size enforces "
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


#: The rules that are claims about Outlook specifically. They are suppressed
#: inside a downlevel-revealed conditional (``<!--[if !mso]><!-->``), because
#: markup Outlook cannot see cannot be a problem for Outlook. Named rather
#: than matched on the ``outlook-`` prefix, so the suppression is a decision
#: rather than a naming coincidence — ``img-width-attr`` is motivated by
#: Outlook too, and deliberately keeps firing there: a width attribute is good
#: practice in every client.
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

#: How many regions the size breakdown names. Enough to point at the culprit,
#: short enough to read in a failure message.
_HEAVIEST_REGIONS = 5


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


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
        if tag == "table" and self._tables:
            self._check_table(self._tables.pop())

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
        elif not table.has_header and not presentational:
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


def size_report(html: str) -> SizeReport:
    """
    Attribute the rendered bytes to the section markers that delimit them.

    ``Email._validate_size`` reports a total and stops there, which tells you
    an email is too big without telling you what to cut. This says which
    region spent it. It *extends* that check rather than reshaping it — the
    static method and its message text are asserted by existing tests.

    Regions run from one ``<!-- marker -->`` to the next; bytes before the
    first marker are attributed to ``"(document head)"``. ``<!--[if ...]>``
    conditional comments are not markers.
    """
    markers = list(_MARKER.finditer(html))
    encoded_length = len(html.encode("utf-8"))
    if not markers:
        return SizeReport(total_bytes=encoded_length, regions=[])

    regions = []
    if markers[0].start():
        regions.append(
            RegionSize("(document head)", len(html[: markers[0].start()].encode("utf-8")))
        )
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(html)
        regions.append(RegionSize(marker[1], len(html[marker.start() : end].encode("utf-8"))))
    return SizeReport(total_bytes=encoded_length, regions=regions)


def _budget_findings(html: str) -> list[Finding]:
    """Warn or fail on the size budget, naming where the bytes went."""
    config = get_config()
    report = size_report(html)
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


# ──────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────


def lint_html(html: str) -> list[Finding]:
    """
    Lint rendered email HTML. The entry point #61's ``preview`` CLI reuses.

    Takes a string rather than an ``Email`` so it works on markup from
    anywhere — a saved file, a paste, another builder.
    """
    linter = _Linter()
    linter.feed(html)
    linter.close()
    return linter.findings + _budget_findings(html)


def lint_email(email: Email) -> list[Finding]:
    """Lint a built email. Convenience over ``lint_html(email.render())``."""
    return lint_html(email.render())


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
    "SOURCES",
    "UNSUPPORTED_DECLARATIONS",
    "Finding",
    "RegionSize",
    "Severity",
    "SizeReport",
    "errors",
    "format_findings",
    "lint_email",
    "lint_html",
    "size_report",
]
