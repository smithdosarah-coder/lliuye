# HANDOFF · TO NEXT MAIN CLI · 2026-05-02

> PM 重启电脑 · 当前主 CLI session 不 resume · 新主 CLI 读本 doc + §14 5 必读 + 写 `NEW-MAIN-CLI-RESUMED` commit。

## 1. 实时状态快照 (2026-05-02 PDT)

### Production (https://liuye.me/login)
- F4 v2 黑洞已 ship (cherry-pick + ECS deploy 完 · 22:43 PDT)
- 4 view + 6 Agent workspace + Glassmorphism LoginForm 全可用
- F4 v2 verdict 仍**待 PM**: 自评不到 awwwards 顶级 (色温梯度纯白 / chromatic aberration 不明显) · 比 v1 极简强 · PM 需上看给 A 接受 / B 派 V2 fix

### 4 旧 worker 状态 (前主 CLI commit 485fe21 已声明释放)
- ❌ worker-B1-flywheel — Sprint 1 BE10 + 误派 Sprint 2 enrich 都 ship · **释放退役** · PM 应关 cmd window
- ❌ worker-B4-credit — Sprint 1 BE2 + 误派 Sprint 2 BE7 都 ship · **释放退役** (BE7 提前完成 · Sprint 3 worker-B7 工作量减半)
- ❌ worker-B4-report — Sprint 1 BE3 ship · charter Sprint 2 不参与 · **Sprint 4 整合时再启**
- 🟢 worker-B3 — F4 v2 ship · 续干 Sprint 2 B-3 phase · 已 commit 3/4 (F11+F14+F17) · 等 F12 (视觉清洗 + F1c mock 中文术语合并)

### Sprint 2 真主线 3 新 worker (前主 CLI commit 412f516 创建 worktree + onboarding)
- 🆕 worker-B4-alert (BE5+BE9 · 3 周) — worktree `D:\claude code\work-B4-alert` · branch `feat/phase-b4-alert` · 待 PM 双击 launch.bat 启
- 🆕 worker-B4-compliance (BE4 · 2-2.5 周) — worktree `D:\claude code\work-B4-compliance` · branch `feat/phase-b4-compliance` · 待启
- 🆕 worker-B2 (BE11 商业化 doc only · 1 周) — worktree `D:\claude code\work-B2-biz` · branch `feat/phase-b2-biz` · 待启
- launcher: `C:\Users\Mr.S\Desktop\launch-B-sprint2-NEW.bat`

## 2. 关键 decisions/承诺 (新主 CLI 必守 · 不重蹈)

### 2.1 5 跑偏 root cause 硬规 (前主 CLI commit 412f516 写入 · 写入下次 reset session 必读)

| # | 触发 | 动作 |
|---|---|---|
| 1 | 任何派单前 | `grep "Sprint N" docs/reset/phase-b-charter.md` verify 真排期 |
| 2 | PM 提"worker idle / 挂机" | 先 read charter · 再回 "Sprint X 真主线说应启新 worker Y · 不是给现有 worker 加任务" |
| 3 | Sprint 边界 | mental switch "新 sprint team composition 是哪 N 个" — Sprint 不是 task 续是 team 换 |
| 4 | P0 任务 (e.g. F4 v2 阻 production demo) | commit body 写死优先级 + 阻 worker 进下个 sprint · 不仅给 GO signal |
| 5 | PM 高频提醒 | STOP 5s · 想 "这是 charter 真主线还是凭印象?" · 不立即响应 |

### 2.2 4 视觉硬约束 (前主 CLI 承诺 · F4 v1 翻车后立)

| # | 规则 |
|---|---|
| 1 | 任何视觉决策前必先建参考库 (3+ 顶级截图存 design_mockups/login-v2-references/) |
| 2 | ECS deploy 后**主 CLI 必先亲眼上 https://liuye.me/login** 看效果 |
| 3 | 不满意立即 fix · 直到主 CLI 自己满意才让 PM 看 |
| 4 | Codex/Gemini 审美都不靠谱 · PM 是 final 判官 · 主 CLI 先把不通过的过滤掉 |

### 2.3 Codex 用尽 until 2026-05-08 (Q-043 protocol v2 fallback)

- codex `You've hit your usage limit. Try again at May 8th, 2026 12:47 AM`
- 全 manual review by 主 CLI · trailer `REVIEW-MODE: manual`
- 5 月 8 日 Codex 恢复后建议立即 fire Phase B periodic audit (插入点 4 提前用)

## 3. cron 5 min 巡逻 SOP (新主 CLI 第 1 件事 · 接 PM 双击 launch.bat 后)

PM 重启后启新 cron · prompt verbatim:
```
5m 跑 `git -C "D:/claude code/credit_report_agent_work" log --all --oneline -50 --since="10 minutes ago"` 扫 5 个 worker branch (feat/phase-b3-rm-workbench, feat/phase-b4-alert, feat/phase-b4-compliance, feat/phase-b2-biz, feat/phase-b1-flywheel/feat/phase-b4-credit/feat/phase-b4-report 已 release 不扫) 上有没有新 signal commit。
... (按之前 cron prompt 完整复制 · 加 5 worker branch 名 + sequential codex fallback to manual)
```

## 4. F4 v2 verdict 待 PM (新主 CLI 接手第一问)

PM 上 https://liuye.me/login 给 verdict:
- A 接受当前 F4 v2 (打 git tag · Sprint 1 收尾)
- B 派 V2 fix gap (色温梯度真做 + chromatic aberration 真做 + Bloom 强化)
- C 你已上看了 (告诉新主 CLI verdict)

参考截图: `design_mockups/login-v2-references/awwwards-workshop-fullpage.png` (PM 嫌"垃圾极简"后锁定的视觉目标)

## 5. Phase B 整体进度 (前主 CLI 写)

| Sprint | 真主线 | 完成度 |
|---|---|---|
| Sprint 1 (Week 1-3) | 4 worker · BE10/BE2/BE3/v4 B-1 | **100%** |
| Sprint 2 (Week 3-6) | 4 worker · v4 B-3/BE5+BE9/BE4/BE11 | **5%** (B3 续 75% B-3 phase · 3 新 worker 0%) |
| Sprint 3 (Week 6-10) | 3 worker · BE1+BE12/BE6+BE8/BE7+BE13 | **15%** (BE7 已提前 ship) |
| Sprint 4 (Week 10-14) | 整合 + Codex final audit | 0% |
| Sprint 5 (Week 14-18) | demo + POC 4 维评价 | 0% |

**总体**: ~25-30% · 1 天 wall-clock · 真预计 ~10-14 周完整 ship

## 6. 新主 CLI 起手第 1 件事 (verbatim 模板)

```bash
cd "D:/claude code/credit_report_agent_work"
# 读 §14 5 必读: RESET_MASTER_PLAN.md / docs/reset/north-star.md / phase-a-charter.md / step2-conflict-scan-charter.md / codex-mesh-protocol.md
# 读本 HANDOFF: docs/handoff/HANDOFF_TO_NEXT_MAIN_CLI_2026-05-02.md
# 读 decisions-log 末 50 行 + state-snapshot.md

git log --oneline -30 --all
py scripts/orchestrator/scoreboard.py

git commit --allow-empty -m "chore(resume): NEW-MAIN-CLI-RESUMED · 2026-05-02

产品 north star: 6 Agent 矩阵 RM workbench v4 闭环 · /today 单链路 Agent6→Agent3 + handoff
6 Agent 闭环路径: Agent6 报告 → Agent3 授信 → Agent5 合规 → Agent4 预警 (跨客户) · Agent1 获客 + Agent2 风控 平行
走歪表征 (top 5):
  1. 凭印象决策 (视觉 + 架构 + 派单)
  2. idle 焦虑驱动派单 (charter 真主线被忽略)
  3. Sprint 转换无 mental switch (沿用现有 team)
  4. P0 任务无写死优先级 (worker 自己跳)
  5. PM 高频提醒诱反应 > 思考

当前 Phase: Phase B · Day 2 · Sprint 2 真主线启动中
待启 worker: B4-alert + B4-compliance + B2 (PM 双击 launch.bat 后启)
PM 已拍板:
  - F4 v2 ship 但视觉 verdict 仍待 (A/B/C 选项)
  - 3 旧 worker 释放退役 (B1 + B4-credit + B4-report)
  - B3 续 Sprint 2 B-3 phase (3/4 已 commit · F12 待)

我下一步动作:
  1. 等 PM 双击 launch.bat 启 3 新 worker
  2. 等 PM 给 F4 v2 verdict
  3. 启 cron 5 min 巡逻

Signal: NEW-MAIN-CLI-RESUMED"
git push origin main
```

## 7. 重要文件路径 (新主 CLI 必知)

- 主 worktree: `D:/claude code/credit_report_agent_work`
- 5 worker worktree: `D:/claude code/work-B3-rm-workbench` + `work-B4-alert` + `work-B4-compliance` + `work-B2-biz` + `work-B1-flywheel/work-B4-credit/work-B4-report` (后 3 个已 release)
- launcher: `C:/Users/Mr.S/Desktop/launch-B-sprint2-NEW.bat`
- design references: `design_mockups/login-v2-references/awwwards-workshop-fullpage.png` + `F4-V2-LIVE-2026-05-01.png`
- ECS deploy script: `bash scripts/deploy_to_ecs.sh` (含 build · 前端) / `--skip-build` (后端)
- Production: `https://liuye.me/login` · 后端 ECS 139.196.30.69 · Cloudflare tunnel

## 8. 紧急 fallback (如果新主 CLI 也跑偏)

PM 可:
- 退回最近 git tag: `git reset --hard phase-a-exit-bugfix-2026-05-01` (Phase A 真 exit 状态 · 8 硬线全过 · 4 BUG 修完)
- 或: `git reset --hard phase-b-start-2026-05-01` (Phase B 启动前)

---

**Signal: HANDOFF-PREPARED-FOR-2026-05-02-RESTART**

前主 CLI: Claude Opus 4.7 (1M context) · 2026-05-02 PDT · session 长 1 天 + 大量 cron tick + 5 sub-agent + 多次 ECS deploy · 临近 compression 边界 · 主动让位
