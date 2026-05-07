"""Audit PM7 #4 root cause · mock 数据混入 frontend.

per Codex R1 grounded evidence + handoff §5 R3 v2 件 #1.

Scans web/src for 4 mock-source混入 patterns:
  [1] @/lib/mock/* import sites           e.g. TodayContent.tsx:8-11
  [2] seed* default in zustand stores     e.g. dispatch-store.ts:298-302 threads:seedThreads
  [3] TODAY_*/MORNING_BRIEF_* fixture     e.g. layout-level mock fixture import
  [4] liveMode/mode/dataSource: 'seed'|'mock' default in store/component

不视作 finding (允许):
  · *.spec.ts (test 用 mock 是合规)
  · *.test.ts / *.test.tsx
  · web/src/lib/mock/** (mock fixture 自身定义文件)

Output:
  · 终端 grouped table
  · JSON at .tmp/audit_pm7_mock_sources.json (供 CI baseline diff)

Exit code:
  · 0 always unless --exit-on-regression + 超 baseline
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
JSON_OUT = ROOT / ".tmp" / "audit_pm7_mock_sources.json"

# 允许 list (mock fixture 文件自身 / test spec)
EXCLUDE_DIRS = ("web/src/lib/mock/",)
EXCLUDE_SUFFIX = (".spec.ts", ".spec.tsx", ".test.ts", ".test.tsx")

PATTERNS: dict[str, re.Pattern[str]] = {
    "lib_mock_import": re.compile(r"""from\s+['\"]@/lib/mock(/[^'"]*)?['\"]"""),
    "seed_default": re.compile(
        r"""(?P<key>threads|messages|tickets|customers|tasks|cases|reports|alerts|policies)\s*:\s*seed[A-Z]\w*"""
    ),
    "fixture_const_import": re.compile(
        r"""\b(TODAY_(?:IDLE|RUNNING|HOMEFEED)_\w+|MORNING_BRIEF_\w+|SEED_\w+)\b"""
    ),
    "mode_seed_default": re.compile(
        r"""(?:liveMode|mode|dataSource)\s*:\s*['\"](?P<mode>seed|mock|mock_forced)['\"]"""
    ),
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
    parser.add_argument("--json", action="store_true", help="emit JSON only")
    parser.add_argument(
        "--baseline",
        type=int,
        default=None,
        help="expected baseline count; exit 1 if total exceeds (with --exit-on-regression)",
    )
    parser.add_argument(
        "--exit-on-regression",
        action="store_true",
        help="exit non-zero if total > baseline",
    )
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
        print(f"=== audit_pm7_mock_sources · web/src scan ===")
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
