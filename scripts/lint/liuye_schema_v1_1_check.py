#!/usr/bin/env python3
"""Schema v1.1 健康度检查 · 防 v1.2+ 升级时漏字段或破规则.

(D Phase 5 regression 防御 worker · 2026-05-21 retroactive 补)
(2026-05-21 C 档第 1 步 升级 · 适配 3 layer schema 拆分 — 见 SCHEMA_FILES)

校验项 (硬规则 · 任一 schema fail 即 exit 1):
  C1 · `schema_version` 字段存在 + 格式 `\\d+\\.\\d+`
  C2 · `changelog` 字段存在 + 至少 1 个 entry
  C3 · 每个 field 必有 `scope_tag` ∈ {"retail", "corporate", "both"}
  C4 · enum field (type=="enum") 必有非空 `enum_values` array
  C5 · 每个 field 的 `key` 全大写 + 下划线 + 数字 (^[A-Z][A-Z0-9_]+$)
  C6 · v1.0 baseline 34 字段不可删 (硬编码 baseline · 验证在 3 layer 合集中全存在)
  C7 · 3 layer 不重复 (同一 key 只能在一个 layer · 避免 SSOT 漂移) — 仅 union view + 3 layer 同时存在时检
  C8 · 3 layer 合并后 == union view 字段集 (字段不丢)

退出码: 0 = 全 PASS · 1 = 任一 FAIL
用法:
  py scripts/lint/liuye_schema_v1_1_check.py            # 默认 4 schema 全检 (3 layer + union view)
  py scripts/lint/liuye_schema_v1_1_check.py --json     # 机器可读
  py scripts/lint/liuye_schema_v1_1_check.py --schema templates/credit-terms-schema.json  # 只检单文件

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

# 2026-05-21 C 档第 1 步 升级 · 3 layer schema 拆分
# 2026-05-21 W1 第 1 步 升级 · 加入 decision_context layer (4 agent canonical input schema)
# 默认全检 5 个 (4 layer + union view) · 任一 fail 即 exit 1
SCHEMA_FILES = [
    REPO / "templates" / "client-metadata-schema.json",
    REPO / "templates" / "credit-terms-schema.json",
    REPO / "templates" / "material-facts-schema.json",
    REPO / "templates" / "decision-context-schema.json",  # W1 第 1 步 · credit Agent 决策结果 (跨 agent canonical handoff)
    REPO / "templates" / "placeholder-schema.json",  # union view (backward compat · DEPRECATED)
]
SCHEMA = SCHEMA_FILES[-1]  # 兼容老 --schema 默认值

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
    # 仅 union view (无 'layer' 字段 · 全集) 强制 C6 · 单 layer schema 跳过 (跨层在 C8 验证完整性)
    is_single_layer = bool(data.get("layer"))
    if not is_single_layer:
        current_keys = {f.get("key") for f in fields if isinstance(f.get("key"), str)}
        removed = [k for k in V1_0_BASELINE_KEYS if k not in current_keys]
        if removed:
            failed.append(
                f"C6 · v1.0 baseline 字段被删 ({len(removed)} 个 · 破坏对公 5 docx 向后兼容): "
                f"{', '.join(removed[:10])}"
            )

    return failed


def _lint_one(path: Path, data: dict) -> tuple[list[str], dict]:
    """单个 schema 文件 lint · 返回 (failures, summary_dict)."""
    failed = lint(data)
    fields = data.get("fields", [])
    scopes: dict[str, int] = {}
    for f in fields:
        s = f.get("scope_tag", "?")
        scopes[s] = scopes.get(s, 0) + 1
    summary = {
        "path": str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path),
        "layer": data.get("layer") or ("union-view" if path.name == "placeholder-schema.json" else "?"),
        "schema_version": data.get("schema_version", "?"),
        "field_count": len(fields),
        "scopes": scopes,
        "failures": failed,
    }
    return failed, summary


def _cross_layer_checks(layer_files: list[Path]) -> list[str]:
    """C7 + C8 · 跨 layer 一致性检查.

    C7: 3 layer (不含 union 和 decision_context) 字段不重复
    C8: 3 layer 合并 == union view 字段集

    注: decision_context (W1 第 1 步) 是独立 inter-agent canonical handoff schema ·
    不属 docx placeholder 68 key 集 · 跨层一致性检查仅检 client_metadata/credit_terms/material_facts vs union view.
    """
    failures: list[str] = []
    layers: dict[str, set[str]] = {}
    union_keys: set[str] = set()

    # W1 第 1 步: 跨层一致性仅覆盖 placeholder 三层 + union view · 排除 decision_context
    PLACEHOLDER_LAYERS = {"client_metadata", "credit_terms", "material_facts"}

    for p in layer_files:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        keys = {f.get("key") for f in d.get("fields", []) if f.get("key")}
        if p.name == "placeholder-schema.json":
            union_keys = keys
        else:
            layer_name = d.get("layer") or p.stem
            # decision_context 不参与 placeholder 跨层校验
            if layer_name not in PLACEHOLDER_LAYERS:
                continue
            layers[layer_name] = keys

    # C7 · 3 layer 不重叠
    seen: dict[str, str] = {}
    dups: list[str] = []
    for layer_name, keys in layers.items():
        for k in keys:
            if k in seen:
                dups.append(f"{k} (in {seen[k]} + {layer_name})")
            else:
                seen[k] = layer_name
    if dups:
        failures.append(
            f"C7 · 跨 layer 字段重复 (SSOT 漂移 · 同 key 只能在 1 个 layer): "
            f"{', '.join(dups[:10])}"
        )

    # C8 · 3 layer ∪ == union view
    if union_keys:
        merged = set().union(*layers.values()) if layers else set()
        missing_in_union = merged - union_keys
        missing_in_layers = union_keys - merged
        if missing_in_union:
            failures.append(
                f"C8 · 3 layer 有但 union view 缺: {', '.join(sorted(missing_in_union)[:10])}"
            )
        if missing_in_layers:
            failures.append(
                f"C8 · union view 有但 3 layer 缺: {', '.join(sorted(missing_in_layers)[:10])}"
            )

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Schema v1.1 健康度检查 (3 layer 升级版)")
    parser.add_argument("--json", action="store_true", help="JSON 输出 (CI 集成)")
    parser.add_argument(
        "--schema", type=Path, default=None,
        help="只检单 schema 文件路径 (默认 None · 跑 SCHEMA_FILES 全集)"
    )
    args = parser.parse_args()

    # 选择待检 schema 列表
    targets = [args.schema] if args.schema else SCHEMA_FILES

    all_summaries: list[dict] = []
    all_failures: list[str] = []

    for path in targets:
        if not path.exists():
            msg = f"[FATAL] schema 文件不存在: {path}"
            if args.json:
                all_summaries.append({"path": str(path), "error": msg})
            else:
                print(msg)
            all_failures.append(msg)
            continue

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            msg = f"[FATAL] schema JSON 解析失败 ({path.name}): {exc}"
            if args.json:
                all_summaries.append({"path": str(path), "error": msg})
            else:
                print(msg)
            all_failures.append(msg)
            continue

        failed, summary = _lint_one(path, data)
        all_summaries.append(summary)
        for f in failed:
            all_failures.append(f"[{path.name}] {f}")

    # 跨 layer 一致性 (只在跑全集时做)
    cross_failures: list[str] = []
    if not args.schema:
        cross_failures = _cross_layer_checks(SCHEMA_FILES)
        for f in cross_failures:
            all_failures.append(f"[cross-layer] {f}")

    if args.json:
        print(json.dumps(
            {
                "ok": not all_failures,
                "v1_0_baseline_count": len(V1_0_BASELINE_KEYS),
                "schemas": all_summaries,
                "cross_layer_failures": cross_failures,
                "failures": all_failures,
            },
            ensure_ascii=False, indent=2,
        ))
    else:
        if all_failures:
            for f in all_failures:
                print(f"[FAIL] {f}")
            print(f"\n[FAIL] {len(targets)} schema · {len(all_failures)} 项检查未过")
        else:
            for s in all_summaries:
                scope_str = " + ".join(f"{v} {k}" for k, v in sorted(s["scopes"].items()))
                print(
                    f"[PASS] {s['path']} · layer={s['layer']} · v{s['schema_version']} · "
                    f"{s['field_count']} 字段 ({scope_str})"
                )
            if not args.schema:
                print(
                    f"\n[PASS] {len(targets)} schema 全健康 · v1.0 baseline "
                    f"{len(V1_0_BASELINE_KEYS)} 字段全保留 (3 layer 合集) · 跨层一致性通过"
                )

    return 1 if all_failures else 0


if __name__ == "__main__":
    sys.exit(main())
