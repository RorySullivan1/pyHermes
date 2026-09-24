#!/usr/bin/env python3
"""Probe issue_body.py: every template renders, gates, and numbers correctly, and each one
is also a valid GitHub markdown issue template (it is installed verbatim as one).

    python3 probe_issue_body.py        # exit 0 = every case passed

Negative cases are the point. A gate that passes everything proves nothing, so each defect
class the gate claims to catch is injected and must be caught.
"""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "issue_body.py"
spec = importlib.util.spec_from_file_location("issue_body", SCRIPT)
ib = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ib)

FULL = {
    "epic": {"problem": "P.", "outcome": "O.", "breakdown": "1. A\n2. B (depends on A)",
             "acceptance": "- [ ] a", "non_goals": "None.", "risks": "R.", "dedupe": "searched `x`; none"},
    "task": {"parent": 48, "goal": "G.", "context": "C.", "scope": "In: a\nOut: b",
             "acceptance": "- [ ] a", "depends_on": "None"},
    "bug": {"parent": None, "what_happened": "W.", "steps": "1. x\n2. Observe: y", "expected": "E.",
            "environment": "v1", "evidence": "```\nlog\n```", "acceptance": "- [ ] regression test"},
    "feature": {"problem": "P.", "proposal": "Proposal: p.", "acceptance": "- [ ] a", "non_goals": "N."},
}

results: list[tuple[str, bool, str]] = []


def case(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def main() -> int:
    case("lint-templates: all four are valid GitHub templates", ib.lint_templates() == [], str(ib.lint_templates()))

    for kind, values in FULL.items():
        text, defects = ib.render(kind, values)
        case(f"{kind}: renders", not defects and bool(text), str(defects))
        case(f"{kind}: frontmatter stripped", not text.startswith("---\nname:"))
        case(f"{kind}: pre-filing check clean", ib.check(text, allow_self=True) == [], str(ib.check(text, True)))
        if "## Done when" in text:
            case(f"{kind}: post-filing check FAILS before fill-self [control]", ib.check(text, allow_self=False) != [])
            tmp = Path(tempfile.mkdtemp()) / "b.md"
            tmp.write_text(text)
            r = subprocess.run([sys.executable, str(SCRIPT), "fill-self", str(tmp), "61"], capture_output=True, text=True)
            case(f"{kind}: fill-self numbers the line", r.returncode == 0 and "#61\n```" in r.stdout, r.stderr)
            case(f"{kind}: fill-self drops the 'where N is' wording", "where N is" not in r.stdout)
            case(f"{kind}: post-filing check clean after fill-self", ib.check(r.stdout, False) == [], str(ib.check(r.stdout, False)))

    text, _ = ib.render("task", FULL["task"])
    case("task: parent given -> 'Part of #48'", text.startswith("Part of #48\n"))
    text, _ = ib.render("task", {**FULL["task"], "parent": None})
    case("task: parent null -> no 'Part of' line", "Part of" not in text and text.startswith("## Goal"))
    text, _ = ib.render("epic", {**FULL["epic"], "risks": None})
    case("epic: risks null -> section dropped, Closing kept", "Risks" not in text and "## Closing" in text)
    case("epic: dedupe fills the inline footer slot", "<sub>Dedupe: searched `x`; none</sub>" in text)

    # Negative cases: each must be caught.
    _, d = ib.render("task", {k: v for k, v in FULL["task"].items() if k != "scope"})
    case("missing required key -> named", any("scope" in x for x in d), str(d))
    _, d = ib.render("feature", {**FULL["feature"], "nongoals": "typo"})
    case("unknown key (typo) -> named", any("nongoals" in x for x in d), str(d))
    _, d = ib.render("nope", {})
    case("unknown template -> refused", bool(d))
    d = ib.check("## Goal\n\n<!-- goal: fill me -->\n", True)
    case("leftover slot -> caught", any("unfilled slot: goal" in x for x in d), str(d))
    d = ib.check("## Goal\n\n## Scope\nx\n", True)
    case("empty section -> caught", any("empty section: ## Goal" in x for x in d), str(d))
    vacuous = "## Done when\n\n```\nCloses #N\n```\n\n<sub>e.g. `Closes #1, closes #2`</sub>\n"
    case("footnote keyword does not satisfy post-filing check", ib.check(vacuous, False) != [])
    d = ib.check("---\nname: Task\nabout: x\n---\n## Goal\nx\n", True)
    case("frontmatter left in body -> caught", any("frontmatter" in x for x in d), str(d))

    # Lint must fail on a broken template (proves lint can fail).
    saved = ib.TEMPLATES
    tmpdir = Path(tempfile.mkdtemp())
    shutil.copy(saved / "task.md", tmpdir / "task.md")
    (tmpdir / "task.md").write_text((tmpdir / "task.md").read_text().replace("about: ", "abut: ", 1))
    (tmpdir / "bad.md").write_text("---\nname: Bad\nabout: x\n---\n## A\n{{a}}\n")
    ib.TEMPLATES = tmpdir
    d = ib.lint_templates()
    ib.TEMPLATES = saved
    case("lint: missing about -> caught", any("task.md: `about:`" in x for x in d), str(d))
    case("lint: short name + no slots + {{placeholder}} -> caught",
         sum("bad.md" in x for x in d) == 3, str(d))

    failed = 0
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
        if not ok:
            failed += 1
            print(f"      {detail}")
    print(f"\n{len(results) - failed}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
