#!/usr/bin/env python3
"""Git-triggered guard: report `.claude/` asset defects before a commit or push.

Checks the structural invariants that are cheap to break and expensive to notice later:
a skill folder that no longer matches its `name:` frontmatter, an asset missing `name:` or
`description:`, a `references/` file cited by a SKILL.md that isn't there, and broken
symlinks (this repo single-sources some assets, so a moved canonical file silently breaks
the link).

Opt-in BY PRESENCE: silent in a project with no `.claude/skills` or `.claude/agents`.

**Non-mutating by contract.** It reads, it reports, it never writes — no reformatting, no
renaming, no "helpful" fixes. A hook that edits files during a commit turns a review into a
moving target, and the diff you approved is not the diff you push. If something is wrong,
a human or the model fixes it deliberately.

It never blocks: the dispatcher (`git_guards.py`) emits `permissionDecision: allow` plus an
`additionalContext` warning, so a commit is never vetoed — the model just learns what's
broken. Fails safe: on any unexpected shape or error it reports nothing and the command
proceeds. Runs under `git_guards.py` (one interpreter for all git guards); `main()` keeps
it standalone-runnable.
"""
import json
import os
import re
import sys
from pathlib import Path

GIT_RE = re.compile(r"\bgit\s+(commit|push)\b")
FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
REF_RE = re.compile(r"`(references/[A-Za-z0-9._/-]+)`")
SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "dist", "build"}
FOLD_MARKERS = {">", ">-", ">+", "|", "|-", "|+"}
MAX_FINDINGS = 12


def project_root() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def claude_dirs(root: Path) -> list[Path]:
    """`.claude` directories at depth <= 3. SKIP_DIRS applies to path parts BELOW root
    only — an ancestor directory named `build`/`dist`/… must not disable the guard.
    Deeper trees come first so a defect in a single-sourced asset is reported under its
    canonical path, not a symlink into it."""
    found = []
    for pattern in ("*/*/.claude", "*/.claude", ".claude"):
        for p in root.glob(pattern):
            if p.is_dir() and not (SKIP_DIRS & set(p.relative_to(root).parts)):
                found.append(p)
    return found


def frontmatter(text: str) -> dict[str, str] | None:
    """Top-level frontmatter as {key: scalar}, or None if there is no block. One parse
    serves every check. Folded/literal values (`>-` etc.) resolve to their joined
    continuation lines; quotes are stripped, so `name: "x"` and `name: x` agree."""
    m = FM_RE.match(text)
    if m is None:
        return None
    fm: dict[str, str] = {}
    key = None
    for line in m.group(1).splitlines():
        if line[:1].isspace():
            if key is not None and line.strip():
                fm[key] = (fm[key] + " " + line.strip()).strip()
            continue
        k = re.match(r"^([A-Za-z0-9_-]+)\s*:\s*(.*)$", line)
        if k:
            key = k.group(1)
            val = k.group(2).strip()
            fm[key] = "" if val in FOLD_MARKERS else val.strip("\"'")
    return fm


def read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def check_frontmatter(text: str, rel: str, expected_name: str, out: list[str]) -> None:
    """Shared skill/agent frontmatter contract: block present, name+description present,
    `name:` equal to the containing folder / filename stem."""
    fm = frontmatter(text)
    if fm is None:
        out.append(f"{rel} has no YAML frontmatter block")
        return
    for required in ("name", "description"):
        if required not in fm:
            out.append(f"{rel} frontmatter is missing `{required}:`")
    name = fm.get("name", "")
    if name and name != expected_name:
        out.append(f"{rel} frontmatter `name: {name}` != `{expected_name}` (they must match)")


def check_skill(folder: Path, rel: str, out: list[str]) -> None:
    skill = folder / "SKILL.md"
    if not skill.is_file():
        out.append(f"{rel}/ has no SKILL.md")
        return
    text = read(skill)
    if text is None:
        return
    check_frontmatter(text, f"{rel}/SKILL.md", folder.name, out)
    for ref in set(REF_RE.findall(text)):
        if not (folder / ref).exists():
            out.append(f"{rel}/SKILL.md cites `{ref}` but that file does not exist")


def scan(root: Path, dirs: list[Path]) -> list[str]:
    out: list[str] = []
    seen: set[Path] = set()  # canonical identities — a symlinked asset is checked once

    def first_visit(path: Path) -> bool:
        try:
            canonical = path.resolve()
        except OSError:
            canonical = path
        if canonical in seen:
            return False
        seen.add(canonical)
        return True

    for cdir in dirs:
        # Broken symlinks: the single-sourcing convention links at the layer level, so
        # layer roots plus one level below cover it without an rglob over session logs.
        for link in list(cdir.glob("*")) + list(cdir.glob("*/*")):
            if link.is_symlink() and not link.exists() and first_visit(link):
                out.append(f"{link.relative_to(root)} is a broken symlink")
        skills = cdir / "skills"
        if skills.is_dir():
            for folder in sorted(skills.iterdir()):
                if folder.is_dir() and first_visit(folder):
                    check_skill(folder, str(folder.relative_to(root)), out)
        agents = cdir / "agents"
        if agents.is_dir():
            for path in sorted(agents.glob("*.md")):
                if path.name != "README.md" and first_visit(path):
                    text = read(path)
                    if text is not None:
                        check_frontmatter(text, str(path.relative_to(root)), path.stem, out)
    return out


def check(command: str, root: Path) -> str | None:
    """Advisory message for the dispatcher, or None to stay silent."""
    if not GIT_RE.search(command):
        return None
    try:
        dirs = claude_dirs(root)
        if not any((c / "skills").is_dir() or (c / "agents").is_dir() for c in dirs):
            return None  # no assets here — nothing this guard can speak to
        findings = scan(root, dirs)
    except (OSError, RecursionError):
        return None
    if not findings:
        return None
    shown = findings[:MAX_FINDINGS]
    extra = len(findings) - len(shown)
    return (f"`.claude/` asset integrity — {len(findings)} issue(s) found:\n"
            + "\n".join(f"  - {f}" for f in shown)
            + (f"\n  … and {extra} more" if extra else "")
            + "\nThis check is advisory and non-mutating; fix these deliberately before shipping.")


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    command = (data.get("tool_input") or {}).get("command") or ""
    msg = check(command, project_root())
    if not msg:
        return 0
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": "Asset integrity issues (advisory)",
            "additionalContext": msg,
        }
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
