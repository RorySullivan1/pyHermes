# 2026-09-29 · consumer-package

**Goal:** Implement epic #237 (the package as a consumer sees it).

## What happened
- Branch restarted from `main` @ `dcf3971` after PR #253 merged; epic #238 closed by hand because
  `epic-autoclose` has failed on every run since 2026-09-28 (logs unreadable here, cause unknown).
- #243: `pyhermes/py.typed` (then `svc/py.typed`), and `qa/distribution.py` checking the built wheel.
- #244: MIT `LICENSE` (the owner's choice, asked), SPDX `license`, readme, classifiers, URLs; the
  sdist restricted by `only-include`; CI builds both, `twine check --strict`, renders from each.
- #245: `check` on 3.11-3.14, `data` on 3.11 and 3.13.
- #248: `git mv svc pyhermes`, 1,349 references in 187 files, and `svc/` as a one-release shim.

## Gotchas & dead ends
- **Hatchling always adds `.gitignore` to an sdist**; `exclude` does not remove it. Allowed by name.
- **pip 24.0 `pip show` prints no `License-Expression`** and no home page without a `Homepage` URL
  label; pip 26.2 prints both. CI upgrades pip before `pip show --verbose`.
- **The shim's first draft broke `importlib.resources`**: the import system overwrites an aliased
  module's `__spec__` with the alias's, so `pyhermes.builder` looked like no package. The loader
  keeps the real spec in `loader_state` and restores it in `exec_module`.
- uv's Python 3.14.0rc2 cannot `python -m venv` (ensurepip fails); `uv venv` works.
- The rename ran in a worktree while the matrix tested the main tree, then was cherry-picked; one
  conflict, two appended bullets in `working-in-the-code.md`, both kept.
- A rename changes a baselined comment's hash; the prose baseline entry is rekeyed, not grown.

## State at end
- Four commits pushed, one per sub-issue; goldens byte-identical. No PR opened (not asked).
