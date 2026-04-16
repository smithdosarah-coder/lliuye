# -*- coding: utf-8 -*-
"""Agent1 v2.0 提示词集合。

三套 Prompt：
1. PROFILE_EXTRACT_PROMPT — 从客户统计 + 政策 + 行业指引抽取 IdealProfile
2. BATCH_PITCH_PROMPT    — Top N 线索批量生成切入话术
3. PITCH_GEN_PROMPT      — 单条话术 fallback
"""
from __future__ import annotations


PROFILE_EXTRACT_SYSTEM = "你是一位银行获客画像分析专家，擅长把客户名录的共性和政策导向合成'理想客户画像'。"


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


PITCH_GEN_SYSTEM = "你是资深银行客户经理，擅长首次电话切入话术。"


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
"""


# 批量话术（Top10 一次生成，省 LLM 调用数）
BATCH_PITCH_SYSTEM = "你是资深银行客户经理，擅长针对不同企业生成差异化切入话术。"

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
