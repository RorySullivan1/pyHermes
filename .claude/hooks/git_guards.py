#!/usr/bin/env python3
"""PreToolUse(Bash) dispatcher: every git-triggered advisory guard in one process.

One interpreter spawn per Bash call instead of one per guard — the guards themselves
(`version_guard`, `roadmap_guard`, `asset_integrity`) stay importable and standalone-
runnable; this reads stdin once, hands the command to each guard's `check(command, root)`,
and emits a single combined advisory. A guard that raises is skipped (fail safe, per
guard), and silence from all of them means no output at all.

To add a git-triggered guard: give it a `check(command: str, root: Path) -> str | None`
and add it to GUARDS. Do not wire it as its own fragment — that re-introduces the
per-Bash-call spawn this dispatcher exists to remove.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import asset_integrity  # noqa: E402
import roadmap_guard  # noqa: E402
import version_guard  # noqa: E402

GUARDS = (version_guard, roadmap_guard, asset_integrity)


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    command = (data.get("tool_input") or {}).get("command") or ""
    if not command:
        return 0
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())

    messages = []
    for guard in GUARDS:
        try:
            msg = guard.check(command, root)
        except Exception:
            msg = None  # a broken guard must not break the command
        if msg:
            messages.append(msg)
    if not messages:
        return 0

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "Advisory git guards",
            "additionalContext": "\n\n".join(messages),
        }
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
