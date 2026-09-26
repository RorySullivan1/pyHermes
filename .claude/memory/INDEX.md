# MEMORY INDEX  ·  keep ≤ ~80 lines, ≤ ~200 chars per line

## State            (rewrite in place — current truth only, ≤ ~10 lines)
- pyHermes builds **documents** and renders each onto a **medium**: `svc/builder` is the
  shared kit, `svc/email`, `svc/document` and `svc/brochure` are the media, and exporters sit on
  one contract — `svc/delivery`+`gmail`+`outlook`, and `svc/pdf`. Rationale: CLAUDE.md and
  `.claude/rules/media.md`; do not restate it here.
- **Shipped**: #157, #153, #169, #170, #171, #172, #193 (PRs #167–#203); #201, #150, #202 (PRs #204–#206);
  #209 (PR #222); #217 (PR #234); #221 (PR #235). Stubs #218–#220 are still undefined; each was
  filed against `main` @ `0ac949a` and is defined in place with the `epic` skill, as #217 and #221 were.
- The prose budget is live; the baseline is 45 and may only shrink.

## Decisions        (append-only; supersede, never delete)
- Older entries, and epic #157's, are in sessions/ARCHIVE-2026.md.

- [2026-09-23] **A panel is a fixed box that clips, and the clip is made loud by the print
  engine.** Table cells ran a side onto five sheets; a sentinel read off `page.anchors` names an
  overflowing face — sessions/2026-09-23-brochure-medium.md

- [2026-09-23] **A screen PDF is a profile, not a medium; `SCREEN` stays untagged.** WeasyPrint 70
  tags layout tables as `/Table` and ignores `role` (#202) — sessions/2026-09-23-digital-pdf.md

- [2026-09-23] **An image's CSS width is a cap on 100%, never a fixed px.** A px width is WeasyPrint's
  min-content, so a 600px chart in a half column widened the frame and added a sheet — `media.md` (#201)
- [2026-09-24] **A page opening the body drops its leading break.** The seed leaves ahead of the body
  table made it open a blank sheet. `add_page` is paged-only shorthand; the `Page` node stays — `media.md`

- [2026-09-24] **Re-syncing from claudeBrain is a 3-way merge, never a copy.** Base = the factory
  blob nearest our file; pyHermes-adapted agents/hooks stay ours — sessions/2026-09-24-sync-claudebrain-assets.md
- [2026-09-24] **Spacing has two levels: a preset (or a derived scheme), then `spacing=` per object as a
  derive of the bound scheme.** The email gates both; no px enters the API — `design-axes.md`,
  sessions/2026-09-24-spacing-two-levels.md
- [2026-09-24] **A `colspan` is admitted in a `thead` only, and Outlook's handling of it is unverified
  here.** A cell note is the `[^n]` marker, never a field — #217, sessions/2026-09-24-1208-define-epic-217.md

- [2026-09-24] **A cell's text on its own heat tint takes the more legible theme token, and a
  marker hangs past the point on paper.** Both were found only by the #228 rasters —
  sessions/2026-09-24-table-semantics.md

- [2026-09-24] **An equation's component takes bytes and the [math] extra renders them**, because the
  builder never imports a backend; **the picture is painted for the theme the caller passes** — `math.md`

## Threads          (open items; remove when closed)
- **In this container, PDF byte-determinism tests flake** (no HarfBuzz-Subset), and screenshot
  tests skip unless `PYHERMES_CHROMIUM=/opt/pw-browsers/chromium-1194/chrome-linux/chrome`.
- **Every issue or PR body is written without angle brackets** — GitHub's sanitizer has
  emptied three.
- **A closing keyword closes only the issue it names, and this is now proven both ways.**
  #167 named only the epic and left all nine children open; #168, #191 and #192 named every
  issue and closed every one. One `Closes #N` per sub-issue, and check that summary after
  any epic merge.
- **Four optional extras:** `[pdf]`, `[qa]`, `[data]`, `[charts]`. `[dev]` alone stays free of all
  four; their tests skip, and CI's `pdf` job must name every PDF-reading test module.
- **CLAUDE.md is a router**; the detail is in path-scoped `.claude/rules/*.md`, which load
  only when a matching file is read. Add reasoning there, not back into the router.
- **Factory hand-off for #140 is in `.claude/README.md`** — what claudeBrain should take,
  and the four rules worth inheriting.
- **The baseline may only shrink.** #138 and #139 empty it; nothing may be added.
- **Everything in `.claude/` is a factory asset** except `agents/python-developer.md` and
  `agents/finance-quantitative-developer.md`. No project name may enter the others.

## Log              (append-only pointers)
- Older entries, and epic #157's, are in sessions/ARCHIVE-2026.md.
- [2026-09-23] digital-pdf — **#193 shipped, PR #203** (6/6 closed). PDF determinism needs
  HarfBuzz-Subset; findings #201, #202 filed — sessions/2026-09-23-digital-pdf.md
- [2026-09-23] image-width — **#201 fixed**: `width:100%; max-width:Npx` beside the attribute. Hints and a fixed
  px width each put a4_portrait on six sheets; email screenshots pixel-identical — `media.md`
- [2026-09-24] spacing-two-levels — **#209 implemented** (#211–#216): `dense`, `SizeScheme` as `size_theme`,
  `Spacing` + `SPACING_TOKENS`, the factsheet at 90% of two sheets — sessions/2026-09-24-spacing-two-levels.md
- [2026-09-24] define-epic-217 — **#217 defined, #223–#228 filed** via the github-issues pipeline. `fill-self`
  rewrites the Done-when sentence too; print the diff — sessions/2026-09-24-1208-define-epic-217.md
- [2026-09-24] define-epic-221 — **#221 defined, #229–#233 filed**. mathtext measured: deterministic, no `aligned`,
  `\le` unknown; two stub claims corrected (purity, theme recolour) — sessions/2026-09-24-1312-define-epic-221.md
- [2026-09-24] table-semantics — **#217 implemented** (#223–#228): groups, cell markers, `Column.format`,
  decimal alignment and units, `HeatScale` and bars; `letter_quant_table` — sessions/2026-09-24-table-semantics.md
- [2026-09-24] equations — **#221 implemented** (#229–#233): `MathBlock`, `svc/math` + `[math]`, `math_block`,
  lines shim, `a4_equations`, the factsheet's Sharpe ratio — sessions/2026-09-24-equations.md
