# Data contract — what the factsheet template requires

The **authoritative field list is code**, not this file:

```
python3 scripts/validate_context.py --print-contract
```

`CONTRACT` in `scripts/validate_context.py` is the single source, so the validator and the
documentation cannot drift apart. This file explains the *semantics* — why fields are shaped
the way they are, and which rules are not obvious from a field name.

## Where the data comes from

The data layer hands over a **finished context dict** and **pre-rendered SVG charts**. The
template renders numbers; it never computes them. There is no arithmetic in the template
beyond clamping a composition bar's width, which is presentation.

That boundary is the reason a figure's formatting lives in the template while its *value*
lives in the contract as a number: `return_pct: 0.84`, never `"+0.84%"`. A pre-formatted
string cannot be right-aligned on the decimal, cannot be totalled, and hides its own
precision.

## The rules worth knowing

**Every figure carries its period and its as-of date.** `performance.periods` rows are
`{period, return_pct, as_of}` and `risk_stats` rows are `{label, value, period, as_of}`. A
return without its period and date is not a fact, it is a number — and the template displays
them together so the two can never be separated downstream.

**`period` is a closed list**: `1M 3M 6M YTD 1Y 3Y 5Y 10Y SI`. Free-text periods make two
factsheets non-comparable, which defeats the point of a standard template.

**`as_of_date` may not be in the future.** An as-of date that has not happened yet means the
figures cannot exist. This is an error, not a warning.

**`disclaimer_blocks` holds FILENAMES, never prose.** Each entry names a file under
`assets/compliance/`. The validator rejects an entry that looks like prose — contains `<`,
or runs longer than four words — because approved copy has exactly one source and the
context dict is not it.

**`disclaimer_text` must not appear in an authored context.** It is *derived* at render time
by reading the files named in `disclaimer_blocks`; the validator errors if you supply it,
because a context carrying disclaimer text has bypassed `assets/compliance/` entirely.

```python
ctx["disclaimer_text"] = [
    (assets / "compliance" / name).read_text(encoding="utf-8").strip()
    for name in ctx["disclaimer_blocks"]
]
```

**A block still containing `PLACEHOLDER` is a warning, not an error.** The factsheet renders
so layout work can proceed before sign-off, the page marks the block visibly, and the
warning says plainly that the PDF must not be distributed. See
`assets/compliance/README.md`.

**`performance.chart_path` must be an existing `.svg`** relative to the template directory.
A raster screenshot or a JS chart is rejected at validation, not discovered at render.
A path that resolves *outside* the template directory is a warning: `--strict-fetch` will
refuse it, because the base URL is both the fetch root and the relative-path root.

**Composition weights are numbers and should total ~100.** A sum more than 1.0 off is a
warning, not an error — a deliberately partial exposure list is legitimate, but it should
say so in the caption rather than look like an arithmetic mistake.

## Fail-closed, in two layers

1. **`validate_context.py` runs first** and reports *every* problem at once, in the data's
   own terms. Exit 2 means do not render.
2. **Jinja2 `StrictUndefined`** is the backstop: a field the validator somehow missed raises
   at render time instead of producing a PDF with a blank where a number belongs.

Both exist because they fail differently. `StrictUndefined` only fires on a field the
template actually *references*, one at a time, with a template-internal message. The
validator sees the whole contract, including files on disk and values that are present but
wrong.
