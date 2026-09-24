# hooks/

**Lifecycle enforcement layer.** Deterministic shell scripts the harness runs on
events — the model cannot skip them. This is the floor underneath the whole prompt
stack. Use hooks for anything that must *always* execute.

## Design rules

**Keep checks non-mutating.** A hook that fires on a commit or push may read, judge, and
report — it must not rewrite files. Auto-formatting or "fixing" mid-commit means the diff
that was reviewed is not the diff that ships, and the working tree moves under the person
approving it. Run formatters as an explicit, reviewable step instead, and never let two
formatters that both claim the same files run in parallel. Generated artifacts are checked
in read-only mode; regenerate them deliberately after changing their source.

**Fail safe and stay quiet.** On an unexpected payload, a missing file, or any error, print
nothing and let the command proceed. A guard that breaks the session it was meant to protect
is worse than no guard.

**Opt in by presence.** Detect whether the project has adopted the thing you're guarding
(a `.meta/version`, a `.claude/skills/`) and stay silent when it hasn't, so a fragment
copied downstream doesn't nag about a convention that project never took up.

**Prefer advisory to veto.** Emit `permissionDecision: allow` plus `additionalContext` so
the model learns what's wrong without the action being blocked. Reserve a `deny` (or a
non-zero exit on `PreToolUse`, which vetoes the call) for things that must be stopped.

**Cap the output.** Hook output lands in context every time it fires. Truncate lists and
say how many were omitted.

## Storage — one fragment file per hook (the source of truth)

Claude Code can't load hook definitions from external files; the `hooks` block must be
inline in `settings.json`. To keep that file from becoming a large hand-edited blob,
each hook is stored as its own small `*.json` **fragment** here, and `../settings.json`
is **generated** from them by `build-hooks.py`. Edit the fragments, then rebuild — never
hand-edit the generated `hooks` block.

A fragment is a partial hooks object keyed by event name. Use **exec-form**
(`command` + `args`) for cross-platform reliability:

```json
{ "SessionStart": [ { "matcher": "...", "hooks": [ { "type": "command", "command": "python", "args": [ "..." ] } ] } ] }
```

Every `*.json` here is a fragment (README and `build-hooks.py` are ignored); fragments
merge in filename order, same-event arrays concatenate.

### Rebuild after editing a fragment

```bash
python .claude/hooks/build-hooks.py          # regenerate ../settings.json
python .claude/hooks/build-hooks.py --check   # exit 1 if settings.json is stale
```

(`python3` on macOS/Linux.)

## Fragments in this project (memory lifecycle hooks)

These drive the `session-memory` skill (load / persist / recall):

| Fragment | Event | Subcommand |
|---|---|---|
| `session-start.json` | `SessionStart` | `index` — load `INDEX.md` into context |
| `pre-compact.json` | `PreCompact` | `precompact-hook` — persist reminder before compaction |
| `stop.json` | `Stop` | `stop-hook` — once-guarded end-of-session write reminder |
| `user-prompt-submit.json` | `UserPromptSubmit` | `prompt-hook` — recall on "continue"-style prompts |

To add a hook: drop a `<event>.json` fragment here and run `build-hooks.py`. A
`PreToolUse` fragment that exits non-zero **vetoes** the tool call.

## Guards and filters

Advisory, non-mutating, opt-in by presence — each one allows the action and adds context.
The git-triggered guards share **one fragment and one interpreter spawn**: the
`git_guards.py` dispatcher parses stdin once and runs each guard's `check(command, root)`,
so a plain `ls` pays one fast Python startup, not three. To add a git guard, give it a
`check()` and register it in `git_guards.py` — don't add another per-Bash fragment.

| Fragment | Event | Script | Effect |
|---|---|---|---|
| `pre-tool-use-git-guards.json` | `PreToolUse` (Bash) | `git_guards.py` → `version_guard` + `asset_integrity` | On `git commit`/`push`: reports `.claude/` asset defects (skill folder ≠ `name:`, missing `name:`/`description:`, a cited `references/` file that's absent, broken symlinks); warns when `.meta/version` lacks a label/goals. (The roadmap-drift guard was omitted — the `.meta/roadmap` system wasn't brought into this project.) |
| `pre-tool-use-read-guard.json` | `PreToolUse` (Read) | `pre_read_guard.py` | Stops an accidental whole-file slurp of a very large file. |
| `post-tool-use-bash-filter.json` | `PostToolUse` (Bash) | `post_bash_filter.py` | Keeps verbose command output out of the main context. |
| `post-tool-use-prose-budget.json` | `PostToolUse` (Edit/Write/MultiEdit) | `prose_budget.py` | Reports commentary over the per-scope budget in the `coding-standards` skill. |

`prose_budget.py` is also a **library**, and that is the point of its shape: `scan_source()` and `scan_tree()` return `Finding`s, so a project's CI gate measures with the same code the edit-time note uses. An advisory hook cannot be a gate — it must never block — and a second measurer written for the gate is how the two come to disagree about what the rule is.

It reads `.claude/prose-budget.json`, and **that file is the adoption marker**: absent, every entry point returns nothing, so a project that vendors this and adopts nothing sees no output. Keys are `module`, `class`, `function`, `attribute` and `comment_run` (line caps), `claude_md` (`{"lines": N, "chars": N}` — whole-file caps on `CLAUDE.md`, the other always-loaded prose; the memory INDEX has its own check in `memory.py`, and a whole-file cap is deliberate: scope tables are for code, and a markdown "scope" would be a guess), `include` (roots to scan), and `baseline` (a path to a location-to-reason mapping whose entries are exempt — a `CLAUDE.md` entry exempts both its line and char findings, since a whole-file scope has one location). Baseline keys are qualified names rather than line numbers — a comment run, which has no name, is keyed by a short content hash of its own text — so an edit above a docstring does not invalidate an entry and fail the gate for an unrelated reason; a comment-run key churns only when that comment is rewritten.

A `#:` run before an assignment is measured as **`attribute`**, not as a comment block: that is
Sphinx's way of documenting a module constant, so scoring it as inline prose would force correct
API documentation to be deleted. It is keyed by the constant's name, which survives a line move.

Python only, via `ast` and `tokenize`. `_SCANNERS` is the extension point; a language with no
entry is skipped rather than guessed at.

## Self-maintaining (the drift guard)

Two fragments keep `settings.json` in sync automatically, so you rarely run the
generator by hand:

| Fragment | Event | Calls | Effect |
|---|---|---|---|
| `post-tool-use-build.json` | `PostToolUse` (Edit/Write/MultiEdit) | `build-hooks.py --on-edit` | Auto-rebuilds `settings.json` when Claude edits a fragment here. |
| `session-start-hooks-check.json` | `SessionStart` | `build-hooks.py --warn-if-stale` | Warns in-context at session start if `settings.json` is stale (catches manual/IDE edits). |

`--check` (exit 1 when stale) remains for CI / a pre-commit guard.

## Other generators living here

`catalog.py` is a second mechanical generator (like `build-hooks.py` — a plain script, not a
hook). It regenerates `../CATALOG.md`, the on-demand inventory of this project's skills, agents,
commands, and workflows. It is kept fresh by two fragments and the `/reindex` command:

| Fragment | Event | Calls | Effect |
|---|---|---|---|
| `post-tool-use-catalog.json` | `PostToolUse` (Edit/Write/MultiEdit) | `catalog.py --on-edit` | Rebuilds `CATALOG.md` when an asset file (`SKILL.md`, an agent/command/workflow `.md`) is edited. |
| `session-start-catalog-check.json` | `SessionStart` | `catalog.py --warn-if-stale` | Warns at session start if `CATALOG.md` is stale (catches git/IDE changes). It only *warns* — the catalog is on-demand, never printed into every session. |

## probes/

`probes/` holds probe kits for the hooks themselves — a hook is a check, and a check nobody has
watched fail is not a check. `probe_parallel_state.py` (+ `PROBES.md`) is the controls-first kit
behind the single-cursor decision: it reproduces what happens when two units of work are in
flight, and its 2026-09-10 run **refuted** two of the three claims that motivated it. Run it
before changing `roadmap_guard.py`, `.meta/version`'s shape, or `memory/INDEX.md`'s sections.

`CATALOG.md` is per-tree and **not** symlinked (its content differs per tree, like
`settings.json`); regenerate it in each tree with `python .claude/hooks/catalog.py` or `/reindex`.
