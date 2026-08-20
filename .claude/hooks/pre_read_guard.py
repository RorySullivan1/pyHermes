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
"""
import json
import sys
from pathlib import Path

THRESHOLD_BYTES = 60_000   # only act on files larger than this (~15k tokens)
MAX_LINES = 1500           # lines to keep when we do cap


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
