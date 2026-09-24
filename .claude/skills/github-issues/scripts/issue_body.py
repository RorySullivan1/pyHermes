#!/usr/bin/env python3
"""Render, check, and number issue bodies from the github-issues templates.

    issue_body.py render <kind> <values.json> [--out FILE]
    issue_body.py check  <file> [--allow-self]
    issue_body.py fill-self <file> <number> [--out FILE]
    issue_body.py lint-templates

<kind> is a template under ../references/templates/ (epic, task, bug, feature). The same
files are installed verbatim as GitHub issue templates (`../installs.json`), so each one
is written for both readers:

- YAML frontmatter (`name:`, `about:`, optional `title:`) drives GitHub's template
  chooser. `render` strips it.
- A slot is a guidance comment that names its field: `<!-- problem: guidance -->`. A human
  sees the guidance in the editor. `render` replaces the slot with values.json["problem"].
  A trailing `?` (`<!-- risks?: ... -->`) marks it optional: null or absent removes the
  slot's whole section, or its line if it shares the line with text ("Part of #...").
- The Done-when fence holds `Closes #N`. The issue's own number exists only after
  creation, so `fill-self` replaces the N afterwards. `check --allow-self` is the
  pre-filing gate, and plain `check` is the post-filing one.

Exit status: 0 = clean, 2 = defects, listed on stderr.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "references" / "templates"
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
SLOT = re.compile(r"<!--\s*([a-z_]+)(\?)?:.*?-->", re.S)
HEADING = re.compile(r"^## (.+)$", re.M)
FENCE = re.compile(r"```\n(.*?)\n```", re.S)
CLOSING = re.compile(r"\b(close[sd]?|fix(e[sd])?|resolve[sd]?) #\d+\b", re.I)
UNNUMBERED = re.compile(r"(\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?) #)N\b", re.I)


def _fail(defects: list[str]) -> int:
    for d in defects:
        print(f"issue_body: {d}", file=sys.stderr)
    return 2


def _sections(text: str) -> dict[str, str]:
    parts = HEADING.split(text)
    return dict(zip(parts[1::2], parts[2::2]))


def _drop_optional(text: str, key: str) -> str:
    """Remove an optional slot's section if the slot is all it holds, else its line."""
    whole = re.compile(rf"^## [^\n]*\n\s*<!--\s*{key}\?:.*?-->\s*?\n(?=\s*(## |---|\Z))", re.M | re.S)
    if whole.search(text):
        return whole.sub("", text, count=1)
    return re.sub(rf"^[^\n]*<!--\s*{key}\?:.*?-->[^\n]*\n?", "", text, count=1, flags=re.M | re.S)


def render(kind: str, values: dict) -> tuple[str, list[str]]:
    path = TEMPLATES / f"{kind}.md"
    if not path.is_file():
        known = sorted(p.stem for p in TEMPLATES.glob("*.md"))
        return "", [f"unknown template {kind!r}; known: {', '.join(known)}"]
    text = FRONTMATTER.sub("", path.read_text(encoding="utf-8"), count=1)

    slots = {key: bool(opt) for key, opt in SLOT.findall(text)}
    unknown = sorted(set(values) - set(slots))
    missing = sorted(k for k, opt in slots.items() if not opt and values.get(k) in (None, ""))
    defects = [f"unknown key(s) for {kind}: {', '.join(unknown)}"] if unknown else []
    if missing:
        defects.append(f"missing value for: {', '.join(missing)}")
    if defects:
        return "", defects

    for key, opt in slots.items():
        if opt and values.get(key) in (None, ""):
            text = _drop_optional(text, key)
    text = SLOT.sub(lambda m: str(values[m.group(1)]).strip(), text)
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n", []


def check(text: str, allow_self: bool) -> list[str]:
    defects = []
    if FRONTMATTER.match(text):
        defects.append("template frontmatter left in the body")
    for key, _ in SLOT.findall(text):
        defects.append(f"unfilled slot: {key}")
    if "{{" in text:
        defects.append("a {{placeholder}} is left in the body")
    sections = _sections(text)
    for heading, body in sections.items():
        if not body.strip():
            defects.append(f"empty section: ## {heading}")
    if "Done when" in sections:
        # Only the fenced line counts: the footnote's example keywords must not satisfy this.
        fence = FENCE.search(sections["Done when"])
        line = fence.group(1) if fence else ""
        if not (CLOSING.search(line) or (allow_self and UNNUMBERED.search(line))):
            defects.append("'Done when' has no numbered closing keyword (run fill-self)")
    return defects


def lint_templates() -> list[str]:
    """Each template must work as a GitHub markdown issue template AND as a render source."""
    defects = []
    for path in sorted(TEMPLATES.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        fm = FRONTMATTER.match(text)
        if not fm:
            defects.append(f"{path.name}: no YAML frontmatter (GitHub needs name: and about:)")
            continue
        keys = dict(re.findall(r"^([a-z_]+):\s*(.*)$", fm.group(1), re.M))
        if len(keys.get("name", "").strip("\"'")) <= 3:
            defects.append(f"{path.name}: `name:` missing or not more than 3 characters")
        if not keys.get("about", "").strip("\"'"):
            defects.append(f"{path.name}: `about:` missing")
        body = text[fm.end():]
        if not SLOT.search(body):
            defects.append(f"{path.name}: no slots, so render has nothing to fill")
        if "{{" in body:
            defects.append(f"{path.name}: a {{{{placeholder}}}} would show literally on GitHub")
        if "Done when" in _sections(body) and not UNNUMBERED.search(_sections(body)["Done when"]):
            defects.append(f"{path.name}: 'Done when' lacks a `Closes #N`-style line for fill-self")
    return defects


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("kind")
    r.add_argument("values")
    r.add_argument("--out")
    c = sub.add_parser("check")
    c.add_argument("file")
    c.add_argument("--allow-self", action="store_true")
    f = sub.add_parser("fill-self")
    f.add_argument("file")
    f.add_argument("number", type=int)
    f.add_argument("--out")
    sub.add_parser("lint-templates")
    args = ap.parse_args(argv)

    if args.cmd == "lint-templates":
        defects = lint_templates()
        if defects:
            return _fail(defects)
        print("issue_body: templates clean")
        return 0
    if args.cmd == "check":
        defects = check(Path(args.file).read_text(encoding="utf-8"), args.allow_self)
        if defects:
            return _fail(defects)
        print("issue_body: clean")
        return 0
    if args.cmd == "render":
        values = json.loads(Path(args.values).read_text(encoding="utf-8"))
        text, defects = render(args.kind, values)
        defects = defects or check(text, allow_self=True)
        if defects:
            return _fail(defects)
    else:
        text = Path(args.file).read_text(encoding="utf-8")
        sections = _sections(text)
        fence = FENCE.search(sections.get("Done when", ""))
        if not fence or not UNNUMBERED.search(fence.group(1)):
            return _fail(["no `Closes #N` line under 'Done when' to number"])
        numbered = UNNUMBERED.sub(rf"\g<1>{args.number}", fence.group(1))
        text = text.replace(fence.group(0), f"```\n{numbered}\n```", 1)
        text = text.replace(", where N is this issue's number:", ":", 1)

    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
