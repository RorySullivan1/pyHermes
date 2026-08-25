# 2026-08-25 12:18 · screenshot-runner

**Goal:** Land #59 — headless-Chromium screenshot runner over the fixture gallery

## What happened

- **`qa/screenshots.py`** — `python -m qa.screenshots [fixture ...]` renders every gallery
  fixture at two viewports into `output/screenshots/` (gitignored), plus a `run.json`
  recording what produced them.
- **`tests/test_screenshots.py`** (15 tests) — the pure half (cid inlining, PNG measurement,
  fixture selection, error paths) runs everywhere; the capture half skips without a browser.
- **CI**: new `screenshots` job installs `.[dev,qa]` + `playwright install --with-deps
  chromium`, runs the capture tests, renders the gallery, uploads PNGs + `run.json`.
- **The runner found a real bug on its first run** → filed as **#76** (see below).
- 651 tests with a browser, 646 + 5 skips without. ruff / format / mypy clean.
  Branch `claude/review-open-issues-rr8quq` @ `57b8846`, pushed. No PR yet.

## The decision that shapes the rest

**The user chose: screenshots are CHECKS, not artifacts** — never diffed, never committed.
Therefore the **browser build is recorded, not pinned**. Pinning (a versioned container or a
Playwright-managed browser) buys cross-machine reproducibility that an image a human glances
at does not need. What *is* pinned: viewport sizes, `device_scale_factor=1`, full-page
capture. `run.json` carries the Chromium build, Playwright version, platform and resolved
executable — so if pixel-diff gating ever arrives (explicit non-goal of #54 v1), that record
says whether two sets are comparable and pinning becomes deliberate rather than inherited.

This is a **deliberate deviation from #59's acceptance criterion 4**, which proposed pinning
the browser via a pinned Playwright. Recorded here and in the PR body when one is opened.

## Gotchas & dead ends

- **The container's Chromium and Playwright's expected revision disagree.** `playwright
  1.62.0` wants `chromium_headless_shell-1234`; the image ships `-1194` and sets
  `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`, so `playwright install` is not an option. Fixed with
  an **`PYHERMES_CHROMIUM` env var** naming an executable (here
  `/opt/pw-browsers/chromium`, a symlink to the full `chrome` binary — *not* the headless
  shell). Auto-probing that path was rejected: hardcoding a vendor path is exactly the
  accidental pinning the design avoids.
- **`cid:` must be rewritten to data URIs or the screenshots are worthless** — a browser has
  no MIME message, so every attached image renders as a broken-image icon. Bytes come from
  `Email.assets()`, so the substitution is exact. Screenshot copy only; `render()` and the
  goldens are untouched (a test asserts it).
- **Rewrite `src="cid:…"`, never the bare substring.** `image_matrix` titles a section
  **"Attached (cid:)"** — a substring substitution corrupts copy. Found by a *failing test*,
  not foresight: the naive assertion `"cid:" not in inlined` failed on that title.
- **Block external requests.** Fixtures point at `cdn.example.com`; unblocked, every run
  waits on DNS that never resolves. Blocked, the render shows what a reader with images off
  sees — Outlook's default state.
- **Measure the PNG's own IHDR, not the DOM.** The image is the artifact. A full-page capture
  is as wide as the *document*, so an image wider than its viewport is real information —
  which is precisely how #76 surfaced.
- **Playwright handles are typed `Any` on purpose**: `[qa]` is optional, so playwright is not
  installed in the environment mypy runs in (CI's `check` job takes `[dev]` only).
- Skip-not-fail was verified **both ways**: with `PYHERMES_CHROMIUM` bogus (5 skips) and with
  it set (651 pass).

## #76 — the bug the runner found

`kitchen_sink` renders **387px wide at a 375px viewport**; the reader gets a horizontal
scrollbar. Cause: `base.html`'s mobile rule `.kpi-cell { display:block; width:100%;
padding:14px 16px }` — email HTML has no `box-sizing:border-box`, so under `content-box` the
padding is added *outside* the declared width. Invisible to every check that existed: the
HTML is byte-identical to its golden, the size gate passes, nothing measured layout.

**Not fixed in #59, deliberately** — `base.html` is the surface #38/#45/#46/#55/#56 contend
on, and touching it moves the `kitchen_sink` golden, which is a claim that a visual change is
intended. Preferred fix (in the issue): drop the redundant `width:100%`, since `display:block`
already fills the container and needs no property Outlook lacks.

## Open threads

- **#59 needs a PR** (branch has one commit; nothing opened — needs the user's go-ahead).
  Its body should record the pin-vs-record deviation from acceptance criterion 4.
- Epic #54 remainder: **#60 lint** ∥ then #61 preview CLI → #62 docs. #43/#50 now have their
  eyeball artifacts.
- #60's risk note stands: curate the Outlook-unsupported-CSS list rather than scraping it — a
  noisy linter gets disabled, which is worse than none. Note #76 is exactly the class of bug a
  CSS linter would *not* catch (the property is valid; the box model is the problem), so #60
  and screenshots are genuinely complementary rather than overlapping.
