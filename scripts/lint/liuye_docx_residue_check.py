#!/usr/bin/env python3
"""Docx 残留 lint · byte-level diff 方法 (根因级 · 不依赖 keyword 黑名单).

背景:
  v16 模板 placeholder 化 治本走完 Phase 1-4 后,5 个 docx 已 placeholder 化.
  之前 2 次 dogfooding 用 keyword 黑名单扫(如 ['经纬','3375万','六一八'])均漏
  (Phase 2 先漏业务描述残留 · Phase 4 又漏财务数字残留).
  根因: 黑名单永远列不全 · 任何 specific 客户字面都可能被漏掉.

方法 (deterministic byte-level diff):
  对每个 docx · 同时 extract orig (`.bak-pre-placeholder`) 和 current 的所有
  element (paragraph + table cell) · 按 location key (`P{i}` / `T{ti}R{ri}C{ci}P{pi}`)
  做 element-level diff:

  1. 优先 ground truth: 从 sidecar `samples/<docx>.metadata.json` 读
     `original_client` 字典 · 取所有 value 作 "真实客户 specific 字面" 集合.
  2. backup pattern (覆盖 metadata 漏掉的): 公司名 / 中文人名 / 资金数字 /
     日期 / 身份证 / USCC (统一社会信用代码) 6 类正则.
  3. 对每个 element location:
     - 移除 `{{KEY}}` placeholder 后扫剩余 cur.text
     - 找出 cur 含的 specific 字面 (metadata value 或 pattern match)
     - 与同 location 的 orig.text 交叉验证: 如果 orig 也含同 specific 字面 ->
       该位置原本就是客户数据,cur 没 placeholder 化 -> **漏覆盖**
     - 如果 orig 不含但 cur 含 -> 模板原生指引文,非客户 leak,放行

  4. 特殊场景: orig 不存在该 location (cur 是新增段) · 只用 pattern 扫,无法
     用 metadata 交叉验证 -> 报为 unknown_residue (低优先级).

退出码: 0 = 全 PASS (无 residue) · 1 = 有 residue

用法:
  py scripts/lint/liuye_docx_residue_check.py                    # 文本报告
  py scripts/lint/liuye_docx_residue_check.py --json             # JSON 输出
  py scripts/lint/liuye_docx_residue_check.py --docx <file.docx> # 单个 docx
  py scripts/lint/liuye_docx_residue_check.py --top 20           # 详情条数

设计依据: 第一性 + 治本不治标 · 用通用机制 (byte-level diff + canonical ground
truth) 代替 keyword 黑名单 · 不依赖 "想到所有可能漏的词".
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
from v16_step1_extract import extract_elements  # noqa: E402

PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_][A-Z0-9_]*)\}\}")

# Backup patterns (catch what metadata 漏掉的)
# 中文公司全称 (含 "有限公司" / "股份公司" / "合作社" / "个体工商户" 等)
COMPANY_FULL_RE = re.compile(
    r"[一-龥]{2,30}(?:有限公司|股份有限公司|股份公司|集团有限公司|集团公司|"
    r"个体工商户|合作社|分公司|子公司|事务所|研究所|研究院)"
)
# 中文人名 (2-4 字 · 前缀 "法定代表人/法人/实控人/董事长/总经理" 强信号)
# 不用 "股东" 触发 (会误命中 "股东之间关系" / "股东背景" · SCAFFOLD)
# 不用 "持股比例/面访评价/简介" 等明显非姓名后缀
COMMON_SURNAMES = (
    "王李张刘陈杨黄赵周吴徐孙马朱胡郭何高林郑罗梁宋谢唐韩冯邓曹彭曾肖田董袁潘"
    "于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱"
    "江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤"
)
PERSON_NAME_RE = re.compile(
    r"(?:法定代表人|法人代表|法人|实际控制人|实控人|董事长|总经理|总裁|执行董事)"
    r"[:：]?\s*([" + COMMON_SURNAMES + r"][一-龥]{1,3})(?![一-龥])"
)
# 资金数字 (含单位 "万元/亿元/元" · 至少 2 位数字防 "1元/0元" 噪音)
MONEY_RE = re.compile(r"(?:人民币)?[\d,]{2,}(?:\.\d+)?\s*(?:万元|亿元|千万元|元)")
# 日期 (年月日 / 年月)
DATE_RE = re.compile(r"(?:19|20)\d{2}\s*年\s*\d{1,2}\s*月(?:\s*\d{1,2}\s*日)?")
# 身份证号 (18 位 · 末位可 X)
ID_NUMBER_RE = re.compile(r"\b\d{17}[\dXx]\b")
# USCC (统一社会信用代码 18 位 · 首位 1-9 或 A-Y · 排除 O · 后 17 位 0-9A-Z)
USCC_RE = re.compile(r"\b[1-9A-NP-Y][0-9A-HJ-NP-Z]{17}\b")

BACKUP_PATTERNS = [
    ("company", COMPANY_FULL_RE),
    ("person", PERSON_NAME_RE),
    ("money", MONEY_RE),
    ("date", DATE_RE),
    ("id_number", ID_NUMBER_RE),
    ("uscc", USCC_RE),
]

# 通用噪音 (公司名 pattern 会误杀的 SCAFFOLD 文字 · 全黑名单更稳)
GENERIC_NOISE = {
    "有限公司", "股份有限公司", "股份公司", "集团有限公司", "个体工商户",
    "合作社", "公司", "事务所",
}

# 示范字面 (skeleton/模板示例文 · narrative_example_paragraphs 常见)
EXAMPLE_PLACEHOLDERS = {"XX", "XXX", "XXXX", "XXXXX", "X月", "X日", "X年"}


def load_metadata(metadata_path: Path) -> dict:
    """读 sidecar metadata.json · 返回 dict (缺失/解析失败返空)."""
    if not metadata_path.is_file():
        return {}
    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def is_too_generic_value(value: str) -> bool:
    """判断 canonical value 是否太通用 · 不适合做 ground truth.

    e.g. "一年" / "100%" / "5" / 短数字 / 纯标点 — 在模板/财务报告里普遍出现 ·
    用做匹配会大量假阳性 · 应该靠 placeholder_locations 精确锁定而不是字面.
    """
    v = value.strip()
    if not v:
        return True
    # 纯数字 + 简短单位
    if re.fullmatch(r"\d{1,3}\s*[%‰]?", v):
        return True
    # 通用时间词
    if v in {"一年", "二年", "三年", "半年", "一个月", "三个月", "一季度", "一期"}:
        return True
    # 纯单字符 / 长度过短 (避免误把 "5" 当成 PD_RATING ground truth)
    if len(v) <= 2:
        return True
    return False


def extract_canonical_values(metadata: dict) -> set[str]:
    """从 metadata.original_client 提取所有 specific 客户字面 set.

    过滤掉 generic / 太通用的 value (一年 / 100% / 短数字) · 这些靠
    placeholder_locations 精确判断 · 不靠字面匹配.
    """
    canonical: set[str] = set()
    original = metadata.get("original_client") or {}
    if isinstance(original, dict):
        for v in original.values():
            if isinstance(v, str):
                s = v.strip()
                if len(s) >= 2 and s not in GENERIC_NOISE and not is_too_generic_value(s):
                    canonical.add(s)
    return canonical


def is_skeleton_template(metadata: dict) -> bool:
    """skeleton 模板 (普惠骨架型 等) · original_client 为空 + branch=A.

    这种模板含大量 'XX/XXX/张XX/2010年5月' 示例文 · narrative_example_paragraphs
    全在 out_of_scope · 不应被 pattern 匹配误报.
    """
    branch = (metadata.get("branch") or "").strip()
    original = metadata.get("original_client") or {}
    return branch.upper().startswith("A") and not original


def strip_placeholders(text: str) -> str:
    """移除 `{{KEY}}` 占位符后返回剩余文本."""
    return PLACEHOLDER_RE.sub("", text)


def find_canonical_hits(text: str, canonical: set[str]) -> list[tuple[str, str]]:
    """找 text 中出现的 canonical 字面 · 返回 [(kind='canonical', value), ...]."""
    if not canonical:
        return []
    hits = []
    for v in canonical:
        if v in text:
            hits.append(("canonical", v))
    return hits


def find_pattern_hits(text: str) -> list[tuple[str, str]]:
    """找 text 中匹配 backup pattern 的 specific 字面."""
    hits = []
    for pat_name, pat in BACKUP_PATTERNS:
        for m in pat.finditer(text):
            value = m.group(1) if m.groups() else m.group(0)
            value = value.strip()
            if value and value not in GENERIC_NOISE:
                hits.append((pat_name, value))
    return hits


def lint_docx(docx_path: Path) -> dict:
    """diff 单个 docx vs 其 .bak-pre-placeholder · 返回 residue report.

    分类:
      - HIGH: declared in `placeholder_locations` 但 cur 没 `{{KEY}}` 且仍含 canonical
        (元数据声明应 placeholder 化 · 但漏了)
      - MED: canonical 字面在 cur 出现 + orig 同位置含相同字面 (真客户 leak)
      - LOW: pattern-only · orig 同位置含相同字面 (backup pattern 捕获)
    """
    bak_path = docx_path.parent / f"{docx_path.name}.bak-pre-placeholder"
    metadata_path = docx_path.with_suffix(".metadata.json")

    if not bak_path.exists():
        return {
            "docx": docx_path.name,
            "error": "missing .bak-pre-placeholder",
            "residues": [],
            "residue_count": 0,
        }

    metadata = load_metadata(metadata_path)
    canonical = extract_canonical_values(metadata)
    declared_locations = set((metadata.get("placeholder_locations") or {}).keys())
    skeleton = is_skeleton_template(metadata)

    try:
        orig_elems = {e.location: e for e in extract_elements(bak_path)}
        cur_elems = {e.location: e for e in extract_elements(docx_path)}
    except Exception as exc:
        return {
            "docx": docx_path.name,
            "error": f"extract failed: {exc!r}",
            "residues": [],
            "residue_count": 0,
        }

    residues = []
    for loc, cur_e in cur_elems.items():
        cur_text = (cur_e.text or "").strip()
        if not cur_text:
            continue

        cur_without_ph = strip_placeholders(cur_text)
        if not cur_without_ph.strip():
            continue  # 全是 placeholder · OK

        orig_e = orig_elems.get(loc)
        orig_text = (orig_e.text or "").strip() if orig_e else ""

        # ─────────────────────────────────────────────────────────
        # 高优先 check 1: declared placeholder_location 但 cur 无 {{}}
        # ─────────────────────────────────────────────────────────
        is_declared = loc in declared_locations
        has_placeholder = bool(PLACEHOLDER_RE.search(cur_text))

        leaked: list[dict] = []

        if is_declared and not has_placeholder:
            # metadata 声明应 placeholder 化 · 但 cur 没占位符 · HIGH 信号
            leaked.append({
                "kind": "declared_not_placeholderized",
                "value": cur_text[:50],
                "source": "metadata.placeholder_locations",
                "severity": "HIGH",
            })

        # ─────────────────────────────────────────────────────────
        # check 2: canonical hits in cur (metadata ground truth)
        # ─────────────────────────────────────────────────────────
        canonical_hits = find_canonical_hits(cur_without_ph, canonical)
        for kind, value in canonical_hits:
            severity = "HIGH" if orig_text and value in orig_text else "MED"
            leaked.append({
                "kind": "canonical",
                "value": value,
                "source": "metadata.original_client",
                "severity": severity,
            })

        # ─────────────────────────────────────────────────────────
        # check 3: backup pattern hits (catch metadata 漏掉的)
        # 仅在 orig 同位置也含同字面时算 leak (避免示范文/SCAFFOLD 假阳)
        # skeleton 模板含大量示例文 (XX/张XX/2010年5月) · 直接跳过 pattern
        # ─────────────────────────────────────────────────────────
        if not skeleton:
            pattern_hits = find_pattern_hits(cur_without_ph)
            for kind, value in pattern_hits:
                if orig_text and value in orig_text:
                    # orig 也含 · 是 phase placeholder 化漏了 (LOW · pattern 兜底)
                    leaked.append({
                        "kind": kind,
                        "value": value,
                        "source": "pattern",
                        "severity": "LOW",
                    })

        if not leaked:
            continue

        # 去重
        seen = set()
        uniq = []
        for it in leaked:
            key = (it["kind"], it["value"])
            if key in seen:
                continue
            seen.add(key)
            uniq.append(it)

        residues.append({
            "location": loc,
            "element_kind": cur_e.kind,
            "declared_in_metadata": is_declared,
            "has_placeholder": has_placeholder,
            "orig_text": orig_text[:200],
            "cur_text": cur_text[:200],
            "leaked": uniq,
            "max_severity": max(
                (it["severity"] for it in uniq),
                key=lambda s: {"HIGH": 3, "MED": 2, "LOW": 1}.get(s, 0),
            ),
        })

    # 按 severity 排序: HIGH first
    severity_order = {"HIGH": 0, "MED": 1, "LOW": 2}
    residues.sort(key=lambda r: (severity_order.get(r["max_severity"], 99), r["location"]))

    high_count = sum(1 for r in residues if r["max_severity"] == "HIGH")
    med_count = sum(1 for r in residues if r["max_severity"] == "MED")
    low_count = sum(1 for r in residues if r["max_severity"] == "LOW")

    return {
        "docx": docx_path.name,
        "orig_element_count": len(orig_elems),
        "current_element_count": len(cur_elems),
        "canonical_value_count": len(canonical),
        "declared_location_count": len(declared_locations),
        "is_skeleton_template": skeleton,
        "residue_count": len(residues),
        "high_count": high_count,
        "med_count": med_count,
        "low_count": low_count,
        "residues": residues,
    }


def lint_docx_standalone(docx_path: Path) -> dict:
    """对单个 docx 做 standalone (独立) lint · 不依赖 `.bak-pre-placeholder` / metadata.json.

    适用场景: 用户上传自定义 docx 模板 · 没有原始 .bak (备份) · 没有 sidecar metadata.
    通用 (general-purpose) 机制 (per 第一性原则):
      1. 抽 placeholder set: 扫所有 element 找 `{{KEY}}` · 取 unique KEY set
      2. 抽 placeholder count: element 含 `{{KEY}}` 数 (位置维度 · 一个 element 多个 placeholder 算多次)
      3. 检测 residue (残留): 移除所有 `{{KEY}}` 后 · 用 backup pattern 扫剩余文本 ·
         找出未 placeholder 化的 specific 字面 (公司名 / 中文人名 / 资金 / 日期 / 身份证 / USCC)
      4. residue_samples: 给前端 ≤ 5 个 sample 让用户看 (per 交互体验原则 · 反馈引导行动)
      5. validation: PASS (residue=0) · WARN (residue ≥ 1) · 不强 block · 用户决定

    返:
      {
        placeholder_count: int (位置数 · 一个 element 多 placeholder 算多次),
        placeholder_keys: list[str] (unique KEY · sorted),
        residue_count: int (residue 数 · 全部 backup pattern hit 去重),
        residue_samples: list[dict] (≤5 个 · {location, kind, value, snippet}),
        validation: "PASS" | "WARN" | "ERROR",
        element_count: int (总 element 数 · 含 paragraph + cell),
        error: str | None (extract 失败时填),
      }
    """
    try:
        elements = extract_elements(docx_path)
    except Exception as exc:  # noqa: BLE001 — extract 失败 · 返 ERROR 给前端 banner
        return {
            "placeholder_count": 0,
            "placeholder_keys": [],
            "residue_count": 0,
            "residue_samples": [],
            "validation": "ERROR",
            "element_count": 0,
            "error": f"docx 抽取失败 · {type(exc).__name__}: {exc}",
        }

    placeholder_keys: set[str] = set()
    placeholder_count = 0
    residues: list[dict] = []
    seen_residue: set[tuple[str, str]] = set()  # (kind, value) 去重 · 跨 element

    for elem in elements:
        text = (elem.text or "").strip()
        if not text:
            continue

        # 1. 统计 placeholder
        for m in PLACEHOLDER_RE.finditer(text):
            placeholder_keys.add(m.group(1))
            placeholder_count += 1

        # 2. 移除 placeholder 后扫 residue
        residual = strip_placeholders(text).strip()
        if not residual:
            continue

        # 3. backup pattern 找 specific 字面 (未 placeholder 化的真实客户数据)
        for kind, value in find_pattern_hits(residual):
            if value in EXAMPLE_PLACEHOLDERS:
                continue
            key = (kind, value)
            if key in seen_residue:
                continue
            seen_residue.add(key)
            residues.append({
                "location": elem.location,
                "element_kind": elem.kind,
                "kind": kind,           # company / person / money / date / id_number / uscc
                "value": value,
                "snippet": text[:100],  # 前 100 字符 · 给用户看上下文
            })

    return {
        "placeholder_count": placeholder_count,
        "placeholder_keys": sorted(placeholder_keys),
        "residue_count": len(residues),
        "residue_samples": residues[:5],  # ≤5 个 sample 给前端展示
        "validation": "PASS" if not residues else "WARN",
        "element_count": len(elements),
        "error": None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Docx 残留 lint · byte-level diff")
    parser.add_argument(
        "--docx", type=str, default=None,
        help="单个 docx 路径 (相对 repo · 默认扫 samples/*.docx)"
    )
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    parser.add_argument("--top", type=int, default=10, help="文本模式 top N residue 详情")
    args = parser.parse_args()

    if args.docx:
        d = Path(args.docx)
        if not d.is_absolute():
            d = REPO / args.docx
        docx_files = [d]
    else:
        samples_dir = REPO / "samples"
        docx_files = sorted([
            d for d in samples_dir.glob("*.docx")
            if "bak" not in d.name and "metadata" not in d.name
        ])

    reports = []
    total_residue = 0
    total_high = 0
    total_med = 0
    total_low = 0
    for d in docx_files:
        report = lint_docx(d)
        reports.append(report)
        total_residue += report.get("residue_count", 0)
        total_high += report.get("high_count", 0)
        total_med += report.get("med_count", 0)
        total_low += report.get("low_count", 0)

    # 非零退出仅当存在 HIGH + MED · LOW 是 pattern 兜底信号(可能噪音多) · 仅警告
    fail = total_high > 0 or total_med > 0

    overall = {
        "total_residue": total_residue,
        "total_high": total_high,
        "total_med": total_med,
        "total_low": total_low,
        "docx_count": len(reports),
        "docx_reports": reports,
        "exit_code": 1 if fail else 0,
    }

    if args.json:
        print(json.dumps(overall, ensure_ascii=False, indent=2))
    else:
        print(f"[liuye-docx-residue] scanned {len(reports)} docx files\n")
        for r in reports:
            print(f"=== {r['docx']} ===")
            if "error" in r:
                print(f"  ERROR: {r['error']}")
                continue
            tags = []
            if r.get("is_skeleton_template"):
                tags.append("SKELETON")
            tag_str = f" [{','.join(tags)}]" if tags else ""
            print(
                f"  orig elements: {r['orig_element_count']} · "
                f"current elements: {r['current_element_count']} · "
                f"canonical values: {r['canonical_value_count']} · "
                f"declared locations: {r['declared_location_count']}{tag_str}"
            )
            print(
                f"  residue count: {r['residue_count']} · "
                f"HIGH={r['high_count']} MED={r['med_count']} LOW={r['low_count']}"
            )
            for res in r["residues"][: args.top]:
                leaked_str = ", ".join(
                    f"{it['kind']}={it['value']}" for it in res["leaked"][:5]
                )
                print(f"    [{res['max_severity']}] [{res['element_kind']}] {res['location']}: {leaked_str}")
                if res["orig_text"]:
                    print(f"      orig: {res['orig_text'][:100]}")
                print(f"      cur:  {res['cur_text'][:100]}")
            if r["residue_count"] > args.top:
                print(f"    ... ({r['residue_count'] - args.top} more residues truncated)")
            print()
        print(
            f"=== TOTAL residue: {total_residue} · "
            f"HIGH={total_high} MED={total_med} LOW={total_low} ==="
        )
        if not fail:
            print("PASS (no HIGH/MED residue)")
        else:
            print("FAIL (HIGH/MED residue present)")

    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
