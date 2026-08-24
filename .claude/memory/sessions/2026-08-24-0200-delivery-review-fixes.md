# 2026-08-24 02:00 · delivery-review-fixes

**Goal:** Fix all 7 code-review findings against #68 (`svc/delivery`), using parallel agents.

## What happened
- Code review (two passes) found 7 defects. I re-verified every one by reproduction before acting — all real. Notably **all 5 of my `bbc43c1` docstring/commit claims about determinism were false** for the image path.
- **Partitioned 4 agents by disjoint code region, not 1-per-finding**: 7 concurrent editors on one 264-line file would have clobbered each other. Wire conformance (F1/F3/F4) · envelope validation (F5) · cid collection (F6/F7) · determinism (F2). Zero merge conflicts resulted.
- Settled the 3 embedded design decisions myself up front so 4 agents wouldn't invent 4 answers: asymmetric seam handling, the Content-ID trap, docs-over-engineering for determinism.
- Integrated as 4 commits (`bffa272`, `2993c92`, `f31d563`, `c2a9e62`), verified all 7 fixes by reproduction on the *merged* tree, then corrected CLAUDE.md + memory myself. **423 tests**, ruff/format/mypy green.

## Gotchas & dead ends
- **Worktrees came from the branch base (`main`), not the tip** — `svc/delivery/` didn't exist in any of them. Two agents self-corrected; two needed telling. The dangerous failure mode isn't an error, it's an agent *improvising the missing file* and reporting success on code never under review.
- **Agents leave work uncommitted** — branches sat at `bbc43c1` with `commits_ahead=0`. My original plan to `git merge` their branches would have merged nothing. Commit in the worktree, then cherry-pick.
- Stop hook flagged `.claude/worktrees/` as untracked; correct fix was `.gitignore`, not committing live checkouts of the repo into itself.
- **The hard-fail I chose in #68 amplified a parser gap into a correctness bug**: unreferenced-asset was fatal, and the collector couldn't see `<style>`/mso-conditional refs, so a valid email would be *rejected*. `base.html` only survives because it emits the header background twice (VML + plain style) — the header epic (#38) would have broken it.

## State at end
- Branch `claude/review-open-issues-rr8quq` @ 4 fix commits on top of `bbc43c1`; `main` still `07d5609`.
- All 7 findings verified fixed by reproduction, not by agent report.

## Open threads
- **#73 filed**: `images.py` tells callers delivery adds `@` to a Content-ID, but `_CONTENT_ID_RE` forbids `@` and RFC 2392 makes qualifying it break the cid link. The comment is wrong.
- #72 still open (public `Email.metadata` vs documented opacity).
- #58's snapshot harness must normalize the MIME boundary — `message.py`'s docstring now says exactly what.
