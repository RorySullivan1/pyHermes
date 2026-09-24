#!/usr/bin/env python3
"""Validate a factsheet context dict against the data contract. Stdlib only.

Runs BEFORE render, and is the fail-closed gate: a factsheet missing its disclaimer, its
as-of date, or its audience label must not produce a PDF at all. Jinja2's StrictUndefined
catches a missing field at render time, but only once it is referenced and only with a
template-internal message — this reports every problem at once, in the data's own terms.

The CONTRACT below is the single source of truth for the field list. `references/
data-contract.md` explains the semantics and points here rather than restating the fields,
so the two cannot drift. Dump the machine copy with `--print-contract`.

Exit codes: 0 valid, 1 warnings only, 2 invalid (do not render).

Usage:
    validate_context.py context.json [--template-dir DIR] [--json] [--print-contract]
"""
import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Periods a return row may be labelled with. A free-text period makes two factsheets
# non-comparable, which is the whole reason this is a closed list.
PERIODS = ("1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y", "10Y", "SI")

# (dotted path, kind, required, note)
CONTRACT = (
    ("product.name",            "str",        True,  "Index or product name as approved"),
    ("product.identifier",      "str",        True,  "Ticker/ISIN — the unambiguous handle"),
    ("product.currency",        "str",        True,  "ISO 4217, e.g. USD"),
    ("as_of_date",              "date",       True,  "ISO YYYY-MM-DD; never in the future"),
    ("audience_label",          "str",        True,  "Distribution/audience restriction; "
                                                     "printed in the running footer"),
    ("strategy.description",    "str",        True,  "Approved prose; never generated"),
    ("key_facts",               "label_value", True, "Rows for the key-facts table"),
    ("performance.chart_path",  "svg_path",   True,  "Pre-rendered SVG, relative to the "
                                                     "template dir"),
    ("performance.periods",     "returns",    True,  "Rows of {period, return_pct, as_of}"),
    ("risk_stats",              "stats",      True,  "Rows of {label, value, period, as_of}"),
    ("methodology",             "str_or_list", True, "Methodology notes"),
    ("composition",             "weights",    True,  "Rows of {name, weight_pct}"),
    ("disclaimer_blocks",       "compliance", True,  "Filenames under assets/compliance/ — "
                                                     "NEVER inline text"),
    ("product.inception_date",  "date",       False, "ISO date"),
    ("product.rebalance",       "str",        False, "e.g. Monthly"),
    ("performance.chart_caption", "str",      False, "Figure caption"),
    ("logo_path",               "path",       False, "Local image, relative to template dir"),
    ("footnotes",               "str_or_list", False, "Numbered notes"),
)


class Problem:
    __slots__ = ("severity", "field", "message")

    def __init__(self, severity, field, message):
        self.severity, self.field, self.message = severity, field, message

    def as_dict(self):
        return {"severity": self.severity, "field": self.field, "message": self.message}


def dig(data, dotted):
    node = data
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None, False
        node = node[part]
    return node, True


def check_date(value, field, problems, allow_future=False):
    if not isinstance(value, str) or not ISO_DATE.match(value):
        problems.append(Problem("error", field, f"must be ISO YYYY-MM-DD, got {value!r}"))
        return
    try:
        parsed = dt.date.fromisoformat(value)
    except ValueError:
        problems.append(Problem("error", field, f"not a real date: {value!r}"))
        return
    if not allow_future and parsed > dt.date.today():
        problems.append(Problem(
            "error", field,
            f"{value} is in the future — an as-of date that has not happened yet means the "
            f"figures cannot exist"))


def check_rows(value, field, required_keys, problems):
    if not isinstance(value, list) or not value:
        problems.append(Problem("error", field, "must be a non-empty list of objects"))
        return []
    rows = []
    for index, row in enumerate(value):
        where = f"{field}[{index}]"
        if not isinstance(row, dict):
            problems.append(Problem("error", where, "must be an object"))
            continue
        for key in required_keys:
            if key not in row or row[key] in (None, ""):
                problems.append(Problem("error", where, f"missing `{key}`"))
        rows.append((where, row))
    return rows


def check_numeric(row, key, where, problems):
    if key in row and not isinstance(row[key], (int, float)):
        problems.append(Problem(
            "error", where,
            f"`{key}` must be a number, got {type(row[key]).__name__} — formatting is the "
            f"template's job, so a pre-formatted string cannot be aligned or totalled"))


# Derived at render time by reading the files named in `disclaimer_blocks`. It must NOT
# appear in an authored context: a context that carries disclaimer prose directly has
# bypassed assets/compliance/, which is the one place approved copy may come from.
DERIVED_FIELDS = ("disclaimer_text",)

# A fixture marks itself with `_sample`. The validator refuses to stay quiet about it, so
# synthetic figures cannot reach a distributed factsheet by being forgotten about.
SAMPLE_MARKER = "_sample"


def validate(data, template_dir):
    problems = []
    if not isinstance(data, dict):
        return [Problem("error", "<root>", "context must be a JSON object")]

    if data.get(SAMPLE_MARKER):
        problems.append(Problem(
            "warning", SAMPLE_MARKER,
            f"this context is marked SAMPLE DATA ({data[SAMPLE_MARKER]}). It exists to "
            f"regression-test the layout; every figure in it is synthetic. Never render it "
            f"as a real factsheet"))

    for field in DERIVED_FIELDS:
        if field in data:
            problems.append(Problem(
                "error", field,
                "must not be authored: it is derived at render time from the files named in "
                "`disclaimer_blocks`. Disclaimer copy comes from assets/compliance/ only"))

    for field, kind, required, _note in CONTRACT:
        value, present = dig(data, field)
        if not present or value in (None, "", [], {}):
            problems.append(Problem(
                "error" if required else "warning", field,
                "required by the contract and missing or empty" if required
                else "optional and absent"))
            continue

        if kind == "str" and not isinstance(value, str):
            problems.append(Problem("error", field, "must be a string"))
        elif kind == "date":
            check_date(value, field, problems)
        elif kind == "str_or_list" and not isinstance(value, (str, list)):
            problems.append(Problem("error", field, "must be a string or a list of strings"))
        elif kind == "label_value":
            for where, row in check_rows(value, field, ("label", "value"), problems):
                pass
        elif kind == "returns":
            for where, row in check_rows(value, field, ("period", "return_pct", "as_of"),
                                         problems):
                check_numeric(row, "return_pct", where, problems)
                if row.get("period") not in PERIODS:
                    problems.append(Problem(
                        "error", where,
                        f"period {row.get('period')!r} is not one of {', '.join(PERIODS)} — "
                        f"free-text periods make two factsheets non-comparable"))
                if isinstance(row.get("as_of"), str):
                    check_date(row["as_of"], f"{where}.as_of", problems)
        elif kind == "stats":
            for where, row in check_rows(value, field,
                                         ("label", "value", "period", "as_of"), problems):
                if isinstance(row.get("as_of"), str):
                    check_date(row["as_of"], f"{where}.as_of", problems)
        elif kind == "weights":
            rows = check_rows(value, field, ("name", "weight_pct"), problems)
            for where, row in rows:
                check_numeric(row, "weight_pct", where, problems)
            total = sum(r.get("weight_pct", 0) for _w, r in rows
                        if isinstance(r.get("weight_pct"), (int, float)))
            if rows and abs(total - 100.0) > 1.0:
                problems.append(Problem(
                    "warning", field,
                    f"weights sum to {total:.2f}, not ~100 — intended for a partial "
                    f"exposure list? Say so in the caption"))
        elif kind in ("svg_path", "path"):
            target = (template_dir / value).resolve()
            if not target.is_file():
                problems.append(Problem("error", field, f"file not found: {target}"))
            elif kind == "svg_path" and target.suffix.lower() != ".svg":
                problems.append(Problem(
                    "error", field,
                    f"{value} is not .svg — charts are pre-rendered vector, never a raster "
                    f"screenshot and never a JS chart"))
            elif template_dir.resolve() not in target.parents:
                problems.append(Problem(
                    "warning", field,
                    "resolves outside the template directory, so --strict-fetch will refuse "
                    "it; stage the asset under the template root"))
        elif kind == "compliance":
            if not isinstance(value, list) or not value:
                problems.append(Problem(
                    "error", field,
                    "must be a non-empty list of filenames under assets/compliance/"))
                continue
            for index, name in enumerate(value):
                if not isinstance(name, str):
                    problems.append(Problem("error", f"{field}[{index}]", "must be a filename"))
                    continue
                if "<" in name or len(name.split()) > 4:
                    problems.append(Problem(
                        "error", f"{field}[{index}]",
                        "looks like prose, not a filename — disclaimer text must come from "
                        "an approved file in assets/compliance/, never from the context"))
                    continue
                path = (template_dir / "assets" / "compliance" / name).resolve()
                if not path.is_file():
                    problems.append(Problem(
                        "error", f"{field}[{index}]",
                        f"no approved snippet at assets/compliance/{name}"))
                elif "PLACEHOLDER" in path.read_text(encoding="utf-8", errors="replace"):
                    problems.append(Problem(
                        "warning", f"{field}[{index}]",
                        f"{name} is still a PLACEHOLDER — the PDF will render but must not "
                        f"be distributed until compliance supplies the approved copy"))
    return problems


def print_contract():
    print(f"{'field':28} {'kind':13} {'req':4} note")
    for field, kind, required, note in CONTRACT:
        print(f"{field:28} {kind:13} {'yes' if required else 'no':4} {note}")
    print(f"\nvalid period tokens: {', '.join(PERIODS)}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("context", nargs="?", help="JSON file holding the context dict")
    ap.add_argument("--template-dir", default=None,
                    help="root that relative asset paths resolve against "
                         "(default: this skill's directory)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--print-contract", action="store_true",
                    help="dump the authoritative field list and exit")
    args = ap.parse_args(argv)

    if args.print_contract:
        print_contract()
        return 0
    if not args.context:
        ap.error("context is required unless --print-contract is given")

    source = Path(args.context)
    if not source.is_file():
        print(f"validate: context not found: {source}", file=sys.stderr)
        return 2
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except ValueError as exc:
        print(f"validate: context is not valid JSON — {exc}", file=sys.stderr)
        return 2

    template_dir = Path(args.template_dir) if args.template_dir else Path(__file__).parent.parent
    problems = validate(data, template_dir)
    errors = [p for p in problems if p.severity == "error"]
    warnings = [p for p in problems if p.severity == "warning"]

    if args.json:
        print(json.dumps({
            "errors": len(errors), "warnings": len(warnings),
            "problems": [p.as_dict() for p in problems],
        }, indent=2))
    else:
        for problem in errors + warnings:
            print(f"{problem.severity.upper():7} {problem.field}: {problem.message}")
        if not problems:
            print("validate: context satisfies the contract.")
        else:
            print(f"\nvalidate: {len(errors)} error(s), {len(warnings)} warning(s).")
            if errors:
                print("Do NOT render: the contract fails closed by design.")
    return 2 if errors else (1 if warnings else 0)


if __name__ == "__main__":
    raise SystemExit(main())
