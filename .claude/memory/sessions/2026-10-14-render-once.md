# 2026-10-14 — epic #419, the render path does each expensive step once

Implemented #426–#428 on `claude/integrate-claude-assets-pyhermes-d4spzb`, on top of the
memory-only PR #439. One PR, one `Closes #N` per sub-issue.

- **#426** `render_pdf` is `layout()` then the new `render_layout(laid_out, profile)`; the
  kept-only branch and its `DEFAULT_OPTIONS` merge are gone (WeasyPrint 70 merges in both
  `HTML.render` and `Document.write_pdf`). `page_count` and `anchor_tops` take a layout as well
  as a document. `qa/preview.py` lays a paged document out once for its PDF and page count.
- **#427** `LazyHint` in `builder/medium.py`, exported: `Medium.validate` passes one, and its
  text is built when a constraint formats it. A passing render walks `images()` zero times
  (was once). `assets()` has its own walk, so "one walk, not two" in the issue became "none".
- **#428** `to_wire_bytes` memoises per message in a `WeakKeyDictionary`, guarded by a shape
  (parts, raw headers, payload objects, preamble, epilogue, policy) read after serialising.

Verified: `tests/test_render_once.py` (13 tests, 8 fail on the old source). Every printed
fixture's PDF, `PRINT` and `SCREEN`, was byte-identical old against new with fontTools'
`timestampNow` pinned, which also removes this container's determinism flake for a probe.
