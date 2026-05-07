"""Audit PM7 #3 + grounded report Critical Gap #5 · inline style 残留.

per `docs/reset/product-readiness-grounded-2026-05-07.md` §0.5:
  · CustomerListClient 31 inline · PersonalFinancePanel 22 · DecisionPanel 18 = 71 baseline
  · Codex R2 共识: 仅迁**静态视觉样式** · 保留 dynamic (e.g. width: ${pct}% / Recharts)

This script counts JSX `style={{` occurrences per file · groups per directory ·
lets future PR diff baseline.

Excludes:
  · *.spec.ts / *.test.* (test fixture)
  · web/src/lib/mock/** (mock data)

Output:
  · 终端 per-file count + grouped totals
  · JSON at .tmp/audit_inline_style.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB_SRC = ROOT / "web" / "src"
JSON_OUT = ROOT / ".tmp" / "audit_inline_style.json"

EXCLUDE_DIRS = ("web/src/lib/mock/",)
EXCLUDE_SUFFIX = (".spec.ts", ".spec.tsx", ".test.ts", ".test.tsx")

# Match `style={{` literal inline-style JSX prop.
# We do NOT count `style={cssVar}` (variable ref · likely styled component).
INLINE_STYLE_RE = re.compile(r"""\bstyle=\{\{""")


@dataclass
class Finding:
    file: str
    line: int
    snippet: str


def _is_excluded(rel_path: str) -> bool:
    if any(rel_path.startswith(d) for d in EXCLUDE_DIRS):
        return True
    return rel_path.endswith(EXCLUDE_SUFFIX)


def scan() -> list[Finding]:
    findings: list[Finding] = []
    for path in WEB_SRC.rglob("*.tsx"):
        _scan_file(path, findings)
    findings.sort(key=lambda f: (f.file, f.line))
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
        for _ in INLINE_STYLE_RE.finditer(raw):
            findings.append(Finding(file=rel, line=lineno, snippet=raw.strip()[:120]))


def render_summary(findings: list[Finding]) -> str:
    if not findings:
        return "  (none)"
    by_file: Counter[str] = Counter(f.file for f in findings)
    lines = ["", "[per-file count] (top 30)"]
    for file, n in by_file.most_common(30):
        lines.append(f"  {n:>4}  {file}")

    by_dir: Counter[str] = Counter()
    for f in findings:
        parts = f.file.split("/")
        if len(parts) >= 4:
            key = "/".join(parts[:4])
        else:
            key = f.file
        by_dir[key] += 1
    lines.append("")
    lines.append("[per-dir count] (top 15)")
    for dirpath, n in by_dir.most_common(15):
        lines.append(f"  {n:>4}  {dirpath}")
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
        print(f"=== audit_inline_style · web/src scan ===")
        print(f"WEB_SRC={WEB_SRC}")
        print(f"total findings: {len(findings)}")
        print(f"json out: {JSON_OUT.relative_to(ROOT)}")
        print(render_summary(findings))

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
