# 2026-08-24 03:30 · delivery-docs-and-pr

**Goal:** Close #71 (docs) and open the PR taking epic #52 to `main`.

## What happened
- **#71 scoped against what already existed** rather than against its own checklist. CLAUDE.md already carried architecture sections for delivery/gmail/outlook from #68–#70, so the genuinely missing pieces were:
  - **`### Writing a delivery consumer`** — the seven rules both adapters share, so a third (a generic SMTP sender) transplants instead of re-deriving: authorized transport not credentials; serialise via `to_wire_bytes()`; reuse `retry_with_backoff` with your own `is_transient`; never retry an unrecognised failure; map to `TransportError` chaining; name provider differences in the docstring; test against a fake. Plus the standing rule that an insufficient builder contract gets *filed* (#72/#73), never worked around from delivery code.
  - **`### Deliberate non-features`** — eight decisions in one table (no `Date`/`Message-ID`, no `Bcc`, no plain-text yet, no size re-check, no OAuth flows, no campaign management, no tracking, no HTTP-date `Retry-After`).
  - Corrected the stale **"Scope today"** paragraph (was "builder plus MIME assembly, adapters not built") and the **Open work** section (#52 complete; #72/#73 named).
- **Adapter setup guides: decided they belong in module docstrings**, not a separate document. No README or `docs/` tree exists, and CLAUDE.md is Claude-facing architecture — a usage example belongs where a developer opening the module lands.
- **Docs verified by execution**, per #71's own criterion: all 24 `from svc… import …` symbols CLAUDE.md names resolve; the delivery example runs and writes an `.eml`; the adapters' documented return types confirmed (`str` for Gmail, `None` for Graph).
- Opened the PR for epic #52: 14 commits, `svc/delivery` + `svc/gmail` + `svc/outlook` + 4 test modules, 510 tests.

## Gotchas & dead ends
- Nearly wrote a fourth delivery-ish CLAUDE.md section before checking; the existing three already covered structure, purity, the seam check, retry and the transport choice. Reading first turned a redundant section into two focused subsections.

## State at end
- **Epic #52 complete** (#68–#71). 510 tests, ruff/format/mypy green, wheel verified for both adapters.
- PR open against `main`; branch `claude/review-open-issues-rr8quq`.

## Open threads
- **No README exists** — a real gap now the project can build *and* send. Out of #71's scope; worth filing.
- #72 / #73 await decisions (neither blocking).
- Next epic by the contention analysis: #57 → #58 (fixture gallery + golden harness), then evacuate `base.html` via #33 + #63.
