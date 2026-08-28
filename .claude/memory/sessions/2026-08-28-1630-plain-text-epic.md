# 2026-08-28 · plain-text epic (#53) — review + #108

Branch `claude/review-open-issues-rr8quq`, restarted from `main` @ `4a35861`
(PR #112, epic #56, merged).

## The epic review

#53 was already broken out into #108–#111 earlier the same day. Re-reading the
four against merged `main` found a defect in three of them.

**#108's body had been silently truncated.** GitHub's sanitizer eats bracketed
tag names *even inside code spans*: the `a` entry vanished from the blessed-set
list, and the body cut off mid-sentence at `<table>` — taking the entire
acceptance-criteria section with it. The same sanitizer had eaten a `<link>`
from PR #112's body an hour earlier, and `<name>`/`<fixture>` placeholders from
#110.

**Repo notation rule, learned twice in one day:** in any GitHub body, write
element names bare (`p`, `br`, `a`) and character references double-escaped
(`&amp;copy;`). A single-escaped entity is decoded on the way in, so
"`&copy;` decodes to `©`" stores as a tautology.

**#109 named three fields that do not exist.** It had been written from the
epic's prose rather than from `inspect.signature`:

| issue said | shipped |
|---|---|
| `AuthorBlock.title` | `AuthorBlock.job_title` |
| `ContactBlock.body`, through the degrader | `ContactBlock.description`, **escaped plain text** |
| container `title`/`subtitle` | containers have `title` only |

The last is not cosmetic: `subtitle` is a **component** field — all ten carry
it, no container does — so the projection code goes somewhere different than
the issue said.

**Verify a premise by grepping the code, not by re-reading the docs.** The
epic's "five blessed raw-HTML surfaces" claim was checked against the templates
directly (which variables are emitted without `escape_html`) rather than
trusted. It held — but that is the check that would have caught #109's field
names before they were filed.

## #108, as shipped

`svc/builder/textgen.py`: `html_to_text(html, link_format=format_link)`,
`html.parser`-based, stdlib-only, importing nothing from the builder (an AST
test holds that). 45 tests.

## Two defects in my own first cut

Both found by a **smoke script over realistic inputs**, not by the unit tests —
which passed, because I had written them against the behaviour I intended
rather than the behaviour I got:

1. **Source newlines inside a paragraph became line breaks.** A browser
   collapses them to a space; only `br` and `li` actually break a line. The fix
   is a `_BREAK` sentinel that holds structural breaks apart from the source's
   own whitespace, so one collapse pass can tell them apart. Real caller HTML
   in a disclaimer is indented across lines, so this would have fired
   immediately in production.
2. **`script` and `style` bodies were emitted as copy.** "An unknown element
   contributes its text" is right for a `table`; for these two it is a defect,
   because a browser renders no text for either. They are dropped whole — not
   an exception to the closed set, since the set governs which elements get a
   *projection* and these get none.

The lesson worth keeping: **a closed-set converter needs a smoke pass over
realistic input before its tests are written**, or the tests inherit the
author's assumptions instead of checking them.

## State at end

1474 tests with a browser, 4 skipping even then. ruff / `ruff format --check` /
mypy clean. **No golden moved** — #108 is a pure module, which is what its
acceptance criteria required. Next: #109.
