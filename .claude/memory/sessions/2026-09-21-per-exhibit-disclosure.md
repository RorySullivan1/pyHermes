# Epic #153 — per-exhibit disclosure

Filed 2026-09-04 against `ba8f321`, executed 2026-09-21 on top of the media rescope.

## The decision the epic reserved for its owner

**`disclosure` is plain text, escaped by the template.** Put to the user with the two real
options and their costs; they took the epic's own recommendation. The blessed raw-HTML set
in `textgen.py` stays closed at five. The accepted cost is no inline "see full disclosures"
link; the argument is reversibility — widening plain text to HTML later is additive and
back-compatible, narrowing is not, and shipping the XSS surface is the expensive direction
once callers have markup in their data.

A third option was offered and declined: plain text plus a structured `disclosure_url`,
which would have bought the link without a sixth raw-HTML surface. Worth remembering if the
link requirement ever materialises — it is the smaller of the two upgrade paths.

## What the epic got wrong, and it was the phasing

#154 was specified to leave every golden byte-identical; #155 to opt a fixture in. Those
cannot be separate commits: `test_every_data_table_argument_is_exercised` introspects
`DataTable.__init__`, so the moment the field exists the suite is red until a gallery table
sets it. The split was drawn on "does the golden move" before anyone read the test.

**The byte-identity claim still got proven, just not as a commit boundary**: the field went
in with an empty default, every golden was verified untouched, and only then did the
fixtures opt in. The proof is a test per exhibit rather than a commit that no longer exists.

## `justify` versus a standing non-goal

`text-align: justify` tripped three alignment tests, and all three were worth reading rather
than working around:

- **The pairing rule was substantively right.** `align="justify"` had to travel with the
  style, or a disclosure justifies in Gmail and reads ragged-right in Outlook's Word engine.
  Not test-appeasement — the half-themed failure in the client hardest to check.
- **The vocabulary check was right about the axis and wrong about its scope.** `TextAlign`
  omits justify because it "does nothing to a single short line"; a disclosure is the one
  place in the package rendering multi-sentence prose narrow enough for it to do something.
  Fixed by `_TEMPLATE_FIXED_ALIGNMENTS` — a template may fix an alignment the axis does not
  offer, a caller may not reach one — **plus a new test pinning that `TextAlign` still
  excludes justify**. Widening a guard without pinning what it still forbids is how a guard
  becomes a comment.

That is the fifth instance of *a check can be wrong about its scope*, and the first where
the answer was to widen one rather than narrow the code.

## Verified by looking

Standing rule 3, three renders: Chromium desktop, Chromium at 375px, and a rasterised PDF
page. No defect this time — unlike #164, which found two. The mobile "rivers" risk the epic
flagged is real and mild: the two-line disclosure reads cleanly at 375px, so justify stays
the default and `disclosure_align=` is a later additive call.

Golden diff: **56 insertions, 0 deletions** across 12 files — one `p` per exhibit plus the
text projection, nothing existing moved. 1946 passed / 74 skipped (up 17); ruff, format and
mypy clean. The change touches no optional extra, so both install shapes are unaffected.

## The medium dividend

`disclosure` was designed for an email and reached the paged document for free, because the
exhibits belong to the shared kit rather than to either medium. The paged fixture opts in
too, so a golden pins it and a future medium-specific fork of these templates cannot
silently drop compliance copy from the PDF. That is #157 paying out on the first epic
written after it.
