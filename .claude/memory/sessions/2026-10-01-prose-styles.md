# 2026-10-01 · prose-styles

**Goal:** Implement #280: the HTML a prose field carries takes the theme.

## What happened
- PR #294 (#272) merged first; the branch fast-forwarded to `main`.
- `pyhermes/builder/prose.py`: the `prose` Jinja filter (context-passing) styles `h3`, `h4`, `ul`,
  `ol`, `li`, `blockquote`, `a` and `hr` from `text/prose-styles.html`, one line per tag; an
  author's `style` wins. `refuse_top_headings` refuses `h1`/`h2` at construction in
  `TextBlock.content`, `Card.body` and `NumberedItem.body`.
- Three component tokens, `prose_gap` / `prose_indent` / `prose_item_gap`, in every preset, declared
  by the three owners through `PROSE_TOKENS`.
- `kitchen_sink` gained a "Desk Detail" section carrying every tag; its three A/B goldens moved
  with it. `a4_portrait` and `slide_16_9` moved by one line: their cross-reference link took the
  link style. Nothing else moved.
- Manual page 9 lists the tags; pages 2 and 8 point at it and name the refusal.

## Decisions
- Refuse, not demote, `h1`/`h2`: a silent rewrite hides the section-title rule; accepting later is additive.
- On a section's ground a link takes the ground's type colour (`surface_theme` is in the context).

## Verification
- `tests/test_prose_styles.py`: per-tag theme values, a sentinel theme/size/font, the author's style,
  the refusal, card and list bodies, the ground, an overlay. Five mutations each failed it; the
  CardGroup one needed both orientations parametrised to bite.
- Screenshots of the new section at 1000 and 375px read as intended, no overflow.
- ruff, format, `python -m mypy` and the prose budget clean. The only suite failures are the four
  `test_digital_pdf` tests that need HarfBuzz-Subset, as on `main` here. Bare `mypy` here cannot
  see jinja2; use `python -m mypy`.
