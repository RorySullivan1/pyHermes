---
name: factsheet-template
description: >
  Building a branded, standardized product factsheet as a PDF — the layout, the brand
  tokens, the data contract, and the mandatory compliance blocks. Use this skill whenever
  the work is a factsheet, tearsheet, index or fund one-pager, QIS or systematic-strategy
  product sheet, or any periodic product document with performance figures, risk statistics
  and a disclaimer. Trigger on "factsheet", "tearsheet", "index factsheet", "product
  one-pager", "monthly report for the index", "strategy sheet", "add the returns table",
  "where does the disclaimer go", "as-of date", "data contract for the report", and on
  requests to render one from a data dict or a JSON context. Also use it when a factsheet
  fails to render, when a required field is missing, or when disclaimer copy is not yet
  available. Depends on `weasyprint-print-html` for all print-HTML rules and tooling —
  follow that skill for CSS support, pagination, linting, rendering and snapshotting; this
  skill owns only the factsheet's brand, layout, data contract and compliance handling.
---

# Factsheet template

A two-page A4 factsheet for systematic / QIS index products. The engine rules are **not**
repeated here: follow **`weasyprint-print-html`** for print CSS, pagination, the lint →
render → snapshot loop, and every script except `validate_context.py`.

What this skill owns: the brand layer, the layout, the data contract, and the rule that
approved copy has exactly one source.

## Pipeline

```
data layer → context dict (+ pre-rendered SVG charts)
          → validate_context.py          ← fail-closed gate, runs BEFORE anything renders
          → Jinja2 + StrictUndefined     ← backstop for whatever the validator missed
          → weasyprint-print-html: lint → render → snapshot → look at the pages
```

The template **renders** numbers; it never computes them. Returns, statistics and weights
arrive finished. Charts arrive as SVG files and are passed as paths.

## Build one

1. **Validate first.** `python3 scripts/validate_context.py context.json`. Exit 2 means do
   not render — read `references/data-contract.md`. Field list:
   `validate_context.py --print-contract`.
2. **Stage a render directory.** Copy `factsheet.html.j2`, `factsheet.css`, the engine's
   `print-base.css`, `fonts/`, `compliance/` and the chart SVG into **one directory**, and
   render from there. This is not tidiness: `base_url` is both the relative-path root and
   the `--strict-fetch` root, so a bundle that reaches through `../` cannot be sandboxed.
3. **Load the approved copy from files** — never from the context:
   ```python
   ctx["disclaimer_text"] = [
       (stage / "compliance" / name).read_text(encoding="utf-8").strip()
       for name in ctx["disclaimer_blocks"]
   ]
   ```
4. **Render the template** with `StrictUndefined` and `autoescape=True`:
   ```python
   env = Environment(loader=FileSystemLoader(stage), undefined=StrictUndefined,
                     autoescape=True)
   html = env.get_template("factsheet.html.j2").render(**ctx)
   ```
5. **Run the engine loop** — lint, render, snapshot, and **view the page PNGs**. Two pages is
   the target; the footer's page count looks after itself.

## Rules specific to factsheets

**Never write, paraphrase, shorten, reflow or "improve" disclaimer or regulatory text.** It
comes only from `assets/compliance/`, verbatim, supplied by the user or compliance. If the
copy is not ready, leave the `PLACEHOLDER` file in place and say so — the page marks it
visibly and validation warns that the PDF must not be distributed. Drafting substitute
wording is not a helpful stopgap; it produces a document that looks approved and is not.

**The mandatory blocks are structural.** Audience label, as-of date, product identifier and
disclaimer live in the layout, not in optional fields. There is no code path that omits them.

**Every figure travels with its period and its as-of date.** The contract requires both on
each return and each statistic, and the template prints them together.

**Fail closed.** A factsheet missing its disclaimer or its as-of date must not render at all.
Two layers enforce it, because they fail differently — the validator sees the whole contract
including files on disk; `StrictUndefined` catches whatever the validator missed, but only
on fields the template references.

**Fonts are bundled, and `fonts/` ships empty.** No unlicensed font enters the repository.
Until the licensed faces are dropped in, the documented fallback stack renders and **three
checks stay loud**: lint W004, the render's `fonts` warning bucket, and `snapshot.py`'s
fallback-family flag. If all three are quiet and you added no fonts, the checks are broken —
not the fonts. See `assets/fonts/README.md`.

**A4 by default.** To switch to US Letter, set the mm variables *and* restate
`@page { size: Letter; }` — WeasyPrint resolves `@page` descriptors before custom
properties, so `size: var(--page-size)` does not work.

## Files

| Path | What it is |
|---|---|
| `assets/factsheet.html.j2` | The two-page layout. Mandatory blocks are structural. |
| `assets/factsheet.css` | Brand tokens over `print-base.css`; `@font-face` declarations. |
| `assets/fonts/` | **Empty by design** — licensed faces go here. |
| `assets/compliance/` | Approved copy only. Placeholders until supplied. |
| `scripts/validate_context.py` | The fail-closed gate. `--print-contract` dumps the fields. |
| `references/data-contract.md` | Field semantics and the rules behind them. |
| `references/layout-spec.md` | Section order, sizing, chart spec, how to grow it. |
| `probes/` | Sample context + chart, and the run log. |
| `DECISIONS.md` | Why it is shaped this way. |

## Verifying a change

`probes/sample-context.json` + `probes/sample-performance.svg` are the worked example. A
change to the template or CSS must still produce **two pages**, lint clean, and show the
running footer on both. `probes/PROBES.md` records the last run and what it proved.
