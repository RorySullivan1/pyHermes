# MEMORY INDEX  ·  keep ≤ ~80 lines, ≤ ~200 chars per line

## State            (rewrite in place — current truth only, ≤ ~10 lines)
- pyHermes builds **documents** and renders each onto a **medium**: `svc/builder` is the
  shared kit, `svc/email`, `svc/document` and `svc/brochure` are the media, and exporters sit on
  one contract — `svc/delivery`+`gmail`+`outlook`, and `svc/pdf`. Rationale: CLAUDE.md and
  `.claude/rules/media.md`; do not restate it here.
- **Shipped and closed**: #157 (PR #167), #153 (PR #168), #169 (PR #190), #170 (PR #191),
  #171 apparatus (PR #192), #172 brochure (PR #194, #186–#189), #193 digital PDF (PR #203, #195–#200).
- **#201 fixed** on `claude/gifted-ritchie-7dkp5g` (not yet a PR). Open issues: #150 needs Outlook; #202 the PDF/UA
  tagger keeps `SCREEN` untagged.
- The prose budget is live; the baseline is 45 and may only shrink.

## Decisions        (append-only; supersede, never delete)
- Older entries, and epic #157's, are in sessions/ARCHIVE-2026.md.

- [2026-09-21] **GitHub closing keywords do not cascade to sub-issues.** `Closes #157` closed
  the epic and left all nine children open; a bare `#158` in a PR table cross-links but never
  closes. An epic PR lists `Closes` once per sub-issue —
  sessions/2026-09-17-2353-multi-medium-rescope.md

- [2026-09-21] **`disclosure` is plain text; the blessed raw-HTML set stays closed at five.**
  No inline link, deliberately: widening plain text to HTML later is additive, narrowing is
  not — sessions/2026-09-21-per-exhibit-disclosure.md
- [2026-09-21] **A template may fix an alignment the caller-facing axis does not offer.**
  `justify` sets the disclosure; `TextAlign` still excludes it, and a test pins that, because
  widening a guard without pinning what it forbids turns it into a comment —
  sessions/2026-09-21-per-exhibit-disclosure.md

- [2026-09-22] **The distance to a brochure is a medium; the distance to a factsheet is not.**
  A factsheet needs break discipline and document apparatus on the paged medium already shipped;
  a brochure needs fold geometry, imposition and print prep, so it is `svc/brochure/`, not a page
  preset — sessions/2026-09-22-1351-format-coverage-audit.md

- [2026-09-22] **A page is a sheet with a margin; the frame is what the margin leaves.** No preset
  frame may be 680px, or a template reading the email frame looks right on paper —
  sessions/2026-09-22-1903-pagination-hardening.md

- [2026-09-22] **Python numbers everything but the page; a forward reference is why one check
  waits for the projection.** `Document.validate()` is the sanctioned exception to validation at
  construction — sessions/2026-09-22-2200-document-apparatus.md
- [2026-09-23] **A panel is a fixed box that clips, and the clip is made loud by the print
  engine.** Table cells ran a side onto five sheets; a sentinel read off `page.anchors` names an
  overflowing face — sessions/2026-09-23-brochure-medium.md

- [2026-09-23] **A screen PDF is a profile, not a medium; `SCREEN` stays untagged.** WeasyPrint 70
  tags layout tables as `/Table` and ignores `role` (#202) — sessions/2026-09-23-digital-pdf.md

- [2026-09-23] **An image's CSS width is a cap on 100%, never a fixed px.** A px width is WeasyPrint's
  min-content, so a 600px chart in a half column widened the frame and added a sheet — `media.md` (#201)

- [2026-09-24] **Re-syncing from claudeBrain is a 3-way merge, never a copy.** Base = the factory
  blob nearest our file; pyHermes-adapted agents/hooks stay ours — sessions/2026-09-24-sync-claudebrain-assets.md

## Threads          (open items; remove when closed)
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
- [2026-09-22 21:00] data-layer — **#170 shipped, PR #191**: formatters, tone, `svc.data` adapters.
  No `from_frame`: the purity test wins. mypy's `follow_imports="skip"` is ignored for `.pyi`
  unless `follow_imports_for_stubs=true` — sessions/2026-09-22-2100-data-layer.md

- [2026-09-22 22:00] document-apparatus — **#171 shipped, PR #192** (5/5 closed): anchors, numbering,
  contents, footnotes, xrefs, running section. Every mechanism probed under WeasyPrint 70 first
  — sessions/2026-09-22-2200-document-apparatus.md

- [2026-09-23] brochure-medium — **#172 shipped, PR #194** (4/4 closed, CI green first push): folds, panel, imposition,
  bleed and marks, five editorial primitives. A test that reads the table it tests agrees with a
  wrong one — sessions/2026-09-23-brochure-medium.md
- [2026-09-23] digital-pdf — **#193 shipped, PR #203** (6/6 closed). PDF determinism needs
  HarfBuzz-Subset; findings #201, #202 filed — sessions/2026-09-23-digital-pdf.md
- [2026-09-23] image-width — **#201 fixed**: `width:100%; max-width:Npx` beside the attribute. Hints and a fixed
  px width each put a4_portrait on six sheets; email screenshots pixel-identical — `media.md`
