#!/usr/bin/env python3
"""PreToolUse(Bash) guard: warn when the version cursor has drifted from the roadmap.

Opt-in BY PRESENCE: silent unless the project has BOTH a `.meta/roadmap/INDEX.md` (it has
adopted the development-map flow) and a `.meta/version` with a label. It only speaks up at
`git push` time, and only when the cursor (`.meta/version`) and the map (`.meta/roadmap/`)
disagree — e.g. shipping a version the roadmap doesn't list, one the INDEX still marks
`planned` while it's in progress, or one the version marks `shipped` but the INDEX does not.

Like `version_guard.py` it NEVER blocks: it emits only an `additionalContext` nudge (no
`permissionDecision`, so the normal permission prompt still applies), so the push proceeds
and the model just learns the map needs a
status update (`/roadmap-status` to reconcile, `/roadmap-set` to re-slice). Fails safe: on
any unexpected shape or error it prints nothing and the push proceeds.

Parallel work: this guard is per-version and stays correct with a second version in flight in
another worktree. `.meta/version` and `memory/INDEX.md` are the single-cursor files — see
`probes/PROBES.md` and the 2026-09-10 decision in `.claude/memory/INDEX.md`.
"""
from __future__ import annotations
import json
import os
import re
import sys
from pathlib import Path

PUSH_RE = re.compile(r"\bgit\s+push\b")
# A roadmap INDEX "Versions" table row: | vX.Y.Z | stage | goal | status |
ROW_RE = re.compile(r"^\|\s*(v\d[\w.\-]*)\s*\|.*\|\s*([^|]+?)\s*\|\s*$")


def meta_dir() -> Path:
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(root) / ".meta"


def current_version(text: str) -> str:
    for line in text.splitlines():
        m = re.match(r"^#?\s*version:\s*(\S+)", line.strip(), re.IGNORECASE)
        if m and m.group(1) not in ("", "<label>"):
            return m.group(1)
    return ""


def current_status(text: str) -> str:
    for line in text.splitlines():
        m = re.match(r"^status:\s*(\S+)", line.strip(), re.IGNORECASE)
        if m:
            return m.group(1).lower()
    return ""


def parse_index(text: str) -> dict:
    """Return {version: status_text} from the INDEX versions table.

    Deliberately NOT a cursor lookup. Every comparison below is keyed off *this* worktree's
    own `version:` label, so the guard stays correct with a second version in flight in
    another worktree (probed 2026-09-10 — `probes/PROBES.md`).
    """
    statuses: dict[str, str] = {}
    for line in text.splitlines():
        m = ROW_RE.match(line.strip())
        if not m:
            continue
        version, status = m.group(1), m.group(2).strip()
        low = status.lower()
        if "version" in low and "status" in low:  # header row leaked through — skip
            continue
        statuses[version] = status
    return statuses


def check(command: str, root: Path) -> str | None:
    """Advisory message for the dispatcher (`git_guards.py`), or None to stay silent."""
    if not PUSH_RE.search(command):
        return None

    index_path = root / ".meta" / "roadmap" / "INDEX.md"
    version_path = root / ".meta" / "version"
    if not index_path.is_file() or not version_path.is_file():
        return None  # roadmap flow not adopted (or no cursor) — stay silent

    try:
        index_text = index_path.read_text(encoding="utf-8", errors="replace")
        version_text = version_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    current = current_version(version_text)
    if not current:
        return None
    status = current_status(version_text)
    statuses = parse_index(index_text)
    if not statuses:
        return None  # couldn't parse the table — say nothing rather than guess

    # Only flag UNAMBIGUOUS drift, keyed off the version's own status, so the normal
    # between-versions state (last-shipped version + a different next-planned cursor)
    # does NOT false-positive.
    warning = ""
    index_status = statuses.get(current, "").lower()
    if current not in statuses:
        warning = (f"`.meta/version` is {current}, but that version isn't listed on the "
                   f"roadmap INDEX (`.meta/roadmap/INDEX.md`). Add it to the map or re-slice "
                   f"with `/roadmap-set`.")
    elif status == "shipped" and "shipped" not in index_status:
        warning = (f"`.meta/version` marks {current} as shipped, but the roadmap INDEX still "
                   f"lists it as `{statuses[current]}`. Flip its row to `shipped` so the map "
                   f"tracks reality (`/roadmap-status` to reconcile).")
    elif status == "in-progress" and "planned" in index_status:
        warning = (f"You're shipping in-progress work for {current}, but the roadmap INDEX "
                   f"still lists it as `planned`. Mark its row `in-progress`.")
    return warning or None  # empty when status and map agree — nothing to say


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    command = (data.get("tool_input") or {}).get("command") or ""
    msg = check(command, meta_dir().parent)
    if not msg:
        return 0
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": msg,
        }
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
