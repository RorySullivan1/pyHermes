# 2026-08-20 12:05 · review-open-issues

**Goal:** Review open GitHub issues and recommend tackle order

## What happened
- Listed the 10 open issues (#5–#14). Padding trio #1/#2/#3 is **closed** — fixed by
  commit f8f0d7e, merged as PR #4. Memory INDEX was stale on that point.
- **Verified every issue claim by reproducing it**, not by reading. All bug reports
  (#5, #6, #7, #8) are accurate. Repro table:
  - #5 `TwoColumn(left=..., right=None).render()` → TemplateError (crash)
  - #6a colors shorter than cells → TemplateError `list object has no element 1` (crash)
  - #6b ragged cells vs headers → **no error**, silently misaligned table
  - #7 `Email(metadata={"firm_name":"Acme"})` → **no error**; `EmailMetadata.validate()`
    is genuinely never called
  - #8a `background_color="not-a-color"` → **no error**, malformed CSS ships
  - #8b bad ratio → bare `ValueError`, escapes the `EmailBuilderError` contract
- **Found an unfiled bug, more severe than #5** (see below).
- Delivered a ranking; no code changed this session.

## Gotchas & dead ends
- **UNFILED BUG — every container crashes when `title` is omitted.**
  `Container._base_context()` (svc/builder/containers.py:43-50) only injects
  `section_title` when a title is set, but all four container templates evaluate
  `{% if section_title %}`. Under Jinja2 `StrictUndefined`, testing an *undefined name*
  in an `{% if %}` raises — it does not fall through as falsey. So:
  `FullWidth(content=TextBlock("x")).render(engine)` → TemplateError.
  Affects `FullWidth`, `Highlight`, and all three `TwoColumn` ratios.
  Both the template docs ("Optional heading") and the signature
  (`title: Optional[str] = None`) advertise this as supported.
  - **Not a regression from PR #4** — present since the init commit (15e096e);
    confirmed with `git log -S"if section_title"`.
  - `test_builder.py` misses it because all 9 of its sections pass a title. Any future
    test suite must cover the title-less path.
  - Same root cause as #5: conditional context injection vs. unconditional template vars.
- General lesson: under `StrictUndefined`, the `if self.x: ctx["x"] = ...` pattern in
  `_base_context`/`render` is a landmine. Prefer always injecting the key with a default,
  or guard the template with `{{ x | default('') }}` / `is defined`.

## State at end
- **Shipped.** Filed the container-title bug as **#15**, then fixed the whole
  cluster (#5/#6/#7/#8/#15) in one commit on `claude/review-open-issues-rr8quq`.
- Extra bug found while verifying, not in any issue: the documented
  "empty colors = no colors" DataTable path **also** crashed —
  `row.colors[loop.index0]` on an empty list. Fixed by guarding the template
  with `{% elif row.colors and row.colors[loop.index0] %}`.
- `python test_builder.py` passes at 35.9 KB and `weekly_market_wrap_v2.html`
  is **byte-identical** to before the change — proof the happy path is untouched.

## Open threads
- Recommended order, pending user go-ahead:
  1. **Correctness cluster #5 + #6 + #7 + #8 + the unfiled title bug as ONE pass** —
     only issues producing wrong/crashed output today; same three files
     (`containers.py`, `components.py`, `models.py`); two shared root causes
     (conditional context injection; validation written but never wired up).
  2. #9 pytest suite — *after* the fixes, so the tests lock in the new error paths
     rather than being written against code about to change.
  3. #11 CI (needs #9), then #10 wheel packaging, #12 escaping helper,
     #13 stale docstring (5-min, batch it), #14 retire `assembler.py` (confirm first).
- #12 is ranked low on *current* impact only — it jumps to the top the moment newsletter
  content comes from any non-hand-curated source (a `"` in `ChartBlock(alt_text=...)`
  breaks the `alt` attribute outright).
- ~~Asked whether to file the container-title bug and start the cluster.~~ Done — user
  said go ahead; #15 filed, cluster fixed, PR opened.
- **#9 (pytest) is the natural next step** and is now much cheaper: the repro suite used
  to verify this work covers every fixed error path and can be lifted straight into
  `tests/` nearly as-is.
