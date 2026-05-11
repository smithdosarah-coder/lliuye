# -*- coding: utf-8 -*-
"""Agent1 v2.0 提示词集合。

PB#2 (2026-05-06 · Q-053) 后:
- system prompt 走 shared.prompts.agent_helpers.build_channel_ssot_prompt
- 本 module 仅保留 user prompt template (含业务 schema / 字段定义)
- 旧 hardcode SYSTEM_* 已删除 (不向下兼容 · per CLAUDE.md "不留死代码")

三套 user prompt template：
1. PROFILE_EXTRACT_PROMPT — 从客户统计 + 政策 + 行业指引抽取 IdealProfile
2. BATCH_PITCH_PROMPT    — Top N 线索批量生成切入话术
3. PITCH_GEN_PROMPT      — 单条话术 fallback
"""
from __future__ import annotations


PROFILE_EXTRACT_PROMPT = """请综合以下三类信息，定义一张可用于外网 look-alike 检索的"理想客户画像"。

【已有客户统计】
{customer_stats}

【政策规则摘要】
{policy_rules}

【行业指引】
{industry_guide}

【要求】
1. 画像要聚焦（不要给出"所有制造业企业"这种宽泛定义）
2. 有硬性指标（行业、规模、地域、必备资质）
3. 有加分项（让候选更优质的特征）
4. 有排除项（政策或指引明确不支持的）
5. reasoning 里解释：依据哪些客户特征和政策条款得出画像
6. 如果客户名录样本太少（< 10 家），仍要给出画像，但在 reasoning 中说明"样本量较小"

严格按下述 JSON schema 输出，只输出 JSON，用 ```json``` 包裹：
{{
  "profile_id": "auto",
  "name": "简短画像名称，15字以内",
  "target_industries": ["行业1", "行业2"],
  "target_sub_industries": ["细分1"],
  "target_regions": ["省/市1", "省/市2"],
  "scale_range": ["小型", "微型"],
  "revenue_range": [最小营收_万元, 最大营收_万元],
  "must_have_tags": ["必备资质/标签"],
  "nice_to_have_tags": ["加分标签"],
  "exclude_tags": ["排除标签"],
  "policy_context": "当前政策语境的一段描述（80-150 字），话术会用",
  "reasoning": "画像依据说明（100-200 字）"
}}
"""


PITCH_GEN_PROMPT = """请为以下潜在客户生成一段电话首访切入话术（80-120 字）。

【目标客户】
企业名：{company_name}
行业/细分：{industry} / {sub_industry}
规模/营收：{scale} / {revenue}
主营业务：{main_business}
核心标签：{tags}

【推荐产品 Top3】
{products}

【当前政策语境】
{policy_ctx}

【要求】
1. 直接从客户可能关心的点切入（政策红利 / 行业趋势 / 主推产品）
2. 介绍 1 个主打产品 + 核心数字（额度、利率优惠）
3. 结尾留钩子引导下一步沟通
4. 口语化，不要书面体
5. 不要虚构数字，只用【推荐产品】里给出的数字
6. 不要"您好，我是某某银行"这种客套开场，直接从业务切入
7. 不要出现任何解释/括号/引号，只输出话术正文

只输出话术文本。

{fewshot_block}
"""


# ---------------------------------------------------------------------------
# Few-shot 经验沉淀（数据飞轮第 4 环）
# 从 data/feedback/*.jsonl 的审贷员修改提取，用 scripts/extract_feedback_fewshots.py
# 生成。手改只会被下次脚本覆盖——别手改。
# ---------------------------------------------------------------------------
# BEGIN AUTO-GENERATED FEW-SHOT EXAMPLES (do not edit manually)
PITCH_FEWSHOT_EXAMPLES: list[dict] = [
    {"bad": "您好，我们银行有贷款产品，利率很低，可以了解一下。", "good": "陈总您好，注意到贵司刚中标杭州地铁 7 号线设备包，应收账款回款通常 90-180 天。我们行『保理 / 应收质押融资』可垫资 500-2000 万、期限 3-6 月、费率年化 3-5%，今年同业头部已批的同类制造业客户平均 4 个工作日放款。想请教一下贵司这批应收的账期节奏？", "reason": "原话术无中标信号锚 / 无应收账款行业话术 / 无具体金额 / 无费率 · 改后含信号 + 行业痛点 + 产品具体数字 + 同业锚 + 钩子"},
    {"bad": "贵司可申请我们的设备贷款，金额最高 3000 万。", "good": "李总您好，注意到贵司近期通过专精特新『小巨人』认定，研发设备投入按贵司年报口径 1200 万。我们行『设备贷 / 固定资产贷款』专精特新通道最高 3000 万、4 年期、LPR 减 30bp，央行 5000 亿科创再贷款额度配套，平均放款周期 8 个工作日。想约个时间聊聊贵司今年扩产的设备规划吗？", "reason": "原话术无认定锚点 / 无研发数据 / 无利率优惠 / 无政策配套 · 改后含具体认定 + 数据锚 + 利率 + 政策配套 + 钩子"},
    {"bad": "建议贵司了解我们的流动资金贷款，可以支持日常经营。", "good": "王总您好，看到贵司排污许可证 4 月刚通过 IV 级评定，今年 Q2 旺季备货大概率拉高存货占款。我们行『流动资金贷款』化工行业专配 800-2500 万、1 年期、LPR+30bp 起，环保合规客户优先排队。贵司今年 Q2 原料采购峰值大概在哪个月？", "reason": "原话术无许可证信号 / 无行业季节性 / 无定价信号 / 无差异化政策 · 改后含监管信号 + 行业经营节奏 + 产品差异化 + 钩子"},
]
# END AUTO-GENERATED FEW-SHOT EXAMPLES


def render_fewshot_block(examples: list[dict] | None = None, max_n: int = 3) -> str:
    """把 PITCH_FEWSHOT_EXAMPLES 渲染成 prompt 可插入的字符串。无示例返回空串。"""
    items = (examples if examples is not None else PITCH_FEWSHOT_EXAMPLES)[:max_n]
    if not items:
        return ""
    lines = ["【参考修正示例（审贷员历史修改）】"]
    for i, ex in enumerate(items, start=1):
        lines.append(f"示例{i}")
        lines.append(f"  原始：{ex.get('bad', '')}")
        lines.append(f"  更优：{ex.get('good', '')}")
        if ex.get("reason"):
            lines.append(f"  原因：{ex['reason']}")
    return "\n".join(lines)


# 批量话术（Top10 一次生成，省 LLM 调用数）
BATCH_PITCH_PROMPT = """请为下列每条线索生成一段电话首访切入话术（80-120 字/条）。

【当前政策语境】
{policy_ctx}

【线索列表】
{leads_block}

【要求】
1. 每条话术直接切入，口语化，不要客套开场
2. 使用该条线索【推荐产品】中给出的真实数字，不要虚构
3. 80-120 字
4. 结尾留钩子

请严格按下述 JSON 格式输出，用 ```json``` 包裹，不要任何解释：
{{
  "pitches": [
    {{"lead_id": "LEAD_xxx", "pitch": "话术正文"}}
  ]
}}
"""
