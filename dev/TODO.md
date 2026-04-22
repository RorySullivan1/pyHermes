# Fix: Section Title Clipping and Content Padding in Container Templates

## Context

The email builder produces HTML emails with section titles that appear "chopped off" at the top and content areas with unnatural tight spacing. The root cause is in the container templates (`full-width.html` and `highlight.html`) where both the **title row** and **content row** use `2px` top padding — far too little for visual breathing room.

The design palette comment in `templates/base.html` establishes an academic financial aesthetic with generous spacing, but the container templates undercut it with near-zero top padding on every section.

## Issues Found

### 1. Section titles appear chopped/clipped
- **File**: `templates/common/containers/full-width.html` line 16 and `templates/common/containers/highlight.html` line 17
- **Current**: `padding:2px 32px 12px 32px` on the title `<td>`
- **Problem**: 2px top padding means the title text sits flush against the top of its section — barely any space between the previous section's bottom and this section's heading. The `h2` at 17px font with `line-height:1.2` gets visually clipped at the top.

### 2. Content area has cramped top spacing
- **File**: `templates/common/containers/full-width.html` line 26 and `templates/common/containers/highlight.html` line 25
- **Current**: `padding:2px 32px 26px 32px` on the content `<td>`
- **Problem**: Only 2px between the title's bottom border and the component content below it. Text, tables, and KPI strips feel jammed against the section rule.

## Proposed Changes

### Fix 1 — Section title top padding
Change title `<td>` padding from `2px 32px 12px 32px` to `22px 32px 12px 32px` in both templates.

- **22px top** gives proper visual separation from the previous section
- **12px bottom** before the `border-bottom` rule is fine as-is

### Fix 2 — Content top padding
Change content `<td>` padding from `2px 32px 26px 32px` to `16px 32px 26px 32px` in both templates.

- **16px top** gives proper breathing room between the title's bottom-border rule and the content
- **26px bottom** is fine as-is

## Files to Modify

| File | Line | Change |
|------|------|--------|
| `templates/common/containers/full-width.html` | 16 | `padding:2px 32px 12px 32px` -> `padding:22px 32px 12px 32px` |
| `templates/common/containers/full-width.html` | 26 | `padding:2px 32px 26px 32px` -> `padding:16px 32px 26px 32px` |
| `templates/common/containers/highlight.html` | 17 | `padding:2px 32px 12px 32px` -> `padding:22px 32px 12px 32px` |
| `templates/common/containers/highlight.html` | 25 | `padding:2px 32px 26px 32px` -> `padding:16px 32px 26px 32px` |

## Verification

1. Run `python test_builder.py` to regenerate `weekly_market_wrap_v2.html`
2. Open the output in a browser and verify:
   - Section titles ("Market Snapshot", "Week in Review", etc.) have clear top spacing — no clipping
   - Content below each title rule has comfortable breathing room
   - The overall rhythm feels consistent with the academic financial design
