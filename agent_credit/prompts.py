# -*- coding: utf-8 -*-
"""Agent3 v2.0 提示词 — 3 组 user prompt template

PB#2 (2026-05-06 · Q-053) 后:
- system prompt 走 shared.prompts.agent_helpers.build_credit_ssot_prompt
- 本 module 仅保留 user prompt template (业务 schema / 字段定义)
- few-shot 注入逻辑 build_system_prompt(base) 保留 (Phase B BE10)
- 旧 hardcode SYSTEM_* 已删除 · RETAIL_REDLINE_* 死代码顺手清

3 组 user template:
- CORPORATE_DECISION_USER : 对公决策说明输入
- CORPORATE_REDLINE_USER  : 对公红线解释输入 (JSON 列表)
- RETAIL_DECISION_USER    : 对私决策说明输入

约束：不得编造数字；所有数字从输入结构里取；语言风格对标银行审贷会材料。
"""

# ---------------------------------------------------------------------------
# 对公决策说明
# ---------------------------------------------------------------------------

CORPORATE_DECISION_USER = """
## 企业基本情况
{company_summary}

## 申请事项
- 申请额度: {requested_amount} 万元
- 申请期限: {requested_term} 个月
- 用途: {purpose}

## 评分结果
- 财务风险: {financial_score}/100
- 行业风险: {industry_score}/100
- 经营风险: {operational_score}/100
- 担保风险: {guarantee_score}/100
- 综合: {composite_score}/100 (等级 {risk_grade})

## 触发的红线 ({red_line_count} 条)
{red_line_detail}

## 额度测算
- 营收法: {revenue_method} 万
- 净资产法: {netasset_method} 万
- 现金流法: {cashflow_method} 万
- 担保法: {collateral_method} 万
- 综合建议: {suggested_amount_range} 万

## 相似历史案例 (Top 3)
{similar_cases_summary}

## 确定性决策
- 决策: {decision}
- 批复额度: {approved_amount} 万
- 期限: {approved_term} 个月
- 利率: {interest_rate} ({rate_benchmark})
- 附加条件: {conditions}

---
请按以下结构输出决策意见 (控制在 500 字以内):

### 一、客户基本情况
(2-3 句话概述企业和申请事项)

### 二、评分结论
(综合评分、等级、关键风险点 3-5 句话)

### 三、决策说明
(为什么给出这个决策，要联系红线命中和案例对比)

### 四、额度与利率依据
(额度和利率的测算逻辑)

### 五、附加条件
(附加的授信条件，列表式)
"""

# ---------------------------------------------------------------------------
# 对公红线解释（JSON 列表）
# ---------------------------------------------------------------------------

CORPORATE_REDLINE_USER = """
## 企业画像
{company_summary}

## 触发的红线
{hit_rules_detail}

请严格按以下 JSON 结构输出（不要额外文字）:
[
  {{"rule_id": "...", "explanation": "...", "severity": "高/中/低", "waiver_advice": "..."}}
]
"""

# ---------------------------------------------------------------------------
# 对私决策说明
# ---------------------------------------------------------------------------

RETAIL_DECISION_USER = """
## 客户画像摘要
{customer_summary}

## 评分卡结果
- 综合评分: {fico_score} ({grade} 档)
- 偿债能力: {repayment_capacity}
- 还款意愿: {repayment_willingness}
- 稳定性: {stability}
- 抵押估值: {collateral}

## 红线命中 ({count} 条)
{red_line_detail}

## 确定性决策
- 决策: {decision}
- 额度: {approved_amount} 万
- 利率: {interest_rate}

---
请在 200 字以内给出决策说明，结构: 一句话结论 + 主要理由 (2-3 点) + 附加说明 (若有红线或边界)
"""

# ---------------------------------------------------------------------------
# Phase B BE10 · few-shot 注入接入点 (数据飞轮第 4 环)
#
# scripts/inject_fewshot_to_prompts.py 会在文件末尾注入 marker 包围的
# FEW_SHOT_EXAMPLES = [...] 常量 (后赋值覆盖此处默认 [])。
# build_system_prompt(base) 把 examples 拼到 base prompt 末尾, 让 LLM
# 看到"审贷员历史改动样例" → 收敛输出风格。
#
# PoC 范围: 只 agent_credit · 其他 5 agent 下一迭代接入 (per runbook §PoC scope)。
#
# Production 安全 (per Codex V2 review):
#   - LIUYE_FEWSHOT_POC_ENABLED env 默认 "0" · 关 → build 直返 base · 无副作用
#   - PII redaction (手机/身份证/银行卡/邮箱) 在喂 LLM 前 mask · per Evidence-First 自审层
# ---------------------------------------------------------------------------

import os
import re

FEW_SHOT_EXAMPLES: list[dict] = []  # default; injected block at file end shadows

POC_FLAG_ENV = "LIUYE_FEWSHOT_POC_ENABLED"

# 中国常见 PII pattern · 进 LLM 前 mask · 保 LLM 看不到具体值但保留字段语义
_PII_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b1[3-9]\d{9}\b"), "<MOBILE>"),                      # 手机号
    (re.compile(r"\b\d{17}[\dXx]\b"), "<ID-CARD>"),                    # 身份证 18
    (re.compile(r"\b\d{15}\b"), "<ID-CARD-15>"),                       # 旧身份证 15
    (re.compile(r"\b\d{16,19}\b"), "<BANK-CARD>"),                     # 银行卡 16-19
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "<EMAIL>"),         # 邮箱
)


def _redact_pii(text: str) -> str:
    """对单条字符串扫 PII pattern 并 mask · 多条 pattern 顺序应用."""
    if not isinstance(text, str):
        text = str(text)
    for pat, repl in _PII_PATTERNS:
        text = pat.sub(repl, text)
    return text


def _redact_value(value):
    """递归对 dict / list / scalar 走 _redact_pii."""
    if isinstance(value, dict):
        return {k: _redact_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_value(v) for v in value]
    if isinstance(value, str):
        return _redact_pii(value)
    return value


def _format_fewshot_block(examples: list[dict]) -> str:
    """把 candidates examples 渲染成 prompt 末尾追加的 markdown 块.

    跳过缺关键字段的条目 + 喂 LLM 前 PII redact · 保护 prompt 不被脏数据 / 隐私污染。
    """
    rendered = []
    for ex in examples:
        reason = _redact_pii((ex.get("reason") or "").strip())
        sample_input = _redact_value(ex.get("sample_input") or {})
        preferred = _redact_value(ex.get("preferred_output") or {})
        diff = _redact_pii((ex.get("diff_summary") or "").strip())
        if not reason or not preferred:
            continue
        rendered.append(
            f"- 反馈原因: {reason}\n"
            f"  原输出关键字段: {sample_input}\n"
            f"  审贷员偏好输出: {preferred}\n"
            f"  改动摘要: {diff}",
        )
    if not rendered:
        return ""
    header = (
        "\n\n## 历史反馈学到的偏好示例（few-shot · 仅供风格收敛 · 不复制具体数字）\n"
    )
    return header + "\n".join(rendered)


def build_system_prompt(base: str) -> str:
    """把 base system prompt + few-shot 块拼成最终 system prompt.

    Production 默认安全 (per Codex V2):
      LIUYE_FEWSHOT_POC_ENABLED != "1" → 直返 base (PoC opt-in · 无副作用)
      = "1" + 无 FEW_SHOT_EXAMPLES → 返 base (向下兼容)
      = "1" + 有 examples → 返 base + few-shot block (PII redacted)
    """
    if os.environ.get(POC_FLAG_ENV, "0") != "1":
        return base
    block = _format_fewshot_block(FEW_SHOT_EXAMPLES)
    if not block:
        return base
    return base + block
