"""Audit PM7 #1+#5 root cause · disabled / 占位 / silent CTA.

per handoff §5 R3 v2 件 #1 + Codex R1 evidence (ComposerBar.tsx:216-240 silent warn).

Scans web/src for 4 dead-CTA patterns:
  [1] static disabled prop on JSX button     `<button ... disabled` (no value or =true)
  [2] empty/stub onClick handler             `onClick={() => {}}` / `onClick={() => undefined}`
  [3] silent fallback console.warn in catch  `.catch(... console.warn(...silent`
  [4] TODO/占位 markers near JSX             single-line `// TODO` / `// 占位` / `// stub`
                                             (heuristic · only flagged when on its own line)

Excludes:
  · *.spec.ts / *.test.* (test file)
  · web/src/lib/mock/** (mock fixture)

Output:
  · 终端 grouped table
  · JSON at .tmp/audit_dead_cta.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB_SRC = ROOT / "web" / "src"
JSON_OUT = ROOT / ".tmp" / "audit_dead_cta.json"

EXCLUDE_DIRS = ("web/src/lib/mock/",)
EXCLUDE_SUFFIX = (".spec.ts", ".spec.tsx", ".test.ts", ".test.tsx")

PATTERNS: dict[str, re.Pattern[str]] = {
    # JSX <button ... disabled> with no value (literal flag) OR disabled={true}
    "static_disabled": re.compile(
        r"""<button\b[^>]*?\b(?:disabled(?=[\s>])|disabled=\{true\})"""
    ),
    # onClick handler that does nothing
    "empty_onclick": re.compile(
        r"""onClick=\{\s*\(\s*\)\s*=>\s*(?:\{\s*\}|undefined|null|void\s+0)\s*\}"""
    ),
    # silent fallback in catch (per ComposerBar.tsx:216-240 root cause)
    "silent_catch_warn": re.compile(
        r"""\.catch\b[^)]*?(?:console\.(?:warn|log)|/\*\s*silent\s*\*/)"""
    ),
    # standalone marker lines
    "todo_marker": re.compile(r"""^\s*//\s*(?:TODO|占位|stub|FIXME)\b"""),
}


@dataclass
class Finding:
    kind: str
    file: str
    line: int
    snippet: str


def _is_excluded(rel_path: str) -> bool:
    if any(rel_path.startswith(d) for d in EXCLUDE_DIRS):
        return True
    return rel_path.endswith(EXCLUDE_SUFFIX)


def scan() -> list[Finding]:
    findings: list[Finding] = []
    for path in WEB_SRC.rglob("*.ts"):
        _scan_file(path, findings)
    for path in WEB_SRC.rglob("*.tsx"):
        _scan_file(path, findings)
    findings.sort(key=lambda f: (f.kind, f.file, f.line))
    return findings


def _scan_file(path: Path, findings: list[Finding]) -> None:
    rel = path.relative_to(ROOT).as_posix()
    if _is_excluded(rel):
        return
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return
    for lineno, raw in enumerate(text.splitlines(), start=1):
        for kind, pat in PATTERNS.items():
            if pat.search(raw):
                findings.append(
                    Finding(kind=kind, file=rel, line=lineno, snippet=raw.strip()[:120])
                )


def render_table(findings: list[Finding]) -> str:
    if not findings:
        return "  (none)"
    lines = []
    by_kind: dict[str, list[Finding]] = {}
    for f in findings:
        by_kind.setdefault(f.kind, []).append(f)
    for kind in sorted(by_kind):
        group = by_kind[kind]
        lines.append(f"\n[{kind}] {len(group)} finding(s)")
        for f in group:
            lines.append(f"  {f.file}:{f.line}  {f.snippet}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--baseline", type=int, default=None)
    parser.add_argument("--exit-on-regression", action="store_true")
    args = parser.parse_args()

    findings = scan()

    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(
        json.dumps(
            {"total": len(findings), "findings": [asdict(f) for f in findings]},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    if args.json:
        print(json.dumps([asdict(f) for f in findings], ensure_ascii=False, indent=2))
    else:
        print(f"=== audit_dead_cta · web/src scan ===")
        print(f"WEB_SRC={WEB_SRC}")
        print(f"total findings: {len(findings)}")
        print(f"json out: {JSON_OUT.relative_to(ROOT)}")
        print(render_table(findings))

    if args.exit_on_regression and args.baseline is not None:
        if len(findings) > args.baseline:
            print(
                f"\n[REGRESSION] total {len(findings)} > baseline {args.baseline}",
                file=sys.stderr,
            )
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
