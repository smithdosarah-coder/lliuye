# 实体归一 Contract v1.1 · 2026-05-09

> **状态**: ✅ Phase A frozen (Phase A common worker · 2026-05-09)
> **Tier**: 1 (red zone · per `docs/arch/instruction-source-of-truth.md` v1.0)
> **Owner**: common worker (mesh/common) · 修改走 RFC (`shared-change-protocol.md`)
> **依赖**: shared/entity_resolver/ (50 单测 · GB 32100-2015 真校验码)
> **下游**: 6 agent realtime_stream/api.py (Phase B 各自接入)

---

## 1. 目的

6 agent 跨源企业实体合并去重 · 防 "海康在 gsxt/Tavily/微信名字不一样导致系统当 3 家" 问题.

PM 2026-05-08 痛点真根因复盘:
- channel agent 16% 匹配率根因之一 = 同一公司多源错配 (codex R1 第 1 关键洞察)
- candidate dict 缺 unique id → 前端 find 命中错误 (commit `c074d43` 真根因 fix)

## 2. 公开 API (frozen · 不许 ABI 改 · 改走 RFC)

```python
from shared.entity_resolver import (
    EntityKey,                # frozen dataclass · hashable
    resolve_entity,           # name + uscc → EntityKey
    make_unique_id,           # name + uscc + idx → str (per candidate-identity-contract)
    normalize_company_name,   # 规则化清洗
    validate_uscc,            # 顶层 dispatcher (默认仅格式 · strict=True 启 GB32100)
    validate_uscc_format,     # 仅长度 + 字符集
    validate_uscc_checksum,   # GB 32100-2015 真校验码
)
```

### 2.1 主入口

```python
key = resolve_entity(
    name="杭州海康威视股份有限公司",
    uscc="91440300708461136T",
    strict=False,  # True 时 USCC 必过 GB32100 校验码 · 推荐生产
)
# EntityKey(uscc="91440300708461136T", name_normalized="海康威视", confidence=1.0)
```

### 2.2 同实体判断 (多源去重)

```python
e1.matches(e2)        # bool · 主键比对
e1 == e2              # 与 matches() 等价 · __eq__ 走 matches
hash(e1) == hash(e2)  # 同主键 hash 相同
{e1, e2}              # 同主键 set 折叠成 1 个
```

### 2.3 候选 unique id (per candidate-identity-contract.md §2)

```python
make_unique_id(name="海康威视", uscc="91440300708461136T", idx=0)
# "uscc_91440300708461136T"

make_unique_id(name="某不知名小厂", idx=3)
# "name_<md5前12位>"

make_unique_id(idx=5)
# "cand_005"
```

## 3. 主键优先级 (硬规)

按优先级降序:

| # | 条件 | EntityKey 字段 | confidence | id 派生 |
|---|---|---|---|---|
| 1 | USCC 通过 (format · strict 时含 checksum) | uscc + name_normalized | 1.0 | `uscc_<USCC>` |
| 2 | USCC 缺/非法 + name 有 | name_normalized only | 0.5 | `name_<md5前12位>` |
| 3 | 都缺 | empty | 0.0 | `cand_<idx:03d>` |

## 4. GB 32100-2015 校验码算法 (validate_uscc_checksum 真实现)

### 4.1 字符集 (31 chars)

```
"0123456789ABCDEFGHJKLMNPQRTUWXY"
```

排除易混 5 字符: **I O S V Z**.

### 4.2 加权因子 W_i (前 17 位)

```python
W = (1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28)
```

### 4.3 校验码计算

```
S = Σ(W_i · value(C_i))   for i in 0..16
expected = (31 - (S mod 31)) mod 31
check_char = CHARSET[expected]
```

第 18 位字符必须 == check_char · 否则 invalid.

### 4.4 真 USCC 测试样本 (NECIPS 公开)

- `91440300708461136T` (腾讯科技深圳) · 算法验证 PASS
- 算法生成 valid 例: `91330000725930080D` / `91110000100003962Y`

## 5. 6 Agent 接入点 (Phase B 各 agent 自接)

| Agent | 接入位置 | 用途 | 写域归属 |
|---|---|---|---|
| channel | `agent_channel/api.py` candidate emit | 候选 candidate 去重 + unique id | channel worker |
| report | `agent_report/api.py` 报告对象企业归一 | 防同企业多次写报告 | report worker |
| credit | `agent_credit/decision_engine.py` 决策对象 | 跨 agent handoff 主键 | credit worker |
| alert | `agent_alert/api.py` 在贷客户池归一 | 预警绑定客户 | alert worker |
| compliance | `agent_compliance/api.py` 客户业务归一 | 政策影响范围 | compliance worker |
| riskctrl | `agent_riskctrl/backtesting.py` 历史样本 | 回测样本一致性 | riskctrl worker |

### 5.1 接入 contract (各 agent 必满足)

每个 agent 在 emit candidate / customer / record 时:
1. 必调 `make_unique_id(...)` 生成 id 字段
2. id 字段必非空 (兜底 `cand_<idx>`)
3. id 字段在同 list 内 unique (调用方负责)
4. 需要跨源去重时调 `resolve_entity(...)` 得 EntityKey · 用 set 自动折叠

## 6. LLM Fuzzy Match (Phase B 各 agent 自接 · resolver 不内置)

触发条件:
- 多个 candidate 的 name_normalized 高度相似但不相等 (e.g. "海康威视" vs "海康威视数字技术")
- 都没 USCC anchored

接入方式 (各 agent 自实现 · 走 PIPL fallback chain):

```python
from shared.llm_caller import LLMCaller

caller = LLMCaller(agent_id="<agent>", endpoint="entity_fuzzy")
result = caller.chat_json([
    {"role": "system", "content": "判定两个企业名是否同一实体"},
    {"role": "user", "content": f"企业A: {name1}\n企业B: {name2}\n输出: {{\"score\": 0-1, \"reason\": ...}}"},
])
fuzzy_score = result["score"]

# 阈值规则:
# ≥ 0.85 → 视作同实体 · 合并 · confidence 取 fuzzy_score
# 0.6-0.85 → 标 "待人审" · 不自动合并
# < 0.6 → 拒绝合并 · 保留两条
```

PIPL 合规底线 (per CLAUDE.md §3.6):
- LLMCaller 默认 fallback chain `("deepseek", "dashscope")` 全境内
- audit log 含 `region` 字段 · 跨境调用可追溯

## 7. 失败隔离

| 失败场景 | 行为 | 后果 |
|---|---|---|
| validate_uscc_checksum 字符不在 charset | 返 False (KeyError 兜) | 退化到 name fallback |
| LLM fuzzy 调用失败 | 各 agent 自捕获 · 不 raise | 退化到 name_normalized 比对 |
| name 完全空 + uscc 完全空 | EntityKey() empty | confidence=0.0 · 调用方判 valid |

## 8. 红线 (任一触发即 stop-the-line)

per CLAUDE.md §3.6 stop-the-line 10 条 · 实体归一相关:

1. **跨源同字段值不一致** (e.g. gsxt 注册资本 1000 万 · Tavily 抓 800 万) → 用 4 Tier 权重仲裁 (per `shared/data_tiers.py` · Tier 高赢) · **不 silent 选其一**
2. **entity_key 一旦生成不可改** (immutable) · 防 cross-agent handoff 主键漂移 · EntityKey 是 frozen dataclass 强制
3. **USCC anchored 状态不一致不算 match** (一边有 USCC 一边没 · 即使 name 一样 · 不假合并) · 谨慎规则 · 测试 `test_uscc_anchored_vs_name_only_not_match` 守卫

## 9. EntityKey hash/eq 契约

- `__hash__` 基于主键 (USCC anchored 走 USCC · name-only 走 name_normalized)
- `__eq__` 与 `__hash__` 对齐 (Python 契约 · hash 相等必 eq 相等)
- `confidence` 字段不入 hash/eq · 同主键多源 confidence 应一致 (1.0 / 0.5)
- frozen=True · 实例不可变 · 防跨 agent handoff 漂移

## 10. 单测覆盖 (50 cases · 6 类)

| 类 | 测试数 | 覆盖 |
|---|---|---|
| TestUsccFormat | 11 | 长度 / 字符集 / 5 个排除字符 (I O S V Z) |
| TestUsccChecksum | 6 | GB 32100 真算法 + 边界 |
| TestValidateUsccDispatcher | 2 | 顶层 strict 切换 |
| TestNormalizeCompanyName | 6 | 后缀 / 前缀 / 标点 / 幂等 |
| TestResolveEntity | 6 | 主入口 4 路径 + strict 模式 |
| TestEntityKeyMatching | 5 | matches / 谨慎规则 / 空键 |
| TestEntityKeyHash | 3 | hash + set 去重 |
| TestMakeUniqueId | 9 | 3 优先级 + strict + 唯一性 |
| TestCrossSourceDedup | 2 | 端到端多源场景 |

跑通: `py -m pytest tests/shared/test_entity_resolver.py -v` → 50 passed.

## 11. ABI 稳定性承诺

Phase A 冻结后 · 以下 API 不许 break (Phase B worker 依赖):

- `EntityKey` 类签名 (字段 / __hash__ / __eq__ / matches / is_uscc_anchored)
- `resolve_entity(name, uscc, *, strict=False)` 函数签名
- `make_unique_id(name, uscc, idx, *, strict=False)` 函数签名
- `validate_uscc(uscc, *, strict=False)` 函数签名
- 输出 id 格式 (uscc_X / name_X / cand_X · Phase B 前端依赖)

加新参数走 keyword-only 默认值 · 不破老调用. 删/改字段必须 RFC + 6 worker confirm.

## 12. 待 Phase B 各 agent 接入 (本 contract 不直接管)

- [ ] channel candidate emit 时调 make_unique_id (现已用 c074d43 · Phase B 校验)
- [ ] report 报告对象企业 USCC 抽取 + 归一
- [ ] credit 决策对象绑定 EntityKey
- [ ] alert 在贷客户池 EntityKey
- [ ] compliance 客户业务 EntityKey
- [ ] riskctrl 历史样本 EntityKey

per `docs/handoff/phase-r3-worker-runbook.md` Phase B §B.2 step 6.
