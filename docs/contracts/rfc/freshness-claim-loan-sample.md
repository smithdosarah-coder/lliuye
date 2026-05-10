# RFC: shared/evidence_freshness 加 LOAN_SAMPLE ClaimType + 365d SLA

**发起人**: riskctrl worker (worktree `D:/claude code/credit_report_agent_work_mesh/riskctrl` · branch `feat/allin-riskctrl`)
**日期**: 2026-05-09
**变更类型**: 红区 (`shared/evidence_freshness.py` ClaimType enum + FRESHNESS_SLA_DAYS map + mock 数据 schema)
**关联 commit**: 待 common worker 实施 (本 worker 不动 shared/)
**审批状态**: 🟡 PROPOSED · 等 PM + common worker ratify
**触发来源**: `docs/working/riskctrl-read-through-concerns.md` §2 异议 #3 (read-through verify after common signal `af2ce90`)

---

## 0. 触发原因

riskctrl ALL IN Phase B read-through verify · `git diff main..feat/allin-common -- shared/evidence_freshness.py` 空 · common worker A-1 ~ A-9 未碰 freshness 模块 · 但 riskctrl 业务必触此 gap:

- riskctrl 跑 `backtest` endpoint (`agent_riskctrl/api.py:310`) 消费 CSV 历史贷款样本 (`data/mock/agent2-samples/loans.csv` 7500 行 · MAX_ROWS=50000)
- 每条样本是 evidence 类型: 历史授信结果 + 贷后表现 (label_default / days_past_due 列)
- 红线 #6 "无源健康检查" + CLAUDE.md §3.5.1 第 6 原则 "证据时效硬约束 · staleness_policy_passed 必过"

**根因**: CLAUDE.md §3.5.1 现 11 ClaimType 全是 "外部抓取类" (新闻 180d / 财报 120d / 处罚 365d / 政策 365d / 案例 730d 等) · 没有 "历史样本类" claim · riskctrl 无法 freshness_check.

## 1. 现状 → 提议

### `shared/evidence_freshness.py` (红区 · common worker 改)

**现 ClaimType enum** (假设 · 待 common 验):
```python
class ClaimType(str, Enum):
    NEWS = "news"
    FINANCIAL = "financial"
    PENALTY = "penalty"
    POLICY = "policy"
    CASE = "case"
    # ... (其他 6 类 · 全外部抓取)
```

**新增 ClaimType + SLA**:
```python
class ClaimType(str, Enum):
    # ... (existing 11)
    LOAN_SAMPLE = "loan_sample"          # 单条历史贷款样本 (riskctrl backtest 用)
    BACKTEST_FIXTURE = "backtest_fixture"  # 回测固定基线 fixture (champion vs challenger 用)

FRESHNESS_SLA_DAYS = {
    # ... (existing 11)
    ClaimType.LOAN_SAMPLE: 365,      # 信贷周期 12 月 · 银保监年度审计周期
    ClaimType.BACKTEST_FIXTURE: 730,  # 固定基线允许更长 (2y · 信贷周期完整覆盖)
}
```

### mock 数据 schema (绿区 · 各 worker 适配 mock)

`data/mock/agent2-samples/loans.csv` 现列假设无 `evidence_date`. 加列:
```
loan_id,customer_id,loan_amount_wan,debt_ratio,company_age_years,industry,
days_past_due,label_default,sample_date  ← 新加 (ISO YYYY-MM-DD · 该笔授信发生月)
```

riskctrl backtest 内消费:
```python
# agent_riskctrl/backtesting.py:run_backtest 内
from shared.evidence_freshness import check_freshness, ClaimType

if "sample_date" in df.columns:
    stale_mask = df["sample_date"].apply(
        lambda d: not check_freshness(d, ClaimType.LOAN_SAMPLE)
    )
    if stale_mask.mean() > 0.3:  # 超 30% 样本过期 → warn
        logger.warning("backtest sample staleness > 30%% · KS 不可信")
```

### `shared/evidence_drawer/drawer.py` 受益 (无需改)

EvidenceDrawer 已 `claim_type: str # per shared.evidence_freshness.ClaimType` (drawer.py:21) · 加 LOAN_SAMPLE 后 riskctrl 落 evidence 时可填 `claim_type="loan_sample"` · drawer 自动正确算 freshness_summary.

## 2. 影响面

| 文件 | 被谁用 | 本次变更 | 兼容性 |
|---|---|---|---|
| `shared/evidence_freshness.py` | 6 agent (channel/report/credit/alert/compliance/riskctrl) + audit script | 加 2 enum + 2 SLA entry · 纯加法 | ✅ 向后兼容 (现 11 ClaimType 不动) |
| `data/mock/agent2-samples/loans.csv` | riskctrl backtest + champion_challenger | 加 1 列 sample_date | ✅ 现消费方 list comprehension 不会破 (新列被忽略) |
| `scripts/audit/freshness_check.py` | CI freshness audit | 自动 pick up 新 ClaimType (enum-driven) | ✅ |
| `agent_riskctrl/backtesting.py` | riskctrl 自己 | run_backtest 加 stale-rate warn (本 worker 自改) | ✅ |

## 3. 风险

- **R1**: mock 数据加列后 · `tests/agent_riskctrl/test_backtest_real.py` 等单测可能因 fixture 不更新而 skip stale check · **mitigation**: 本 worker 同 PR 更新 fixture
- **R2**: 365d SLA 是否合适 (信贷周期 12 月 vs 经济周期更长?) · **mitigation**: 该值 production 调 · 仅作 default · 业务方可 override
- **R3**: 历史 7500 行样本可能全 < 365d 也可能全 > 365d (mock 制造时 random 分布) · 需 common 给 mock 时 sample_date 真实分布锚 (建议: 80% 近 12 月 + 20% 12-36 月 · 反 5 原则 #2 难度分层)

## 4. 实施顺序 (建议)

1. common worker 改 `shared/evidence_freshness.py` 加 2 ClaimType + 2 SLA
2. common worker / data-foundation worker 改 `data/mock/agent2-samples/loans.csv` 加 sample_date 列 (按 R3 mitigation 分布)
3. riskctrl worker (我) 改 `agent_riskctrl/backtesting.py` 加 stale check + warning
4. riskctrl worker 加 `tests/agent_riskctrl/test_freshness_loan_sample.py` 单测

步 1-2 是 RFC 范围 (common 域) · 步 3-4 是 worker 自改 (riskctrl 域)

## 5. Authorized-By

待 PM 拍板 · trailer `Authorized-By: PM` 加于 step 1-2 commit.

## 6. 关联

- AGENT_IDENTITY.md: "遇 shared/ contract 缺口 ... 必提 Q/RFC · 不本地绕开"
- KT §3.6 红线 #6 "无源健康检查" + CLAUDE.md §3.5.1 第 6 原则
- `docs/working/riskctrl-read-through-concerns.md` §2 异议 #3 (worker 自留底)
