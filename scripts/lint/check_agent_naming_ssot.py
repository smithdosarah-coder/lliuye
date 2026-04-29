#!/usr/bin/env python3
"""SSOT lint · 6 Agent × 8 列命名一致性校验.

Spec: docs/contracts/agent-naming-ssot.md v1.0 §4 (Phase A 验收硬线 #8).

校验项:
  C1 · backend mount prefix (agent_*/api.py @app.METHOD route) 与 SSOT route 列共形
  C2 · frontend archive 目录 web/src/app/archive/<id>/ 存在
  C3 · auth_service/rbac.py VALID_AGENTS 与 SSOT agent_id 列共形
  C4 · evaluation/<eval_baseline>.yaml 存在
  C5 · agent_*/api.py docstring 自报 mount 与实际 @app 一致

PM-pending: compli vs compliance 双 id (SSOT §3) · 校验降级为 WARN · 不是 ERROR.
退出码: 0 = 全 PASS (含 WARN) · 1 = 任一 ERROR.

用法:
  py scripts/lint/check_agent_naming_ssot.py
  py scripts/lint/check_agent_naming_ssot.py --strict   # WARN 也判 fail
  py scripts/lint/check_agent_naming_ssot.py --json     # 机器可读输出
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SSOT_PATH = REPO_ROOT / "docs/contracts/agent-naming-ssot.md"

# PM-pending 集 · 校验降 WARN
PM_PENDING_AGENT_IDS = {"compli", "compliance"}


# ---------------------------------------------------------------------------
# Parse SSOT markdown table
# ---------------------------------------------------------------------------

def parse_ssot_table(md: str) -> list[dict]:
    """提取 §1 8 列表 row · 返回 list of dict (per agent)."""
    in_table = False
    rows: list[dict] = []
    for line in md.splitlines():
        if "## 1. 8 列 SSOT 表" in line:
            in_table = True
            continue
        if in_table and line.startswith("## "):
            break
        # 表头识别 (含 'agent_id' 列)
        m_header = re.match(r"^\|\s*agent_id\s*\|", line)
        if m_header:
            continue
        # 跳分隔行 |---|---|...
        if re.match(r"^\|\s*[-:]+\s*\|", line):
            continue
        if in_table and line.startswith("|"):
            # markdown 表 cell 分隔符 = unescaped `|` · `\|` 是 row 内字面值 (e.g. "compli\|compliance")
            # 用 negative lookbehind 跳过 `\|`
            raw_cells = re.split(r"(?<!\\)\|", line)
            # 头尾空 cell (line 以 `|` 起 / 止)
            if raw_cells and raw_cells[0].strip() == "":
                raw_cells = raw_cells[1:]
            if raw_cells and raw_cells[-1].strip() == "":
                raw_cells = raw_cells[:-1]
            cells = [c.strip() for c in raw_cells]
            if len(cells) < 8:
                continue
            agent_id_raw, zh, biz, brand, route, color, rbac, eval_base = cells[:8]

            def clean(s: str) -> str:
                # 反 markdown 强调符 + emoji + 反 escape `\|` → `|`
                s = s.replace(r"\|", "|")
                s = re.sub(r"\*\*", "", s)
                s = re.sub(r"`", "", s)
                s = re.sub(r"^🟡\s*", "", s)
                return s.strip()

            agent_id = clean(agent_id_raw)
            # 双 id 占位 (e.g. "compli|compliance (PM TBD §3)") · 先剥 (...) 元数据再取 alts
            agent_id_core = re.sub(r"\([^)]*\)", "", agent_id).strip()
            ids = []
            for tok in re.split(r"[\s|/,]+", agent_id_core):
                tok = tok.strip("()\\ ")
                if not tok or tok in {"PM", "TBD", "§3"}:
                    continue
                # 守: agent_id 必须 [a-z][a-z0-9_-]*
                if not re.match(r"^[a-z][a-z0-9_-]*$", tok):
                    continue
                ids.append(tok)
            if not ids:
                continue
            rows.append({
                "agent_ids": ids,                    # canonical OR PM-pending alts
                "is_pm_pending": len(ids) > 1 or any(i in PM_PENDING_AGENT_IDS for i in ids),
                "zh": clean(zh),
                "business": clean(biz),
                "brand": clean(brand),
                "route_raw": clean(route),           # 含 "/archive/<TBD>" 占位
                "color_token": clean(color),
                "rbac_roles": [r.strip(" /") for r in re.split(r"\s*/\s*", clean(rbac).replace("·", "/")) if r.strip(" /")],
                "eval_baseline": clean(eval_base).replace("(PM TBD 后改)", "").strip(),
            })
    return rows


# ---------------------------------------------------------------------------
# Probes
# ---------------------------------------------------------------------------

def probe_backend_mount(agent_dir: Path) -> set[str]:
    """grep agent_*/api.py @app.METHOD("/api/<prefix>/...") · 返回 prefix 集."""
    prefixes: set[str] = set()
    api_py = agent_dir / "api.py"
    if not api_py.exists():
        return prefixes
    text = api_py.read_text(encoding="utf-8", errors="replace")
    # 匹配 @app.get("/api/xxx/..."), @app.post("/api/xxx/..."), 等
    for m in re.finditer(r'@app\.(?:get|post|put|delete|patch)\("(/api/[a-z][a-z0-9_-]*)/', text, re.IGNORECASE):
        prefix = m.group(1)
        # /api/channel · /api/compliance 等
        agent_part = prefix.replace("/api/", "")
        prefixes.add(agent_part)
    return prefixes


def probe_frontend_archive_dir(agent_id: str) -> bool:
    return (REPO_ROOT / "web" / "src" / "app" / "archive" / agent_id).is_dir()


def probe_rbac_valid_agents() -> set[str]:
    rbac_py = REPO_ROOT / "auth_service" / "rbac.py"
    if not rbac_py.exists():
        return set()
    text = rbac_py.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'VALID_AGENTS\s*=\s*\((.*?)\)', text, re.DOTALL)
    if not m:
        return set()
    return set(re.findall(r'"([a-z_][a-z0-9_-]*)"', m.group(1)))


def probe_eval_baseline_exists(rel_path: str) -> bool:
    return (REPO_ROOT / rel_path).is_file()


# ---------------------------------------------------------------------------
# Check engine
# ---------------------------------------------------------------------------

class Issue:
    __slots__ = ("level", "code", "agent", "msg")

    def __init__(self, level: str, code: str, agent: str, msg: str) -> None:
        self.level = level
        self.code = code
        self.agent = agent
        self.msg = msg

    def asdict(self) -> dict:
        return {"level": self.level, "code": self.code, "agent": self.agent, "msg": self.msg}


def run_checks() -> list[Issue]:
    if not SSOT_PATH.exists():
        return [Issue("ERROR", "SSOT_MISSING", "—", f"SSOT not found: {SSOT_PATH}")]

    ssot_rows = parse_ssot_table(SSOT_PATH.read_text(encoding="utf-8", errors="replace"))
    if len(ssot_rows) != 6:
        # SSOT 表 6 行 (PM 拍板后 compli/compliance 锁单 id 也仍是 6 row)
        return [Issue("ERROR", "SSOT_PARSE", "—",
                      f"SSOT 表行数 = {len(ssot_rows)} · expect 6 (per §1 6 Agent)")]

    issues: list[Issue] = []

    # build agent_id → SSOT row map (含 PM-pending alts)
    by_id: dict[str, dict] = {}
    canonical_ids: list[str] = []
    pending_alts: list[str] = []
    for row in ssot_rows:
        for aid in row["agent_ids"]:
            by_id[aid] = row
        if row["is_pm_pending"]:
            pending_alts.extend(row["agent_ids"])
        else:
            canonical_ids.extend(row["agent_ids"])

    # ----- C1 + C5: backend mount -----
    backend_dirs = sorted(REPO_ROOT.glob("agent_*"))
    backend_dirs = [d for d in backend_dirs if (d / "api.py").exists()]

    discovered_prefixes_by_dir: dict[str, set[str]] = {}
    for d in backend_dirs:
        prefixes = probe_backend_mount(d)
        discovered_prefixes_by_dir[d.name] = prefixes

    # 反推 dir → expected agent_id 候选 (e.g. agent_compliance → "compli" or "compliance")
    for dir_name, prefixes in discovered_prefixes_by_dir.items():
        # dir_name = "agent_<x>" · 抽 <x>
        suffix = dir_name.removeprefix("agent_")
        # 验 prefixes 都在 SSOT 内
        for p in prefixes:
            if p not in by_id:
                level = "WARN" if p in PM_PENDING_AGENT_IDS or any(a in PM_PENDING_AGENT_IDS for a in by_id) else "ERROR"
                issues.append(Issue(level, "C1_BACKEND_MOUNT_NOT_IN_SSOT",
                                    p, f"{dir_name}/api.py 用 /api/{p}/* · SSOT §1 无此 agent_id"))
        # dir_name suffix 与 prefix 是否一致 (e.g. agent_compliance + /api/compliance/* 一致 OK · agent_compliance + /api/compli/* 警告)
        if prefixes and suffix not in prefixes:
            # PM-pending 期允许 mismatch (compli vs compliance) · 否则 ERROR
            in_pending = (suffix in PM_PENDING_AGENT_IDS) or any(p in PM_PENDING_AGENT_IDS for p in prefixes)
            level = "WARN" if in_pending else "ERROR"
            issues.append(Issue(level, "C5_DIR_PREFIX_MISMATCH",
                                suffix, f"{dir_name}/ vs mount /api/{sorted(prefixes)} · dir suffix 与 prefix 不同"))

    # ----- C2: frontend archive dir -----
    for row in ssot_rows:
        for aid in row["agent_ids"]:
            if probe_frontend_archive_dir(aid):
                # 命中即 OK (PM-pending agent 任一 alt 命中即可)
                break
        else:
            level = "WARN" if row["is_pm_pending"] else "ERROR"
            issues.append(Issue(level, "C2_ARCHIVE_DIR_MISSING",
                                "/".join(row["agent_ids"]),
                                f"web/src/app/archive/<id>/ 不存在 (尝试 alts: {row['agent_ids']})"))

    # ----- C3: RBAC VALID_AGENTS -----
    rbac_valid = probe_rbac_valid_agents()
    if not rbac_valid:
        issues.append(Issue("ERROR", "C3_RBAC_PARSE",
                            "—", "auth_service/rbac.py VALID_AGENTS 解析失败"))
    else:
        for row in ssot_rows:
            hit = any(aid in rbac_valid for aid in row["agent_ids"])
            if not hit:
                level = "WARN" if row["is_pm_pending"] else "ERROR"
                issues.append(Issue(level, "C3_RBAC_MISSING",
                                    "/".join(row["agent_ids"]),
                                    f"VALID_AGENTS={sorted(rbac_valid)} 不含 SSOT alts {row['agent_ids']}"))
        # 反向检查: RBAC 有但 SSOT 无
        ssot_all_ids = {aid for r in ssot_rows for aid in r["agent_ids"]}
        for v in rbac_valid:
            if v not in ssot_all_ids:
                issues.append(Issue("ERROR", "C3_RBAC_EXTRA",
                                    v, f"RBAC VALID_AGENTS 含 '{v}' · SSOT 表无此 agent_id"))

    # ----- C4: evaluation baseline -----
    for row in ssot_rows:
        eb = row["eval_baseline"]
        if not eb:
            issues.append(Issue("WARN", "C4_EVAL_EMPTY",
                                "/".join(row["agent_ids"]), f"SSOT eval_baseline 列空"))
            continue
        if not probe_eval_baseline_exists(eb):
            level = "WARN" if row["is_pm_pending"] else "ERROR"
            issues.append(Issue(level, "C4_EVAL_MISSING",
                                "/".join(row["agent_ids"]), f"{eb} not found"))

    # ----- C6: PM-pending status report (compli vs compliance · audit Cat 8) -----
    # 不是 ERROR · 而是显式列出当前跨栈使用情况 · 让 PM 看到实际分布再决
    for row in ssot_rows:
        if not row["is_pm_pending"]:
            continue
        observations: list[str] = []
        for aid in row["agent_ids"]:
            seen_in: list[str] = []
            # backend api mount
            for dir_name, prefixes in discovered_prefixes_by_dir.items():
                if aid in prefixes:
                    seen_in.append(f"backend({dir_name}/api.py)")
                    break
            # frontend archive
            if probe_frontend_archive_dir(aid):
                seen_in.append(f"frontend(/archive/{aid})")
            # RBAC
            if aid in rbac_valid:
                seen_in.append(f"rbac({aid})")
            # eval baseline 文件名 substring
            if aid in row["eval_baseline"]:
                seen_in.append(f"eval({row['eval_baseline'].split('/')[-1]})")
            observations.append(f"{aid}@[{', '.join(seen_in) or 'NONE'}]")
        issues.append(Issue("WARN", "C6_PM_PENDING_DUAL_ID",
                            "/".join(row["agent_ids"]),
                            f"双 id 跨栈分布: {' · '.join(observations)} · PM 拍板后 lint 收紧 (audit Cat 8)"))

    return issues


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    # Force UTF-8 stdout (Windows GBK locale 默认会 mojibake emoji + 中文)
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true",
                        help="WARN 也判 fail (默认仅 ERROR fail)")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args(argv)

    issues = run_checks()

    errors = [i for i in issues if i.level == "ERROR"]
    warns = [i for i in issues if i.level == "WARN"]

    if args.json:
        out = {
            "ssot_path": str(SSOT_PATH.relative_to(REPO_ROOT)),
            "errors": [i.asdict() for i in errors],
            "warnings": [i.asdict() for i in warns],
            "pass": len(errors) == 0 and (not args.strict or len(warns) == 0),
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"== SSOT lint · {SSOT_PATH.relative_to(REPO_ROOT)} ==")
        if not issues:
            print("  ✅ all 6 agent × 5 check PASS")
        for i in errors:
            print(f"  ❌ ERROR [{i.code}] agent={i.agent} · {i.msg}")
        for i in warns:
            print(f"  ⚠️  WARN  [{i.code}] agent={i.agent} · {i.msg}")
        print(f"-- summary: {len(errors)} error · {len(warns)} warn --")
        if errors:
            print("FAIL · 修后重跑 · 详 docs/contracts/agent-naming-ssot.md")
        elif warns and args.strict:
            print("FAIL (--strict) · WARN 视作错")
        else:
            print("PASS (WARN 不阻塞 · PM 拍板 §3 后 WARN→ERROR)")

    if errors or (warns and args.strict):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
