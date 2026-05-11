# B.3.4 mesh 起步说明 · 修正版 (2026-05-11 06:30 GO)

> **背景**: PM 凌晨 03:45 verify 给 6 件痛 + 总结 "所有后端前端混乱·没一个 agent 独立业务逻辑·连最早期 demo 都不如"
> **5+ 轮辩论**: 主 CLI ultrathink + codex R5/R6/R7 + PM 直觉 + KT 2026-05-10 retro
> **PM 06:30 GO**: 接受 KT+codex R7 brutal 修正 · 5 worker → 4 worker · 3D 降级 next sprint

## PM 凌晨 6 件痛 (verbatim)

1. **获客 (channel)**: 点击空白页也会跳转出查询 + 解释后端逻辑/信源
2. **风控 (riskctrl)**: 演示后大面积空白 · 数据非常少
3. **风控**: 演示没成功 · 实际没有按钮
4. **预警 (alert)**: 队列出来 · 不能点客户详情 · **严重排版问题** (PM 06:00 截图揭示 idle 中间 + 右下大空白)
5. **合规 (compliance)**: 完全乱的排版 · 没任何功能展示
6. **报告 (report)**: 后端调用失败

PM 总结: "所有后端前端都混乱·没一个 agent 有独立业务逻辑·连最早期 demo 都不如"

## 关键 verdict 演化 (5+ 轮辩论)

| 轮 | 提出方 | verdict |
|---|---|---|
| R1-R4 主 CLI | 主 CLI ultrathink | 假设: 6 助手缺 detail drawer |
| R5 codex | gpt-5.5 xhigh | **打脸主 CLI**: drawer 都在 (引用 5 个 file:line) · 真因 = WorkSession 契约缺失 |
| R6 codex | gpt-5.5 xhigh | v2 圆环不解决 6 件痛 · 8-12 天工期 · 推荐先 B.3 修底子 + 小驾驶舱 |
| PM 直觉 | PM 05:25 | 每个 agent 必须独立可用 · 不强协同 |
| PM 截图 | PM 06:00 | alert idle 中间 + 右下大空白 · idle 状态没引导 |
| KT 2026-05-10 | 另一 CC 主 CLI 复盘 | **真根因更深**: 6 助手同构重复 · 1 bug 改 6 处 · E2E 拖到 Day 28 · 41 worktree 协调开销 |
| R7 codex | gpt-5.5 xhigh | 同意 KT · 主 CLI 5 worker 计划反 R4+缺 R1 · 3D 是 scope inflation · brutal 排序 |

## 4 worker 修正版 · KT brutal 排序

### P0-R1 · shared-extract (2-3 天 · 1 worker)

- worktree: `credit_report_agent_work_mesh/shared-extract`
- branch: `feat/b34-shared-extract`
- 任务: inventory 6 助手重复模块 → 抽 shared/ (evidence_pipeline / output_validator / knowledge_base / RBAC) + contract test
- 关键: 不是 "everything shared" · 是 "shared contract + shared invariants + local adapters where domain truly differs" (codex R7 挑战 KT)
- **TDD red-to-green** · test commit 先 · 实现 commit 后

### P0-R5 · e2e-daily (1 天 · 1 worker · 并行 P0-R1)

- worktree: `credit_report_agent_work_mesh/e2e-daily`
- branch: `feat/b34-e2e-daily`
- 任务: cron 6am 跑 admin E2E + Playwright 视觉回归 (PM alert idle 空白入 spec)
- 6 助手基础 E2E spec (admin 真号登录 + 跑 demo + 验 done)
- 视觉回归 baseline (idle 状态不能纯白色)

### P0-R2 · fix-bugs (2 天 · 1 worker · 并行 P0-R1)

- worktree: `credit_report_agent_work_mesh/fix-bugs`
- branch: `feat/b34-fix-bugs`
- 任务: 修 4 件具体 bug · 每件 TDD red-to-green
  - channel 点空白触发搜索
  - report 后端 503 真因排查 + 修
  - alert 客户行可点 + 排版
  - compliance 详情体验

### P0-PM · fix-indep (2-3 天 · 1 worker · 并行 P0-R1)

- worktree: `credit_report_agent_work_mesh/fix-indep`
- branch: `feat/b34-fix-indep`
- 任务:
  - **alert idle 空白填实** (PM 截图直接痛 · 最优先)
  - 6 助手 idle 空白同改 (共享原则: 主 CTA + 占位 + 完成后显啥提示)
  - 主按钮简化 (1 主 + 1 次 · 删多余 toggle)
  - 6 助手独立可用 (default 演示模式 · 不显"等别人")

### P1 · fix-contract (等 P0-R1 完成后启 · 不在本批)

- worktree 已起: `credit_report_agent_work_mesh/fix-contract` (但 prompt 待 P0-R1 完成后更新)
- 任务: WorkSession contract (跨 6 助手共用会话语言)
- 工期: 2 天 · 在 P0-R1 抽完 shared 后才有 stable base

### P2 · 3D 方案 (降级 next sprint · 不在本批)

- codex R7: "scope inflation · 在 control plane 还没修好时上新视觉是反模式"
- 等 P0+P1 全 ship 后再启

## 通用规则 (4 worker 都遵守 · KT R1-R6)

1. **R1 · 禁 Agent 内重复共享业务概念** · 必须先抽 shared/
2. **R2 · TDD 测试先行** · test commit 先 · 实现 commit 后 · CI red-to-green
3. **R3 · fix-forward budget** · ≤ 10 hotfix/sprint · 超出 stop-the-line
4. **R4 · mesh ≤ 6 长期 + ≤ 2 临时 = ≤ 8** · 本批 4 worker · 加主 CLI = 5 · 合规
5. **R5 · 真号 E2E 每日跑** · BLOCKED 48h 内升 PM
6. **R6 · 反模式清单** (8 条 · 见 KT 文档)

## commit trailer (4 worker 都必带)

```
KT-2026-05-10-COMPLIANT: yes
R1-R6-CHECKED: yes (or specify which R checked)
TEST-COMMITTED-FIRST: yes
REVERSE-RATIO: <X.X%>
Signal: <RESUMED | STEP-X-DONE | READY | BLOCKED>
Worker: <name>
Refs: B.3.4-KT-<RN>
```

## 主 CLI 角色 (PM 现有窗口)

- **不动 main worktree** · 让 worker 各自跑
- **每天 9am cherry-pick / merge** worker signal commit + 看 e2e-daily 报告
- **撞 BLOCKER 48h 内**升 PM 拍板
- **每周日清** ≥ 7 天未活动的 worktree (KT R4)

## decisions-log

任何方向变化 / PM 拍板 → 写 `docs/handoff/decisions-log.md` 新 Q-NNN entry + ACTIVE-DECISIONS-BACK-WRITTEN trailer

## 历史镜像 (5+ 轮辩论存档)

- `D:/claude code/.tmp/codex-r6-stderr.log` · codex R6 v2 圆环 verdict
- `D:/claude code/.tmp/codex-r7-stderr.log` · codex R7 KT verdict (本次 brutal 排序)
- `docs/working/B.2.4-system-audit-2026-05-11.md` · 主 CLI 初版 audit (含错的部分 · DetailDrawer 假设错)
- `docs/KT-2026-05-10-efficiency-collapse-retro.md` · KT 2026-05-10 retro (真根因来源)
