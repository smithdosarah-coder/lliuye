# B.3.4 mesh 起步说明 (2026-05-11 凌晨 05:30)

> **背景**: PM 在 5 月 11 日凌晨 03:45 admin 真号 verify production · 给出 6 件痛 + 总结 "**所有后端前端都混乱 · 没一个 agent 有独立业务逻辑 · 连最早期 demo 都不如**"。
> **拍板**: 不再 patch · 从源头解决 · 5+ 轮 codex 辩论后 · PM 决定**用 mesh 5 worker 并行 · 分 2 组**。

## PM 凌晨 6 件痛 (verbatim)

1. **获客**: 点击空白页也会跳转出查询 + 让我解释后端逻辑 / 信源 / 搜索逻辑
2. **风控**: 点演示后大面积空白 · 数据非常少
3. **风控**: 演示没成功 · 大面积空白 · 实际没有按钮
4. **预警**: 队列出来了 · 但不能点客户详情 · 严重排版问题
5. **合规**: 完全乱的排版 · 没任何功能展示
6. **报告**: 后端调用失败

## codex R5 + R6 verdict (主 CLI 同意)

**真原因不是"缺详情抽屉"** (主 CLI 错判 · 抽屉都在):
- channel: `CandidateDetailDrawer` (ChannelWorkspace.tsx:702)
- alert: `AlertDrillDrawer` + selectedClientId (AlertWorkspace.tsx:377)
- credit: `CaseDetailDrawer` + export_docx (CreditWorkspace.tsx:742, 2108)
- compliance: 可选 violation detail + export (ComplianceWorkspace.tsx:679)
- riskctrl: rule selection + per-rule stats + export (RiskctrlWorkspace.tsx:552)

**真原因**: **6 个助手没有统一的"会话语言"** · 每个助手自己手搓 live/demo/input/session/action state · ALL IN reframe 删 mock fallback 换 `EMPTY_SESSION` · 后端/前端 mismatch → 看起来"产品空白" → PM 看到的就是这个

**PM 2026-05-11 05:25 追加**: 每个助手必须**独立可用** · 不强协同 (e.g. credit 不强等 report)

## 5 个 worker 分两组 · 并行

### 组 A · 主线修 BUG (3 worker · 5-6 天)

| Worker | 任务 | worktree | branch | 工期 |
|---|---|---|---|---|
| **fix-contract** | 定 6 助手共用会话语言 + 适配层 + 持久化 | `credit_report_agent_work_mesh/fix-contract` | `feat/b34-fix-contract` | 3 天 (**前 2 天必须 ship 契约 spec 给组 B**) |
| **fix-bugs** | 修 4 件具体 bug (channel 点空白 / report 503 / alert 排版 / compliance 详情) | `credit_report_agent_work_mesh/fix-bugs` | `feat/b34-fix-bugs` | 2 天 |
| **fix-indep** | 6 助手独立可用 + 主按钮简化 + 删多余 toggle | `credit_report_agent_work_mesh/fix-indep` | `feat/b34-fix-indep` | 1-2 天 |

### 组 B · 3D 方案 (2 worker · 8-12 天)

| Worker | 任务 | worktree | branch | 工期 |
|---|---|---|---|---|
| **3d-frame** | three.js / WebGL 3D 场景框架 + 圆环 6 助手布局 | `credit_report_agent_work_mesh/3d-frame` | `feat/b34-3d-frame` | 8-10 天 (前 2 天独立做视觉 · 不等契约) |
| **3d-data** | 接现有后端 API + 渲染 WorkSession 数据 | `credit_report_agent_work_mesh/3d-data` | `feat/b34-3d-data` | 8-10 天 (前 2 天等 fix-contract 给契约 · 然后 6-8 天接) |

## 通用规则 (5 worker 都遵守)

1. **每个 worker 一开窗** · 先复述 PM 真意 (避免跑偏) · 等主 CLI verify GO 才动手
2. **commit 粒度 = TaskCreate 粒度** · 每步独立 commit · 不攒大 commit
3. **fire signal commit** 走 commit trailer · 不在 chat 说"已完成":
   ```
   Signal: WORKER-<NAME>-READY-FOR-MERGE
   Worker: <name>
   Refs: B.3.4-2026-05-11
   ```
4. **撞 BLOCKER 立刻 fire Signal:BLOCKED** · 不死磕
5. **改 web/ 必带 trailer**:
   ```
   PRESERVES: F-XXX (保留的 feature)
   NEW-DOM: data-testid="..." (新增 selector)
   SMOKE-PASS: <spec>.spec.ts (跑通的 smoke)
   ```

## 6 助手共用会话语言 (worker fix-contract 第 1-2 天 ship)

```python
@dataclass
class WorkSession:
    session_id: str             # 会话 ID
    agent: str                  # channel/credit/report/alert/compliance/riskctrl
    state: Literal["idle", "running", "done", "reviewing", "finalized", "error"]
    input: dict                 # 输入
    result_summary: str         # 结果摘要 (人类可读)
    result_items: list[dict]    # 结果列表 (给详情抽屉用 · 每项有 id/title/detail)
    selected_item_id: str | None  # 当前选中
    available_actions: list[str]  # 可用动作 (export/approve/reject/...)
    errors: list[dict]          # 错误列表 (typed · 含 code+message+details)
    data_source: Literal["live", "cached", "fallback", "demo_fixture"]
    created_at: str
    updated_at: str
```

worker fix-contract 第 2 天 deadline: ship `shared/work_session.py` + `docs/contracts/work-session-v1.0.md` + fire signal `WORKER-FIX-CONTRACT-SPEC-V1` · 给 3d-data 接口。

## 主 CLI 角色 (PM 现有窗口)

- **不动 main worktree** · 让 worker 各自跑
- **每天 cherry-pick / merge** worker signal commit
- **PM verify GO** worker 完成
- **撞冲突 stop the line** · 不强 merge

## decisions-log

任何方向变化 / PM 拍板 → 写 `docs/handoff/decisions-log.md` 新 Q-NNN entry · 同 commit 加 ACTIVE-DECISIONS-BACK-WRITTEN trailer。

## 紧急联系

撞 BLOCKER · 写 `docs/handoff/BLOCKED-<worker>-<timestamp>.md` + fire signal commit · 主 CLI 看 git log 仲裁。
