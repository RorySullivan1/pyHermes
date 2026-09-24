# 2026-09-24 · spacing-two-levels

**Goal:** Implement epic #209, spacing at two levels (sub-issues #211–#216), and open a PR onto `main`.

Started from `main` @ `0ac949a`. The factsheet #216 rewrites lived only on `feature/fund-factsheet`,
because PR #207 was closed unmerged with no comment. That branch was merged into
`claude/gifted-ritchie-7dkp5g` first, so the epic's PR also carries the factsheet, the
leading-break fix and `add_page` from #207 and #208.

| Issue | What landed |
|---|---|
| #211 | `DENSE_SIZES` derived from compact, `SizeTheme.DENSE`, `PRINT_DENSITIES`; `letter_dense` paged fixture, 2 sheets |
| #212 | `resolve_size_scheme` passes a `SizeScheme`; `check_density` in `Document.__init__`; `Config.allow_custom_email_density`, the first bool field |
| #213 | `Spacing`, `TOKEN_LAYERS`, `coerce_spacing`; `engine.scheme_of` / `rebind` / `respaced`; Panel uses them |
| #214 | `spacing=` and `SPACING_TOKENS` on FullWidth, FlowedColumns, TwoColumn, ThreeColumn; Page takes every section token |
| #215 | `spacing=` on every public component; long table at `table_cell_pad=3` repeats its header on each sheet |
| #216 | Factsheet at `dense`: risk, trading, fundamentals and distributions tables added, 90% of each sheet |

## Decisions and why
- **The email gate lifts with one switch for both cases**, a custom scheme and `dense`: each is "a
  density no client has rendered", and the caller who has rendered theirs says so once.
- **The gate is `medium.email`, not "not paged".** Plain HTML is never read in Outlook. The
  *spacing* refusal is "not paged", because plain HTML still uses the email skeleton's `@media` block.
- **Unsafe off paper:** the tokens the `@media` block reads (`card_pad_*`, `mobile_*`,
  `table_cell_pad_mobile`) plus `pad_x`. Content padding is not on the list: the collapse
  already replaces it with `mobile_pad_*` for every section, overridden or not.
- **A container declares only its own template's tokens; a Page declares all of them.** A split
  cannot tighten its tables, so the factsheet sets the table's own spacing.
- **Refused whatever the object:** width tokens, the type layer, the component leadings,
  `kpi_value`, and the box sizes `cta_width`, `cta_height`, `list_ordinal_width`. The reverse
  sentinel test found the last three.
- **`kpi_value` is 17 in dense, not the probe's 16:** 16 gave up more than body type, breaking
  compact's rule that the number the reader came for shrinks least.

## What surprised
- `TestTheTokensAreLive` lost `table_cell_pad` and `kpi_pad_y` once `kitchen_sink` overrode its only
  table and KPI strip. The test now strips the overrides, since its subject is the document's scheme.
- A harness screenshot inlines attached images and a bare page does not, so crop coordinates from
  one do not fit the other. Photograph from the page you measured.
- Playwright needs `PYHERMES_CHROMIUM=/opt/pw-browsers/chromium-1194/chrome-linux/chrome` here.

## Verification
Full suite, ruff, format and mypy clean. Goldens moved: `kitchen_sink` and its three
derivatives (only the four overridden tokens), plus the new `letter_dense`. Email screenshots
inspected at both viewports; lint clean. `tests/test_spacing.py` joined CI's `pdf` job.

**Next:** PR #222 is open onto `main`; watch its CI and review. If #207 is reopened and merged
first, the factsheet commits drop out of #222's diff.
