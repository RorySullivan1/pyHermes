# 2026-10-14 · codebase-review-issues

**Goal:** a fresh review of the package after #418 and #419 shipped, filed as one epic plus standalone bugs (owner's ask).

No source changed. Inputs: two `/code-review high` passes over PR #440's change (owner's runs, 6 and 8 findings, mostly
overlapping), and four parallel reviewers, one per area (builder structure, rendering kit, the three paged media,
exporters/check/adapters), each told to report only findings it reproduced on `main` @ `c56a771`. Every finding was
then re-probed here before filing; all reproduced. Filed with `issue_body.py` (render, check, create, fill-self, check,
PATCH) through `gh api`; a dry run rendered and checked all 27 bodies first.

| Issue | What |
|---|---|
| #442 | Epic: the once-only render paths keep their contracts (follow-up to #419) |
| #443 | The wire-bytes memo's value holds its own key, so every message (refused ones too) lives forever |
| #444 | `LazyHint` breaks a host constraint that treats its hint as a `str`; it also holds the document |
| #445 | `render_layout` writes under a profile other than the layout's; `page_count` takes anything |
| #446 | Task: one layout per `preview` run (`--screenshot`, deck `--lint` lay out again), one save path (depends on #445) |
| #447 | A directly built `EmailImage` skips the URL scheme, Content-ID and format checks |
| #448 | Formatters round under the caller's decimal context; `number(1e26, 2)` raises `InvalidOperation` |
| #449 | `FactList` with 4 facts in 3 columns renders 2 columns |
| #450 | NaN and infinity pass construction (glance, sizing, `Spacing`, `PageFormat`, split weights, `Config`) |
| #451 | The prose filter cuts the trailing slash off an unquoted `href` |
| #452 | `DataTable` mutates the caller's `TableRow`s, so a second table shows the first's format |
| #453 | `OnlySections` misses a note or citation in a section's `source` line |
| #454 | A figure hosted by `TextBlock` skips the anchor, citation and legend checks |
| #455 | A `Decimal` figure under a float `HeatScale` or bar raises `TypeError` at render |
| #456 | `Term('Term premium')` anchors as `term-premium`, colliding with `Term('Premium')` |
| #457 | A sparkline column's `auto` tone overwrites a cell's own tone |
| #458 | A brochure ground image shared by two panels is checked at the last panel's width |
| #459 | Long speaker notes push a handout past one page a sheet; contents numbers then disagree |
| #460 | A panel inset leaving no room is refused only at render, without naming the panel |
| #461 | A running header and footer in the same margin box: one silently vanishes |
| #462 | A `Slide` added twice prints the first sheet's number on both |
| #463 | A relative image URL is silently dropped from the PDF, not refused |
| #464 | `table_from_frame` drops a formatter or tone given for a non-numeric column |
| #465 | `page-size-declared` cannot fire when a running box sets `font-size` |
| #466 | `pyhermes.check` exits 1 with a traceback when a draft raises a non-builder error |
| #467 | `render_math` depends on the caller's matplotlib rcParams (`text.usetex` raises `RuntimeError`) |
| #468 | `qr_code` lets segno's and Python's exceptions escape for a bad size or long URL |

## Decisions and why
- **One epic, the rest standalone**, as the owner asked. The epic is the four #419 follow-ups: they share a cause
  (doing a step once broke a contract) and #446 depends on #445. The 22 others each want one PR of their own.
- **#450 merges three reviewers' non-finite findings** (glance, sizing/`Config`, split weights): one cause, one fix shape.
- **Not filed, reproduced but minor:** a backslash in a `FontStack` family escapes its CSS quote; `bps()` hard-codes
  `,` thousands with `decimal=','`; `decimal_pads` aligns on `.` only; `FlowedColumns(count=2.0)` renders
  `column-count:2.0`; `PdfProfile(dpi=True)`; `outlook-transparent-background` misses the `background:` shorthand.
  File them if a sibling fix touches the same code.

## Gotchas
- `TwoColumn`'s first positional parameter is `ratio`; a probe passing blocks positionally gets a `TypeError` that
  looks like a finding and is not.
- A raw-bytes search for `/StructTreeRoot` in a PDF finds nothing because the objects are compressed; compare whole
  renders with fontTools' `timestampNow` pinned instead.

## State at end
- 27 issues open: #442 (4 children), #447–#468 standalone. Nothing implemented.
