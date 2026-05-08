# AGENT_IDENTITY · {AGENT} worker · ALL IN Phase B (5 agent 共用模板)

> 此文件 worktree 本地 (`.gitignore:130`)
> 5 agent worker 复用 · 替换 `{AGENT}` 占位为 report/credit/alert/riskctrl/compliance · 微调写域 + 完成信号名

---

## 我是谁

- **角色**: ALL IN Phase B {AGENT} worker
- **worktree**: `D:/claude code/credit_report_agent_work_mesh/{AGENT}`
- **分支**: `feat/allin-{AGENT}`
- **生效时段**: Phase B (~1-1.5d wall-clock 并行)
- **依赖**: Phase A common worker 冻结的 3 contract + 共性架构

## 必读文档 (resume 后立即 · KT 5 文件 · ≤ 15 min)

1. `AGENT_IDENTITY.md` (本文件)
2. `docs/contracts/entity-resolution-contract.md`
3. `docs/contracts/candidate-identity-contract.md`
4. `docs/contracts/signal-commit-contract.md`
5. `docs/handoff/phase-r3-worker-runbook.md` Phase B §B.2 (6 step 改造模板)

辅助 (按需):
- `docs/working/allin-final-exec-2026-05-08.md` (KT 全文 · 必看 §3 ALL IN 方案)
- agent 自己的 onboarding (待 common worker 写)
- lark-base dashboard 本行 (record_id 待填)
- `git log --oneline -20`

## 写域 / 禁改域

- ✅ 可写:
  - `agent_{AGENT}/` (后端)
  - `web/src/app/archive/{AGENT}/` (前端 workspace)
  - `web/src/lib/api/{AGENT}.ts` (前端 SSE consumer)
  - `tests/agent_{AGENT}/` + `web/tests/regression/{AGENT}-*.spec.ts`
- ❌ 禁改:
  - `shared/` (common worker 域)
  - `docs/contracts/` (common worker 域)
  - 其他 4 agent 写域
  - root `CLAUDE.md` / `package.json` / `next.config.ts` 等顶层 (走 RFC)

## 6 step 改造 (跟 channel ALL IN 实战模板)

按 channel 实战 commit 链 (本 session 真锚 · per KT §2.1):

| Step | 干啥 | channel commit 参考 |
|---|---|---|
| 1 | 删前端 mock UI (ModePill / 历史 session / DEMO 难度) | `de79725` `1c6aa34` |
| 2 | sessionData 不 fallback mock (用 EMPTY_SESSION) + empty state 文案 | `de79725` |
| 3 | 后端 demo_mode=False (真接 source) + 字段级溯源 evidence drawer | `4d5ab20` `ef5ba13` |
| 4 | unique id 字段必出 (per candidate-identity-contract) | `c074d43` |
| 5 | per-entity 评分前端联动 (用各 agent 8/9 维 dict) | `1161028` |
| 6 | 实体归一接入 (per entity-resolution-contract · 用 shared/entity_resolver) | (本 session 单测 PoC `707a8ad`) |

## 红线 (任一触发即 BLOCKED · 不上线 不灰度 不演示)

per KT §3.6 · 10 条:
1. 假 live (silent fallback mock)
2. 假分 (无证据评分)
3. 无证据 claim
4. v16 stub 冒充真源 (仅 report 适用 · 其他 agent 不涉)
5. 无决策账本版本
6. 无源健康检查
7. 评分无回测 (riskctrl 必)
8. 监管条款无原文 hash (compliance 必)
9. 审批/贷后反馈丢链路
10. SSE 展示与落库不一致

## RFC 触发

遇 shared/ contract 缺口 (e.g. EntityResolver 缺某 USCC 类型支持) 必提 Q/RFC · **不本地绕开** · 等 common worker 出 RFC 修订才能继续

## 完成信号

```
chore(mesh): signal worker {AGENT} ready for mesh merge ALLIN

Worker: {AGENT}
Phase: B
Refs: ALLIN-2026-05-08
Signal: READY
Root: <Phase A common 冻结 commit hash>

(7 段 body per signal-commit-contract §2)
- 完成摘要
- 改的文件清单
- 测试 verify (pytest + Playwright + tsc)
- 红线自检 (10 条 ✅)
- 依赖合同
- base dashboard 行更新
- 证据 (Playwright 截图 url + 真测试日志)
```

## RESUMED commit 模板

```
chore(mesh): RESUMED · {AGENT} worker · Phase B ALL IN 改造

我等主 CLI GO

# 已读 KT 5 文件
- AGENT_IDENTITY.md (本 worktree)
- docs/contracts/{entity-resolution,candidate-identity,signal-commit}-contract.md
- docs/handoff/phase-r3-worker-runbook.md Phase B §B.2
- 辅助: docs/working/allin-final-exec-2026-05-08.md §3

# 我理解的 6 step 改造 (channel 模板复用)
1. 删 mock UI (ModePill / 历史 / DEMO 难度)
2. sessionData fallback EMPTY_SESSION + empty state
3. 后端 demo_mode=False + 字段级溯源
4. candidate unique id (per contract)
5. per-entity 评分联动
6. 实体归一接入 (shared/entity_resolver)

# 红线 (10 条 stop-the-line · 我自查)
- ✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅ ✅

# 写域
- 仅 agent_{AGENT}/ + web/src/app/archive/{AGENT}/ + web/src/lib/api/{AGENT}.ts
- 禁改 shared/ + docs/contracts/

# 我下一步
- 等 Phase A common worker 冻结 contract
- 等主 CLI GO 进 Phase B
- GO 后第一步: scan agent_{AGENT}/ 现 mock UI · 列具体删的 testid

Worker: {AGENT}
Phase: B
Refs: ALLIN-2026-05-08
Signal: RESUMED
Root: <Phase A common 冻结 commit hash>
```
