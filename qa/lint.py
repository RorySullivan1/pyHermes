"""
Email-client lint pass (#60): portability checks over rendered HTML.

The constraints that actually break emails are documented prose, not checks.
Outlook's Word engine ignores ``max-width``, so every ``<img>`` needs a
``width=`` attribute — a rule :mod:`svc.builder.images` follows and nothing
verified end to end. ``alt`` is required at construction, but nothing asserted
it survived into the markup. This module turns those into findings.

Usage::

    from qa.lint import lint_html, lint_email

    findings = lint_email(email)                 # rules + the size breakdown
    errors = [f for f in findings if f.severity is Severity.ERROR]

Four commitments shape it:

**It parses, it does not grep.** The repo learned this the expensive way: a
``grep`` for ``Contact Us`` matched inside an HTML section-marker comment and
produced a confident, wrong answer. :class:`html.parser.HTMLParser` is stdlib,
so the check costs no dependency.

**It observes, it never patches.** Findings fail or warn; nothing rewrites
HTML. Epic #54's first principle.

**Every rule carries its source.** An unsourced rule does not ship — see
``SOURCES`` below. A rule asserting something about a mail client that nobody
can trace is indistinguishable from a rule asserting a preference.

**It lands green.** A linter that arrives red teaches everyone to ignore it, so
a rule whose finding cannot be fixed today is *filed and deferred*, never
downgraded into a permanent warning. See ``DEFERRED_RULES``.
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
        "EmailImage requires it at construction; this checks the render."
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
    "size-budget": (
        "Gmail clips a message above ~102 KB behind a 'View entire message' "
        "link. svc/config.Config.size_limit_kb; Email._validate_size enforces "
        "the total, this attributes it."
    ),
}

#: Rules that are real and sourced but do **not** ship, because the current
#: templates violate them and the fix moves surfaces several epics contend on.
#: Filed instead — see #78. Listed here so the omission is a recorded decision
#: rather than an oversight, and so whoever fixes the finding knows a rule is
#: waiting to be switched on.
DEFERRED_RULES: dict[str, str] = {
    "outlook-line-height": (
        "Outlook Classic does not support unitless line-height (e.g. 1.5); "
        "percentages are required. base.html and the component templates use "
        "unitless values in 107 places, so the rule cannot land green. #78."
    ),
    "outlook-transparent-background": (
        "Outlook Classic treats a background-color with transparency as a "
        "background image, inheriting VML's limitations. base.html's header "
        "scrim is rgba(20,30,44,0.65). #78."
    ),
    "empty-url": (
        "base.html emits background-image:url('') when header_bg_image_url is "
        "unset; an empty url() can resolve to the current document. #78."
    ),
}

#: Inline-style declarations Outlook's Word engine cannot lay out. Deliberately
#: tiny and deliberately absent of `max-width`: the repo pairs `max-width` with
#: a `width=` attribute on purpose, so denying it would fire on correct code —
#: and a noisy rule gets switched off, which is worse than no rule. The
#: `img-width-attr` rule covers the case that actually matters.
UNSUPPORTED_DECLARATIONS: dict[str, frozenset[str]] = {
    "display": frozenset({"flex", "inline-flex", "grid", "inline-grid"}),
    "position": frozenset({"absolute", "fixed"}),
}

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
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.findings: list[Finding] = []
        self._in_style = False

    # -- helpers ------------------------------------------------------

    def _where(self, detail: str = "") -> str:
        line, column = self.getpos()
        return f"line {line}, col {column}{f' ({detail})' if detail else ''}"

    def _report(self, rule_id: str, severity: Severity, message: str, detail: str = "") -> None:
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

    def handle_data(self, data: str) -> None:
        if self._in_style:
            self._check_at_import(data)

    def handle_comment(self, data: str) -> None:
        # Conditional comments carry real CSS for Outlook; an @import there
        # would be just as external as one in a <style> block.
        self._check_at_import(data)

    # -- rules --------------------------------------------------------

    def _check_image(self, attributes: dict[str, str]) -> None:
        source = attributes.get("src", "")[:60]

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

        if not attributes.get("alt", "").strip():
            self._report(
                "img-alt",
                Severity.ERROR,
                "<img> has empty or missing alt text; with images blocked — "
                "Outlook desktop's default — this is all the reader gets.",
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
