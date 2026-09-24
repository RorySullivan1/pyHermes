# Decisions — factsheet-template

Why this skill is shaped this way. The engine-level decisions live in
`../weasyprint-print-html/DECISIONS.md`; this file covers only the factsheet. Kept in the
bundle because the skill is copied into other repositories and the reasoning must travel
with it.

## Separation

- **Depends on `weasyprint-print-html`, does not duplicate it.** Engine rules change with
  WeasyPrint releases; brand and compliance change with the business. Restating the print
  rules here would guarantee they drift, and the stale copy would be the one nobody
  corrects.
- **The template renders numbers, never computes them.** The data layer supplies a finished
  context dict and pre-rendered SVG charts. The only arithmetic in the template is clamping
  a composition bar's width, which is presentation.

## Compliance

- **Approved copy has exactly one source: `assets/compliance/`.** Claude never writes,
  paraphrases, shortens or reflows it. Three enforcement points, because one is not enough:
  `disclaimer_blocks` holds filenames and the validator rejects entries that look like prose;
  the derived `disclaimer_text` field is *rejected* if authored by hand; and the template
  reads files rather than accepting inline text.
- **Placeholders warn, they do not block.** Layout work has to be able to proceed before
  legal sign-off, so a `PLACEHOLDER` block renders — visibly marked on the page, with a
  warning that says the PDF must not be distributed. The alternative (hard failure) would
  push people to write substitute wording, which is the outcome this whole arrangement
  exists to prevent.
- **Mandatory blocks are structural, not fields.** Audience label, as-of date, product
  identifier and disclaimer are in the layout with no code path that omits them. A factsheet
  missing one is not a lighter-weight factsheet; it is a compliance incident.

## Data contract

- **The contract is code; the doc describes it.** `CONTRACT` in `validate_context.py` is the
  single source and `--print-contract` dumps it, so `references/data-contract.md` cannot
  silently drift from what is actually enforced.
- **Two fail-closed layers, because they fail differently.** The validator sees the whole
  contract at once, including files on disk and values that are present but wrong. Jinja2's
  `StrictUndefined` only fires on a field the template actually references, one at a time —
  useful as a backstop, useless as the only gate.
- **Figures are numbers, not formatted strings.** `return_pct: 0.84`, never `"+0.84%"`. A
  pre-formatted string cannot be aligned on the decimal, cannot be totalled, and hides its
  own precision. Formatting is the template's job.
- **`period` is a closed list.** Free-text periods make two factsheets non-comparable, which
  defeats the point of a standard template.
- **A future as-of date is an error, not a warning.** Figures cannot exist for a date that
  has not happened.

## Layout

- **Returns and risk sit side by side out of necessity, not taste.** Stacked, they pushed
  page 1 past its printable height and stranded the risk table alone on a page of its own —
  observed on the first render of the sample context, fixed in one iteration. Both tables are
  short *by contract*, so the side-by-side row is safe to mark `break-inside: avoid`.
- **The disclaimer must be allowed to fragment.** No `break-inside: avoid` on it. Long legal
  copy that cannot break overflows and is clipped, which is the worst possible failure for
  that particular block.
- **The composition bar is a background-color div.** Not an image (one more asset to fetch),
  not `box-shadow` (dropped by WeasyPrint).
- **`fonts/` ships empty.** Confirmed with the user: embedding and server-side rendering are
  separate licence grants and an unlicensed embed is a real liability. The fallback stack
  keeps the template renderable while three independent checks stay noisy, so the substitution
  can never be silent.
- **A4 default, Letter by override.** Confirmed with the user. `size` is restated rather than
  variable-driven because WeasyPrint resolves `@page` descriptors before custom properties.

## The fixture is an instrument, not a sample

- **[2026-09-16] The chart fixture is a geometric stand-in, and the figures are round.** The
  first build shipped a 58KB matplotlib render of a synthetic price series plus a context of
  realistic-looking returns — "+61.40% since inception", "Sharpe 1.12". That is a *product
  sample*, and invented performance figures riding inside a factsheet template into an internal
  repository is the same hazard the compliance placeholders exist to prevent. The fixture now
  uses round numbers (1, 2, 5, 10, 20, 50), an "Example Systematic Index" identity, and a
  `_sample` marker the validator always reports.
- **The stand-in keeps the same footprint** (510×184pt = 180mm×65mm), so pagination is still
  regression-tested against real geometry — the fixture lost its realism, not its job.
- **Building the realistic sample was still worth it.** It is what exposed three defects the
  small fixtures missed: the linter firing E003 as an *error* on a correct template (it followed
  `<link>` but not `@import`), W004 reading `var(--family-display)` as a font name, and page 1
  overflowing to three pages. The lesson is about what gets *committed*, not what gets built: a
  realistic render is a good scratch artifact and a poor repository fixture.

## Placement

This bundle ships with **placeholder compliance copy and no font files**, which is what makes
it safe to keep in a shared repository. The real brand faces, the approved disclaimers and any
work templates belong in the internal repository — copy the bundle there and replace the two
directories. Nothing else needs to change.
