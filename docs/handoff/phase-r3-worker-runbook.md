# ALL IN Phase A/B/C Worker Runbook v1.0 · 2026-05-08

> **Owner**: 主 CLI + 6 worker
> **依赖**: KT 文档 `docs/working/allin-final-exec-2026-05-08.md`
> **状态**: 待新主 CLI 接手 → Phase A 启动

---

## Phase A · common worker (单 worker · 0.5 天)

### A.1 准备

- worktree: `D:/claude code/credit_report_agent_work_mesh/common`
- 分支: `feat/allin-common-contracts`
- 角色: common (admin role · 可改 shared/)

### A.2 必交付物 (Gate: 5 worker 只读通过才进 Phase B)

1. **完善 3 contract** (现 outline · 补真 spec):
   - `docs/contracts/entity-resolution-contract.md` (USCC 校验码 + LLM fuzzy 真实现 + 6 agent 接入 wrapper)
   - `docs/contracts/candidate-identity-contract.md` (5 agent unique id 接入点 + Playwright contract test)
   - `docs/contracts/signal-commit-contract.md` (git hook + cherry-pick 自动化脚本 + base dashboard 行更新)

2. **抽 3 共性架构** (新建 shared/):
   - `shared/live_shell/` (LiveShell 6 agent 统一 "启动→流式→操作" 框架)
   - `shared/evidence_drawer/` (统一证据展示 component)
   - `shared/source_health/` (数据源健康检查)

3. **6 个 resume 脚本骨架** (`.mesh-launcher/`):
   - `resume-common.ps1`
   - `resume-{report,credit,alert,riskctrl,compliance}.ps1`

4. **lark-base dashboard 创建** + schema (12 字段 per KT §6.2)

5. **更新桌面脚本** `launch-all-LIUYE.bat` (3 cmd → 7 cmd)

6. **5 agent worker AGENT_IDENTITY 模板** (各自写域 / 禁改域 / KT 5 文件 / 完成信号 / 证据要求)

### A.3 完成信号

- Commit subject: `chore(mesh): signal common worker ready · ALLIN Phase A complete`
- 5 worker (report/credit/alert/riskctrl/compliance) 各自 git pull common 分支验证 `read-through OK`
- 主 CLI ratify Phase A close-out

---

## Phase B · 5 agent worker 并行 (并行 wall-clock 1-1.5 天)

### B.1 5 worker 各自准备

| Worker | worktree | 分支 | 写域 |
|---|---|---|---|
| report | `mesh/report` | `feat/allin-report` | `agent_report/` + `web/src/app/archive/report/` |
| credit | `mesh/credit` | `feat/allin-credit` | `agent_credit/` + `web/src/app/archive/credit/` |
| alert | `mesh/alert` | `feat/allin-alert` | `agent_alert/` + `web/src/app/archive/alert/` |
| riskctrl | `mesh/riskctrl` | `feat/allin-riskctrl` | `agent_riskctrl/` + `web/src/app/archive/riskctrl/` |
| compliance | `mesh/compliance` | `feat/allin-compliance` | `agent_compliance/` + `web/src/app/archive/compliance/` |

### B.2 每 worker 6 step (跟 channel ALL IN 模板)

按 channel 实战 (本 session commit 链):
1. 删前端 mock UI (ModePill / 历史 session / DEMO 难度)
2. sessionData 不 fallback mock (用 EMPTY_SESSION) + empty state 文案改
3. 后端 demo_mode=False (真接 source · 不 silent fallback)
4. 字段级溯源 evidence drawer (前端消费后端 dataSources)
5. unique id 字段后端必出 (per candidate-identity-contract)
6. per-entity 评分前端联动 (用各 agent 自己的 8/9 维 dict)

### B.3 完成信号 (per signal-commit-contract)

```
chore(mesh): signal worker <agent> ready for mesh merge ALLIN

Worker: <agent>
Phase: B
Refs: ALLIN-2026-05-08
Signal: READY
Root: <Phase A common 冻结 commit hash>

(7 段 body · per signal-commit-contract §2)
```

### B.4 BLOCKED 处理

任一 worker 撞 stop-the-line 10 红线 (KT §3.6) → 立即 fire `Signal: BLOCKED` + 列违反条 + 提 RFC. 主 CLI 仲裁.

---

## Phase C · 主 CLI 整合 (0.5 天)

### C.1 收 5 worker signal

- 用 `py "C:/Users/Mr.S/.claude/skills/multi-cli-mesh/scripts/orchestrator/scoreboard.py"` 看全 worker 状态
- 等 5 worker 全 fire `Signal: READY` (或 BLOCKED 单独处理)

### C.2 cherry-pick 整合 (per signal-commit-contract §3)

按完成顺序 cherry-pick (不强制 report→credit→alert→riskctrl→compliance · 哪个先 ready 先合):

1. DIFF guard: `git diff <worker>..<base> -- shared/` 必空 (per AGENT_IDENTITY 禁改域)
2. cherry-pick worker code commits 入 main
3. 跑跨 agent 集成 test (Playwright × 6 agent 真测一遍)
4. 写 close-out commit
5. 更新 lark-base 该 agent 行 `status: merged`

### C.3 部署 + 真验收

- `bash scripts/deploy_to_ecs.sh` (含 web build + restart)
- Playwright 跑 6 agent 全套 spec
- 用户体验真验: 5 角色目标 (RM 2h→20min · 审贷员 30min→5min 等) 是否真达到

---

## 红线 (跨 Phase · 任一触发即 stop-the-line)

per KT §3.6 · 10 条:
1. 假 live · 2. 假分 · 3. 无证据 claim · 4. v16 stub 冒充真源 · 5. 无决策账本版本 · 6. 无源健康检查 · 7. 评分无回测 · 8. 监管条款无原文 hash · 9. 审批/贷后反馈丢链路 · 10. SSE 展示与落库不一致

---

## ROI 锚点 (真估)

- channel 单 agent 实战 (本 session 真锚): ~3-4 天
- 5 agent 串行: 4-5 天
- mesh 并行 (本 plan): **2-2.5 天** (Phase A 0.5d + Phase B 1-1.5d + Phase C 0.5d)
- 加速 ~2x · 用 signal 时间戳 + 验收日志复盘验证

---

## 待新主 CLI 接手第一组动作

1. 读 KT 5 文件 (KT + 3 contract + 本 runbook)
2. 跑 git log 看最近 commit
3. 写 NEW-MAIN-CLI-RESUMED commit (per CLAUDE.md §14 模板)
4. 等 PM verify GO
5. PM GO 后:
   - 调 lark-doc 创建主 PRD
   - 调 lark-base 创建 dashboard
   - 创建 6 mesh worktree (`git worktree add ...`)
   - 写 6 AGENT_IDENTITY.md (per KT §10)
   - 启 common worker (cmd 2 cd `mesh/common` 跑 resume-common.ps1)
   - common worker 干 Phase A 5 件交付物
   - Gate: 5 agent worker 各自 read-through 通过
   - 启 5 agent worker (cmd 3-7) 进 Phase B
   - 收 signal · 进 Phase C 整合
