# 2026-08-24 16:00 · package-config

**Goal:** Make the arbitrary magic numbers scattered through the package controllable
through some form of package config (user request).

## What happened
- Added **`svc/config.py`**: one frozen `Config` dataclass + `get_config()` / `set_config()` /
  `config_override()` / `Config.from_env()`. Ten fields: `size_limit_kb`, `size_warn_kb`,
  `inline_image_limit_kb`, the five retry knobs (`retry_max_attempts`, `retry_initial_delay`,
  `retry_backoff_factor`, `retry_max_delay`, `retry_max_hint_delay`),
  `request_timeout_seconds`, `error_body_excerpt_chars`.
- Wired at the four use sites: `Email._validate_size` (`svc/builder/email.py`),
  `EmailImage.inline`'s cap (`svc/builder/images.py`), `retry_with_backoff`
  (`svc/delivery/retry.py`), and `GraphApiTransport` + `_body_of` (`svc/outlook/sender.py`).
  Nothing in `svc/gmail` needed it — its timeout belongs to the caller's googleapiclient.
- `tests/test_config.py`: 32 tests in four classes; the fourth, **`TestTheWiringIsLive`**,
  changes each value and asserts behaviour follows. That class is the deliverable — the other
  three only test the dataclass.
- CLAUDE.md gains a `## Configuration — svc/config` section (the judgment-call vs
  fact-about-the-world line, the five rules, and an "adding a tunable" recipe) plus
  cross-references from the 102 KB and inline-cap bullets and delivery-consumer rule 3.
- Full gate green: **593 tests**, ruff, `ruff format --check`, mypy. Commit `68ddb8d`.

## Decisions
- **Judgment call vs fact about the world is the whole selection rule.** Configurable: numbers
  somebody *picked*. Not configurable and staying literals: `ACCEPTED = 202`, the transient
  status families, the Content-ID charset/length, the 680 px frame (that's epic #45's, as a
  *theme*, not a free-form number).
- `size_limit_kb` is included deliberately even though 102 KB is a real Gmail limit — a
  non-Gmail channel is legitimately not subject to it, so it is configurable *and* documented
  as a fact, keeping a raise a conscious act rather than a knob turned to pass a test.
- **Never read the environment on import.** `from_env()` is explicit; `svc/delivery`'s purity
  and its byte-for-byte dry-run guarantee is the first thing ambient state would cost.
- **Read via `get_config()` at use time, never bind at import.** Public constants
  (`INLINE_LIMIT_KB`, `DEFAULT_TIMEOUT_SECONDS`, `_SIZE_LIMIT_KB`) stay as the mirrored
  *shipped default* — tests build payloads relative to them — while the enforced value is the
  active config's.
- **Explicit argument beats config**: `retry_with_backoff`'s numeric params became
  `| None = None` meaning "ask the config"; passing one still wins.
- Config validation raises plain **`ValueError`**, joining neither the `EmailBuilderError`
  nor the `DeliveryError` tree — a bad limit is a setup/programming error, not rejected data.

## Gotchas & dead ends
- **A cross-field rule makes partial overrides fail, and that is correct.**
  `config_override(size_limit_kb=10)` alone raises, because the default
  `inline_image_limit_kb=48` then exceeds the whole budget. First instinct was to blame the
  rule; the rule was right and the *test* was incomplete. Overrides that lower
  `size_limit_kb` must lower `inline_image_limit_kb` with it.
- **`None` was already taken.** For `GraphApiTransport(timeout=...)`, `None` means *no*
  timeout, so it cannot also mean "unspecified" — needed a private `_USE_CONFIGURED` sentinel.
  Same trap will hit any future nullable tunable.
- Making a KB field a float broke `b"\x00" * (INLINE_LIMIT_KB * 1024)` in an existing test:
  KB thresholds are honestly ints (delays are not), and a public constant must not change
  type under callers.
- `mypy` on PATH is `/root/.local/bin/mypy`, on an interpreter that cannot see jinja2, so it
  reports two phantom import errors. **Run `python -m mypy`.**

## State at end
- `claude/review-open-issues-rr8quq` @ `68ddb8d`, pushed to PR #74. 593 tests green.

## Open threads
- `svc/config.py` is not re-exported from `svc/__init__.py` (which re-exports nothing by
  design) — callers use `from svc.config import ...`.
- When epic #45 lands, the 680 px frame becomes a *theme*, not a Config field; keep them
  separate.
