# -*- coding: utf-8 -*-
"""硬字段格式正则抽取器 — 从材料文本中结构化提取格式固定的信息.

为什么做:
  material_kb.py 原始实现依赖"关键词+邻近"(如"电话:\\s*XXX")启发式抽取,
  对真实客户材料的 OCR 文本召回率偏低(中锐样本 GT 命中 33%)。
  本模块改用 "格式正则 + 上下文证据"方式 — 统一信用代码 / 身份证 / 手机 /
  银行账号 / 邮编 等字段的格式是硬约束,从全文正则直接打捞,比关键词启发式鲁棒。

设计:
  - 每个字段一个 EXTRACT_FUNCS 函数,接收 text,返回去重后的命中值(+ 来源片段)
  - 聚合函数 extract_hard_fields 对整个 file_contents 扫一遍,按出现频次/先后择优
  - 不做"值是否合理"的语义判断(留给调用方);只做格式合规
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any


# ────────────────────────────────────────────────────────────
# 字段格式正则 — 每个字段一条强约束格式
# ────────────────────────────────────────────────────────────

# 统一社会信用代码: 18 位, 首两位固定 91/92 等机构类型; 中国大陆普遍 91 开头
# 来源: GB 32100-2015; 第 1 位登记管理部门 + 第 2 位机构类别 + 6 位行政区划 +
# 9 位组织机构代码 + 1 位校验码(0-9/A-Z,排除 I/O/S/V/Z)
_USC_RE = re.compile(r"\b[159][0-9][0-9]{6}[0-9A-HJ-NPQRTUWXY]{9}[0-9A-HJ-NPQRTUWXY]\b")

# 身份证号码: 18 位, 6 位行政区 + 8 位生日(19xx/20xx) + 3 位顺序 + 1 位校验(0-9/X)
_ID_RE = re.compile(r"\b[1-9][0-9]{5}(?:19|20)[0-9]{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12][0-9]|3[01])[0-9]{3}[0-9Xx]\b")

# 手机号码: 1 + [3-9] + 9 位
_PHONE_RE = re.compile(r"(?<![\d])1[3-9][0-9]{9}(?![\d])")

# 邮编: 6 位, 大陆编码以 1-8 开头, 第 2 位 0-9
_POSTCODE_RE = re.compile(r"(?<![\d])[1-8][0-9]{5}(?![\d])")

# 银行账号: 10-25 位连续数字(多数对公账号 12-19 位)
_BANK_ACC_RE = re.compile(r"(?<![\d])[0-9]{11,22}(?![\d])")

# 日期: YYYY-MM-DD / YYYY年MM月DD日 / YYYY.MM.DD
_DATE_RE = re.compile(
    r"(?<!\d)(19|20)\d{2}[年\-./](0?[1-9]|1[0-2])[月\-./](0?[1-9]|[12]\d|3[01])日?(?!\d)"
)


# ────────────────────────────────────────────────────────────
# 单字段抽取
# ────────────────────────────────────────────────────────────

def extract_usc(text: str) -> list[str]:
    """统一社会信用代码 — 去重保序."""
    seen: set[str] = set()
    out: list[str] = []
    for m in _USC_RE.finditer(text):
        v = m.group(0)
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def extract_id_numbers(text: str) -> list[str]:
    """18 位身份证号 — 去重保序."""
    seen: set[str] = set()
    out: list[str] = []
    for m in _ID_RE.finditer(text):
        v = m.group(0)
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def extract_phones(text: str) -> list[str]:
    """手机号 — 去重保序."""
    seen: set[str] = set()
    out: list[str] = []
    for m in _PHONE_RE.finditer(text):
        v = m.group(0)
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def extract_postcodes(text: str) -> list[str]:
    """邮编 — 带上下文过滤(需出现 邮编/邮政编码 字样或紧邻地址)."""
    hits: list[str] = []
    seen: set[str] = set()
    # 优先取 "邮编:" / "邮政编码:" 附近的
    for m in re.finditer(r"邮[政编]*编?[码号]?\s*[:：]?\s*([1-8][0-9]{5})", text):
        v = m.group(1)
        if v not in seen:
            seen.add(v)
            hits.append(v)
    return hits


def extract_bank_accounts(text: str) -> list[str]:
    """银行账号 — 带上下文过滤.

    银行账号格式与其他长数字难区分,必须要求 '账号/账户' 上下文.
    """
    hits: list[str] = []
    seen: set[str] = set()
    # 匹配 "账号/账户/银行账号/基本账户: XXX" 形态
    pat = re.compile(r"(?:账\s*号|账\s*户|银行账[号户]|基本账户|结算账户)\s*[:：]?\s*([0-9]{11,22})")
    for m in pat.finditer(text):
        v = m.group(1)
        if v not in seen:
            seen.add(v)
            hits.append(v)
    return hits


# ────────────────────────────────────────────────────────────
# 聚合: file_contents → {字段 → 优选值}
# ────────────────────────────────────────────────────────────

def _pick_most_frequent(values: list[str]) -> str | None:
    """高频项优先(多个源都出现的更可信),并列时取首个."""
    if not values:
        return None
    c = Counter(values)
    top, top_n = c.most_common(1)[0]
    return top


def extract_hard_fields(file_contents: dict[str, str]) -> dict[str, Any]:
    """从所有材料文本中抽取硬字段.

    Returns:
      {
        "uscc": "91...",
        "controller_id": "350...",  # 身份证首选(频次最高)
        "id_numbers_all": [...],     # 全部身份证(debug/多股东)
        "phone": "138...",           # 手机首选
        "phones_all": [...],
        "post_code": "350001",
        "bank_account": "409...",
        "dates_all": [...],          # 全文日期命中(audit/registration 判断用)
        "_source_counts": {字段: 命中次数}
      }
    """
    all_usc: list[str] = []
    all_ids: list[str] = []
    all_phones: list[str] = []
    all_postcodes: list[str] = []
    all_banks: list[str] = []
    all_dates: list[tuple[str, str, str]] = []

    for _fname, content in file_contents.items():
        if not content:
            continue
        all_usc.extend(extract_usc(content))
        all_ids.extend(extract_id_numbers(content))
        all_phones.extend(extract_phones(content))
        all_postcodes.extend(extract_postcodes(content))
        all_banks.extend(extract_bank_accounts(content))
        for m in _DATE_RE.finditer(content):
            all_dates.append((m.group(1) + m.group(0)[2:], "", ""))

    out: dict[str, Any] = {}

    uscc = _pick_most_frequent(all_usc)
    if uscc:
        out["uscc"] = uscc

    # 身份证首选频次最高;保留全部
    if all_ids:
        out["controller_id"] = _pick_most_frequent(all_ids)
        out["id_numbers_all"] = list(dict.fromkeys(all_ids))
        # 从身份证提取生日: 第 7-14 位
        did = out["controller_id"]
        if did:
            y, mo, d = did[6:10], did[10:12], did[12:14]
            try:
                out["controller_birth"] = f"{int(y)}年{int(mo)}月{int(d)}日"
            except ValueError:
                pass

    # 手机
    if all_phones:
        out["phone"] = _pick_most_frequent(all_phones)
        out["phones_all"] = list(dict.fromkeys(all_phones))

    # 邮编
    if all_postcodes:
        out["post_code"] = _pick_most_frequent(all_postcodes)

    # 银行账号
    if all_banks:
        out["bank_account"] = _pick_most_frequent(all_banks)
        out["bank_accounts_all"] = list(dict.fromkeys(all_banks))

    out["_source_counts"] = {
        "uscc": len(all_usc),
        "id": len(all_ids),
        "phone": len(all_phones),
        "postcode": len(all_postcodes),
        "bank": len(all_banks),
        "date": len(all_dates),
    }

    return out


if __name__ == "__main__":
    # Smoke: 粘 OCR 原文到 text 即可快速自检
    import sys
    from pathlib import Path
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
        if target.is_file():
            fc = {target.name: target.read_text(encoding="utf-8", errors="ignore")}
        else:
            fc = {}
            for fp in target.rglob("*.txt"):
                fc[fp.name] = fp.read_text(encoding="utf-8", errors="ignore")
        print(extract_hard_fields(fc))
