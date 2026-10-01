# 2026-10-01 · customise-the-layout

**Goal:** Implement #272: a manual page for the customisation surface.

## What happened
- PR #293 (#281) merged first; the branch fast-forwarded.
- `docs/manual/09-customise-the-layout.md`: per-object `spacing=` and `SPACING_TOKENS`, a house
  density (`COMPACT_SIZES.derive(space=...)` + `allow_custom_email_density`), a custom
  `Component` through `template_overlay=` (checked lint-clean in the page), replacing a packaged
  template, what raw HTML in a `TextBlock` can do, and a table of deliberate limits.
- Linked from the manual index and from *Look and feel*.

## Gotchas & dead ends
- The spacing layer is `space`, not `spacing`; `derive(spacing=...)` raises.
- A section's `spacing=` does not reach its blocks: each object accepts only the names it reads.
  The first draft said otherwise.
- `PYHERMES_ALLOW_CUSTOM_EMAIL_DENSITY` is read only through `set_config(Config.from_env())`.
- Outlook claims were grounded in `outlook-html-specifications` (div/p padding "limited"), and
  the `hr` advice in the `Divider` template's own reason. #261 and #265 shipped, so the limits
  table offers their features as alternatives; only #280 is still open.
