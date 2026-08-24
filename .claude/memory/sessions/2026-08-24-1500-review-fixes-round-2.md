# 2026-08-24 15:00 · review-fixes-round-2

**Goal:** Fix all findings from two code-review passes over PR #74 (the delivery epic), using parallel agents.

## What happened
- Two review passes overlapped heavily; consolidated to **8 unique findings** across 4 files, then partitioned **1 agent per file** (retry / message / gmail / outlook) so nothing collided. All four cherry-picked with zero conflicts.
- **I verified the headline finding myself before dispatching, and both reviews had it half-wrong.** They implied "broaden the isinstance check". Measured: `requests.exceptions.ConnectionError`/`Timeout` are `OSError` but not the builtins ✅ finding real — but `requests.exceptions.HTTPError` is *also* `OSError` (so broadening makes a 400 "transient"), and `httplib2.ServerNotFoundError` is *not* `OSError` at all (so broadening doesn't even fix Gmail's own transport). Mandated **status-first ordering** to both adapter agents instead.
- Fixes: `Retry-After` given its own `max_hint_delay` ceiling (a8538af) · `cid:` collected only from fetching attributes (684ecb9) · Gmail status-first + 403-by-reason + `max_attempts` guard (3548bc3) · Outlook URL-encoding + timeout + status-first + `max_attempts` (67c0b0b). **561 tests**, all gates green.

## Gotchas & dead ends
- **The two adapter agents solved the same sub-problem differently**: Gmail hard-imported `requests`/`httplib2`; Outlook used `pytest.importorskip`. Neither is wrong in isolation, but shipping both is incoherent. Harmonised on hard imports + **declared dev deps**, because a silently-skipped test rebuilds the exact blind spot being fixed. `pyproject.toml` was outside every agent's scope — the coordinator has to own cross-cutting config.
- A commit that adds tests importing an undeclared library **breaks CI on its own**, so the pyproject change was *amended into* the Gmail commit rather than following it — no commit in history lands red.
- The Gmail agent went further than asked on F3 and fetched Google's live error-handling guide, confirming `rateLimitExceeded`/`userRateLimitExceeded` carry `code: 403` with explicit backoff guidance. That evidence (and its URL) is cited in the code, so the claim is checkable later.
- **4 of 4 worktrees again started from a commit with no `svc/delivery`.** This is now the default expectation, not a surprise.

## State at end
- PR #74: 4 review-fix commits on top of the epic. 561 tests, ruff/format/mypy green, pushed.

## Open threads
- **No README** — still the outstanding repo gap.
- `max_hint_delay = 300s` is a judgment call, not a documented Graph maximum.
- Outlook's `_NETWORK_ERROR_NAMES` name-matching is an acknowledged heuristic for clients whose exceptions don't derive from `OSError`.
