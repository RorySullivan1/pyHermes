# 2026-08-23 21:15 · delivery-foundation

**Goal:** Set execution priority across the backlog, then start #52 — and actually ship code.

## What happened

### Priority analysis (no code)
- Grounded it in contention, not value: `base.html` is **277 lines** and `EmailMetadata` **21 fields**; 5 issues queue on the first (#33/#41/#42/#49/#63), 4 on the second (#34/#40/#48/#64). With 36 open issues and 0 shipped, ordering is about not serialising on two files.
- Recommended: (0) #57→#58 golden harness, closing #32 — gallery-first so the harness isn't built twice; (1) **evacuate `base.html`** via #33 + #63 back-to-back (header ~120 + footer ~90 of 277 lines leave, so migrations then touch three files instead of one); (2) themes; parallel track = #52, the only epic with zero contention.

### #52 built out + #68 shipped
- Filed **#68** (foundation), **#69** (Gmail + shared retry), **#70** (Outlook + transport choice), **#71** (docs), linked all four, rewrote the epic body. Slicing deviations recorded on the epic: dry-run folded into #68 (unverifiable PR otherwise), retry folded into #69 (undesignable without a failing transport).
- Filed **#72** against the *builder*, per #52 principle 1 — see gotchas.
- **Implemented #68**: `svc/delivery/{__init__,exceptions,message}.py` — `DeliveryError`/`MessageError`, `build_message()`, `save_eml()`, `collect_cid_references()`. 27 new tests, **406 total**, ruff/format/mypy clean, wheel verified locally (built it, installed into a clean venv outside the tree, assembled + reparsed a `multipart/related` message).
- Corrected CLAUDE.md's now-false claims (delivery "does not exist", "None open" issues) and added a concise `## Architecture — svc/delivery` section. Full consumer-side docs + adapter guides stay with #71.

## Gotchas & dead ends
- **Verified two MIME behaviours empirically instead of assuming** (both are now load-bearing):
  - `EmailMessage.add_related(cid=...)` stores the value **verbatim** — a bare `content_id` yields an RFC-invalid `Content-ID` header. Assembly must pass `<id>`.
  - Passing `filename` **without** `disposition="inline"` yields `Content-Disposition: attachment` — inline art shows as a paperclip. Correct incantation: `set_content(html, subtype="html")` → `make_related()` → `add_related(..., cid="<id>", disposition="inline")`.
- **The predicted contract gap appeared immediately (#72).** `Email` publishes `render()`/`assets()` but nothing to read its own metadata, so delivery can't default the `Subject` header without touching `_metadata`. Filed rather than worked around; `build_message(subject=...)` is required for now (defensible anyway — the envelope is the sender's business).
- CID references live in **CSS too** (`url(cid:…)` from `header_bg_image_url`), not just `src=`. An attribute-startswith check alone would miss them.

## State at end
- Branch `claude/review-open-issues-rr8quq` carries the delivery foundation + memory logs; `main` still at `07d5609`.
- 406 tests green; full local gate (pytest/ruff/format/mypy/wheel) passing.

## Open threads
- #69 Gmail next: it sets the adapter shape **and** the retry policy #70 reuses.
- #72 needs a decision (public `Email.metadata` vs documented opacity); if an accessor lands, `build_message`'s `subject` becomes optional.
- The `multipart/alternative` slot is left open for plain-text (#53).
