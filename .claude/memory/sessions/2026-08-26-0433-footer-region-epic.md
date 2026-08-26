# 2026-08-26 04:33 · footer-region-epic

**Goal:** Plan and execute epic #55: make the footer a first-class region

## What happened
- Read #55 and its five sub-issues (#63–#67) against #38's **merged** implementation, which
  the epic body explicitly requires ("where it compromised, this epic inherits the
  compromise"). Executed all five on `claude/review-open-issues-rr8quq`, one commit per
  step except #64/#65, which do not stand apart.
- **#63 — extraction, and the region-shape decision.** The issue asked to decide one
  template vs two *consciously*. Two, forced by the DOM: the contact card is a `<tr>` inside
  the body table and the legal block is a sibling `<table>` below it, with `</table>` +
  `<!-- /Main container -->` between them. A single fragment would have to close a tag the
  skeleton opened — unbalanced on its own, valid at exactly one insertion point. The variant
  argument agrees: two templates make dropping the contact card an *omission*.
- **#64 + #65 — the model and the API, as one commit.** Splitting them leaves an
  intermediate where the wording has moved off `EmailMetadata` but nothing can render it.
  Five copy fields moved to a new `Footer`; the disclaimer, `current_year`, `firm_name` and
  the three URLs stayed facts. Rather than transplant `Header`'s plumbing a second time, the
  shared half became a **`Region` base**: validation, the image walk, facts-over-presentation
  layering, and `render_slots()`.
- **#66 — `MinimalFooter` + the compliance floor.** The variant *composes* the shipped legal
  template (same path in `TEMPLATE_PATHS`), so a test can assert the legal block comes out
  byte-identical to the default footer's. `REQUIRED_SLOTS` makes an unfilled legal slot a
  construction-time `ValidationError`; a parametrized test walks every exported `Footer` and
  asserts the disclaimer and unsubscribe link survive its render.
- **#67 — docs.** CLAUDE.md's composition model, ownership rule (one table, both regions),
  standing rule 4, public API, directory map, gallery table and Open work; README's
  composition section; this file + INDEX.
- **Byte-identity held at every step.** The strongest evidence: after adding the fifth
  fixture, `git status qa/fixtures/goldens/` showed exactly two `??` and zero ` M`.
- 828 tests green (767 before), ruff + `ruff format --check` + mypy clean, wheel verified by
  building it and running the extended CI smoke script from a clean venv outside the tree.

## Gotchas & dead ends
- **`mypy` on PATH is a different environment** and reports `jinja2` import-not-found. Use
  `python -m mypy`. Not a repo problem; cost a few minutes of false alarm.
- **The `minimal_footer` fixture initially rendered the wrong unsubscribe label.** It passed
  `unsubscribe_label` flat *and* `.footer(MinimalFooter())`. An explicit region **replaces**
  the metadata-built one — documented precedence inherited from #38, and the flat/explicit
  conflict check only fires inside `EmailMetadata`, where both spellings are visible. Caught
  by reading the screenshot, not by a test. Fixed by putting the label on the region, with a
  comment in the fixture and a paragraph in CLAUDE.md; the API was left alone, since making
  the swap raise would break the documented way to swap a region.
- **`config_override(size_limit_kb=…)` has cross-field rules.** Lowering the limit below
  `inline_image_limit_kb` (48) raises `ValueError` from `Config.__post_init__`. Override both.
- `Header.template_path` became `TEMPLATE_PATHS`, keyed by slot. Two test lines referenced it;
  nothing else did.
- Whitespace mechanics repeated from #33 exactly: the region template ends at its last markup
  line, the `{{ slot }}` placeholder sits at column 0, and the blank line *after* the old
  block is deleted so the placeholder's own newline supplies it. Do not reach for `{{ x -}}` —
  `-` strips all contiguous whitespace, not one newline.

## State at end
- Branch `claude/review-open-issues-rr8quq` @ five commits on `main` (`673a6f2`): the memory
  commit from #38, then #63, #64+#65, #66, #67. Epic #55 complete, not yet pushed or PR'd at
  the time this file was written.
- `base.html` 177 → **116 lines** (head, skeleton, preheader). Four slots:
  `header_html`, `sections_html`, `footer_contact_html`, `footer_legal_html`.
- Gallery is five fixtures: `minimal`, `kitchen_sink`, `image_matrix`, `minimal_header`,
  `minimal_footer`.

## Open threads
- #76 (mobile `.kpi-cell` overflow) and #78 (three deferred Outlook lint rules) are still
  open and still deliberately unbundled — each changes rendered output, which is exactly what
  the region epics promised not to do. Their golden diff is the point rather than the problem,
  and they are now a smaller target than before either epic ran.
- Remaining epics: #45 size themes, #46 color themes, then #53 plain-text and #56 typography.
  They contend on `base.html` and `EmailMetadata`, but on far less of both than they did.
