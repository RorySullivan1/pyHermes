# 2026-08-23 19:15 · open-color-theme-epic

**Goal:** Design and file the color/shadow theming epic (#46) with sub-issues #47-#51

## What happened
- Audited color usage before designing: **18 distinct hex values, ~235 occurrences across all 20 template files**; the 13-role palette comment in `base.html` is dead text (5 colors it doesn't name: `#F8F7F5` highlight tint, `#EAE8E4`, `#8A8880`, `#141E2C` scrim base, `#90A4AE`/`#CFD8DC`). Shadows = hero `text-shadow`s + the `rgba(20,30,44,0.65)` scrim (`#141E2C` @ 0.65). Python-side color literals: `Card.color = "#5A5A5A"` default, `default_color(fallback="#5A5A5A")`, containers' Jinja `default('#FFFFFF' / '#F8F7F5')`.
- Filed **epic #46** (color themes) + sub-issues, GitHub-linked as real sub-issues, mirroring epic #45's structure/voice:
  - #47 — `svc/builder/theming.py`: frozen `Theme` (Palette / TextColors / SemanticColors / ShadowStyle), `DEFAULT_THEME`, `THEMES` registry; zero render change.
  - #48 — `EmailMetadata.theme` (Theme instance | preset name); one resolution in `Email.render()`; inert.
  - #49 — migrate all color/shadow literals + Python fallbacks to `{{ theme.* }}`; byte-identity at default.
  - #50 — open the seam: exported `Theme` construction + `derive(**overrides)`, second curated preset `"slate"`.
  - #51 — docs: theming model, no-hardcoded-color rule, rewritten customization boundary in CLAUDE.md.
- No code changed; nothing pushed beyond this memory update.

## Gotchas & dead ends
- The dark-mode-forcing block (`[data-ogsc]`/`[data-ogsb]` + `prefers-color-scheme`) and the mobile `@media` block hardcode their **own copies** of palette colors with `!important` — the sneakiest migration surface; same divergence class as #41's sizes.
- `Card.color`'s construction-time default cannot see the render-time theme → must become "unset → resolved at render to theme neutral" (#49 owns it).

## State at end
- Open epics: #38 (header region), #45 (size themes), #46 (color themes). Shared prerequisite for all migration work: #32 golden test.
- PR #31 still open/green on this branch, awaiting the user's merge decision.

## Open threads
- Three epics now touch `base.html` + `EmailMetadata` — sequence the base.html-touching PRs (#33 / #41-#42 / #49), don't interleave.
- The render-context injection mechanism is built ONCE: whichever of #40 (sizes) or #48 (theme) lands first sets the pattern; the other reuses it.
