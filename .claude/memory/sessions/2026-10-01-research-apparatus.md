# 2026-10-01 · research-apparatus

**Goal:** Implement epic #220 (#308–#312): a list of exhibits, lettered appendices, citations
with a bibliography, a glossary, and a research-note fixture with the docs.

## What happened
- #308: `Contents(of="exhibits", label=)`, `ContentsPage(of=, label=)` and `ExhibitsPage`, a
  contents sheet in its own slot; the skeleton prints `{{ contents_html }}{{ exhibits_html }}`
  on one line, so no golden moved.
- #309: `Appendices(sections)`, a section list like `Page`. The walk sets `Container.letter` and
  `Exhibit.appendix`; `Container.heading()` formats `Config.appendix_heading`. Anchors
  `exhibit-a-1`. #171's running-header and `target-counter` probes re-run and pass.
- #310: `Reference` + `Bibliography` in `pyhermes/builder/research.py`; `[@key]` is cut by
  `split_markers` beside `[^n]`, each leaf gets the walk's `Citing`, and `marked_copy()` lists
  the fields the walk reads. Unknown key refused by `validate()`; one bibliography per document.
- #311: `Term` + `Glossary`, a layout table whose cells take `stack-column`; its anchors join
  the document's through the new `Component.anchors()`.
- #312: `a4_research_note` (paged) and `research_note` (email) share `qa/fixtures/_research.py`;
  `test_research_note.py` compares the two text parts' apparatus and reads both lists' pages
  back from the PDF. Manual page 10, `apparatus.md` sections, README rows.
- Goldens: every existing one byte-identical except the kitchen-sink family, which gained the
  rule-1 section (Bibliography + Glossary). All new fixtures lint-clean and photographed.

## Gotchas & dead ends
- `pkill -f "pytest ..."` matched its own shell and killed the run; a clean baseline needed a
  `git worktree` of HEAD, since editing during a run contaminates it.
- `test_spacing` reads `SPACING_TOKENS` directly; a container of sections declares through
  `spacing_tokens()`, so the reverse and refusal tests now read `_declared(cls)`.
- In plain text a numeric citation "[1]" looks like a footnote marker "[1]"; kept and recorded
  in `apparatus.md` rather than moving every golden that carries a note.
