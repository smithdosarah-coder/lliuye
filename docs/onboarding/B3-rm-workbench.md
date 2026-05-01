# Worker-B3 Onboarding · RM workbench v4 (Phase B Sprint 1+2+3+4)

> Phase B Stream 1 · 17 action 全 sprint (Sprint 1 B-1 phase + Sprint 2-3 B-3 + Sprint 4 B 末)
>
> 总工程量: 5-6 周 (含并行 4-5 周 wall-clock)
> Dispatch signal: `PHASE-B-SPRINT-1-DISPATCHED`

## 0. worktree

- `D:\claude code\work-B3-rm-workbench` · branch `feat/phase-b3-rm-workbench` (新建 · 已 checkout)
- resume: cd worktree · `git status` (clean) · 直接干 §1.1 Sprint 1 任务

## 1. 任务 · 分 sprint 交付 (per `docs/research/FINAL-FRONTEND-OPTIMIZATION-PLAN-V4-2026-05-01.md`)

### 1.1 Sprint 1 任务 (Week 1-3 · B-1 phase · ~1 周本 worker 占用)

| # | Action | 工程量 | 验收 |
|---|---|---|---|
| **F1** | 千分位 + 术语 + 金额标准 (`¥50,000,000.00` + Tabular Figures + 严格右对齐 + 纯中文术语) | 0.5-1 周 | 4 角色 view 全数字达金融规范 + Tabular Figures CSS 接 |
| **F2** | Today AI 助手卡路由修补 (`TodayContent.tsx:29` 修跳 `/dispatch` bug) | 0.5 天 | 助手卡进 `/archive` 或具体 agent · 消息卡仍 `/dispatch` |
| **F3** | Hero minimum 真指标 (替 `TICKET_FALLBACK_COUNT` 真 ticket-store · 不显效率/转化率装饰) | 0.3 周 | Hero 待办数 + SLA 全真数据 · 无源 fallback 标识 |
| **F4** | 登录页黑洞重设 (3D 几何粒子 OR 极简磨砂玻璃 + 中性深灰/蓝) | 0.3 周 | 银行客户首屏不联想"资金被吞" · Interstellar 实验撤 |
| **F5** | CustomerContextGateway (读 ?customer query · focus customer-store · 传入 4 workspace) | 0.5-1 周 | RM 从 customer/dispatch/today 进 workspace 后 hero/query/默认 scan 一致 · 不删 CustomerSelector 保留 demo 切换 |
| **F6** | C14 Evaluation Baseline Gate (与 worker-B1 配套) | 3-5 天 | 6 Agent baseline 跑通 · 红线接 CI · 与 worker-B1 BE10 互依 |

### 1.2 Sprint 2-3 任务 (Week 3-10 · B-3 phase · ~3 周本 worker 占用)

F7-F17 见 `docs/research/FINAL-FRONTEND-OPTIMIZATION-PLAN-V4-2026-05-01.md` §1 (Today 单链路 + handoff 任务卡 + Action Card 组件族 + A5 spike + 视觉清洗 + 全屏渐变折中 + Live evidence + dispatch 单发送 + warroom rejected lane + ...)

### 1.3 Sprint 4 任务 (Week 10-14 · B 末 phase · ~1 周本 worker 占用)

C11 audit 降级 + C12 ScanCTA + C13 抽 hook + C18 Agent1 similarity 前端

## 2. 必读

- `RESET_MASTER_PLAN.md`
- `docs/reset/phase-b-charter.md` v2 (Stream 1 worker-B3 完整 17 action 排期)
- `docs/research/FINAL-FRONTEND-OPTIMIZATION-PLAN-V4-2026-05-01.md` (主 CLI + Codex + Gemini 三方辩论 R3 综合 final · PM ratify)
- `docs/research/three-way-debate-r1-v2-{mainCLI,codex,gemini}-2026-04-30.md` (R1 v2 三方独立草案)
- `docs/research/three-way-debate-r2-v2-{mainCLI,codex,gemini}-2026-05-01.md` (R2 v2 三方互检)
- CLAUDE.md §7 (前端设计系统 platform shell-v2)

## 3. 红线 (per v4 三方辩论共识)

- ❌ 全屏渐变全撤 (per 三方 lock 折中 · 主区 `#F7F9FC` + 装饰区保留 4 主题 Masthead/选中/Hover)
- ❌ A5 完整跨冲突 UI Phase B 做 (Codex 反对没 audit 账本 · spike + Phase C 完整)
- ❌ 一刀切删 CustomerSelector (Codex 反对 · 保留 demo/异常切换入口)
- ❌ IM 降级到边缘 (Codex 反对 · dispatch 保留为协作 + ⌘+K command)
- ❌ Phase B 大改 Report+Riskctrl 布局 (推 Phase C)
- ❌ 装饰 KPI ("效率提升 35.8%" 类无真数据指标 · 反 Evidence-First)

## 4. ACK (Sprint 1 阶段性)

Sprint 1 完 commit `Signal: WORKER-B3-PHASE-B1-DONE` · trailer:
```
F-DELIVERED: F1, F2, F3, F4, F5, F6
SPRINT: 1 of 4
PRESERVES: F-XXX (per docs/features-inventory.md)
NEW-DOM: data-testid="..." (新 selector)
SMOKE-PASS: web/tests/regression/<spec>.spec.ts (本 sprint 新加 spec 跑通)
TSC-CLEAN: yes
HARDLINE-PHASE-B-#3: 部分 met (B-3 + B 末完后才完整 met)
```

最终 (Sprint 4 完): `Signal: WORKER-B3-RM-WORKBENCH-V4-DONE` (17 action 全 done)

## 5. Codex + Gemini (三方辩论持续)

- Pre-dispatch (插入点 1): Codex draft 落 `docs/audit/codex-drafts/B3-rm-workbench.md`
- Post-DONE (插入点 2 · 每 sprint 完): Codex review · 主 CLI 综合 · Gemini 看截图给视觉 verdict (重大改动走 R1+R2+R3 如 Q-044 protocol)

---

**Author**: 主 CLI · 2026-05-01 · Worker-B3 (Phase B Sprint 1+2+3+4 · 2 of 4 in Sprint 1)
