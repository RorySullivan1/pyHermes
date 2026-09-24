# The verification surface — who can confirm this worked

The project's answer, per surface, to one question: **can the agent confirm this itself, or
must a human — and why?** Every workflow that ends in "done" reads this file instead of
re-deriving what it can check, and every human gate in this repo traces back to a row here.

Produced and refreshed by the **`establish-verification`** workflow. This file is a *project*
record: the table below describes **pyHermes** (the rows replace the factory's example ones). The model above the table travels unchanged.

## Why this file exists

This repo's recurring defect is **verification steps that cannot verify** — an audit that runs
in plan mode and can't run the check, a probe bound early so it fails to compile on the version
it was meant to test, an advisory wrapper that crashes instead of advising. Each one *looked*
like verification from the outside. The fix is not more checks; it is a written, per-surface
answer that cannot be satisfied by a check that doesn't run.

The `claim-grounding` skill answers this for an **asset's factual claims**. This file answers it
for the **project's own work** — the email that has to fit under 102 KB and survive Outlook,
the document that has to paginate, the brochure that has to print.

## The three tiers

| Tier | Means | Requires |
|---|---|---|
| `agent-runnable` | A command the agent can execute here, whose result is the verdict | The exact command, and evidence it has been seen to **fail** |
| `human-gated` | Confirmation needs something the agent cannot reach | The blocker, and what the human is asked to report back |
| `unverified` | Nobody has a check yet | An owner and a next action — this tier is a debt marker, not a resting state |

### Rules that make the tiers mean something

- **Name the command, not the capability.** "The tooling is tested" is not a check; `pytest` is. If the *check* column holds nothing you could paste into a shell, the row is
  `unverified` wearing a disguise.
- **A check that cannot fail is not a check.** Before a row may be marked `agent-runnable`, the
  command must have been observed to fail on deliberately broken input at least once — the same
  controls discipline `claim-grounding` requires of a probe. Record that in *last-run*.
- **`human-gated` is a real answer, not a failure.** It is what lets a workflow place an
  honest gate instead of reporting success it cannot see. What makes the row useful is the
  **reason** (so nobody re-litigates it) and the **report contract** (what the human returns —
  often just a binary "worked / didn't", which is all an air gap can carry).
- **Split a surface rather than calling it "mixed".** If part of a surface is machine-checkable
  and part isn't, that is two rows. "Mixed" hides which half is actually covered.
- **A stale `agent-runnable` row is a claim about the past.** *last-run* is what distinguishes a
  check that works from one that used to.
- **Say whether the check gates or only reports.** Several of this repo's checks are advisory by
  contract — `asset_integrity.py` never vetoes a commit, and `contrast.py` exits 0 on a failing
  pair and puts the verdict in its output. A caller that reads exit status alone will record a
  pass that never happened. Where the two differ, the *check* column says which to read.
- **Never promote a tier to close a gap.** Downgrading is free; upgrading needs a command and a
  failure. Reporting `unverified` is always cheaper than a wrong "verified".

## The surface table — pyHermes

CLAUDE.md standing rule 3 says the same thing in prose: screenshots approximate Gmail, lint owns
Outlook, PDF rasterisation owns pagination, and a byte-verified diff is not a verified render.

| Surface | Check | Tier | Reason | Last run |
|---|---|---|---|---|
| Builder logic, validation, size limits | `pytest` | `agent-runnable` | Pure Python; extras' tests skip when the extra is absent (read the skip count) | — |
| Style and types | `ruff check . && ruff format --check .` and `mypy` | `agent-runnable` | Pure source analysis | — |
| Prose budget | `pytest tests/test_prose_budget.py` | `agent-runnable` | Baseline may only shrink; gated in the suite | — |
| Rendered HTML bytes | goldens in `pytest` (`--update-goldens` only to accept an intended change) | `agent-runnable` | Byte comparison — proves *sameness*, never *correctness* of a render | — |
| Outlook compatibility — static | `python -m qa.preview <fixture> --lint` | `agent-runnable` | Lint rules encode the Word-engine contract (`outlook-html-specifications`) | — |
| Outlook compatibility — rendering | open the message in classic Outlook and look | `human-gated` | No Word-engine renderer is reachable from a session; human reports what broke | — |
| Gmail-like layout | `python -m qa.preview <fixture> --screenshot` (needs `.[qa]`) | `agent-runnable` | Chromium approximates Gmail-in-a-browser; a real Gmail client is `human-gated` | — |
| Paged document / brochure pagination | `python -m qa.preview a4_portrait --screenshot` (needs `.[pdf]` + `.[qa]`) — look at each sheet image | `agent-runnable` | PDF rasterised one image per sheet; needs Pango/Cairo | — |
| Print HTML — static rules | `.claude/skills/weasyprint-print-html/scripts/lint_print_html.py` | `agent-runnable` | Pure source analysis; the skill's `probes/flawed.html` is the negative control | — |
| Brochure on press (colour, folding, trim) | print and fold a proof | `human-gated` | Physical output; the PDF is RGB by decision (`brochure.md`) | — |
| Delivery (Gmail / Outlook send) | adapter unit tests in `pytest`; a real send | tests `agent-runnable`, send `human-gated` | Adapters never own authentication — a live send needs the user's credentials | — |
| Wheel install | the CI `wheel` job | `agent-runnable` (CI) | Builds and renders from a clean venv | — |
| Asset shape (`.claude/`) | `asset_integrity.py` fed a git-commit hook payload — **advisory: reports, never vetoes** | `agent-runnable` | Pure file-shape analysis | — |

**Reading `—` in *last-run*.** The tier is **claimed, not proved** until someone has watched the
command fail on deliberately broken input. Run the `establish-verification` workflow to stamp
each row.

## See also

- **`establish-verification`** workflow — how the rows get produced and refreshed.
- **`claim-grounding`** skill — the same question asked of an asset's *claims* rather than the
  project's *work*.
