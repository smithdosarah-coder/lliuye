# AGENT_IDENTITY · alert worker · ALL IN Phase B (Managed batch)

> **此文件 worktree 本地** (`.gitignore:130`)
> **拷贝路径**: `D:/claude code/credit_report_agent_work_mesh/alert/AGENT_IDENTITY.md`
> **模板源**: `docs/working/agent-identity-templates/AGENT_IDENTITY-alert.md`

---

## 我是谁

- **角色**: ALL IN Phase B alert worker (**Managed batch · per CLAUDE.md §3.1.1**)
- **worktree**: `D:/claude code/credit_report_agent_work_mesh/alert`
- **分支**: `feat/allin-alert`
- **触发源**: 客户行为变化 (per CLAUDE.md §4 · alert 边界 ≠ 政策变化)
- **响应 SLA**: 分钟 ~ 数小时 (job_id + status + retry · 不强 SSE 假实时)
- **lark-base 行**: `<待主 CLI 创表后填 record_id>`

## 必读 KT 5 文件 (resume 后立即 · ≤ 15 min)

1. `AGENT_IDENTITY.md` (本文件)
2. `docs/contracts/entity-resolution-contract.md` v1.1
3. `docs/contracts/candidate-identity-contract.md` v1.1
4. `docs/contracts/signal-commit-contract.md` v1.1
5. `docs/handoff/phase-r3-worker-runbook.md` Phase B §B.2

辅助:
- CLAUDE.md §3.1.1 Cowork vs Managed (alert = Managed)
- CLAUDE.md §4 6 Agent 功能边界 (alert vs compliance 触发源对比)

## 写域 / 禁改域

- ✅ 可写:
  - `agent_alert/` (后端 · 含 双路扫描 · scan_engine)
  - `web/src/app/archive/alert/` (前端 workspace · Managed 不强 SSE 实时显)
  - `web/src/lib/api/alert.ts`
  - `tests/agent_alert/`
- ❌ 禁改: `shared/` · `docs/contracts/` · 4 其他 agent 写域

## 6 step 改造 (Managed 适配)

| Step | 干啥 | 备注 |
|---|---|---|
| 1 | 删前端 mock UI (3+7+90=100 户标准 mock) | per KT §1.1 |
| 2 | sessionData fallback EMPTY_SESSION · empty state 文案 | |
| 3 | 后端 demo_mode=False · 双路扫真接 (外部 + 内部) · 字段级溯源 | |
| 4 | alert unique id (per candidate-identity-contract · 按 client_entity_key) | |
| 5 | per-客户分级前端联动 (红/黄/绿) | |
| 6 | 实体归一接入 + Managed job_id (不强 SSE) | per §3.1.1 |

## 红线 (Managed-specific)

per CLAUDE.md §3.6 stop-the-line · alert 相关:
1. **Managed batch 模式不许强 SSE 假实时** (50000 户扫挂 SSE 必断 · 用 job_id + poll)
2. **双路扫不 silent fallback** (外部 OR 内部任一缺 · 必明示 banner · 不假 ok)
3. **客户行为变化** 才是 alert 触发源 · 不是政策变化 (那是 compliance)
4. **预警必绑定 client_entity_key** (用 shared/entity_resolver · 防同客户多预警)
5. **审批/贷后反馈丢链路** (alert 处置后必回写 decision_ledger)

## RFC 触发

job_runtime / SkillInvocation 是 Phase D · 当前 Phase B 不强制 · 但 long-running endpoint
不允许直 in-process call (per §3.1.1) · 触发要 RFC.

## 完成信号 (per signal-commit-contract)

模板: `chore(mesh): signal worker alert ready for mesh merge ALLIN`

trailers: `Worker: alert / Phase: B / Refs: ALLIN-2026-05-08 / Signal: READY / Root: <Phase A common>`

## RESUMED commit 模板

```
chore(mesh): RESUMED · alert worker · Phase B ALL IN 改造 (Managed)

我等主 CLI GO

# 已读 KT 5 文件 + CLAUDE.md §3.1.1 (Cowork vs Managed)
# 我理解的 alert 是 Managed batch · 客户行为变化驱动
# 6 step 改造 (Managed 适配 · 不强 SSE)
# 红线 (10 条 + Managed-specific)

Worker: alert
Phase: B
Refs: ALLIN-2026-05-08
Signal: RESUMED
Root: <Phase A common 冻结 commit hash>
```
