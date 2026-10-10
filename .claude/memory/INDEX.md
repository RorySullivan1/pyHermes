# MEMORY INDEX  ·  keep ≤ ~80 lines, ≤ ~200 chars per line

## State            (rewrite in place — current truth only, ≤ ~10 lines)
- pyHermes builds **documents** and renders each onto a **medium**: `pyhermes/builder` is the
  shared kit, `pyhermes/email`, `document`, `brochure` and `deck` are the media, and exporters sit on
  one contract — `delivery`+`gmail`+`outlook`, and `pdf`. Rationale: CLAUDE.md and `media.md`.
- **Shipped through PR #414** (epic #386); #402 is in the PR after it. Epics #157–#220 and #218 (PRs #167–#314); deck bugs #315–#317
  (PR #369); #361 (PR #370); #354 and #372 (PR #371); #318 (PR #373); #346 (PR #374); #324 (PR #376);
  #329 (PR #378); #335 (PR #380); #340 (PR #382); #384 (PRs #406, #411, #412); #385 (PR #413); the paper band seam (PR #408). #219 DOCX and #300
  PPTX were closed as not planned (2026-10-01, `media.md`). #288 is the owner's Outlook-desktop check.
- The prose budget is live; the baseline is 44 and may only shrink.
- **Open from the 2026-10-10 review**: epics #418 (delivery contract, #420–#425) and #419 (render path once, #426–#428),
  open; the seven standalone bugs #429–#435 are fixed in one PR (2026-10-10). sessions/2026-10-10-1725-codebase-review-issues.md

## Decisions        (append-only; supersede, never delete)
- Older entries, and epic #157's, are in sessions/ARCHIVE-2026.md.
- [2026-09-28] **A test gated on an extra must run in some CI job, and a job list by hand is how three
  never did.** One all-extras job that fails on a skip its extra should lift — #239, sessions/2026-09-28-2015-package-review-issues.md
- [2026-10-01] **pyHermes grows by media, not by portability.** A DOCX/PPTX walk is a second render path
  over 46 classes, and a chart is PNG bytes by the time it is in the tree; #219 and #300 closed — `media.md`
- [2026-10-06] **A house face rides `Document.fonts()`, never `assets()`; justify and fine print are paper's,
  unset in an email; BackMatter stays at `small`; a qualifier reaches the notes** — `design-axes.md` (#385)
- [2026-10-06] **Bleed is a negative-margin block, top edge only where the medium says the section opens a sheet;
  a pin floats to the footnote area (absolute overlapped); a separated row is one real table row** — `media.md`,
  `design-axes.md` (#386)
- [2026-10-09] **A size is read from the system, never typed (owner's principle, standing rule 13):
  `content_width()` for a picture's cell, `SizeTheme` for a density, a named constant for an asset's
  own size; the gallery is exempt** — `working-in-the-code.md`, `design-axes.md`

## Threads          (open items; remove when closed)
- **#394's ruling (justify on paper only) was taken under a goal**; the owner may widen it.
- **#400's ruling: `skip_first` is opt-in, not the default under an `EmptyCover`** (goal-taken; `media.md`).
- **A share table holds its share in Word's engine** (owner, via COM, PR #371); a real Outlook client
  is still #288's. The measure is `ch`: in Georgia 75ch sets ~99 characters (`design-axes.md`).
- **Outlook desktop's handling of `dir=rtl` on a reversed split is unverified here**, nor #319's VML
  arrow (or #399's connector), nor #325's square badge and dot, nor #331's empty rule cells (`font-size:0`), nor #337's legend
  swatch; all join #288's check.
- **`kitchen_sink` is at its 90 KB ceiling**: `modern_fonts` has 357 bytes left after the phone-margin fixes
  (+330), and #340 before it untitled the three wide `ThreeColumn` ratios; the next epic must merge or move.
- **The suite runs on Windows since #372** (PR #371); no Windows CI job — the owner's run is the check.
- **`epic-autoclose` works** (closed #273, #354, #361, #346, #324, #329, #335). Still confirm each epic closed after its merge.
- **In this container, PDF byte-determinism tests flake** (no HarfBuzz-Subset), and screenshot
  tests skip unless `PYHERMES_CHROMIUM=/opt/pw-browsers/chromium-1194/chrome-linux/chrome`.
- **Every issue or PR body is written without angle brackets** — GitHub's sanitizer has
  emptied three.
- **A closing keyword closes only the issue it names, and this is now proven both ways.**
  #167 named only the epic and left all nine children open; #168, #191 and #192 named every
  issue and closed every one. One `Closes #N` per sub-issue, and check that summary after
  any epic merge.
- **Six optional extras:** `[pdf]`, `[qa]`, `[data]`, `[charts]`, `[math]`, `[qr]` (#344; `zxing-cpp` joined
  `[qa]` as the decoder). `[dev]` alone stays free of
  them; CI's `all-extras` fails on any skip naming one (#239), so a skip reason must name its extra.
- **CLAUDE.md is a router**; the detail is in path-scoped `.claude/rules/*.md`, which load
  only when a matching file is read. Add reasoning there, not back into the router.
- **Factory hand-off for #140 is in `.claude/README.md`** — what claudeBrain should take,
  and the four rules worth inheriting.
- **The baseline may only shrink.** #138 and #139 empty it; nothing may be added.
- **Everything in `.claude/` is a factory asset** except `agents/python-developer.md` and
  `agents/finance-quantitative-developer.md`. No project name may enter the others.

## Log              (append-only pointers)
- Older entries, and epic #157's, are in sessions/ARCHIVE-2026.md.
- [2026-10-05] windows — the 7 reported Windows failures were already fixed by #372; its own drive-path
  test still failed (a `WindowsPath` prints backslashes), fixed — sessions/2026-10-05-1657-windows-suite-recheck.md
- [2026-10-05] paper-band-seam — 1px seam at a band edge on paper, fixed in `columns.html`;
  paint order, two forms — sessions/2026-10-05-1903-paper-band-seam.md
- [2026-10-06] memory — the index trimmed to budget: five 2026-10-05 log pointers archived, #387 and the
  seam thread closed.
- [2026-10-06] print-typography — epic #385 built in one PR — sessions/2026-10-06-print-typography.md
- [2026-10-06] single-sheet-print — epic #386 built in one PR — sessions/2026-10-06-single-sheet-print.md
- [2026-10-06] adjacent-markers — #402: a footnote marker after another opens on a comma, `apparatus.md`.
- [2026-10-10] codebase-review-issues — **19 review findings filed as 18 issues**: #418, #419 and children,
  bugs #429–#435; every finding re-probed on `ac0a8a4` — sessions/2026-10-10-1725-codebase-review-issues.md
- [2026-10-10] standalone-bugs — #429–#435 fixed in one PR: a scheme never follows / ? #, one cid one payload,
  `kept_sections` scoped, one `metadata()`, `hang()` never splits a word, unique frame columns, the copyright from its parts.
