#!/usr/bin/env python3
"""PreToolUse(Read) guard: stop an accidental whole-file slurp of a very large file.

If the model issues a Read with no `limit` and no `offset` against a file bigger than
the byte threshold, this rewrites the input to read only the first MAX_LINES lines and
tells the model how to get more. It NEVER touches reads where the model set an explicit
limit/offset (that's intentional paging), and it no-ops on normal-sized files.

Correctness note: this trades completeness for context safety. The threshold is high so
it only fires on genuinely huge files, and the truncation is announced so the model can
re-read a specific slice. Tune THRESHOLD_BYTES / MAX_LINES or remove the hook if you'd
rather never auto-limit. Fails safe: any error → no change, read proceeds.

EXEMPT_DIRS is not a tuning knob in the same sense — see the comment on it. Set it to the
top-level directories holding the project's AUTHORITATIVE source. In a repo whose biggest
files are exactly its golden source, an unset EXEMPT_DIRS means the hook fires almost
exclusively on the files it must never truncate.
"""
import json
import os
import sys
from pathlib import Path

THRESHOLD_BYTES = 60_000   # only act on files larger than this (~15k tokens)
MAX_LINES = 1500           # lines to keep when we do cap

# Never cap a read of the authoritative source. A partial view of the one file that DEFINES
# the system is how a truncated read becomes a wrong change — and where the feedback loop is
# slow or lossy (a manual hand-off, a deploy, a human reporting "it didn't work"), that is
# undiagnosable. Pay the tokens. Set this per project; ("src", "schema") suits a repo whose
# golden source lives there. Empty tuple = guard everything.
EXEMPT_DIRS: tuple[str, ...] = ("src", "schema")


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, ValueError):
        return 0
    if data.get("tool_name") != "Read":
        return 0
    ti = data.get("tool_input") or {}
    # Respect explicit paging intent.
    if ti.get("limit") or ti.get("offset"):
        return 0
    fp = ti.get("file_path")
    if not fp:
        return 0
    try:
        p = Path(fp)
        size = p.stat().st_size
    except OSError:
        return 0
    if size <= THRESHOLD_BYTES:
        return 0
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    try:
        parts = p.resolve().relative_to(root.resolve()).parts
    except (OSError, ValueError):
        parts = p.parts
    if parts and parts[0] in EXEMPT_DIRS:
        return 0
    try:
        line_count = p.read_bytes().count(b"\n") + 1
    except OSError:
        return 0
    if line_count <= MAX_LINES:
        return 0

    new_input = dict(ti)
    new_input["offset"] = 1
    new_input["limit"] = MAX_LINES
    approx_tok = round(size / 4 / 1000, 1)
    msg = (f"Read auto-limited to the first {MAX_LINES} of {line_count} lines: "
           f"{fp} is ~{approx_tok}k tokens and reading it whole would crowd the main "
           f"context. Re-read with an explicit offset/limit for a specific section, or "
           f"delegate analysis of the full file to the token-manager agent.")
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "Large-file read capped to protect context",
            "updatedInput": new_input,
            "additionalContext": msg,
        }
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
