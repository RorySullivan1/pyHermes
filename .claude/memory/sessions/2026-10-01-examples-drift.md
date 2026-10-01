# 2026-10-01 · examples-drift

**Goal:** Implement #281 (the README's facts and the committed examples had drifted, and
nothing checked either) and open its PR.

## What happened
- PR #292 (#259) merged first; the branch fast-forwarded.
- Three of four examples were stale: `quarterly-review` since #157 (no PDF metadata, page
  margin, break rules, footnotes or contents leaders), and both emails since #282's `@media`
  line. All three regenerated; the quarterly review's PDF too, and its four sheets checked.
- `TestTheCommittedOutputIsCurrent` compares each example to a fresh render, using the golden
  harness's report through the new `qa.goldens.difference_report` with a remedy argument.
- The README drops the test count, names the six CI jobs, describes the three galleries, and
  its layout tree gains `math/`.

## Gotchas & dead ends
- `fund-factsheet`'s Content-IDs hash matplotlib PNGs, and `matplotlib~=3.11` can resolve a
  newer release on CI. The comparison masks `cid:` + 16 hex; a changed title still fails.
- A mutation that edited text absent from the file "passed" and proved nothing; check that a
  perturbation actually landed before reading its result.
