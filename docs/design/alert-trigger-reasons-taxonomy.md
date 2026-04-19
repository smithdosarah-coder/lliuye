# Agent4 预警 · trigger_reasons 枚举规约

**所属 Phase**：Phase 1 Task C
**代码位点**：`agent_alert/cross_matcher.py::_infer_trigger_reasons`
**模型位点**：`agent_alert/alert_engine.py::AlertReport.trigger_reasons` + `HitItem.extras["trigger_reasons"]`
**日期**：2026-04-19

---

## 1. 枚举语义定义（三值封闭集）

| 值 | 语义 | 对客户经理的语言表达 |
|---|---|---|
| `external_signal` | 仅外部路径命中（裁判文书 / 舆情 / 工商 / 风险标签 / 行业信号） | 「客户触发了 **外部信号**，需人工核对是否与当前账户相关」 |
| `internal_rule` | 仅内部路径命中（本行制度条款 / 贷后检查 / 内控阈值 / 授信集中度等） | 「客户触发了 **内部规则**，制度层面该客户已越线」 |
| `cross_hit` | 外部 + 内部双路同时命中 | 「**交叉命中** — 外部有坏信号、内部制度也已响应，建议优先处置」 |

**枚举封闭性**：上述 3 值为穷举，不允许新增第 4 类而不走 RFC。若某客户无任何 hit，字段为空列表 `[]`（green 灯的正常状态，不是"第 4 类"）。

---

## 2. 推断规则（结构推断，非关键词映射）

伪代码（权威实现见 `agent_alert/cross_matcher.py::_infer_trigger_reasons`）：

```python
def infer(hits: list[RuleHit]) -> list[str]:
    routes = {h.route for h in hits}     # {"external"} | {"internal"} | {"external", "internal"} | set()
    if not routes:
        return []
    has_ext = "external" in routes
    has_int = "internal" in routes
    if has_ext and has_int:
        return ["cross_hit"]
    if has_ext:
        return ["external_signal"]
    return ["internal_rule"]
```

**上游结构依赖**：`RuleHit.route: str`（`agent_alert/cross_matcher.py::RuleHit.__slots__`）硬编 2 值 `"external"` / `"internal"`，分别由 `_match_external()` / `_match_internal()` 写入。2 值是完备集——扩第 3 路径必须同步扩本枚举（走 RFC）。

**为什么 cross_hit 不返回 `["cross_hit", "external_signal", "internal_rule"]`**：
- 前端分桶展示按"最有信息量的 reason"取色；cross_hit 已蕴含其他两者的出现。
- 减少下游消费侧的枚举互斥判断成本（按集合长度 1 即可 switch）。
- 如后续需要细分，扩 `trigger_reasons_detail: list[str]` 而不改现有字段语义。

---

## 3. 为什么不用关键词黑名单

对齐 **CLAUDE.md §12**：「不写关键词 / 正则黑名单兜底幻觉」。

对齐 **CLAUDE.md §3.1**（确定性 vs 概率性计算）：分类判断属确定性计算，必须用已存在的结构化信号（`route`）做推断，不能用 LLM 现场分类、也不能用字符串匹配兜底。

具体不做的反例：

- ❌ `if "涉诉" in customer.narrative: return "external_signal"`
- ❌ `if customer.hit_rule.startswith("LAW"): return "cross_hit"`
- ❌ 维护一张 `RULE_ID_TO_REASON = {"LAW-001": "external_signal", ...}` 映射表

反例问题：

1. **永远列不全**：新规则 / 新信号源一出现，黑名单即 silent miss
2. **语义漂移**：关键词 / 规则 ID 不代表 route 归属（同一 rule_id 可能出现在不同 route 的 hits 里）
3. **测试悖论**：要给黑名单写测试，就得枚举所有关键词——等于把黑名单"白纸化"，没解决根本问题

结构推断从 `RuleHit.route` 取值，**上游已经决定**这条 hit 属于哪一路；本枚举只做"route 集合 → 3 值"的代数映射，Closed、Testable、Refactorable。

---

## 4. 前端展示约定（Stage 3 hook）

前端消费路径（不在本 Phase 实装，移交 `docs/progress/agent4-phase-1-frontend-handoff.md`）：

| 枚举值 | 建议色系 hook（`docs/design/platform-shell-v1.md` 4 主题变量） | UI 形态 |
|---|---|---|
| `external_signal` | `--g3`（中间档暖色）| 标签 · 外部 |
| `internal_rule` | `--g5`（偏冷档）| 标签 · 内部 |
| `cross_hit` | `--g7`（最暖 / 最红）+ 粗描边 | 标签 · 交叉命中 · 优先 |

**绝对红线**：前端代码不得自己"推断" trigger_reasons——runtime yaml 里已回填、`evaluation/manual/4_YYYYMMDD.yaml` 是唯一事实来源。前端读字段即可，不允许基于 grade / evidence 文本反推。

**数据源路径**：
- `evaluation/manual/4_20260419.yaml` · `customers[].trigger_reasons: list[str]`
- API（未实装，后续 Phase 挂 `agent_alert` endpoint 时）· 同字段名、同枚举

---

## 5. 变更约束

- 本枚举（`external_signal` / `internal_rule` / `cross_hit`）**不可在不发 RFC 的前提下增删**
- `_infer_trigger_reasons` 单测（`agent_alert/tests/test_trigger_reasons.py`）锁 3 case 必须保持绿
- 任何尝试改为关键词 / 规则 ID 黑名单的 PR 一律 block（review 会 grep 否定证据：`grep -E "RULE_ID_TO_REASON|keyword.*reason" agent_alert/` 必须 0 hit）

---

## 6. 相关文档

- `CLAUDE.md` §12（不黑名单兜底）/ §3.1（确定性 vs 概率性）
- `docs/design/platform-shell-v1.md`（色系变量规范）
- `docs/progress/agent4-phase-1-frontend-handoff.md`（前端实装移交）
- `evaluation/runner/adapters/agent4_alert.py`（adapter pass-through 消费点）
