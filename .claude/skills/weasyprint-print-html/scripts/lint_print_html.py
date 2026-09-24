#!/usr/bin/env python3
"""Static checks on print-bound HTML/CSS, before any render is attempted.

Catches the defects that cost a render cycle: JavaScript that will never run, remote
assets that will silently fail to fetch, a missing `@page` rule, CSS WeasyPrint ignores,
and layout constructs that break across page boundaries.

Exit codes: 0 clean, 1 warnings only, 2 errors present (a render is not worth attempting).

KNOWN FALSE POSITIVES (regex/heuristic parsing, by design — a real CSS parser is not worth
the dependency here):
  - A flagged token inside a quoted string is still flagged. Comments are NOT a false
    positive source: `<!-- -->` and slash-star bodies are blanked before any check, so a
    property or `@page` merely *mentioned* in a comment cannot satisfy or trip a rule.
    (That blind spot was real — the negative-control fixture's own comment said "@page"
    and silenced E003 until comments were blanked.)
  - W004 (font-family with no @font-face) only sees CSS reachable from the entry file via
    local `<link rel="stylesheet">` or `@import`. A face declared in a sheet injected some
    other way (a build step, a <style> written at runtime) reports a false positive.
  - W005 (flex/grid without break-inside) matches within a single declaration block. A rule
    that sets `display:flex` and a *separate* rule that sets `break-inside:avoid` on the same
    selector reads as a violation.
  - W003 (table without thead) counts `<table>` and `<thead>` occurrences per file; a table
    inside an HTML comment or a Jinja block counts.
Each is a warning, never an error, precisely because the parser is approximate.
"""
import argparse
import json
import re
import sys
from pathlib import Path

RASTER_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".webp"}
GENERIC_FAMILIES = {
    "serif", "sans-serif", "monospace", "cursive", "fantasy", "system-ui",
    "ui-serif", "ui-sans-serif", "ui-monospace", "inherit", "initial", "unset",
}
# Two DIFFERENT failure modes, measured against WeasyPrint 69.0 rather than assumed
# (probes/PROBES.md records the run). Conflating them produces wrong advice: `transform`,
# `border-radius`, gradients, `opacity`, `gap`, grid and `float` ARE supported, and telling
# an author otherwise costs them design range for no reason.
#
# DROPPED: the CSS parser rejects the declaration and WeasyPrint logs
# "Ignored `prop:value` … unknown property". The style simply does not exist.
DROPPED_PROPERTIES = {
    "box-shadow": "a 0.4pt border, or a .band background-color block",
    "text-shadow": "a solid colour with enough contrast",
    "filter": "pre-process the image, or overlay a background-color",
    "backdrop-filter": "a solid or gradient background-color",
    "mix-blend-mode": "a flat colour chosen to look like the blended result",
    "background-blend-mode": "one background-color or a linear-gradient (both supported)",
    "clip-path": "border-radius (supported), or crop the image before embedding",
    "mask": "crop the image before embedding",
    "perspective": "nothing — 3D has no meaning on paper",
    "transform-style": "nothing — 3D has no meaning on paper; 2D `transform` IS supported",
    "aspect-ratio": "explicit mm dimensions — this is why .figure sizes in mm",
    "writing-mode": "nothing supported; restructure the content instead",
}
# INERT: parses cleanly, WeasyPrint says nothing, and it has no effect on a static page.
# Dead code that reads as intent, which is worse than a warning.
INERT_PROPERTIES = {
    "animation": "delete it — a PDF page does not animate",
    "transition": "delete it — there is no interaction to transition",
    "will-change": "delete it — there is no compositing to hint at",
    "scroll-behavior": "delete it — a page does not scroll",
}


class Finding:
    __slots__ = ("severity", "rule", "path", "line", "message", "fix")

    def __init__(self, severity, rule, path, line, message, fix=""):
        self.severity, self.rule = severity, rule
        self.path, self.line = path, line
        self.message, self.fix = message, fix

    def as_dict(self):
        return {
            "severity": self.severity, "rule": self.rule, "file": str(self.path),
            "line": self.line, "message": self.message, "fix": self.fix,
        }


def _lines(text):
    return text.splitlines()


def _line_of(text, index):
    return text.count("\n", 0, index) + 1


def blank_comments(text):
    """Blank comment bodies, preserving newlines so reported line numbers stay true.

    Without this, a rule can be satisfied or tripped by a comment: the @page check in
    particular passed on any file whose comments merely mentioned `@page`.
    """
    def wipe(match):
        return re.sub(r"[^\n]", " ", match.group(0))

    text = re.sub(r"<!--.*?-->", wipe, text, flags=re.S)
    return re.sub(r"/\*.*?\*/", wipe, text, flags=re.S)


def linked_stylesheets(text, path):
    """Local stylesheets reachable from `text`: <link rel="stylesheet"> and @import.

    Both must be followed. Following only <link> made E003 — an *error* — fire on a
    perfectly good template whose `@page` lived in an @import-ed base sheet.
    """
    out = []
    for m in re.finditer(r"<link\b[^>]*>", text, re.I):
        tag = m.group(0)
        if not re.search(r"rel\s*=\s*['\"]?[^'\">]*stylesheet", tag, re.I):
            continue
        href = re.search(r"href\s*=\s*['\"]([^'\"]+)['\"]", tag, re.I)
        if not href or re.match(r"https?://", href.group(1), re.I):
            continue
        out.append((path.parent / href.group(1)).resolve())
    # @import url("x.css") | @import 'x.css' — url() form and bare-string form.
    for m in re.finditer(r"@import\s+(?:url\(\s*)?['\"]?([^'\")\s;]+)", text, re.I):
        target = m.group(1)
        if re.match(r"https?://", target, re.I):
            continue
        out.append((path.parent / target).resolve())
    return out


def check_scripts(text, path, findings):
    for m in re.finditer(r"<script\b", text, re.I):
        findings.append(Finding(
            "error", "E001", path, _line_of(text, m.start()),
            "<script> tag: WeasyPrint never executes JavaScript, so this renders nothing.",
            "Pre-render the chart to SVG (matplotlib with svg.fonttype='path') and <img> it."))


def check_remote(text, path, findings):
    patterns = (
        (r"\bsrc\s*=\s*['\"](https?://[^'\"]+)['\"]", "src"),
        (r"<link\b[^>]*href\s*=\s*['\"](https?://[^'\"]+)['\"]", "stylesheet href"),
        (r"url\(\s*['\"]?(https?://[^'\")]+)", "CSS url()"),
    )
    for pattern, where in patterns:
        for m in re.finditer(pattern, text, re.I):
            findings.append(Finding(
                "error", "E002", path, _line_of(text, m.start()),
                f"Remote asset in {where}: {m.group(1)[:60]}",
                "Vendor the file next to the template and use a relative path "
                "(resolved via base_url)."))


def check_at_page(all_css_text, entry_path, findings):
    if not re.search(r"@page\b", all_css_text):
        findings.append(Finding(
            "error", "E003", entry_path, 0,
            "No @page rule found in the document or its linked stylesheets.",
            "Import assets/print-base.css, or declare @page with size, margin and a "
            "@bottom-center margin box carrying counter(page)/counter(pages)."))


def check_unsupported(text, path, findings):
    for prop, fix in DROPPED_PROPERTIES.items():
        for m in re.finditer(rf"(?<![\w-]){re.escape(prop)}\s*:", text, re.I):
            findings.append(Finding(
                "warning", "W001", path, _line_of(text, m.start()),
                f"`{prop}` is dropped by WeasyPrint's CSS parser (logged as "
                f"\"unknown property\"); the declaration has no effect.",
                f"Use {fix}."))
    for prop, fix in INERT_PROPERTIES.items():
        for m in re.finditer(rf"(?<![\w-]){re.escape(prop)}\s*:", text, re.I):
            findings.append(Finding(
                "warning", "W007", path, _line_of(text, m.start()),
                f"`{prop}` parses without complaint but does nothing on a static page — "
                f"WeasyPrint will NOT warn you about it.",
                fix))
    for m in re.finditer(r"position\s*:\s*sticky", text, re.I):
        findings.append(Finding(
            "warning", "W001", path, _line_of(text, m.start()),
            "`position: sticky` is rejected as an invalid value (other `position` values "
            "are fine).",
            "Use a @page margin box for repeating content, or <thead> for table headers."))


def check_media_screen(text, path, findings):
    for m in re.finditer(r"@media[^{]*\bscreen\b", text, re.I):
        findings.append(Finding(
            "warning", "W002", path, _line_of(text, m.start()),
            "@media screen block: WeasyPrint renders with media_type='print', so this is dead.",
            "Move the rules into the print context or delete them."))


def check_tables(text, path, findings):
    tables = len(re.findall(r"<table\b", text, re.I))
    theads = len(re.findall(r"<thead\b", text, re.I))
    if tables > theads:
        findings.append(Finding(
            "warning", "W003", path, 0,
            f"{tables} <table> element(s) but only {theads} <thead>: headers will not "
            "repeat on continuation pages.",
            "Wrap the header row in <thead> and set `break-inside: avoid` on tr."))


def check_fonts(all_css_text, entry_path, findings):
    declared = {
        m.group(1).strip().strip("'\"").lower()
        for m in re.finditer(
            r"@font-face\s*\{[^}]*?font-family\s*:\s*([^;}]+)", all_css_text, re.I | re.S)
    }
    used = set()
    for m in re.finditer(r"(?<![\w-])font-family\s*:\s*([^;}]+)", all_css_text, re.I):
        # Skip the declarations inside @font-face itself.
        window = all_css_text[max(0, m.start() - 400):m.start()]
        if window.rfind("@font-face") > window.rfind("}"):
            continue
        for part in m.group(1).split(","):
            name = part.strip().strip("'\"").lower()
            # `font-family: var(--family-display)` names a variable, not a face. The faces
            # are whatever the variable resolves to, declared elsewhere in the corpus.
            if name.startswith("var("):
                continue
            if name and name not in GENERIC_FAMILIES:
                used.add(name)
    for name in sorted(used - declared):
        findings.append(Finding(
            "warning", "W004", entry_path, 0,
            f"font-family `{name}` has no @font-face rule: WeasyPrint will fall back "
            "silently to whatever the host has installed.",
            "Bundle the font file and declare @font-face with a relative src, or remove "
            "the family. Verify after rendering with `pdffonts`."))


def check_flex_grid(text, path, findings):
    for m in re.finditer(r"\{[^{}]*\}", text):
        block = m.group(0)
        if not re.search(r"display\s*:\s*(inline-)?(flex|grid)", block, re.I):
            continue
        if re.search(r"break-inside\s*:\s*avoid", block, re.I):
            continue
        findings.append(Finding(
            "warning", "W005", path, _line_of(text, m.start()),
            "flex/grid container without `break-inside: avoid`: flex and grid layouts do "
            "not fragment predictably across a page boundary.",
            "Add `break-inside: avoid` and keep the container smaller than one page, or "
            "use block flow / a table for content that may cross pages."))


def check_image_weight(text, path, threshold_kb, findings):
    for m in re.finditer(r"<img\b[^>]*\bsrc\s*=\s*['\"]([^'\"]+)['\"]", text, re.I):
        src = m.group(1)
        if re.match(r"(https?:|data:)", src, re.I):
            continue
        target = (path.parent / src).resolve()
        if target.suffix.lower() not in RASTER_SUFFIXES or not target.is_file():
            continue
        kb = target.stat().st_size / 1024
        if kb > threshold_kb:
            findings.append(Finding(
                "warning", "W006", path, _line_of(text, m.start()),
                f"{src} is {kb:.0f} KB (threshold {threshold_kb:.0f} KB).",
                "Render vector art as SVG, or downsample the raster and render with "
                "--optimize-images (optionally --jpeg-quality)."))


def lint(paths, threshold_kb):
    findings, css_corpus, seen = [], [], set()

    def read(p):
        try:
            return p.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            findings.append(Finding("error", "E000", p, 0, f"Unreadable: {exc}"))
            return ""

    queue = [Path(p).resolve() for p in paths]
    entry = queue[0] if queue else Path(".")
    while queue:
        path = queue.pop(0)
        if path in seen:
            continue
        seen.add(path)
        text = read(path)
        if not text:
            continue
        text = blank_comments(text)
        is_html = path.suffix.lower() in {".html", ".htm", ".j2", ".jinja", ".jinja2"}
        check_remote(text, path, findings)
        check_unsupported(text, path, findings)
        check_media_screen(text, path, findings)
        check_flex_grid(text, path, findings)
        if is_html:
            check_scripts(text, path, findings)
            check_tables(text, path, findings)
            check_image_weight(text, path, threshold_kb, findings)
        queue.extend(linked_stylesheets(text, path))
        css_corpus.append(text)

    corpus = "\n".join(css_corpus)
    if corpus:
        check_at_page(corpus, entry, findings)
        check_fonts(corpus, entry, findings)
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="+", help="HTML and/or CSS files to check")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--image-threshold-kb", type=float, default=500.0)
    args = ap.parse_args(argv)

    findings = lint(args.paths, args.image_threshold_kb)
    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]

    if args.json:
        print(json.dumps({
            "errors": len(errors), "warnings": len(warnings),
            "findings": [f.as_dict() for f in findings],
        }, indent=2))
    else:
        for f in errors + warnings:
            where = f"{f.path}:{f.line}" if f.line else str(f.path)
            print(f"{f.severity.upper():7} {f.rule}  {where}\n         {f.message}")
            if f.fix:
                print(f"         fix: {f.fix}")
        if not findings:
            print("lint: clean — no errors or warnings.")
        else:
            print(f"\nlint: {len(errors)} error(s), {len(warnings)} warning(s).")
    return 2 if errors else (1 if warnings else 0)


if __name__ == "__main__":
    raise SystemExit(main())
