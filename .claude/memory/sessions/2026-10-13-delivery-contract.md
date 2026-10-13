# 2026-10-13 — epic #418, every send keeps the delivery error contract

Implemented #420–#425 on `claude/integrate-claude-assets-pyhermes-d4spzb`, restarted from `main` at
`cdfdc32` (PR #437 had merged). One PR, one `Fixes #N` / `Closes #N` line per sub-issue.

- **#420** Outlook `send_message` checks `max_attempts` before any attempt (Gmail's shape) and no
  longer exempts `ValueError` from the `TransportError` wrap.
- **#421** `retry_with_backoff` ignores a negative or NaN hint (`hinted >= 0`), so the ladder applies;
  zero is honoured. Chosen over clamping to zero: an unreadable hint is no hint.
- **#422** `filename_problem()` in `builder/images.py`: empty, `.`/`..`, a separator, any C0 control
  or DEL. `Attachment` (MessageError), a CID `EmailImage` and `ImageAsset` (ValidationError) share it.
  `create_draft` also writes each part under its last path segment (`_base_name`).
- **#423** `_recipients` parses with `getaddresses`; a named address goes as `"name" <addr>`.
- **#424** The wire budget runs on every message and names inline images; wording kept
  (`attachment limit`, `with attachments`) so the existing tests stand. One test that pinned the
  old decision was replaced.
- **#425** `PERMANENT_ERROR_NAMES` + `is_permanent_failure()` in `delivery/retry.py`, checked over
  the MRO before each adapter's `OSError` rule.

`tests/test_delivery_contract.py` runs each case through both adapters. Every new test was run
against the old source and failed there. The prose baseline shrank 44 → 43 (the Outlook comment
the fix removed). Same container flake: two PDF byte-determinism tests fail on `main` too.
