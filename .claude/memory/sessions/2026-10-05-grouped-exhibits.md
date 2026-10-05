# 2026-10-05 — epic #335, exhibits that group

Implemented #336–#339 on `claude/integrate-claude-assets-pyhermes-d4spzb`, restarted from
`main` after PR #379 merged.

- **#336** `FigureGrid(panels, caption, label="Exhibit", source, disclosure, columns=2)` in the
  new `pyhermes/builder/exhibits.py`, `analysis/figure-grid.html`. `leaves()` now stops at any
  `Exhibit` that holds blocks, so the grid is numbered once and its panels never; panels anchor
  `<grid anchor>-<letter>` through `Component.anchors()`. A panel's label, anchor, caption,
  source, disclosure, notes and wrap are refused; a decorative panel too.
- **#337** `Legend(entries, layout="row")`, `LegendEntry(label, tone|color|series)`,
  `analysis/legend.html`; `ChartBlock(legend=)` through a new `Component.render_context(engine)`.
  `SERIES_TOKENS` and `chart_colors()` moved to `theming.py`; `data/style.py` re-exports. A hex
  is checked against the document's theme in `add_section` (`legends(_held(section))`).
- **#338** `source`, `as_of`, `source_notes` on `Container` and the five leaf sections;
  `common/source-line.html`. The walk reads sections as holders after their blocks
  (`Document._holders()`); the deck's `_marked` reads each section's line before the slide's.
  The keyword is `source_notes` because `Slide.notes` is speaker notes.
- **#339** `_research.py` gains Exhibit 3 (a grid with a key and an xref to panel (b)), a
  section source citing and calling a note, and B.2 (a grid in an appendix);
  `tests/test_grouped_exhibits.py`; `apparatus.md`, `data-layer.md`, `builder-architecture.md`;
  the manual section in page 10.

**Found:** a grid and a legend put `kitchen_sink` 1.8 KB over the 90 KB warning in
`modern_fonts`. The chart became a two-panel grid (chart + picture on the same bytes) with a
two-entry key, and *Portfolio Variance*'s two equations joined it in one `Stack` under
*Cumulative Performance*; the legend's two wrapper divs became one; the kitchen sink's grid
carries no disclosure or standfirst (the research note pins both). `modern_fonts` is left
with 323 bytes.

**Probes:** both sweep tests (`.figure` keeps a grid on one sheet; `.fine-print` keeps a section
source with its section, full width and split) were checked to fail with the rule stripped.

Same container flakes as before: PDF byte determinism in `test_digital_pdf`, `test_attachments`
and the handout test, each also failing on clean `main`.
