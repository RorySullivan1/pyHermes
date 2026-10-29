# Reference reports

The three reports every roadmap gate is tested against ([.meta/roadmap/INDEX.md](../.meta/roadmap/INDEX.md)).
A gate passes when these reports pass it, not when a feature list is done. A new medium or layout primitive
is admitted only for one of them (standing rule 14).

| Report | Medium | Built today by | Status |
|---|---|---|---|
| [`daily-note`](daily-note/SPEC.md) | Email | `examples/daily-investment-note` | Stand-in: replace before Gate 1 |
| [`research-report`](research-report/SPEC.md) | Paged document | `examples/quarterly-review` | Stand-in: replace before Gate 1 |
| [`product-brochure`](product-brochure/SPEC.md) | Brochure | `qa/fixtures/tri_fold_letter.py` | Stand-in: replace before Gate 1 |

Each directory holds a `SPEC.md` (owner, audience, cadence, sections, data inputs) and a `build.py` whose
`build()` returns the built document. `tests/test_reference_reports.py` builds, renders and lints all three in
CI. Replacing a stand-in means pointing its `build.py` at the real source and updating its spec.

## The speed benchmark

The roadmap promises to make research reports faster to produce. This is how that is measured, at every gate:

```bash
pip install -e ".[dev,charts,pdf]"
python -m qa.benchmark            # five runs a report; -n to change
```

For each report it prints:

- **Author lines**: the lines of code in the source that builds it, without blanks, comments or docstrings.
  The proxy for what an author writes. It counts that one file, data included, not shared helpers.
- **Build, render and check ms**: median machine time to build the document, render it, and lint it under
  its medium's rules.
- **PDF ms**: median time to print it, for a paged medium with `[pdf]` installed.
- **Lint errors**: must be 0.

**The author's minutes** (wall-clock time from new data to a sent note) cannot be measured by a script. The
owner records them below when a real report replaces its stand-in.

## Recorded runs

### Baseline: v0.3.0, 2026-10-28

All three stand-ins, five runs each; Python 3.11.17 on Linux x86_64, in a cloud session, so treat the
milliseconds as relative.

| Report | Author lines | Build ms | Render ms | Check ms | PDF ms | Lint errors |
|---|---|---|---|---|---|---|
| daily-note | 291 | 213 | 6 | 15 | n/a | 0 |
| research-report | 101 | 1 | 2 | 6 | 622 | 0 |
| product-brochure | 159 | 4 | 4 | 11 | 890 | 0 |

The daily note's build time is its two matplotlib charts. Machine time is under a second for every report,
so the cost to cut is the author's: 100 to 300 lines of hand-built section tree per report.

| Report | Author's minutes, data to sent |
|---|---|
| daily-note | not yet recorded: needs the real note |
| research-report | not yet recorded: needs a real report |
| product-brochure | not yet recorded: needs the real piece |
