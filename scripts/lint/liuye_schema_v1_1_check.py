#!/usr/bin/env python3
"""Schema v1.1 健康度检查 · 防 v1.2+ 升级时漏字段或破规则.

(D Phase 5 regression 防御 worker · 2026-05-21 retroactive 补)

校验项 (硬规则 · 任一 fail 即 exit 1):
  C1 · `schema_version` 字段存在 + 格式 `\\d+\\.\\d+`
  C2 · `changelog` 字段存在 + 至少 1 个 entry
  C3 · 每个 field 必有 `scope_tag` ∈ {"retail", "corporate", "both"}
  C4 · enum field (type=="enum") 必有非空 `enum_values` array
  C5 · 每个 field 的 `key` 全大写 + 下划线 + 数字 (^[A-Z][A-Z0-9_]+$)
  C6 · v1.0 baseline 34 字段不可删 (硬编码 baseline · 验证全存在)

退出码: 0 = 全 PASS · 1 = 任一 FAIL
用法:
  py scripts/lint/liuye_schema_v1_1_check.py
  py scripts/lint/liuye_schema_v1_1_check.py --json   # 机器可读

依据: D Phase 4 worker 5 schema v1.1 brief · D Phase 5 worker TODO
  "建议加 scripts/lint/liuye_schema_v1_1_check.py 防 schema v1.2 时再升级出回归"
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent  # credit_report_agent_work/
SCHEMA = REPO / "templates" / "placeholder-schema.json"

VALID_SCOPE_TAGS = {"corporate", "retail", "both"}

# v1.0 baseline · 从 git show 8e786d9:templates/placeholder-schema.json 抽出的全 34 字段 ·
# 不可删 · 任一缺即判 v1.0 → v1.x 升级破坏向后兼容 · 现有对公 5 docx 模板会 broken
V1_0_BASELINE_KEYS = [
    # 基础企业身份 (10)
    "CLIENT_FULL_NAME", "CLIENT_CORE_NAME", "CLIENT_LEGAL_REP", "CLIENT_USCC",
    "CLIENT_ESTABLISHMENT_DATE", "CLIENT_REGISTERED_CAPITAL", "CLIENT_PAID_IN_CAPITAL",
    "CLIENT_REGISTERED_ADDRESS", "CLIENT_OPERATING_ADDRESS", "CLIENT_LOCATION_CITY",
    # 行业 / 业务 (6)
    "CLIENT_INDUSTRY_FULL", "CLIENT_INDUSTRY_CODE", "CLIENT_INDUSTRY_CATEGORY",
    "CLIENT_BUSINESS_SCOPE", "CLIENT_BUSINESS_DESC", "CLIENT_BACKGROUND",
    # 股权结构 (5)
    "CLIENT_PARENT_FULL_NAME", "CLIENT_PARENT_SHORT_NAME",
    "CLIENT_GROUP_FULL_NAME", "CLIENT_GROUP_SHORT_NAME", "CLIENT_LONG_CORE_NAME",
    # 经营规模 (4)
    "CLIENT_OPERATING_YEARS", "CLIENT_EMPLOYEE_COUNT",
    "CLIENT_SHAREHOLDER_PRIMARY", "CLIENT_SHARE_PCT_PRIMARY",
    # 授信信息 (3)
    "CREDIT_AMOUNT", "CREDIT_EXPOSURE", "CREDIT_PERIOD",
    # 评级 / 政策 (2)
    "PD_RATING", "INDUSTRY_POLICY_GUIDANCE",
    # 叙述类 (4)
    "FOUNDED_YEAR", "BUSINESS_QUALIFICATION_DESC",
    "BUSINESS_HISTORY_DESC", "BUSINESS_STRATEGY_DESC",
]

_VERSION_RE = re.compile(r"^\d+\.\d+(?:\.\d+)?$")
_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]+$")


def lint(data: dict) -> list[str]:
    """跑 6 项检查 · 返回 fail 描述列表 (空 = 全 PASS)."""
    failed: list[str] = []

    # ─── C1 · schema_version 存在 + 格式合规 ───
    version = data.get("schema_version")
    if not version:
        failed.append("C1 · schema_version 字段缺失")
    elif not isinstance(version, str) or not _VERSION_RE.match(version):
        failed.append(f"C1 · schema_version 格式非法: {version!r} (应为 'N.N' 或 'N.N.N')")

    # ─── C2 · changelog 至少 1 entry ───
    changelog = data.get("changelog")
    if not isinstance(changelog, list):
        failed.append("C2 · changelog 字段缺失或非数组")
    elif len(changelog) < 1:
        failed.append("C2 · changelog 为空 · 至少 1 entry")

    # fields 数组 root check
    fields = data.get("fields")
    if not isinstance(fields, list):
        failed.append("FATAL · fields 字段缺失或非数组 · 后续检查跳过")
        return failed

    # ─── C3 · 每个 field 有 scope_tag ∈ {retail, corporate, both} ───
    missing_scope: list[str] = []
    invalid_scope: list[str] = []
    for f in fields:
        key = f.get("key", "(unknown)")
        scope = f.get("scope_tag")
        if scope is None:
            missing_scope.append(key)
        elif scope not in VALID_SCOPE_TAGS:
            invalid_scope.append(f"{key}={scope!r}")
    if missing_scope:
        failed.append(f"C3 · 字段缺 scope_tag: {', '.join(missing_scope[:10])}")
    if invalid_scope:
        failed.append(
            f"C3 · scope_tag 非法 (合法值 {sorted(VALID_SCOPE_TAGS)}): "
            f"{', '.join(invalid_scope[:10])}"
        )

    # ─── C4 · enum field 必有非空 enum_values ───
    enum_no_values: list[str] = []
    enum_empty_values: list[str] = []
    for f in fields:
        if f.get("type") != "enum":
            continue
        key = f.get("key", "(unknown)")
        ev = f.get("enum_values")
        if ev is None:
            enum_no_values.append(key)
        elif not isinstance(ev, list) or len(ev) < 1:
            enum_empty_values.append(key)
    if enum_no_values:
        failed.append(f"C4 · enum field 缺 enum_values: {', '.join(enum_no_values)}")
    if enum_empty_values:
        failed.append(f"C4 · enum field enum_values 为空数组: {', '.join(enum_empty_values)}")

    # ─── C5 · key 全大写 + 下划线 + 数字 ───
    bad_keys: list[str] = []
    for f in fields:
        key = f.get("key")
        if not isinstance(key, str):
            bad_keys.append(f"(non-string={key!r})")
            continue
        if not _KEY_RE.match(key):
            bad_keys.append(key)
    if bad_keys:
        failed.append(
            f"C5 · key 命名违反 ^[A-Z][A-Z0-9_]+$ : {', '.join(bad_keys[:10])}"
        )

    # ─── C6 · v1.0 baseline 34 字段不可删 ───
    current_keys = {f.get("key") for f in fields if isinstance(f.get("key"), str)}
    removed = [k for k in V1_0_BASELINE_KEYS if k not in current_keys]
    if removed:
        failed.append(
            f"C6 · v1.0 baseline 字段被删 ({len(removed)} 个 · 破坏对公 5 docx 向后兼容): "
            f"{', '.join(removed[:10])}"
        )

    return failed


def main() -> int:
    parser = argparse.ArgumentParser(description="Schema v1.1 健康度检查")
    parser.add_argument("--json", action="store_true", help="JSON 输出 (CI 集成)")
    parser.add_argument(
        "--schema", type=Path, default=SCHEMA, help="schema 文件路径 (默认 templates/placeholder-schema.json)"
    )
    args = parser.parse_args()

    if not args.schema.exists():
        msg = f"[FATAL] schema 文件不存在: {args.schema}"
        if args.json:
            print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
        else:
            print(msg)
        return 1

    try:
        data = json.loads(args.schema.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        msg = f"[FATAL] schema JSON 解析失败: {exc}"
        if args.json:
            print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False))
        else:
            print(msg)
        return 1

    failed = lint(data)
    fields = data.get("fields", [])
    version = data.get("schema_version", "?")

    if args.json:
        print(json.dumps(
            {
                "ok": not failed,
                "schema_version": version,
                "field_count": len(fields),
                "v1_0_baseline_count": len(V1_0_BASELINE_KEYS),
                "failures": failed,
            },
            ensure_ascii=False, indent=2,
        ))
    else:
        if failed:
            for f in failed:
                print(f"[FAIL] {f}")
            print(
                f"\n[FAIL] schema v{version} · {len(fields)} 字段 · {len(failed)} 项检查未过"
            )
        else:
            # 统计 scope 分布
            scopes: dict[str, int] = {}
            for f in fields:
                s = f.get("scope_tag", "?")
                scopes[s] = scopes.get(s, 0) + 1
            scope_str = " + ".join(f"{v} {k}" for k, v in sorted(scopes.items()))
            print(
                f"[PASS] schema v{version} 健康 · {len(fields)} 字段 ({scope_str}) "
                f"· v1.0 baseline {len(V1_0_BASELINE_KEYS)} 字段全保留 · 6 项检查全通过"
            )

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
