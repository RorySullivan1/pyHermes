# 2026-10-01 17:07 · exporter-epics-review

**Goal:** Review epics #218 (deck + PPTX) and #219 (DOCX): build or scrap

Planning only; no source changed. The owner doubted that a DOCX and a PPTX exporter could land
without doubling the project, and named the chart as the example: an image here, a native object
there. Both epics were built out earlier today against `main` @ `cf2cd5b` (#296–#301 under #218,
#302–#307 under #219, #308–#312 under #220), so the review read every sub-issue.

## What happened
- **Recommended: scrap both exporters as specified; keep the deck medium without #300.** The owner
  decides; nothing was closed or edited on GitHub.
- **Measured why "the same contract as the PDF exporter" is false.** The PDF rides the one HTML render
  path (652 lines, no per-component code). A DOCX or PPTX walk cannot start from the HTML, so each is a
  second render path: a projection per public class, the three axes re-bound as Word styles or a slide
  master, the apparatus re-implemented (footnotes through raw OOXML; python-docx has no footnote API),
  a fourth golden artefact with a read-back harness, an extra, a CI job, a rules file.

  | On `main` | Size |
  |---|---|
  | HTML templates, shared by three media | 41 files, 1,776 lines |
  | PDF exporter | 652 lines |
  | The one non-HTML projection, plain text | 26 `text()` methods; 1,130 lines of converter + tests |
  | Public classes a DOCX/PPTX walk must project | 46 (components 16, surfaces 3, containers 6, regions 7+11, page, panel) |
  | `Column` fields a Word/PPT table must honour | 10, plus groups, units, heat scales, bars, decimal alignment |

- **The sub-issues make it a permanent tax**: a pending set that must shrink to empty and a
  completeness test like `test_text_projection.py`, so every future component (the five #220 adds)
  would need three projections, not one.
- **The fidelity ceiling is low, and the chart is the general case.** A chart enters the tree as PNG
  bytes from a drawn Figure (`chart_from_figure`); the data is gone before any exporter sees it. A
  native chart needs a chart model (type, series, categories, axes, formats) that pyHermes deliberately
  lacks ("pyHermes does not draw charts"), consumed by matplotlib, python-pptx and raw DrawingML for
  Word: a second product. Both epics concede "No native chart". Equations stay pictures, a
  `FontStack` collapses to one face, footnotes may fall back to endnotes, heat and bars become
  shading. What is editable is titles, prose and tables; a pitchbook is mostly charts.
- **The deck medium is a different animal.** #296–#299 and #301 are in-architecture: `Panel` →
  `Slide`, `overflowing_panels` → `overflowing_slides`; the brochure cost ~1,064 lines and 94 tests
  for a whole medium. Worth keeping only if a PDF deck is wanted on its own.

## Gotchas & dead ends
- The branch `claude/gifted-ritchie-7dkp5g` was 316 files behind `main` and carried four memory
  commits whose INDEX edits `main` had since archived. Rebuilt it on `main` and ported the one file
  `main` lacked (`sessions/2026-09-28-2015-package-review-issues.md`) rather than rebasing into an
  INDEX conflict.
- `issue_read get_sub_issues` on a six-child epic exceeds the tool's output cap; read the saved JSON
  with python instead.

## State at end
- Proposal on the table, awaiting the owner: close #219 and #302–#307 as not planned with one
  reasoning comment on the epic; rescope #218 to the deck medium (drop #300, strip the PPTX line
  from #299, retitle); record the decision in `media.md` beside the exporter contract and reword
  README's "each is a new epic on the same contract"; keep one bounded door, a `[docx]` adapter from
  one `DataTable` to one Word table, as a task filed only when someone asks.

## Open threads
- If the owner says build anyway: #300 and #302 each name "whichever lands first sets the projection
  contract", so the first PR must define the per-class registry both exporters share.
