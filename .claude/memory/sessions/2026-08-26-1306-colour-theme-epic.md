# 2026-08-26 13:06 · colour-theme-epic

**Goal:** Execute epic #46: colour themes

## What happened
- Executed all five sub-issues (#47–#51) on `claude/review-open-issues-rr8quq`, one commit
  each, straight after epic #55 merged as PR #81.
- **#47 — the audit and the frozen `Theme`.** `svc/builder/theming.py`: `Palette`,
  `TextColors`, `SemanticColors`, `ShadowStyle`, all frozen with no optional token field, so
  completeness is structural rather than remembered. Shadows stored as hex + alpha; `Rgba.css`
  composes the CSS form on a byte-exact contract. A test asserted **nothing imported the
  module**, which made "inert" checkable instead of claimed.
- **#48 — the plumbing, and the mechanism decision #40 inherits.** The user chose the bound
  engine view from three options. `TemplateEngine.bound(**shared)` → `BoundEngine`, a
  per-render view merging shared values into every context. Nothing in the section tree
  changed signature; annotations moved to a `Renderer` protocol.
- **#49 — the migration.** 245 literals across 20 templates, both VML halves, the Jinja
  defaults and the Python fallbacks. Mapped **by role, not by value**.
- **#50 — the seam.** `Theme.derive(**layers)`, the public API, the curated `slate` preset,
  and the `slate_theme` gallery fixture.
- **#51 — docs.** CLAUDE.md gained a Theming section; the "Not parameters, deliberately"
  paragraph was rewritten (colour left that list); a fifth standing rule; README gained a
  Colour section.
- 938 tests green (874 → 886 → 906 → 938), ruff + mypy clean, lint pass clean on both presets.

## Gotchas & dead ends
- **The palette comment in `base.html` was *wrong*, not merely incomplete.** It named row-alt
  as `#F5F4F1`; `data-table.html` alternates with `#F8F7F5`, and `#F5F4F1` appears nowhere
  else in the repo. Deleted in #49 and replaced by a pointer to `theming.py`.
- **Map colours by role, never by value.** The same `#FFFFFF` is `palette.surface` behind a
  table and `text.on_dark` over the navy; the same `#2C3E50` is `header_bg`, `text.heading`
  and `rule_dark`. Two tokens the first audit missed (`text.heading`, `text.on_accent`) only
  surfaced because the migration had to decide what each *site* meant.
- **Prove byte-identity before the one intended change.** #49 temporarily restored the old
  palette comment, ran the goldens green (21/21), then re-applied the new one and
  regenerated. That is why the golden diff is exactly the comment block in all five fixtures
  and nothing else. Repeat this technique for #45.
- **`{{ theme.* }}` inside an HTML comment is a Jinja syntax error** — Jinja parses `{{ }}`
  anywhere, comments included. Cost one failed render; write prose, not a glob.
- **Migrating broke ~30 tests that render a component standalone** with a bare engine, since
  no theme was in the context. Resolved by having `TemplateEngine.render`/`render_string`
  layer `DEFAULT_THEME` *under* the caller's context: the engine guarantees a theme is
  present, `Email.render()`'s binding decides which and always wins. The perturbed-theme
  tests are what still prove the binder is live.
- `default_color` and `validate_hex_color` were **registered filters no template called**, so
  `default_color`'s `#5A5A5A` was a literal in a dead path. #49 put the filter to work for
  `Card.color`, which removed the literal and restored the validation.
- `dataclasses.replace` on a frozen layer re-runs `__post_init__`, so `derive()` re-validates
  for free. But a non-`str` token slipped past the old `isinstance(value, str)` guard — every
  field on these layers is a colour, so a non-string is now rejected outright.
- Small API facts worth not re-deriving: `TableRow` has no `alt` field (`DataTable` computes
  it by index); `AuthorBlock` takes `job_title`, not `title`; a horizontal `CardGroup`
  requires 2–4 cards; `Card.validate()` is called by the component, not in `__post_init__`.
- `html.index("</style>")` finds the **mso conditional** block first — use `rindex` for the
  real stylesheet.

## State at end
- **PR #82 merged** to `main` (`ec3e2bd`) at 13:15, closing #47–#51 and **epic #46** (5/5).
  All four CI jobs green on the head `9e37ae6` on the first run, in about 90 seconds. 938 tests
  verified again on merged `main`. Branch reset to `main`; PR watch stopped and both check-in
  triggers deleted.
- Gallery is six fixtures; `slate_theme` is the sixth. Zero colour literals remain in any
  template or as a Python default — two tests enforce it, with no documented exceptions.

## Open threads
- **#45 (size themes) is next and inherits three things**: ride `BoundEngine` rather than
  building a second injection mechanism (#48 made that choice, #40 was told to coordinate);
  name tokens by role; prove byte-identity before the intended change.
- #76 and #78 still open. #78 got easier — the scrim is now one `Rgba` read by both the CSS
  and VML halves, so fixing it changes one object rather than two literals.
