# 实体归一 Contract v1.0 · 2026-05-08

> **状态**: outline · 待 Phase A common worker 完善具体 spec
> **Owner**: common worker (mesh/common)
> **依赖**: shared/entity_resolver/ (本 session PoC · 21 单测 PASS)

---

## 1. 目的

6 agent 跨源企业实体合并去重 · 防 "海康在 gsxt/Tavily/微信名字不一样导致系统当 3 家" 问题.

## 2. 核心 API (已存在 · 推广用)

```python
from shared.entity_resolver import (
    EntityKey,           # frozen dataclass · hashable
    resolve_entity,      # name + uscc → EntityKey
    normalize_company_name,  # 规则化清洗
    validate_uscc,       # 18 位 USCC 格式校验
)

# 主入口
key = resolve_entity(name="杭州海康威视股份有限公司", uscc="91330185711315925G")
# EntityKey(uscc="91330185711315925G", name_normalized="海康威视", confidence=1.0)

# 同实体判断 (多源去重)
e1.matches(e2)  # bool
```

## 3. 主键优先级 (硬规)

1. USCC 18 位合法 → `uscc_<USCC>` (confidence=1.0)
2. 仅 name 有 → `name_<md5前 12 位>` (confidence=0.5)
3. 都没 → 兜底 `cand_<idx:03d>` (confidence=0.0)

## 4. 6 Agent 必接入点 (Phase A common 推广)

| Agent | 接入位置 | 用途 |
|---|---|---|
| channel | candidate dict 加 entity_key (本 session 已用 md5 派生 · 推广统一 EntityKey) | 候选去重 |
| report | 报告对象企业归一 (从材料抽 USCC) | 防同企业多次写报告 |
| credit | 决策对象归一 (匹配 channel 候选 ↔ report 对象 ↔ credit 决策) | 跨 agent handoff 主键 |
| alert | 在贷客户池归一 (跟 credit 决策对象 1:1) | 预警绑定客户 |
| compliance | 客户业务归一 (政策命中按 client_entity_key) | 政策影响范围 |
| riskctrl | 历史样本企业归一 | 回测样本一致性 |

## 5. LLM Fuzzy Match (Phase B 加 · 当前 PoC 不调用)

- 触发: 多个 candidate 的 name_normalized 高度相似但不相等 (e.g. "海康威视" vs "海康")
- 走 `shared.llm_caller.LLMCaller(agent_id="entity_resolver", endpoint="fuzzy")`
- PIPL fallback chain (deepseek + dashscope · 全境内)
- 输出: float ∈ [0,1] · ≥ 0.85 视为同实体 · 0.6-0.85 标"待人审" · < 0.6 拒

## 6. 失败隔离

- USCC 校验码 (GB 32100-2015) 当前未实现 · 仅长度 + 字符集. 待 Phase A 加
- LLM fuzzy 失败时降级"仅 name_normalized" 比对 · 不 raise

## 7. 红线

- 跨源同字段值不一致时 (e.g. gsxt 注册资本 1000 万 · Tavily 抓 800 万) 用 4 Tier 权重仲裁 (Tier 高赢) · 不 silent 选其一
- entity_key 一旦生成不可改 (immutable) · 防 cross-agent handoff 主键漂移

## 8. 待 Phase A common worker 补完

- [ ] USCC 校验码算法 (GB 32100-2015)
- [ ] LLM fuzzy match 真实现 (调 shared.llm_caller)
- [ ] 6 agent 接入点的 wrapper 函数
- [ ] 单测扩到 50+ case (现 21 case)
