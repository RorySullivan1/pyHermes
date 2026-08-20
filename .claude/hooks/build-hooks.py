#!/usr/bin/env python
"""build-hooks — compile per-hook fragments into settings.json.

Claude Code has no native way to load hook definitions from external files, so this
script is the bridge: it merges every `*.json` fragment in `.claude/hooks/` into the
`hooks` block of `.claude/settings.json`. The fragments are the source of truth — one
small, single-purpose file per hook — and `settings.json` is a generated artifact you
should not hand-edit.

Each fragment is a partial hooks object keyed by event name, e.g.:

    { "SessionStart": [ { "matcher": "...", "hooks": [ ... ] } ] }

Fragments are merged in filename order; multiple fragments targeting the same event
have their arrays concatenated.

Usage:
    python .claude/hooks/build-hooks.py            # regenerate settings.json
    python .claude/hooks/build-hooks.py --check     # exit 1 if settings.json is stale
    python .claude/hooks/build-hooks.py --warn-if-stale  # SessionStart: warn, never fail
    python .claude/hooks/build-hooks.py --on-edit   # PostToolUse: rebuild iff a fragment changed

Project root is resolved from $CLAUDE_PROJECT_DIR (fallback: cwd), so the same script
works vendored into any project. On macOS/Linux invoke with `python3`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


class BuildError(Exception):
    """A fragment is malformed or unreadable."""


def _force_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def project_root() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def hooks_dir() -> Path:
    return project_root() / ".claude" / "hooks"


def settings_path() -> Path:
    return project_root() / ".claude" / "settings.json"


def fragment_files() -> list[Path]:
    """Every *.json in .claude/hooks/ is a hook fragment (README/scripts are not)."""
    return sorted(p for p in hooks_dir().glob("*.json") if p.is_file())


def merge_fragments() -> dict:
    """Merge all fragments into one hooks object, concatenating per-event arrays."""
    merged: dict[str, list] = {}
    for path in fragment_files():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as error:
            raise BuildError(f"cannot read fragment {path.name}: {error}")
        if not isinstance(data, dict):
            raise BuildError(f"{path.name} must be an object keyed by event name")
        for event, entries in data.items():
            if not isinstance(entries, list):
                raise BuildError(f"{path.name} -> {event} must be a list")
            merged.setdefault(event, []).extend(entries)
    return merged


def load_settings() -> dict:
    if settings_path().exists():
        return json.loads(settings_path().read_text(encoding="utf-8"))
    return {}


def render(merged: dict) -> str:
    settings = load_settings()
    settings["hooks"] = merged
    return json.dumps(settings, indent=2, ensure_ascii=False) + "\n"


def current_text() -> str:
    return settings_path().read_text(encoding="utf-8") if settings_path().exists() else ""


def is_fragment(file_path: str | None) -> bool:
    """True if file_path is a *.json directly inside .claude/hooks/.

    Uses OS file identity (samefile) rather than string equality so it is robust to
    path-format differences (drive letter vs. /c/, slashes, casing) between the
    harness-provided path and CLAUDE_PROJECT_DIR.
    """
    if not file_path:
        return False
    try:
        p = Path(file_path)
        if p.suffix != ".json":
            return False
        return os.path.samefile(p.parent, hooks_dir())
    except (OSError, ValueError):
        return False


def read_stdin_json() -> dict:
    try:
        data = sys.stdin.read()
        return json.loads(data) if data.strip() else {}
    except (ValueError, TypeError, OSError):
        return {}


# --- modes -----------------------------------------------------------------

def mode_build() -> int:
    merged = merge_fragments()
    settings_path().write_text(render(merged), encoding="utf-8")
    print(f"wrote {settings_path().name} from {len(fragment_files())} fragment(s): "
          f"{', '.join(merged) or '(none)'}")
    return 0


def mode_check() -> int:
    n = len(fragment_files())
    if current_text() != render(merge_fragments()):
        print(f"stale: settings.json does not match {n} fragment(s). Run build-hooks.py.")
        return 1
    print(f"ok: settings.json is in sync with {n} fragment(s)")
    return 0


def mode_warn_if_stale() -> int:
    """SessionStart: surface drift into context, but never block the session."""
    try:
        if current_text() != render(merge_fragments()):
            print("WARNING: .claude/settings.json is out of sync with the hook "
                  "fragments in .claude/hooks/. Run `python .claude/hooks/build-hooks.py` "
                  "to regenerate it.")
    except BuildError as error:
        print(f"WARNING: hook fragment problem — {error}")
    return 0


def mode_on_edit() -> int:
    """PostToolUse: if the edited file was a hook fragment, regenerate settings.json."""
    payload = read_stdin_json()
    file_path = (payload.get("tool_input") or {}).get("file_path")
    if not is_fragment(file_path):
        return 0
    try:
        rendered = render(merge_fragments())
    except BuildError as error:
        print(f"hook fragment changed but settings.json NOT rebuilt — {error}")
        return 0
    settings_path().write_text(rendered, encoding="utf-8")
    print(f"rebuilt .claude/settings.json from hook fragments ({Path(file_path).name} changed)")
    return 0


def main(argv: list[str] | None = None) -> int:
    _force_utf8()
    parser = argparse.ArgumentParser(prog="build-hooks.py")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true",
                       help="verify settings.json matches the fragments; exit 1 if stale")
    group.add_argument("--warn-if-stale", action="store_true",
                       help="SessionStart hook: print a warning if stale, always exit 0")
    group.add_argument("--on-edit", action="store_true",
                       help="PostToolUse hook: rebuild iff the edited file is a fragment")
    args = parser.parse_args(argv)

    try:
        if args.check:
            return mode_check()
        if args.warn_if_stale:
            return mode_warn_if_stale()
        if args.on_edit:
            return mode_on_edit()
        return mode_build()
    except BuildError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
