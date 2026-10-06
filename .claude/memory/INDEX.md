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

## Decisions        (append-only; supersede, never delete)
- Older entries, and epic #157's, are in sessions/ARCHIVE-2026.md.
- [2026-09-28] **A test gated on an extra must run in some CI job, and a job list by hand is how three
  never did.** One all-extras job that fails on a skip its extra should lift — #239, sessions/2026-09-28-2015-package-review-issues.md
- [2026-10-01] **pyHermes grows by media, not by portability.** A DOCX/PPTX walk is a second render path
  over 46 classes, and a chart is PNG bytes by the time it is in the tree; #219 and #300 closed — `media.md`
- [2026-10-05] **A badge takes a tone, never a colour, and is square in Outlook by decision: no VML,
  nbsp padding in an mso conditional; a status dot is the same span unlabelled** — `design-axes.md` (#324)
- [2026-10-05] **A timeline spans no cell: a capsule marker the title's height, the rule a half-cell's
  border; a kicker is the `h2`'s sibling, never inside it; four kitchen_sink sections became two Stacks
  to pay for #329's bytes** — `design-axes.md`, `builder-architecture.md` (#329)
- [2026-10-05] **A grid is one exhibit: `leaves()` stops at any `Exhibit`, panels anchor `<grid>-<letter>`;
  a legend names theme colours (a hex is checked in `add_section`), never reads the plot; a section's
  source is `source_notes`, read by the walk after its blocks** — `apparatus.md`, `data-layer.md` (#335)
- [2026-10-05] **A turned page is a body table of its own (a named page is inert on a `tr`); a stamp is a
  fact set OVER the copy, translucent (under, grounds hid it), and no constructor `stamp=`; an aside is a
  value object rendered through `Callout`; a gallery QR is a module-matrix constant** — `media.md`, `brochure.md` (#340)
- [2026-10-05] **A brand tone is a name on the theme (`Theme.tones`), resolved by one `Theme.tone` every template
  reads, refused undeclared by a walk in `Document._add`; `section.background_color` stays a hex** — `design-axes.md` (#387)
- [2026-10-05] **On paper a split's column paints no fill; the band cell does** — an inline-table paints after
  every block background, so its fill overwrote the next section's half-pixel row at a band edge — `design-axes.md`
- [2026-10-06] **A house face rides `Document.fonts()`, never `assets()`; justify and fine print are paper's,
  unset in an email; BackMatter stays at `small`; a qualifier reaches the notes** — `design-axes.md` (#385)
- [2026-10-06] **Bleed is a negative-margin block, top edge only where the medium says the section opens a sheet;
  a pin floats to the footnote area (absolute overlapped); a separated row is one real table row** — `media.md`,
  `design-axes.md` (#386)

## Threads          (open items; remove when closed)
- **#394's ruling (justify on paper only) was taken under a goal**; the owner may widen it.
- **#400's ruling: `skip_first` is opt-in, not the default under an `EmptyCover`** (goal-taken; `media.md`).
- **A share table holds its share in Word's engine** (owner, via COM, PR #371); a real Outlook client
  is still #288's. The measure is `ch`: in Georgia 75ch sets ~99 characters (`design-axes.md`).
- **Outlook desktop's handling of `dir=rtl` on a reversed split is unverified here**, nor #319's VML
  arrow (or #399's connector), nor #325's square badge and dot, nor #331's empty rule cells (`font-size:0`), nor #337's legend
  swatch; all join #288's check.
- **`kitchen_sink` is at its 90 KB ceiling**: `modern_fonts` has 962 bytes left after #340, which untitled
  the three wide `ThreeColumn` ratios to pay for the stamp and the QR button; the next epic must merge or move.
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
