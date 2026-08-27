# 2026-08-26 21:09 · harness-findings

**Goal:** Close #76 (mobile overflow), #78 (three deferred Outlook findings), and #85 (one left margin)

## What happened

Two commits on `claude/review-open-issues-rr8quq`, the first work in a while whose *point*
was a golden diff rather than its absence. Both issues had been deferred by every epic for
the same reason: each changes rendered output, and every epic claimed the gallery stays
byte-identical at each step.

- **#76** — `.kpi-cell` gains `box-sizing:border-box`. All eight fixtures now capture at
  exactly their viewport width at every density. The golden diff is one CSS line (plus its
  comment) per fixture and nothing else.
- **#78** — all three findings fixed, all three rules moved from `DEFERRED_RULES` into
  `SOURCES`. The lint pass now ships **eight** rules and `DEFERRED_RULES` is empty.
- **#85** — filed *from this session*, after the user spotted in a screenshot posted to PR
  #84 that multi-column sections hang left of their own heading. Pre-existing on `main`
  @ `1105532`: the band was never inset by `frame.pad_x`, so it started at x=0 with ~60px
  dead on the right, and its text sat 16-20px in while headings sat at 32.

## Gotchas & dead ends

- **#85's three sub-traps, all found by measuring.** (1) Insetting the band is not enough —
  the columns' *outer* padding has to go to zero, or the text lands at 52 instead of 32.
  (2) The columns are inline-blocks, so the newline between two of them renders as a ~4px
  space: gutters were really 20px, and once the band occupies its full 616px the last column
  wraps. `font-size:0` on the inset cell fixes it (the column cells set their own).
  (3) A highlighted band spends 1px a side on its hairline, so it is 2px too wide for its
  cell and wraps for the same reason — every horizontal inset inside one now gives that
  pixel back (`edge_pad`).
- **Probe the *content* edge, not the box.** A full-width cell sits at x=0 and pads inward;
  a column cell sits at x=32 and does not. Comparing `getBoundingClientRect().left` alone
  says they disagree when they agree. Add `parseFloat(getComputedStyle(el).paddingLeft)`.
  And group cells by `top`, taking the min per row — otherwise a *second* column's cell,
  which legitimately starts mid-frame, reads as a broken left margin.
- **Components indent inside their own box, and that is not a container concern.** Card
  labels (32+1+16) and numbered-list bodies (32+22+12) are meant to sit further in. The
  invariant is about headings and container content cells only.
- **`sync_playwright()` cannot nest in one thread.** A module-scoped fixture holding a
  session open made every later `capture_gallery` test error. Collect all measurements in
  one session, close it, then parametrize the assertions over the collected data — one
  launch *and* per-fixture failure messages.

- **The issue's recommended fix for #76 was wrong, and only measuring showed it.** #76 leaned
  toward dropping `width:100%` because "a `display:block` element already fills its
  container". A `<td>` re-displayed as block *inside a table* shrink-wraps: the cell
  collapsed to 110/116/126px. Both variants fix the page overflow; only `box-sizing` keeps
  the layout. Probe script pattern: patch `base.html`, render, measure
  `documentElement.scrollWidth` + `getBoundingClientRect()` in Playwright, restore in a
  `finally`.
- **`<!--[if !mso]><!-->` is downlevel-revealed, so the linter *does* see what follows.**
  Hiding the rgba scrim from Outlook did not silence `outlook-transparent-background` —
  HTMLParser emits `handle_comment('[if !mso]><!')`, then the real `<div>`, then
  `handle_comment('<![endif]')`. The fix was to teach the linter that state and suppress
  only `_OUTLOOK_ONLY_RULES` there. Named set, **not** an `outlook-` prefix match:
  `img-width-attr` is Outlook-motivated and must keep firing.
- **Unitless → percentage line-height is an *inheritance* change, not just a unit change.**
  Unitless is inherited as a number and recomputed per element; a percentage is inherited as
  the computed px. Nine rendered elements inherited their leading (captions, card labels,
  table cells/headers — all smaller than body), so a blind conversion would have given a
  9.5px caption the body's 24px leading. Seven templates now state it explicitly. Audit
  technique: walk the *rendered* HTML with a tag stack, flag any element with an inline
  `font-size` and no inline `line-height`, report its nearest ancestor's value.
- **"Pixel-identical" was not quite true, and saying so precisely mattered.** Computed
  font-size / line-height / colour / background: **0** differences over 1879 elements. But
  geometry moves up to **0.47px** — Chromium snaps a resolved percentage to a different
  1/64px LayoutUnit than a lazily-computed ratio. Verify against
  `git show HEAD:qa/fixtures/goldens/<name>.html` as the "before".
- **A rule can be satisfied by scope rather than by value.** The scrim could not be made
  opaque — it exists to darken a photograph, and Outlook draws that photo via `v:fill`
  *behind* the div, so an opaque colour would paint over it.
- Two test-only traps: `url("")` inside a double-quoted `style` attribute closes the
  attribute (pick the quote the value does not use); and Python heredoc scripts write at the
  end, so one failed `assert` in a multi-`sub` script means **nothing** was written — a
  docstring anchor that started mid-line silently cost a whole run.

## State at end

- Branch `claude/review-open-issues-rr8quq`, 4 commits on `main` @ `1105532`; **PR #84** open.
- 1239 tests green with a browser (1221 + 18 skips without); ruff + mypy clean.
- Gallery lints clean under all eight rules; `DEFERRED_RULES` empty.
- Desktop screenshot heights unchanged (3030 / 2516 / 3731); mobile all exactly 375px.
- Every heading and container content box starts at `frame.pad_x` in all 8 fixtures.

## Open threads

- **#56 typography** is the last epic. Its sub-issues predate #45/#46 merging, so they will
  name proposals that drifted — reconcile against the merged code.
- **#53 plain-text** contends with nothing and touches `svc/delivery`, not the templates.
- The masthead's VML still emits `<v:fill src="">` when no background image is set. Same
  class of defect as #78's `empty-url`, but inside a conditional comment where the rule
  cannot see it, and guarding it means restructuring the VML block. Not filed yet.
