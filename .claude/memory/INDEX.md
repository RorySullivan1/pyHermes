# MEMORY INDEX  ·  keep ≤ ~80 lines, ≤ ~200 chars per line

## State            (rewrite in place — current truth only, ≤ ~10 lines)
- pyHermes builds **documents** and renders each onto a **medium**: `svc/builder` is the
  shared kit, `svc/email` and `svc/document` are the two media, and three exporters sit on
  one contract — `svc/delivery`+`gmail`+`outlook`, and `svc/pdf`. Rationale: CLAUDE.md and
  `.claude/rules/media.md`; do not restate it here.
- **Epic #157 (rescope to media) is COMPLETE** — #158–#166 on branch
  `claude/gifted-ritchie-7dkp5g`, open as PR #167. Phases 1–4 shipped golden-identical.
- Open: **#150** (banner VML `src`, needs a real Outlook host) and **epic #153**
  (per-exhibit disclosure, #154–#156) — orthogonal, touches no skeleton, frame or region.
- The prose budget is live; the baseline is 45 and may only shrink.

## Decisions        (append-only; supersede, never delete)
- Entries before 2026-08-29 are in sessions/ARCHIVE-2026.md.

- [2026-09-17] **A medium is a product, not a fourth design axis — but it rides the binder
  as the fourth keyword.** Theme/size/font leave the structure untouched; a medium changes
  skeleton, slot set, frame, constraints, lint and exporter, so it is chosen by class, then
  bound so templates can ask `medium.paged` — sessions/2026-09-17-2353-multi-medium-rescope.md
- [2026-09-17] **The frame belongs to the medium, not the density.** compact/spacious never
  change `FrameGeometry.width`; lift it to `PageFormat` and re-inject under `size.frame` so no
  template changes — sessions/2026-09-17-2353-multi-medium-rescope.md
- [2026-09-17] **Per-medium template trees with fallback, forked one template at a time.**
  `ChoiceLoader(templates/<medium>/, templates/shared/)` is "one template set" on day one and
  never a big bang; each fork is a golden-diffed PR with a stated reason —
  sessions/2026-09-17-2353-multi-medium-rescope.md

## Threads          (open items; remove when closed)
- **PR #167 is open for epic #157** (https://github.com/RorySullivan1/pyHermes/pull/167) and
  closes #157–#166 on merge. Next after it lands is #153. Every issue or PR body in this repo
  is written without angle brackets — GitHub's sanitizer has emptied three.
- **Two optional extras now.** `[pdf]` (WeasyPrint, needs Pango/Cairo) and `[qa]` (Playwright
  + pypdfium2). `[dev]` alone must stay free of both; their tests skip, which is the proof.
- **CLAUDE.md is a router**; the detail is in path-scoped `.claude/rules/*.md`, which load
  only when a matching file is read. Add reasoning there, not back into the router.
- **Factory hand-off for #140 is in `.claude/README.md`** — what claudeBrain should take,
  and the four rules worth inheriting.
- **The baseline may only shrink.** #138 and #139 empty it; nothing may be added.
- **Everything in `.claude/` is a factory asset** except `agents/python-developer.md` and
  `agents/finance-quantitative-developer.md`. No project name may enter the others.

## Log              (append-only pointers)
- Entries before 2026-08-29 are in sessions/ARCHIVE-2026.md.
- [2026-09-17 23:53] multi-medium-rescope — brainstormed the epic that makes email one
  `Medium` among paged/PDF/slides/HTML; inventoried the seams (mostly already there) and a
  nine-phase plan whose first four ship golden-identical —
  sessions/2026-09-17-2353-multi-medium-rescope.md
- [2026-09-18 00:20] multi-medium-rescope — all three design calls agreed; **filed epic #157**
  with sub-issues #158–#166, one per phase. Corrected the stale "backlog is empty": #150 and
  #153–#156 were open — sessions/2026-09-17-2353-multi-medium-rescope.md
- [2026-09-20] **A medium is a product, not a fourth axis — but it rides the binder as the
  fourth keyword.** Chosen by class; bound so a template can ask `medium.paged` —
  sessions/2026-09-17-2353-multi-medium-rescope.md
- [2026-09-20] **A check can be wrong about its scope, and fixing the code instead is the
  trap.** Four times in one epic: the theme test scanned one module, the golden harness made
  one directory, `page.html` used the wrong colour idiom, and a README-block check would have
  demanded prose parse as Python — sessions/2026-09-17-2353-multi-medium-rescope.md
- [2026-09-20] **A sentinel must perturb the CURRENT owner.** #159 moved the frame and the
  existing sentinel broke loudly; a subtler change would have left it green and meaningless —
  sessions/2026-09-17-2353-multi-medium-rescope.md
- [2026-09-20] **mypy's per-module override needs both `foo` and `foo.*`**, and a stale
  `.mypy_cache` hides the fix — sessions/2026-09-17-2353-multi-medium-rescope.md

- [2026-09-20 21:00] multi-medium-rescope — **epic #157 complete** (#158–#166): Medium,
  PageFormat, ChoiceLoader, DocumentMetadata, the paged medium, Page/Cover/running boxes/back
  matter, `svc/pdf` on WeasyPrint, the medium-aware harness, and the docs. Every email golden
  byte-identical throughout; the first real PDF found two defects no golden could see —
  sessions/2026-09-17-2353-multi-medium-rescope.md

- [2026-09-20 18:54] multi-medium-rescope — **PR #167 opened** for epic #157: 115 files, +5839
  /-576, 10 commits, `Closes #157` so #158–#166 close with it —
  https://github.com/RorySullivan1/pyHermes/pull/167
