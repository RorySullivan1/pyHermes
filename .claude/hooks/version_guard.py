#!/usr/bin/env python3
"""PreToolUse(Bash) guard: nudge to keep .meta/version complete before a push.

Opt-in BY PRESENCE: if the project has no `.meta/version`, this is silent (it hasn't adopted
the version-labeling flow — e.g. the factory itself). It only speaks up when the file EXISTS
but is incomplete (no `version:` label, or no goals) and the command being run is a `git push`.

It never blocks — it emits `permissionDecision: allow` plus an `additionalContext` warning, so
a push is never vetoed; the model just learns the version isn't fully labeled. Fails safe: on
any unexpected shape or error it prints nothing and the push proceeds. Flip the decision to
`deny` if you want hard enforcement.
"""
import json
import os
import re
import sys
from pathlib import Path

PUSH_RE = re.compile(r"\bgit\s+push\b")


def meta_version_path() -> Path:
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(root) / ".meta" / "version"


def goals_present(text: str) -> bool:
    """True if there's at least one non-empty '- ' bullet under a '## Goals' heading."""
    lines = text.splitlines()
    in_goals = False
    for line in lines:
        if line.strip().lower().startswith("## goals"):
            in_goals = True
            continue
        if in_goals:
            if line.startswith("## "):  # next section
                break
            item = line.strip()
            if item.startswith("- ") and item[2:].strip():
                return True
    return False


def has_version(text: str) -> bool:
    for line in text.splitlines():
        m = re.match(r"^#?\s*version:\s*(\S+)", line.strip(), re.IGNORECASE)
        if m and m.group(1) not in ("", "<label>"):
            return True
    return False


def check(command: str, root: Path) -> str | None:
    """Advisory message for the dispatcher (`git_guards.py`), or None to stay silent."""
    if not PUSH_RE.search(command):
        return None
    mv = root / ".meta" / "version"
    if not mv.is_file():
        return None  # project hasn't adopted version labeling — stay silent
    try:
        text = mv.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    missing = []
    if not has_version(text):
        missing.append("a `version:` label")
    if not goals_present(text):
        missing.append("at least one goal under `## Goals`")
    if not missing:
        return None  # complete — nothing to say
    return (".meta/version exists but is missing " + " and ".join(missing) + ". This push "
            "isn't fully labeled — consider `/version-set` so the PR can be named from the "
            "version's goals (`/version-ship`).")


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    command = (data.get("tool_input") or {}).get("command") or ""
    msg = check(command, meta_version_path().parent.parent)
    if not msg:
        return 0
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "Version label incomplete (advisory)",
            "additionalContext": msg,
        }
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
