#!/usr/bin/env python3
"""SessionStart hook: surface the development map's "you are here" into context.

Opt-in BY PRESENCE: if the project has no `.meta/roadmap/INDEX.md`, this is silent (it
hasn't adopted the development-map flow). When the map exists, it prints the INDEX
dashboard plus the active version cursor from `.meta/version`, so every session opens
knowing the overall plan and the current step.

It never blocks and never fails the session: on any error it prints nothing and exits 0.
The INDEX is meant to be ~one screen by design, so it's cheap to inject verbatim.
"""
import os
from pathlib import Path


def project_root() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def cursor_line() -> str:
    """The active version label + status from .meta/version, if present."""
    mv = project_root() / ".meta" / "version"
    if not mv.is_file():
        return ""
    label, status = "", ""
    try:
        for line in mv.read_text(encoding="utf-8", errors="replace").splitlines():
            s = line.strip()
            low = s.lower()
            if low.startswith("# version:") or low.startswith("version:"):
                label = s.split(":", 1)[1].strip()
            elif low.startswith("status:"):
                status = s.split(":", 1)[1].strip()
    except OSError:
        return ""
    if not label:
        return ""
    return f"{label} ({status})" if status else label


def main() -> int:
    try:
        index = project_root() / ".meta" / "roadmap" / "INDEX.md"
        if not index.is_file():
            return 0  # project hasn't adopted the development map — stay silent
        text = index.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            return 0
        print("Development map (.meta/roadmap/INDEX.md) — the project's stages, versions, "
              "and current position:\n")
        print(text)
        cursor = cursor_line()
        if cursor:
            print(f"\nActive version (.meta/version cursor): {cursor}")
        print("\nUse /roadmap-status to reconcile, /roadmap-set to (re)plan, and the "
              "advance-roadmap-step workflow to build the cursor version.")
    except Exception:  # never break a session over a status print
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
