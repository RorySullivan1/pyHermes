# MEMORY INDEX  ·  keep ≤ ~80 lines, ≤ ~200 chars per line

## State            (rewrite in place — current truth only, ≤ ~10 lines)
- pyHermes builds **documents** and renders each onto a **medium**: `svc/builder` is the
  shared kit, `svc/email` and `svc/document` are the two media, and three exporters sit on
  one contract — `svc/delivery`+`gmail`+`outlook`, and `svc/pdf`. Rationale: CLAUDE.md and
  `.claude/rules/media.md`; do not restate it here.
- **Shipped and closed**: #157 rescope-to-media (PR #167), #153 disclosure (PR #168), #169
  pagination hardening (PR #190, #173–#176), #170 data layer (PR #191, `c76671c`, #177–#180).
- **#171 apparatus implemented on the branch** (#181–#185, `.claude/rules/apparatus.md`); its PR
  closes all six. Next: #172 brochure. #150 needs a real Outlook host.
- The prose budget is live; the baseline is 45 and may only shrink.

## Decisions        (append-only; supersede, never delete)
- Older entries, and epic #157's, are in sessions/ARCHIVE-2026.md.

- [2026-09-17] **A medium is a product, not a fourth design axis — but it rides the binder
  as the fourth keyword.** Theme/size/font leave the structure untouched; a medium changes
  skeleton, slot set, frame, constraints, lint and exporter, so it is chosen by class, then
  bound so templates can ask `medium.paged` — sessions/2026-09-17-2353-multi-medium-rescope.md

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

## Threads          (open items; remove when closed)
- **Every issue or PR body is written without angle brackets** — GitHub's sanitizer has
  emptied three.
- **A closing keyword closes only the issue it names, and this is now proven both ways.**
  #167 named only the epic and left all nine children open; #168 and #191 named every issue
  and closed every one. One `Closes #N` per sub-issue, and check that summary after
  any epic merge.
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
- Older entries, and epic #157's, are in sessions/ARCHIVE-2026.md.
- [2026-09-20] **A check can be wrong about its scope, and fixing the code instead is the
  trap.** Four times in one epic: the theme test scanned one module, the golden harness made
  one directory, `page.html` used the wrong colour idiom, and a README-block check would have
  demanded prose parse as Python — sessions/2026-09-17-2353-multi-medium-rescope.md

- [2026-09-22 21:00] data-layer — **#170 shipped, PR #191**: formatters, tone, `svc.data` adapters.
  No `from_frame`: the purity test wins. mypy's `follow_imports="skip"` is ignored for `.pyi`
  unless `follow_imports_for_stubs=true` — sessions/2026-09-22-2100-data-layer.md

- [2026-09-22 22:00] document-apparatus — **#171 implemented**, six commits: anchors, numbering,
  contents, footnotes, xrefs, running section. Every mechanism probed under WeasyPrint 70 first
  — sessions/2026-09-22-2200-document-apparatus.md
