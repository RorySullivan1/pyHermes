# 2026-09-23 · digital-pdf

**Goal:** Implement epic #193 — the digital PDF, sub-issues #195–#200.

Started from `main` @ `565ace0` plus `2fcece1` (router and memory). Six commits on
`claude/gifted-ritchie-7dkp5g`, one per sub-issue.

| Commit | Issue | What |
|---|---|---|
| `b7af7c6` | #195 | author, description, keywords `meta` lines in both skeletons; outline pinned |
| `525b79e` | #196 | `PdfProfile`, `PRINT` and `SCREEN`; `render_pdf`/`save_pdf`/`layout(profile=)` |
| `3a164eb` | #197 | `Attachment`, `build_message(attachments=)` as `multipart/mixed`, `pdf_attachment()` |
| `e4742d1` | #198 | `Config.attachment_limit_kb` / `attachment_warn_kb`; check over `to_wire_bytes()` |
| `7562b56` | #199 | PDF/UA-1 measured; left opt-in; `digital-pdf.md` |
| `24869f8` | #200 | `letter_landscape_report`, README "Sent as a PDF", router row, cover logo centring |

## Decisions and why
- **Not a medium**: a profile on the exporter plus an attachment path. Reopened only by a
  skeleton, slot or constraint change the screen needs.
- **Identifier stays `None`**: WeasyPrint 70 writes no `/ID` by default (the issue assumed a
  random one), and a variant that needs one derives it from the file's md5. Fixing one in
  `PRINT` would have moved every render.
- **`SCREEN` stays untagged**: WeasyPrint 70's tagger ignores `role`, so 20 of a4_portrait's
  21 tables are layout tables tagged `/Table`, and a decorative image is a `/Figure` with no
  `/Alt`. The markup is right; the file would claim a conformance it lacks. Filed as #202.
- **`size_hint` on `Attachment`** lets the exporter name a remedy without delivery learning
  what a profile is.
- **The metadata lines are inlined in both skeletons**, not a partial: the theming test holds
  that every template paints, and a head-only partial paints nothing.

## What proved it
- PRINT bytes of every printed fixture identical to the previous commit's (worktree script).
- With no attachments, every email-gallery message byte-identical to before, boundaries
  normalised. Adapters changed by zero lines; a test sends through each.
- Read-backs: metadata, outline, image pixel sizes (img and CSS background), links, text,
  alt text (literal and UTF-16 hex), `/MarkInfo`, `/StructTreeRoot`, `/Lang`.
- Rasters of the landscape report, before and after the cover fix.

## Gotchas & dead ends
- **Determinism needs HarfBuzz-Subset.** Without it fontTools stamps the clock into each font's
  `head` table, and renders differ across a second boundary. This container lacked it;
  `apt-get install libharfbuzz-subset0` fixed it. CI's `pdf` job already installs it.
- **WeasyPrint maps no presentational hint**, so an `img` width attribute never reaches a paged
  layout (the cover logo prints at 72px, not 96). Filed as #201.
- **A tagged PDF lives in object streams**: inflate every Flate stream before regex-reading it.
- **A non-ASCII `/Alt` is UTF-16 hex**, `<FEFF...>`, not a literal string.
- **pypdfium2 5 has no bookmark `.title`**: `get_title()`, and `get_bounds()` not `get_pos()`.
- Naming a scratch script `struct.py` shadows the stdlib module and breaks every import.
- Inserting a comment into `build_message` would renumber its baselined comment runs; new
  logic went into helpers (`_attach`, `_check_attachment_budget`) instead.

## State at end
- All six sub-issues built and committed; full suite 2529 passed, ruff, format and mypy clean.
- PR opened with one `Closes` per sub-issue and the epic; CI to be watched.
