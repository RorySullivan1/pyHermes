# 2026-08-28 · typography epic (#56)

Same branch as #87/#98 (`claude/review-open-issues-rr8quq`, off `main` @ `4e01489`,
PR #103 merged). Five commits: #104, #105, #106 ×2, #107.

## What shipped

| | |
|---|---|
| #104 | `svc/builder/typography.py` — `FontStack` (varargs, unquoted storage, byte-exact `css`) + `FontTheme` (four roles), `DEFAULT_FONTS`, `FONT_THEMES`, `resolve_font_theme` |
| #105 | `EmailMetadata.font_theme`, resolved in `Email.render()` and bound on the **existing** `BoundEngine`; `TemplateEngine`'s floor extended |
| #106 (1/2) | Normalise the two spellings of each stack **as literals** — 250 golden lines, no mechanism change |
| #106 (2/2) | Tokenise all 49 `font-family` declarations — **zero** golden lines moved |
| #107 | `MODERN_FONTS`, the `modern_fonts` fixture + golden, the third-axis docs in CLAUDE.md and README |

## Decisions worth not re-deriving

**The design system now has three axes and they are deliberately one shape**: an email-level
field → resolved once in `render()` → bound as a shared value on `TemplateEngine.bound()` →
read as a namespace in every template → a preset registry → a gallery fixture per preset. The
binder now carries `theme`, `size` and `font`, and **no container, component or region has
ever changed signature to accept any of them.** A fourth email-level value should be the
fourth keyword, not a fourth mechanism.

**A vocabulary migration normalises before it tokenises.** The templates spelled the same
stack two ways — `Georgia, 'Times New Roman', serif` in 26 declarations and an unspaced form
in the rest — which is the *general* case, not this axis's quirk: literals accumulate variants
that are identical to a browser and different to a golden. One commit could not be
byte-identical, and a golden diff that mixes "the spelling moved" with "the mechanism moved"
is a diff nobody can review. Splitting it lets the reviewer read "250 lines, spelling" and
"0 lines, mechanism" separately, and the whitespace-only claim on the first was verified by
script rather than by eye.

**A sentinel render catches what a golden structurally cannot.** Rendering the widest fixture
under a theme whose every role is a findable sentinel, and asserting **no shipped family
survives**, is what found the one declaration #106 missed: `data-table.html`'s mono branch
sits inside `{% if loop.first %}Arial…{% else %}Courier…{% endif %}`, so the literal had no
`font-family: ` prefix for the migration to key on. The goldens said nothing, correctly — the
output was right, because the literal was right. Reuse this on any axis that claims to have
tokenised everything.

**The watch-site is the `[if mso]` block, not `@media`.** `body, td, th { font-family: … }`
is Outlook's floor for the whole message, so a literal there renders a themed email
custom-faced in Gmail and Georgia in Outlook — half-theming in the client hardest to check.
Colour's and size's watch-site was the `@media` block; this axis's is a different one, which
is why it is named rather than inherited.

**`font_theme` accepts an object; `size_theme` still does not.** The asymmetry is the same
argument read the other way. Density interacts with the clipping limit, the Word engine and
the mobile collapse at once, so an unrendered scheme is an untested compatibility claim. A
*face* fails visibly and locally, and the terminal-generic rule means the worst case of a
caller's own house font is the reader's default serif — so a house face is exactly the kind of
thing a house should be able to set.

**Roles are named by job, not by face — and this axis is where that was hardest to see.**
`heading` and `body` share one stack in the default, so a value-keyed migration would have
merged them and been byte-identical. `modern_fonts` is what proves the cut was right: it moves
`heading` and holds `body`.

**`kitchen_sink` now holds two fields at their defaults on purpose** (`size_theme`,
`font_theme`, in `ANCHORED_TO_THE_DEFAULT`). That fixture is the byte-identity reference every
migration's claim is measured against, so its density and its faces have to be the ones the
claim is about. The non-default paths belong to `compact_size` / `spacious_size` and
`modern_fonts`, which render the same email one field apart.

## Measured, not assumed

`kitchen_sink` at classic vs modern, all three densities, desktop and mobile: page heights
**identical to the pixel** (2605 / 3154 / 3890 desktop; 3747 / 4655 / 5781 mobile). That is
the orthogonality claim on an image — a face swap moves no px — and a test asserts the
stronger form: strip every `font-family` value from both renders and they are byte-identical.

## State at end

Twelve fixtures. 1429 tests with a browser, 4 skipping even then. ruff / `ruff format --check`
/ mypy clean. Epic #56 closed; **#53 (plain-text, sub-issues #108–#111) is the only open
parent**. No PR opened.
