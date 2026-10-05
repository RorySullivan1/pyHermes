# 2026-10-05 — epic #329, organising content

Implemented #330–#334 on `claude/integrate-claude-assets-pyhermes-d4spzb`, restarted from
`main` after PR #377 merged.

- **#330** `FactList(facts, columns=1, title, value_format)` in `organising.py`,
  `text/fact-list.html`; token `fact_pad`; declares `gutter`, and `pad_x` is a fallback read.
- **#331** `Timeline`, `Event(date, title, body, state)`, `text/timeline.html`; tokens
  `timeline_date`, `timeline_marker`, `timeline_rule` (box) and `timeline_gap`. **Shape:** two
  rows an event, no span; a rowspan draft stretched the marker in Chromium, and the lint
  refuses `colspan` in a body. The marker is a capsule of two half-cells.
- **#332** `TeaserList`, `Teaser(title, url, date, summary, image, tags)`,
  `text/teaser-list.html`; token `teaser_thumb` (box). One column when `medium.paged`. The row
  table must not collapse borders, or a stacked cell drops its padding on a phone.
- **#333** `kicker=` on `Container`, the five sections, `Slide` and `Deck.add_slide`;
  `common/kicker.html`; `check_kicker`; `Config.kicker_max_chars` 40; sections declare
  `caption_gap`. On a slide the band's top padding drops by `Slide.kicker_rise`.
- **#334** `_organised.py`, `organised_layout`, `a4_organised_layout`, `pitch_16_9`'s sidebar,
  `tests/test_organising.py`, the manual section in page 2, `design-axes.md`,
  `builder-architecture.md`, `qa-harness.md`, `deck.md`.

**Found:** `kitchen_sink` with the three objects measured 93.8 KB in `modern_fonts`. The
objects took *Three Equal*'s filler blocks, and *Tail Risk*, *In Their Words* and *Desk Detail*
were folded into Stacks under *Portfolio Variance* and *Desk Note*: 89.4 KB, 615 bytes left.
Three gallery tests walked only a section's top level and now walk `descendants`.

Goldens moved: kitchen_sink and its three A/B siblings, `pitch_16_9`; new: the two organised
fixtures. Same container flakes as before (PDF byte determinism in `test_digital_pdf`,
`test_attachments` and the handout test), each also failing on clean `main`.
