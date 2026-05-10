# Cross-Agent Feedback Protocol v1.0 · 2026-05-09

> **状态**: ✅ Phase A.5 frozen (Phase A.5 hotfix · per RFC cross-agent-feedback-channel · MODIFIED → IMPLEMENTED 2026-05-09)
> **Tier**: 1 (red zone · per `docs/arch/instruction-source-of-truth.md` v1.0)
> **Owner**: common worker · 修改走 RFC
> **依赖**:
> - `shared/feedback_channel/` (events.py + watcher.py + subscribers.py · 单测覆盖)
> - `shared/decision_ledger/` BE7 (Q-055 · 复用 sqlite store)
> - `entity-resolution-contract` v1.1 (FeedbackEvent.subject_entity_key)
> **触发**: RFC cross-agent-feedback-channel · v1.0 modified verdict (`f09766d`) · 应 M1 + M2 + M3 修正

---

## 1. 目的

闭合红线 #9 "审批/贷后反馈丢链路" · 6 agent 现状全前向流 · 加反向流让下游决策回流到上游策略 agent.

4 闭环路径 (event types):
- **approval_override**: credit 审贷员 override → riskctrl (误杀/漏杀分析 → champion_challenger)
- **loan_outcome**: alert 贷后逾期 / 正常结清 → riskctrl (验证策略实际坏账率)
- **policy_violation**: compliance 政策命中已上线策略 → credit / riskctrl (strategy refresh)
- **score_drift**: riskctrl PSI 漂移 → credit (评分模型漂移预警)

## 2. Feedback Event Schema

每条 feedback event 是 LedgerEntry 的 subclass · 复用 BE7 sqlite 存储:

```python
from shared.feedback_channel import FeedbackEvent, FeedbackType

evt = FeedbackEvent(
    feedback_type=FeedbackType.APPROVAL_OVERRIDE,
    producer_agent="credit",
    consumer_agents=["riskctrl"],
    original_decision_id="dec_abc123",   # 上游决策 id (回溯链)
    subject_entity_key="uscc_91440300708461136T",  # per entity-resolution v1.1
    payload={
        "ruleset_id": "rs_v3_2026q1",
        "original_action": "reject",
        "override_action": "approve",
        "reason": "审贷员认可经营改善证据 (近 6 月营收 +25%)",
    },
)
```

**字段**:
| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| feedback_type | enum | ✅ | 4 type 之一 |
| producer_agent | str | ✅ | 6 agent 白名单 |
| consumer_agents | list[str] | ✅ | ≥ 1 个 · 决定 retention (M1) |
| original_decision_id | str | ✅ | 上游决策 id · 回溯链 |
| subject_entity_key | str | ✅ | 复用 entity-resolution v1.1 |
| payload | dict | ✅ | 业务数据 (per feedback_type) |
| ts | str | auto | ISO timestamp |
| event_id | str | auto | uuid |

## 3. M1 · Retention 继承规则 (verdict 修正)

**硬规** (回应 RFC modified verdict M1):
```
feedback event 的 retention_class = MAX(
    DEFAULT_RETENTION_BY_AGENT[consumer_agent] for consumer_agent in consumer_agents
)
```

理由:
- producer 可能是 short retention agent (e.g. alert 90d)
- 若沿 producer retention · 90d 后 raw entry 淘汰 · consumer (riskctrl) 若 watcher 拉慢就丢链路
- 沿 consumer retention 确保 consumer 业务周期内可回溯 (riskctrl standard 5y · credit 5y)

**实现** (per shared/feedback_channel/events.py):
```python
def resolve_feedback_retention(consumer_agents: list[str]) -> str:
    """feedback event retention 继承 consumer agent · 取 MAX (long > standard > short)."""
    from shared.decision_ledger.schema import (
        DEFAULT_RETENTION_BY_AGENT, RETENTION_LONG, RETENTION_STANDARD, RETENTION_SHORT,
    )
    rank = {RETENTION_SHORT: 0, RETENTION_STANDARD: 1, RETENTION_LONG: 2}
    classes = [
        DEFAULT_RETENTION_BY_AGENT.get(a, RETENTION_STANDARD)
        for a in consumer_agents
    ]
    return max(classes, key=lambda c: rank[c])
```

**例**:
- consumer = ["riskctrl"] (standard 5y) → retention = standard
- consumer = ["riskctrl", "credit"] (both standard) → retention = standard
- consumer = ["credit", "report"] (standard + long) → retention = long
- consumer = ["alert"] (short) → retention = short (allowed · 但实际 4 event type 没 alert 作 consumer)

## 4. M2 · Watcher 故障恢复 (verdict 修正)

**last_read_id 持久化** (回应 RFC modified verdict M2):

```python
# 各 consumer agent 启动时 · watcher 自动 catch-up
watcher = FeedbackWatcher(consumer_agent="riskctrl")
watcher.start()  # 内部从 sqlite metadata 读 last_read_id · 续读
```

**实现** (per shared/feedback_channel/watcher.py):
- `data/ledger/feedback_watcher_state.sqlite` (单独 sqlite · 不和 ledger 主表混)
- table `watcher_state(consumer_agent TEXT PRIMARY KEY, last_read_id TEXT, last_poll_ts TEXT)`
- 启动时 `SELECT last_read_id FROM watcher_state WHERE consumer_agent = ?`
- 每次拉 query: `SELECT * FROM ledger WHERE id > ? AND is_feedback = 1 ORDER BY id ASC LIMIT 100`
- 边消费边 update last_read_id (per batch)
- watcher 挂 → 重启续读 · 不丢 event

**poll 间隔**:
- 默认 300s (5 min) · 适合 production
- env override `LIUYE_FEEDBACK_POLL_SEC` · demo 可设 30s
- 失败 backoff: 5s → 15s → 60s → 300s (max)

## 5. M3 · Phase A.5 命名 (verdict 修正)

**命名硬规** (回应 RFC modified verdict M3):

| 阶段 | 域 | worker | 工时 | 状态 |
|---|---|---|---|---|
| Phase A | shared/ + docs/contracts/ + .mesh-launcher/ | common (我) | 0.5d | ✅ DONE (af2ce90) |
| **Phase A.5** | shared/feedback_channel/ + docs/contracts/cross-agent-feedback-protocol.md + ledger schema 扩 | common | 1-2d | 🟢 进行中 (本 commit) |
| Phase B | agent_*/ + web/src/app/archive/*/ | 5 agent worker | 1-1.5d | 🟡 standby (Phase A close-out 后启) |
| Phase B.5 (协同) | credit/alert/riskctrl 加 feedback emit/subscribe | 3 worker 各自 | Phase B 内嵌 | 🟡 等 Phase A.5 close-out |
| Phase C | 整合 | 主 CLI | 0.5d | 🟡 |

**Phase A.5 与 Phase A 不串行阻塞**: 主 CLI 可:
- (a) cherry-pick Phase A close-out 入 main · 启 5 worker Phase B
- (b) 同时 cherry-pick Phase A.5 入 main (本 worker 完事后)
- (c) Phase B.5 协同在 Phase B 内嵌完成 (3 worker emit/subscribe wire-up · 不阻不 emit 的其他 2 worker)

**触发条件**:
- 本 RFC v1.0 落地后 · common worker 转 standby (除非 PM 显式新 GO)
- 任何 agent worker 在 Phase B/B.5 反馈 contract 缺口 · 走新 RFC

## 6. 4 Event 类型详解

### 6.1 approval_override (credit → riskctrl)

**触发**: 审贷员把策略推 reject 改 approve · 或反之 (人工 override)
**payload schema**:
```json
{
  "ruleset_id": "rs_v3_2026q1",
  "original_action": "reject" | "approve" | "manual_review",
  "override_action": "reject" | "approve" | "manual_review",
  "reason": "<审贷员填写的覆盖理由>",
  "reviewer_id": "<credit_officer open_id>"
}
```
**用途**: riskctrl 跑 误杀 (override approve) / 漏杀 (override reject) 分析 → feed champion_challenger

### 6.2 loan_outcome (alert → riskctrl)

**触发**: 贷后 60+ DPD 触发 / 正常结清
**payload schema**:
```json
{
  "loan_id": "L000123",
  "days_past_due": 90,
  "outcome": "default" | "current" | "paid_off" | "restructured",
  "outcome_date": "2026-04-30"
}
```
**用途**: riskctrl 验证策略实际坏账率 vs 回测预测

### 6.3 policy_violation (compliance → credit + riskctrl)

**触发**: compliance 扫到新政策 · 命中已上线策略
**payload schema**:
```json
{
  "policy_id": "pol_20260301_xyz",
  "policy_url": "https://www.cbirc.gov.cn/...",
  "policy_hash": "<sha256:16hex · per stop-the-line #8>",
  "ruleset_ids_affected": ["rs_v3_2026q1"],
  "violation_severity": "high" | "medium" | "low"
}
```
**用途**: credit / riskctrl 触发 strategy refresh

### 6.4 score_drift (riskctrl → credit)

**触发**: PSI > 0.25 评分漂移
**payload schema**:
```json
{
  "rubric_id": "scoring_v3_corporate",
  "drift_value": 0.32,
  "psi_threshold": 0.25,
  "segments_affected": ["sme_manufacturing", "sme_retail"]
}
```
**用途**: credit 收警 · 决定要不要禁用该评分模型

## 7. 失败隔离

| 场景 | 行为 |
|---|---|
| Watcher poll 失败 (sqlite lock / IO error) | log warn · 不 raise · backoff 5→15→60→300s |
| Subscriber callback raise | log error · 不影响其他 subscriber · last_read_id 仍前进 (per-event 错误不阻塞 stream) |
| Producer emit 失败 (sqlite write fail) | producer 自己捕获 + log · 不影响主决策 flow (per CLAUDE.md §3.7.5 silent-fail) |
| 跨 agent contract 不匹配 (e.g. payload schema 改) | 反序列化失败时 log + skip · 不 raise · 加 metric 上报 |

## 8. 红线 (任一触发即 stop-the-line)

1. **producer emit feedback 不上 ledger** · feedback event 必走 `record_feedback()` · 不允许 in-memory queue
2. **consumer skip catch-up** · watcher 启动时必 read last_read_id · 不允许从 0 重读 (会重复消费) 或从 max(id) 跳 (会丢)
3. **retention 取 producer agent** · 必 MAX(consumer_agents retention) per M1 · 防 raw entry 淘汰丢链路
4. **payload schema break** · 4 event type schema 改字段名 / 删字段必走 RFC · 加字段 backward-compat ok
5. **跨 jurisdiction event** · feedback event 必同 jurisdiction (consumer ≠ producer 不允许跨境)

## 9. 实施清单

| # | 文件 | 责任 | 状态 |
|---|---|---|---|
| 1 | `docs/contracts/cross-agent-feedback-protocol.md` v1.0 | common (本 commit) | ✅ |
| 2 | `shared/feedback_channel/{__init__,events,watcher,subscribers}.py` | common | ✅ (本 commit) |
| 3 | `shared/decision_ledger/schema.py` 加 feedback_meta + is_feedback | common | ✅ (本 commit) |
| 4 | `tests/shared/test_feedback_channel.py` | common | ✅ (本 commit) |
| 5 | credit `agent_credit/api.py` 审批 commit 后 emit approval_override | credit worker (Phase B.5) | 🟡 待 Phase B |
| 6 | alert `agent_alert/api.py` ack 后 emit loan_outcome | alert worker (Phase B.5) | 🟡 待 Phase B |
| 7 | riskctrl `agent_riskctrl/champion_challenger.py` watcher.start() + subscribe | riskctrl worker (Phase B.5) | 🟡 待 Phase B |

## 10. ABI 稳定性承诺

Phase A.5 frozen 后不破:
- FeedbackType enum (4 值锁定 · 加 enum 走 RFC · 删/改算 break)
- FeedbackEvent schema (8 字段)
- FeedbackWatcher class signature
- subscribe decorator
- LedgerEntry feedback_meta + is_feedback (新加 optional · 不破老消费)

## 11. 关联

- decisions-log Q-NNN: 待主 CLI 写 (Phase A.5 close-out 时)
- AGENT_IDENTITY 模板: alert/credit/riskctrl 的 6 step 加 step 7 "feedback channel 接入" (Phase B.5 共)
- CLAUDE.md §3.7 active runtime rules: 待主 CLI 加 §3.7.7 cross-agent-feedback retention 规则 (回写)
