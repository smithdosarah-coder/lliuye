# `data/mock/` · 拟真数据底座（Entity-first）

**维护**：data-foundation worker（worktree `demo-data-foundation`）
**上游决策**：`docs/handoff/decisions-log.md` · Q-023 / A-023（2026-04-23）
**Onboarding**：`docs/onboarding/data-foundation-phase-1.md`
**Runbook**：`docs/runbook/data-foundation.md`
**首建时间**：2026-04-24

---

## 为什么要重建（底座哲学）

项目早期在 `demo_data/mock_pool/companies.jsonl`、`industry_cards/*.json`、`customer/` 下铺过一批 mock 数据。PM 在 Q-023 里判定这些数据**太简单 + 太结果导向**：

- 所有企业都是"国家高新技术企业 + 专精特新 + 无红线"套路化标签
- 没有难度分层；Agent1/3/4/5/6 跑出来几乎全绿，银行客户一看就是"跑通 demo"而非真实业务
- 没有埋坑；不用思考的数据训练不出能打的 Agent

重建底座走 **Entity-first** 路线：

1. 先 mock **企业（实体）**，再由实体派生各 Agent 消费的信号——不是为每个 Agent 单独造数据
2. 数据脱敏**再造**，不凭空编——每家企业必须有真实"标杆参考"（A 股年报 / 央行征信模板 / 银保监处罚公告）
3. **难度分层** 硬约束：简单 20% / 中等 50% / 困难 20% / 极端 10%
4. **盲测法**：worker 建材料、PM 埋坑；worker 不看答卷、不"顺手"预判

> 这四条不可违。违任一条即反工。

---

## 两层结构：宽基 100 + 深柱 15

```
data/mock/
├── schemas/
│   ├── wide-base.yaml      ← 宽基 schema
│   └── deep-pillar.yaml    ← 深柱 11 类信号 schema
├── wide-base/              ← 宽基 100 家企业（entity-level · 浅字段）
│   ├── companies.yaml
│   └── source-notes.md
└── deep-pillar/            ← 深柱 15 家候选（signal-level · 深数据）
    ├── shortlist.md
    ├── pit-template.md
    └── pits/<company_id>.md × 15
```

### 宽基 100（wide-base）

- **用途**：Agent1 获客检索池 / Agent4 批量扫描客户池 / Agent5 合规矩阵扫描目标池
- **字段**：浅字段 8-10 个（工商 + 行业 + 规模 + 2-3 条浅舆情），见 `schemas/wide-base.yaml`
- **规模**：100 家，8 大行业分布，4 档难度严格 20/50/20/10
- **来源锚点**：每家企业在 `source-notes.md` 里标注脱敏前身（A 股代码 / 征信模板章节 / 处罚文号）

### 深柱 15（deep-pillar）

- **用途**：Agent3 授信四维评分 / Agent6 报告 11 信号消费 / Agent2 风控策略样本源
- **当前阶段（Batch 1）**：仅产出 15 家 **候选名单** 和 **埋坑清单空模板**（交 PM 填）
- **下阶段（Batch 2）**：PM 回传埋坑清单后，才填 MVP 3 家完整材料包（11 类信号）

深柱 15 从宽基 100 里挑，覆盖 4 档难度：`easy:3 / medium:7-8 / hard:3 / extreme:1-2`，其中至少 1 家"虚假授信"极端样本，参考银保监处罚公告。

---

## 消费方指南

### Agent1 获客（wide-base）

```python
# 伪代码 · 供参考，不是现成 API
from yaml import safe_load
pool = safe_load(open("data/mock/wide-base/companies.yaml"))
candidates = [c for c in pool["companies"]
              if c["industry_l1"] == "制造业" and c["size"] in {"small", "medium"}]
```

### Agent4 预警（wide-base + deep-pillar）

- 宽基扫描：遍历 `wide-base/companies.yaml` 命中外部信号
- 深度材料（Batch 2）：`deep-pillar/<company_id>/` 下的流水 / 征信 / 风险标记

### Agent5 合规（wide-base）

对宽基 100 家批量跑政策条文命中；难度分层直接对应"政策敏感度"梯度。

### Agent6 报告（deep-pillar）

- 消费深柱 15 家（Batch 2 后）的 11 类信号材料包
- 短期内（Batch 1 阶段）继续吃既有 `samples/*.docx` 模板，不切换

### Agent3 授信（deep-pillar · Batch 2 后）

- 吃 Agent6 ReportJSON + deep-pillar 流水/征信/担保做四维评分
- Batch 1 阶段可对宽基 100 家做"浅评分"占位

### Agent2 风控（deep-pillar · Batch 2 后）

- 吃 `strategy_sample_meta` 字段（命中/未命中标签）做 DSL 回测
- Batch 1 阶段用现有 `agent_riskctrl/samples/` 打底

---

## 字段类型约定（schema 通用）

- `difficulty`: 枚举 `{"easy", "medium", "hard", "extreme"}`
- `industry_l1`: 枚举 `{"制造业", "零售商贸", "服务业", "地产关联", "农业", "科技", "跨境外贸", "集团对私"}`
- `region`: 字符串，格式 `省-市-区`（不具体到街道）
- `size`: 枚举 `{"micro", "small", "medium", "large", "group"}`（按工信部 2011 划型标准近似）
- `listed_bool`: 布尔，是否 A 股/港股/美股上市
- `registered_capital`: 字符串，格式 `<数值>万元`（量级保留，具体数值脱敏后浮动 ±30%）
- `establish_year`: 整数 4 位（脱敏前身的年份 ±2 年）
- `benchmark_ref`: 字符串，脱敏标杆锚点（如 `A股600XXX 2023年报 主业/应收账款章节`）
- `unfilled_marker`: 凡 schema 规定必填但当期无法获取的字段，值统一写 `未能自动填写`（对齐 CLAUDE.md §12）

---

## 常见反模式（禁区）

| 反模式 | 为什么禁 | 正解 |
|---|---|---|
| 所有企业都贴"国家高新技术企业 / 专精特新" | 失真，PM 早就戳破了 | 按资质真实分布：~15% 高新 / ~5% 专精特新 / 80% 无特殊资质 |
| 难度简单档超过 20% | 盲测法被绕过 | 严格计数；简单档 ≤20 家（含 20） |
| 企业名凭空编 | 来源不可追溯 | 走脱敏再造：标杆前身 → 改字 → 源注解在 `source-notes.md` |
| 埋坑 worker 先填 | 失去盲测意义 | `pits/<cid>.md` 只是空表，交 PM 填；回传后才进 Batch 2 |
| 深柱 15 家一次性做完整材料包 | 污染 Batch 2 真实性 | Batch 1 只产名单 + 空埋坑；材料包是 Batch 2 的事 |
| LLM 现场生成财务数据 | 违反 CLAUDE.md §3.1 确定性计算边界 | 人工按标杆量级脱敏；如需派生比率走 `financial_analyzer.py` 确定性计算 |

---

## 版本与迭代

- **v1.0**（2026-04-24 · 本次 Batch 1）：schema + 宽基 100 + 深柱 15 名单 + 埋坑模板
- **v1.1**（Batch 2 · 待 PM 回埋坑清单）：深柱 MVP 3 家完整材料包
- **v2.0**（待定）：宽基扩至 300-500，深柱扩至 30-50；接企查查等真实源做混合底座

重大调整需在 `docs/handoff/decisions-log.md` 走 Q/A 走流程，不直接改底座。

---

## 红线复读

1. ❌ 不 commit 真实客户数据
2. ❌ 不动 `agent_*/` / `web/**` / `evaluation/`
3. ❌ 不"为了让跑分好看"而降低埋坑难度
4. ❌ 不凭空编企业，一定要有标杆锚点
5. ✅ 有疑问走 Q/A，不现场改规则
