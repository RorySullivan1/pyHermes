# 2026-09-17 23:53 · multi-medium-rescope

**Goal:** Brainstorm the epic that rescopes pyHermes from email-only to email + paged (PDF/slides) + standalone HTML media

## What happened
- Surveyed the builder for what is medium-agnostic vs email-baked. **The seams already exist**:
  component/container models + validation, theme/font, `type`/`space`/`component` size layers,
  the `Region` SLOTS mechanism, `BoundEngine`, `textgen`, `EmbedStrategy` are all agnostic.
  Email-baked: `FrameGeometry` (680px) sitting *inside* `SizeScheme` (compact/spacious never
  change `width`, only `pad_x` — the frame is the medium's, not the density's); the specific
  slot set in `base.html`; template *markup* (`<tr>`, `[if mso]`, VML); `EmailMetadata` mixing
  facts (`firm_name`, `language`) with email facts (`email_subject`, `unsubscribe_url`);
  `_validate_size` called unconditionally in `render()`; all 10 lint rules; one gallery.
- Proposed model: `Document = Medium × Metadata × Regions × body`. `Medium` owns skeleton, slot
  contract, `PageFormat`, constraints, default embed strategy, lint rule set, template search
  path. `Email` becomes `Document(medium=EMAIL)`; proof of the refactor = byte-identical goldens.
- Nine-phase sequencing, phases 1–4 golden-identical: name the medium → lift the frame →
  ChoiceLoader → split metadata → first paged skeleton + PageFormats → Page + Cover/running
  boxes/back matter → `svc/pdf/` WeasyPrint exporter under `[pdf]` → QA rescope (lint
  `applies_to`, goldens per medium, PDF page screenshots, `preview --medium`) → docs.

## Gotchas & dead ends
- `.claude/memory/INDEX.md` State was stale (said `main @ e5c587a` / PR #146; actual `6b280d8`
  / PR #152, footer + ContactBlock rework, banner VML `src` gate #150). Corrected this session.
- **"No issues open" was wrong.** `list_issues` showed #150 (banner VML) and epic #153 with
  #154–#156 (per-exhibit disclosure) open. The dedup pass before filing is what caught it —
  the INDEX claim was stale, not the tracker. #153 is orthogonal to the rescope and is named
  as Related in #157.
- Issue bodies here carry a notation rule: **no angle brackets anywhere**, GitHub's sanitizer
  strips raw tags even inside fenced code and has emptied three bodies. Element names bare.

## State at end
- **Epic #157 is COMPLETE**: #158–#166 shipped on `claude/gifted-ritchie-7dkp5g`, unmerged.
  Phases 1–4 (Medium, PageFormat, ChoiceLoader, DocumentMetadata) shipped with every golden
  byte-identical; 5–7 added the paged medium, its regions and the PDF exporter; 8 made the
  harness medium-aware; 9 wrote `.claude/rules/media.md` and rescoped CLAUDE.md + README.
- 1929 tests pass with both extras, 1898 with neither. No email golden ever moved.

## Open threads
- Decisions still the user's: units (recommend keep px, 96 dpi), slide = format not medium,
  `text()` stays mandatory for documents, `Page` flattens in email rather than raising, keep
  the project name, one fixture set per medium.
- Next step: open the PR for #157, or land #153 first — they do not contend.
- **Unverified claim retired**: #163 could not check that a print engine honours its page
  breaks; #164 did — identical content, `break_before=True` gives two sheets and `False` one.
- Worth reusing: the perturbation probe (edit one mechanism, assert a NAMED test fails) caught
  every silent `str.replace` no-op, of which there were four — ruff reformats the target and
  the pattern stops matching. Always assert the pattern was found before writing.
