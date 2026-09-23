# 2026-09-22 22:00 · document-apparatus

**Goal:** Implement epic #171 — exhibit numbers, footnotes, a table of contents,
cross-references and a running section header, numbered in Python so every projection agrees.

Started from `main` @ `946386a` (PR #191 merged). Six code commits and one docs commit on
`claude/gifted-ritchie-7dkp5g`.

| Commit | Issue | What |
|---|---|---|
| `8ed74c8` | #183 (1) | Section anchors: slug of the title, `anchor=`, uniqueness in `add_section` — id-only diff, script-verified (89 lines, 16 goldens) |
| `a443cda` | #181 | `Exhibit` mixin: `label=`/`anchor=`, `ChartBlock.caption`, `Config.exhibit_separator`, the numbering walk |
| `3b4a810` | #183 | `Contents` component + `ContentsPage` region, one partial, `target-counter` page numbers |
| `f7c260b` | #182 | `Footnote`, `[^n]` markers, `marked()` macro, `float: footnote` on paper, `Endnotes` in email |
| `d9f4927` | #184 | `a.xref::after` page, `format_link` drops `#` URLs, `Document.validate()` for dangling refs |
| `31adaa2` | #185 | `RunningBox.follow`, per-box named strings, the cleared-fallback design |

## Decisions and why
- **Python numbers everything but the page** — CSS counters would leave the text part unnumbered.
  The walk runs on each `add_section` *and* before each projection, so a shared component carries
  each document's number while that one renders.
- **Markers are a plain-text convention (`[^1]`), notes are plain text.** The raw-HTML set stays
  closed at five; that was the epic's named risk.
- **The dangling-reference check runs at projection start, not `add_section`** — a forward
  reference is ordinary prose. The one sanctioned exception to "validation at construction";
  it runs before any template loads, and `validate()` is public.
- **Contents is structurally aligned**, and `ContentsPage` has no `align`; it is opt-in
  (`EmptyContentsPage` default) unlike the other paged regions.
- **Each running box follows its own string**; a leaf-seeded fallback string cleared by every
  section title, read `last`, with the title read `first`. Four probes; three simpler designs failed.
- **`a4_long_table` pins the footer-follows half**; the paged region-completeness test now reads
  the whole paged gallery, as standing rule 9 words it.

## What proved it
- Every mechanism was probed in a scratch document under WeasyPrint 70 before any code.
- Byte-identity at each mechanism step: goldens unchanged before fixtures opted in (exhibits,
  the notes macro); email goldens unchanged across #185.
- PDF read-back tests: contents page numbers vs. the section's sheet, each note at its marker's
  sheet foot, "(p. N)" vs. the exhibit's sheet, each header a section begun on or before.
- Rasters found three things no golden could: the marker too large in fine print, a chart that
  emptied a third of a sheet, and parenthesised cross-reference copy.

## Environment note
- `python -m pytest` (the uv-tool `pytest` lacks jinja2). Playwright's managed browser is absent;
  `PYHERMES_CHROMIUM=/opt/pw-browsers/chromium-1194/chrome-linux/chrome` makes screenshots run.

## Outcome
- **PR #192 merged** 2026-09-23; one `Closes` per issue, and #171 closed with
  `sub_issues_summary` 5/5. CI green on all six jobs at first push.
