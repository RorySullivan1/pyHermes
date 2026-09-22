# MEMORY INDEX  ·  keep ≤ ~80 lines, ≤ ~200 chars per line

## State            (rewrite in place — current truth only, ≤ ~10 lines)
- pyHermes builds **documents** and renders each onto a **medium**: `svc/builder` is the
  shared kit, `svc/email` and `svc/document` are the two media, and three exporters sit on
  one contract — `svc/delivery`+`gmail`+`outlook`, and `svc/pdf`. Rationale: CLAUDE.md and
  `.claude/rules/media.md`; do not restate it here.
- **Both epics are SHIPPED and closed**: #157 rescope-to-media (PR #167, `eff6ece`, #158–#166,
  golden-identical) and #153 per-exhibit disclosure (PR #168, `72eb30a`, #154–#156).
- **Four epics filed 2026-09-22 from the format-coverage audit**, in dependency order:
  #169 pagination hardening (#173–#176) → #170 data layer (#177–#180) → #171 document
  apparatus (#181–#185) → #172 brochure medium (#186–#189). Plus #150 (needs a real Outlook).
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

## Threads          (open items; remove when closed)
- **Start with #173** (`thead`/`tbody`) — the cheapest high-value fix in the backlog, verified
  against WeasyPrint 70 before filing. Every issue or PR body in this repo is written without
  angle brackets — GitHub's sanitizer has emptied three.
- **A closing keyword closes only the issue it names, and this is now proven both ways.**
  #167 named only the epic and left all nine children open; #168 named all four and closed all
  four (`sub_issues_summary` 3/3). One `Closes #N` per sub-issue, and check that summary after
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


- [2026-09-22 11:17] per-exhibit-disclosure — **PR #168 merged** (`72eb30a`): 28 files, +580/-47.
  #153–#156 all closed by their own keywords, confirming the #167 lesson from the other side —
  sessions/2026-09-21-per-exhibit-disclosure.md

- [2026-09-22 13:51] format-coverage-audit — read-only sweep of `svc/` and every template against
  emails, brochures and factsheets. Nothing changed; the shared markup's missing `thead` is the
  find — sessions/2026-09-22-1351-format-coverage-audit.md

- [2026-09-22 14:07] format-coverage-audit — **filed the four epics** #169–#172 and their seventeen
  sub-issues #173–#189, every claim re-verified against the templates and WeasyPrint 70 first —
  sessions/2026-09-22-1351-format-coverage-audit.md
