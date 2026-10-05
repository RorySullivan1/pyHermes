# 2026-09-28 20:15 · package-review-issues

**Goal:** File the 2026-09-28 package review's findings as work: two epics, one coverage task, three bugs.

Planning only; no source changed. The review (`/code-review` of the package as a whole, focus on
flexibility, deployment and coverage) ran twice and agreed; every claim was re-grounded against
`main` @ `7b5cc7c` before filing. Filed through the `github-issues` pipeline; the `fill-self`
diff was printed each time and every body was updated once.

| Issue | What | Depends on |
|---|---|---|
| #237 | Epic: the package as a consumer sees it (deployment) | |
| #243 | `svc/py.typed` and a wheel-job mypy consumer check | none |
| #244 | Metadata (description, readme, licence, classifiers, urls), sdist `only-include`, `twine check`, sdist listing | none |
| #245 | Matrix 3.11 to 3.14; one extras job on the 3.11 floor | none |
| #248 | Decide `svc` vs `pyhermes` import root; recommend the rename with a warning shim | #243, #244 |
| #238 | Epic: seams for a host application (flexibility) | |
| #246 | `SizeWarning`/`PrintQualityWarning` via `warnings.warn`; drop the success print; AST no-print test | none |
| #249 | `ContextVar` layered over the global config; `Document(config=)`, `build_message(config=)` | #246 |
| #247 | `template_overlay` on Document/Email/EmailBuilder, searched overlay, medium, root | none |
| #239 | Task: an `all-extras` CI job plus `PYHERMES_REQUIRE_EXTRAS` conftest rule (coverage) | none |
| #240 | Bug: both senders hardcode `max_attempts=3`, so `Config.retry_max_attempts` is dead | |
| #241 | Bug: `svc.pdf.available()` and `_backend()` catch `ImportError` only; WeasyPrint without Pango raises `OSError` | |
| #242 | Bug: `GraphApiTransport` resolves `request_timeout_seconds` in `__init__`, against the read-at-use contract | |

## What the review found, grounded
- Three tests have never run in CI: the factsheet two-sheet pin (needs `[pdf]` and `[charts]`,
  no job installs both), the Chromium decimal-alignment test and the preview capture test (browser
  gated, absent from the `screenshots` job's list). `addopts = "-q"` hides the skips.
- Deployment: import root `svc`, no `py.typed`, description still "newsletter HTML email builder",
  no readme/licence/classifiers/urls, wheel-only build (sdist would carry `.claude/` 2.2 MB and
  `tests/` 4.8 MB), matrix 3.11 and 3.13 only.
- Flexibility: four `print` sites vs two `warnings.warn`; `Config` is a module global with no
  per-document injection; `TemplateEngine` has no overlay, only `template_dir` replacing the tree.
- Verified clean: the `check` job is genuinely extra-free; every backend import is lazy;
  `Config.from_env` handles bool and `float | None`.

## Decisions and why
- **Bugs filed standalone, not under an epic.** Each is one PR and closes with its own `Fixes`.
- **Coverage is a task, not an epic.** One PR; it lands first because it changes what every later
  PR is measured against.
- **The rename is the last child of #237**, behind the sdist and wheel checks that prove a rename
  shipped whole; the issue recommends the rename with a one-release `svc` shim.

**Next:** the owner said the bug issues (#240, #241, #242) are the next work. #239 is the other
one-PR item. `.github/workflows/epic-autoclose.yml` is installed, so #237 and #238 close from
their children.

## The three bug fixes, same day
Each on its own branch from `main`, one PR each: #240 → PR #250 (`fix-240`), #241 → PR #251
(`fix-241`), #242 → PR #252 (`fix-242`). Every new test was shown failing on `main`'s code first.
- `mypy` on PATH here runs under an interpreter without jinja2 and reports two import errors on
  `main` too; `python3 -m mypy` is the one that matches CI.
- #241 also moved `layout()`'s `document.render()` outside the error guard, so a builder error is
  never reported as the backend's, and added `BackendError(PdfError)` for the unnamed rest.
- **CI on all three PRs failed without running.** Every job completed `failure` two to three seconds
  after creation, `runner_id` 0, no runner name, log download 404, and the same on three unrelated
  diffs at once while `main` was green two days earlier: GitHub declined to start the jobs at the
  account level (spending limit or payment, usually). A re-run from the session got 403. Each PR
  carries one standing-down comment; each branch was re-verified locally (ruff, `python3 -m mypy`,
  ~2990 tests passed). Nothing in the diffs can clear it; the owner re-runs once Actions is enabled.
- The owner merged all three at 21:58–21:59 UTC with CI still refused; the three push runs on `main`
  failed the same way, so `main` reads red until Actions runs again. Bugs #240–#242 closed by `Fixes`.
