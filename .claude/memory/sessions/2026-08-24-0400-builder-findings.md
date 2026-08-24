# 2026-08-24 04:00 · builder-findings

**Goal:** Resolve #72 and #73 — the two builder-contract findings the delivery epic surfaced — and push onto PR #74.

## What happened
- **#72** — added a read-only `Email.metadata` property, and made `build_message(subject=...)` optional with a fallback to `email.metadata.email_subject`.
- **#73** — rewrote `_validate_content_id`'s message so it stops promising that delivery adds `@` to a Content-ID.
- 11 new tests (521 total); ruff / format / mypy green; the reworked CLAUDE.md example was run rather than assumed.

## Gotchas & dead ends
- **The finding that decided #72: opacity was already illusory.** `EmailMetadata` is a plain mutable `@dataclass`, and `Email.__init__` does `self._metadata = metadata` — storing the *caller's own object*, no copy. So anyone passing an `EmailMetadata` already held a live reference; only the dict path was ever opaque. The issue's "is `Email` deliberately write-only?" framing didn't survive contact with the code — it was write-only by accident, and only half the time. That made "expose it" the low-risk answer.
- Returning a **copy** was considered and rejected: mutating a copy silently does nothing, a subtler trap than the one it closes. The property returns the instance and documents that post-construction mutation is unsupported (it skips `validate()`).
- **`metadata` must NOT go on the `RenderableEmail` protocol.** `EmailBuilder.metadata(data)` is a fluent *setter method*; a protocol member typed as `EmailMetadata` would make `EmailBuilder` stop satisfying a protocol it legitimately satisfies for `render()`/`assets()`. Resolved by duck-typing through `getattr`, with an unbuilt builder falling through to an error that names `.build()` — and a test pinning that wart deliberately.
- Kept `subject=""` an error rather than a fallback: an explicit empty string is a mistake, not a request.

## State at end
- Branch `claude/review-open-issues-rr8quq` (PR #74), 521 tests green. Epic #52 complete; #72/#73 closed by this work.

## Open threads
- **No README** — still the outstanding repo gap.
- Next by the contention analysis: #57 → #58 (fixture gallery + golden harness), then evacuate `base.html` via #33 + #63.
