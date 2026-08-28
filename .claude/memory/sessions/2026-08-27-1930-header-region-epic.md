# 2026-08-27 · header region epic (#87)

Branch `claude/review-open-issues-rr8quq`, restarted from `main` @ `e581ffb` after PR #102
merged. Three commits: #95, #96, #97.

## The headline result

**#95 moved zero rendered bytes.** Every golden was green with the ownership change applied
and no fixture opting in. The strip already rendered from its own template into its own slot
after #89, so promoting it to `Header` was a change of *owner*, not of markup — `base.html`
untouched, same four slot names. That is the region mechanism's own test, and it passed.

## The four regions

| Region | Slot | Variants |
|---|---|---|
| `Header` | `header_bar_html` | `EmptyHeader` |
| `Banner` | `banner_html` | `MinimalBanner` |
| *(body)* | `sections_html` | — |
| `Footer` | `footer_html` | — (PR #86 removed `MinimalFooter`) |

`Header`'s three fields — `align`, `background_color`, `text_color` — are a **contract**: #98
gives the footer's box the same three so a caller learns one surface.

## Decisions worth not re-deriving

**`theme_context()` — generalise on the second case.** The banner had a `render_slots()`
override to resolve its palette against the bound theme; the header needed the same, so the
hook moved onto `Region`. What it returns layers *with the facts*, over presentation, so a
resolved value cannot be shadowed by the raw field — hence **a resolved key takes a different
name** (`header_background`, not `background_color`).

**The presence of a box belongs to the region; a fact is only its content.** Auto-collapsing
the strip on an empty `header_disclaimer` was rejected on ownership, not taste: it would make
the box's existence depend on a fact the email owns. `Footer` draws the same line — an empty
`disclaimer` omits the fine-print *line* while the footer still renders.

**"No fourth region" recorded as superseded, not deleted.** #87 reopened it deliberately: the
strip and the masthead were one region only by accident of file layout. The surviving half —
the preheader stays skeleton plumbing — is stated with the bar a fifth region must clear.

**A kept contract must be stated.** `header_disclaimer` stays raw HTML because escaping it
would break callers passing markup, so `Header.__doc__` warns and a test asserts the warning
survives.

## Measurements

- A blank strip is **14px** on `palette.header_bg`, sitting above the masthead's identical
  `palette.header_bg` — invisible. #96's premise ("reads as a rendering mistake") is only true
  once #95 let the header carry its own background. Worth re-measuring before acting on an
  issue's stated motivation.
- The email frame sits at **160–840** in a 1000px viewport (680px centred). A hardcoded
  screenshot clip of `x=100,width=700` cropped it and looked like a render bug; the two
  elements that legitimately exceed the frame are the full-width wrapper table and its cell.

## Traps hit

- **`EmptyHeader` must be defined after `Header`** — `class Banner` precedes `class Header` in
  `regions.py`, so anchoring an insert on `Banner` put the subclass before its base.
- **The issue itself had drifted**: #97 asked for "five slots" (there are four) and listed
  `MinimalFooter` as a variant (PR #86 removed it). Ground the docs in the code first — a
  script that resolves every backticked identifier is the cheap version.
- Two theming tests generalised rather than growing a third hard-coded name: the namespace
  check reads its accepted names off `theme_context()`, and the colour audit walks every
  fixture's regions.

## Next

**#98** (footer symmetry) — needs reconciling against PR #86 before it is actionable: it still
cites `MinimalFooter` and the two-slot footer, neither of which exists. Its principle 4 (the
library does not require disclaimer language) is already honoured by `REQUIRED_SLOTS`' stated
meaning. Then #53 (plain-text) and #56 (typography).
