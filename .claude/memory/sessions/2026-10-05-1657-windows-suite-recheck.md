# 2026-10-05 16:57 · windows-suite-recheck

**Goal:** Recheck seven Windows test failures on main; fix what remains

## What happened
- The owner reported 6 cp1252 `UnicodeDecodeError`s (bare `read_text()`) and 1 drive-letter
  `load_target` failure. On `main` @ `0d2139a`, Python 3.13, cp1252, no PYTHONUTF8: **both
  already fixed by #372** (`59edafa`): `tests/test_encoding.py` AST guard, and
  `pyhermes/check/target.py` takes `C:/`/`C:\` off before the last-colon split.
- One failure remained, in a test #372 itself added:
  `test_a_drive_path_with_a_callable_splits_on_the_last_colon` expected `No such file: C:/u/weekly.py`.
  The message formats a `Path`; a `WindowsPath` prints `C:\u\weekly.py`. Linux CI never sees it.
  Fixed the test regex to accept either separator. Also corrected qa-harness.md's preview-CLI
  sentence about the last-colon split.
- Full suite on Windows without PYTHONUTF8: 4089 passed, 384 skipped.

## Gotchas & dead ends
- **A `Path` in an error message is OS-shaped.** Any test matching a path in a message must
  accept `[/\\]`, or it passes on Linux CI and fails on Windows.
- The #372 guard checks `read_text`/`write_text` only, not `open()`; a grep found no text-mode
  `open()` in pyhermes/qa/tests today.
- The owner's Python 3.13 lacked `httplib2` and `requests` (declared `[dev]` deps), so
  `test_gmail.py`/`test_outlook.py` failed collection. Installed the two packages directly rather
  than `pip install -e .[dev]`, which would repoint the editable install at the worktree.

## State at end
- Branch `claude/cranky-tu-4cdb7c`: 2 files changed (tests/test_check.py, .claude/rules/qa-harness.md),
  uncommitted at the time of writing; offered commit + PR.

## Open threads
- None beyond landing the one-line test fix.
