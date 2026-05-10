# RFC: 跨 agent feedback channel · 审批/贷后反馈反向链路

**发起人**: riskctrl worker (worktree `D:/claude code/credit_report_agent_work_mesh/riskctrl` · branch `feat/allin-riskctrl`)
**日期**: 2026-05-09
**变更类型**: 红区 (新建 `shared/feedback_channel/` + `docs/contracts/cross-agent-feedback-protocol.md` v1.0) · 黄区 (3 agent 加 endpoint · credit/alert/riskctrl)
**关联 commit**: 待 common worker + 3 worker 协同实施
**审批状态**: 🟡 PROPOSED · 等 PM + common worker ratify (跨域决策 · 涉 credit + alert + riskctrl 三方)
**触发来源**: `docs/working/riskctrl-read-through-concerns.md` §2 异议 #4 (read-through verify after common signal `af2ce90`)

---

## 0. 触发原因

riskctrl ALL IN Phase B read-through verify · `Grep -r "cross.?agent.?feedback|approval_override|loan_outcome.*feedback|overdue.*feedback" docs/contracts/` 0 命中 · `git diff main..feat/allin-common --` 也无任何 feedback channel 设计 · 但**红线 #9 "审批/贷后反馈丢链路"** 是 riskctrl ALL IN 最大 gap · 不闭合即触红线.

**现状链路** (单向 · 缺反向):
```
riskctrl DSL → ledger ✅ (record_dsl_deploy retention=standard 5y)
riskctrl backtest → ledger ✅ (record_backtest_decision retention=short 90d)

❌ credit 审批员 override (人工把 reject → approve) → riskctrl ???
❌ alert 贷后逾期 (60+ DPD 触发预警) → riskctrl ???
   ↑ 现 false_positive_explainer.py 是手动入口 · 没自动 trigger
```

**根因**: 6 agent 现状全是 "前向流" (RM → channel → report → credit → alert → riskctrl/compliance) · 但 **闭环学习要反向流** · 没设计任何 webhook / event bus / pull 机制让下游决策回流到上游策略 agent.

## 1. 现状 → 提议

### 设计方向选择 (3 候选 · 推荐 B)

**方案 A · 同步 webhook**:
- credit 审批 commit 后立刻 POST `/api/riskctrl/feedback/approval_override`
- alert 预警生成后立刻 POST `/api/riskctrl/feedback/loan_outcome`
- ❌ 紧耦合 · credit 必须等 riskctrl 回 200 才完成 · riskctrl 挂 = credit 挂

**方案 B · 共享 ledger watcher** (推荐):
- 复用 `shared/decision_ledger/` (BE7 已有 sqlite 存)
- 加 `shared/feedback_channel/watcher.py` · 后台 cron 拉 ledger event
- riskctrl 订阅 (agent_id="credit", intent_type="approval_override") 和 (agent_id="alert", intent_type="loan_outcome")
- ✅ 解耦 · ✅ 复用现有 ledger · ✅ 失败隔离 (拉失败不影响 credit/alert)
- ⚠️ 异步延迟 (cron 间隔 · 默认 5 min)

**方案 C · 各 worker 自建**:
- riskctrl worker 自己写 `champion_challenger.py` 定时 sql query ledger
- ❌ 各 agent 重复造轮子 · 接 5 个 ledger source 各自实现 · 反 DRY

### 方案 B 落地 spec (建议 common worker 实施)

#### `docs/contracts/cross-agent-feedback-protocol.md` v1.0 (新建)

```markdown
## 1. Feedback Event Schema

每条反馈 event 是 ledger entry 的 subclass · 必含:
- `feedback_type`: enum (approval_override / loan_outcome / policy_violation / score_drift)
- `producer_agent`: agent_id (credit/alert/compliance)
- `consumer_agents`: list[agent_id] (e.g. ["riskctrl", "credit"])
- `original_decision_id`: 上游决策 id (回溯链)
- `payload`: 业务数据 (per feedback_type schema)

## 2. Event 类型

### 2.1 approval_override (credit → riskctrl)
- 触发: 审批员把策略推 reject 改 approve · 或反之
- payload: { ruleset_id, customer_entity_key, original_action, override_action, reason }
- 用途: riskctrl 跑 误杀/漏杀分析 · feed champion_challenger

### 2.2 loan_outcome (alert → riskctrl)
- 触发: 贷后逾期 60+ DPD · 或正常结清
- payload: { customer_entity_key, loan_id, days_past_due, outcome }
- 用途: riskctrl 验证策略实际坏账率 vs 回测预测

### 2.3 policy_violation (compliance → credit/riskctrl)
- 触发: compliance 扫到新政策 · 命中已上线策略
- payload: { policy_id, ruleset_id_affected, violation_severity }
- 用途: riskctrl 触发 strategy refresh

### 2.4 score_drift (riskctrl → credit) [反向也支持]
- 触发: riskctrl 发现 PSI > 0.25 评分漂移
- payload: { rubric_id, drift_value, segments_affected }

## 3. Watcher 实现 (shared/feedback_channel/)

```python
from shared.feedback_channel import FeedbackWatcher, FeedbackEvent

watcher = FeedbackWatcher(consumer_agent="riskctrl")

# 各 worker 启动时注册回调
@watcher.subscribe("approval_override")
def on_approval_override(evt: FeedbackEvent):
    # riskctrl 自己实现 · 调 false_positive_explainer 跑分析
    ...

@watcher.subscribe("loan_outcome")
def on_loan_outcome(evt: FeedbackEvent):
    # riskctrl 验证策略
    ...

watcher.start()  # 后台 asyncio task · 默认 5 min 拉一次 ledger
```

## 4. Ledger 扩展 (shared/decision_ledger/)

LedgerEntry 加 optional 字段:
- `feedback_meta: dict | None` (含 feedback_type / consumer_agents / original_decision_id)
- `is_feedback: bool` (默认 False · True 时 watcher 才拉)
```

#### `shared/feedback_channel/watcher.py` (新建 · ~150 LOC)

```python
class FeedbackWatcher:
    def __init__(self, consumer_agent: str, poll_interval: int = 300): ...
    def subscribe(self, feedback_type: str): ...  # decorator
    def start(self): ...  # asyncio.create_task
    def stop(self): ...
    async def _poll_loop(self): ...  # 拉 ledger 新 entry
```

#### 3 agent 加 endpoint (黄区 · 各 worker 实施)

- credit: 审批 commit 后调 `record_decision(... feedback_meta={"feedback_type": "approval_override", "consumer_agents": ["riskctrl"], ...})`
- alert: 预警 ack 后调同上 (`feedback_type="loan_outcome"`)
- riskctrl: 启动时 `watcher.start()` + 注册 2 个 subscribe handler

## 2. 影响面

| 文件 | 被谁用 | 本次变更 | 兼容性 |
|---|---|---|---|
| `docs/contracts/cross-agent-feedback-protocol.md` | 6 agent + audit | 新建 v1.0 | ✅ 全新 |
| `shared/feedback_channel/__init__.py` + `watcher.py` | 6 agent (consumer) | 新建 · 纯加法 | ✅ |
| `shared/decision_ledger/schema.py` | 6 agent (producer) | 加 2 optional 字段 (feedback_meta / is_feedback) | ✅ 现有 entry 默认 False · 不影响读 |
| `agent_credit/api.py` (decisions endpoint) | credit worker 自改 | 审批 commit 后 emit feedback event | ⚠️ 需 credit worker 协同 |
| `agent_alert/api.py` (alert ack endpoint) | alert worker 自改 | ack 后 emit feedback event | ⚠️ 需 alert worker 协同 |
| `agent_riskctrl/champion_challenger.py` (新加 watcher 启动) | riskctrl worker 自改 | 启动时注册 watcher | ⚠️ riskctrl 自改 |

## 3. 风险

- **R1**: cron 5 min 拉间隔可能导致策略调整延迟 · **mitigation**: production 可调 (env `LIUYE_FEEDBACK_POLL_SEC`) · demo 演示用 30s 间隔
- **R2**: ledger sqlite IO 压力 (6 agent 同时拉) · **mitigation**: watcher 内 dedup 已读 entry id · 每次 query 加 `WHERE id > last_read_id`
- **R3**: feedback event 风暴 (短时间内大量 approval_override) · **mitigation**: watcher 内 batch handler · 每次拉最多 100 条
- **R4**: 跨 agent worker 协同 (credit + alert + riskctrl 三方都要改) · 协调成本高 · **mitigation**: Phase B 各 worker 独立 ship 自己那部分 · Phase C 整合时验跨 agent 链路
- **R5**: 与 §3.7.5 retention 冲突 (alert short 90d · feedback 短期淘汰会丢链路) · **mitigation**: feedback meta 记 `original_decision_id` · short retention 只丢 raw entry · 链路本身在 riskctrl 接收端持久化

## 4. 实施顺序 (建议)

**Phase A 延伸** (common worker 加 1-2 day):
1. common worker 写 `docs/contracts/cross-agent-feedback-protocol.md` v1.0
2. common worker 写 `shared/feedback_channel/watcher.py` + tests
3. common worker 改 `shared/decision_ledger/schema.py` 加 feedback_meta 字段

**Phase B 协同** (3 worker 并行):
4. credit worker 加 approval_override emit
5. alert worker 加 loan_outcome emit
6. riskctrl worker (我) 加 watcher.start() + 2 subscribe handler

**Phase C 整合** (主 CLI):
7. 跨 agent 链路 e2e test (Playwright + 真 sqlite)

## 5. Authorized-By

跨域决策 · 必 PM 显式拍板 · trailer `Authorized-By: PM` 加于 Phase A 延伸的 commit (步 1-3).

## 6. 关联

- AGENT_IDENTITY.md: "遇 shared/ contract 缺口 ... 必提 Q/RFC · 不本地绕开"
- KT §3.6 红线 #9 "审批/贷后反馈丢链路"
- CLAUDE.md §3.7.5 决策账本 retention defaults (本 RFC 复用 · 加 feedback_meta 不破)
- `docs/working/riskctrl-read-through-concerns.md` §2 异议 #4 (worker 自留底)
- 现 `agent_riskctrl/false_positive_explainer.py` 290 行 (手动入口 · RFC 通过后改 watcher 触发)
- 现 `agent_riskctrl/champion_challenger.py` 362 行 (RFC 通过后接 feedback 数据)
