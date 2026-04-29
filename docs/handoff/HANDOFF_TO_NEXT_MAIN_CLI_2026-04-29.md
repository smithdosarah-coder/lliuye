# Handoff to Next Main CLI · 2026-04-29

> 本文件由当前主 CLI (即将交班) 写。下一任 fresh main CLI 必读 · 然后写 `Signal: NEW-MAIN-CLI-RESUMED` commit verify 状态。

---

## 1. 用户档案 (PM 行为模式 · 软知识 · 不读 memory 容易漏)

- **刘野** · 众安信科 AI 中台 · 信贷 6 Agent 矩阵产品负责人
- **AI PM 出身 + vibe coder** · 看得懂代码 + 审得了方案 + 必要时自己动手
- **默认中文** · 代码/命令/变量名英文
- **不要谄媚** · 不夸"很好的问题" · 不"当然可以" · 方案有问题直说
- **结论先行** · verdict 先 · 理由后
- **默认 terse** · 短为先
- **审计 / review 类** · 开头 verdict + 3-5 bullet · 禁散文
- **多档建议给分级** · 高/中/低 ROI · 别让 PM 自己排
- **时间观念严** · 不要乱估时 · 容易翻车 (上一任主 CLI 多次因此被批)

## 2. 项目 production 现状

- ECS: 139.196.30.69 · domain liuye.me · admin user · keypair `~/.ssh/id_ed25519_aliyun_demo`
- 4 services: nginx / cloudflared / lliuye-frontend / lliuye-backend (systemd)
- production 跑 main 分支 · dev 在 chore/l0-infra
- ECS git tree 必须 clean · 任何 dirty 立即 fix-forward
- 部署: `bash scripts/deploy_to_ecs.sh` (full) 或 `--skip-build` (后端改动)
- 改 web/ 后**自动**部署 (CLAUDE.md §13.1) · 不问

## 3. 项目 milestones (PM 已认 · 不要重新讨论)

- 2026-04-16 北部湾首演完成 (6 Agent 矩阵首次客户侧演示)
- 2026-04-19 6 Agent POC B 档落地 (用户认了 · 对外措辞红线: 能说"客户认了"不能说"商业化/签单")
- 客户走访阶段已结束 → Gradio 已归档到 `legacy_gradio/` (Phase B 批 5 完成)

## 4. Reset 工程启动背景

PM 2026-04-29 检查 production · 发现"产品形态走歪了":
- 6 个 workspace 是独立 showroom 页 · 不是 RM workbench (Cursor 模式)
- Look-alike 获客 (Agent1) / Agent6 → Agent3 handoff (核心 pivot) 没真做
- "中间真两边假"联动断 (Channel SSE 只更新候选列 · 其他 panel 仍 mock)
- pin 拖到聊天框变 URL 文本 (root cause: drag source 没 thumbDataUrl)
- decisions-log Q-040/Q-041 active rule 没回写 root CLAUDE.md

PM 决议 reset · 走 3-step 流程 (Step 2 audit → Step 1 cleanup Phase A → Step 3 PRD Phase B)。

## 5. 已 ship 的 Cleanup batches (Phase B 0-6 + 散修)

| Batch | Commit | 内容 |
|---|---|---|
| 0 | `b73b15c` | 凭证 redact (handoff doc + decisions-log:1272+:2364) |
| 1 | `e2ec0c5` | 38 dead files git rm + agent-channel-session refactor |
| 2 | `523efd0` | 4 demo坑 (forceMock + 3 silent fallback) |
| 4 | `99650a9` | 8 dead routes |
| 5 | `ddb565b` | Gradio + form_filler + narrative_pipeline → legacy_gradio/ |
| 6 | `40d8b2c` | docs sync (32 W-* archive + master plan + agent6 yaml v16) |
| B-2 | `37ff24a` | dropdown click-to-fire (4 workspace) |
| B-banner | `78d28d6` | inline error → banner (4 workspace) |
| B-cta | `94e2e88` | Report 巨大按钮收紧 |
| B-pin | `a9370a3` | pin thumbnail真 e2e fix |
| Report empty | `8f8e378` | EmptySkeleton 撑满 viewport |
| Report SSE | `97663e7` | handleApplyLaunch 真 fire SSE |

3 LLM key 已 rotated 2026-04-29 · ECS .env 同步。

## 6. PM 已拍板 5 件 (Phase A 启动前不再争)

1. **杜绝拖死 4 机制**: schema / ≤ 3500 词 / 单 issue ≤ 2 round / dissent 反增即 escalate
2. **Phase A/B 严切阶段** (Phase A 8 项验收硬线 · Phase B 3 项)
3. **active decision 必回写 root CLAUDE.md** (谁改谁回写 · CI lint)
4. **命名 SSOT 8 列**: agent_id / 中文 / 业务名 / UI brand / route / 色彩 / RBAC / eval baseline
5. **Step 3 PRD 取证 Step 2 中并行**

## 7. Step 2 conflict scan 中断状态 (新 CLI 需续上)

主 CLI 在派 5 sub-agent + Codex Round 1 时 PM 切换到 reset planning · 中断:

**已收 (4/5 sub-agent)**:
- ✅ 架构层 (类 1/2/3/4/11) — 7 处 dirty
- ✅ 数据层 (类 5/12) — 数据形态 OK
- ✅ 指令层 (类 1/6/7) — 3 套 LLM caller + 多 active decision 没回写
- ✅ 命名路由层 (类 8/9/10/16) — compliance/compli dual-id 漂

**未收**:
- ❌ 生产同步层 sub-agent (类 0/13/14/15)
- ❌ PRD 取证 sub-agent
- ❌ Codex Round 1 全 17 类

**新主 CLI 任务**:
1. 重派以上 3 任务 (用 `docs/reset/codex-mesh-protocol.md` §4 template)
2. 整合 4+3 sub-agent + Codex Round 1 → conflict register v1 (写 `docs/audit/conflict-register-v1.md`)
3. 给 PM 拍板 → GO Phase A

## 8. 重要发现 (走歪具体表征)

新 CLI 必须 hold 住的 5 大表征 (北极星 doc 详):

1. **`shared/llm/` 已建 (Stage E.3) · 0 agent 用** · `agent_report._build_llm_caller` 第 4 套硬编 OpenAI · CLAUDE.md §3.1 仍写 "shared/ 没 llm_caller" stale
2. **6 workspace 0 个真 4 gate** · grep `liveData` 全 repo 0 命中
3. **`compliance` vs `compli` dual-id 全栈分裂** · `web/src/lib/auth/agent-id.ts` 是补丁映射
4. **`agents.ts:46-47` 仍持 Letterpress legacy color** (`--color-ink` `--color-brass`) · 违 §7
5. **CLAUDE.md §1 4 角色 vs §4 5th "策略经理" 文案漂** · backend `risk_manager` 是真

## 9. mesh + Codex 协作 (新主 CLI 必读 · 详 codex-mesh-protocol.md)

- Codex = cross-AI peer · 不 worker · 不读 worktree · 不直接 push
- 4 插入点: pre-dispatch draft / post-DONE review / arbitration / periodic audit
- 4 类 commit signal: `CODEX-DRAFT-* / CODEX-REVIEW-*-VERDICT / CODEX-ARBITRATION-* / CODEX-PERIODIC-AUDIT-*`
- 4 prompt template verbatim 在 `docs/reset/codex-mesh-protocol.md` §4
- 主 CLI per worker 责任 8 件 (§9 同文档)

## 10. Phase A 7 worker 拆分 (详 phase-a-charter.md)

```
Week 1: A1 contracts + A2 shared infra (并行)
Week 2-3: A3 Channel pilot (依赖 A1+A2) + A5 design + A6 handoff + A7 PRD (并行)
Week 4-5: A4 5 子 thin adapter (依赖 A3 完)
Week 6: integration + Playwright cross-agent smoke
```

## 11. 工具 + Skill 复用

- `multi-cli-mesh` skill: 已有 mesh 框架 (scoreboard / mesh.json / decisions-log) · 直接用
- `start-mesh.bat` / 或我们新写的 `start-reset-mesh.bat` (桌面 · 一键启 worker windows)
- `contract-audit` skill: 跑 CLAUDE.md vs 仓库漂移
- `codex` skill: 跑 codex CLI
- `mem-search` skill: 翻历史 memory

## 12. 红线 (新 CLI 触犯立即 stop the line)

- ❌ 不读 RESET_MASTER_PLAN.md + tier-1 reset docs · 直接做决策
- ❌ 任何 commit 没 `Signal:` trailer (validator 拒)
- ❌ 改 web/* 没 PRESERVES + NEW-DOM + SMOKE-PASS trailer
- ❌ active decision 改了不回写 CLAUDE.md
- ❌ 给 PM 估时 (容易翻车 · PM 已多次表达过)
- ❌ 凭模糊印象做决策 (compression 后必走恢复协议 · 见 CLAUDE.md §14)
- ❌ Codex DISAGREE 自决 MERGED · 必 escalate PM
- ❌ **任何迭代未同步更新 `docs/reset/state-snapshot.md`** (PM 2026-04-29 加 · 见 CLAUDE.md §14.1)

## 13. 当前 git state (2026-04-29 21:XX +08:00)

- main: 最新 sync 含本次 reset handoff commit (Signal: `RESET-HANDOFF-PREPARED`)
- chore/l0-infra: same as main
- 11 个 worktree (mesh.json) · 大多 idle
- ECS: 同步 main · backend 已 restart 用新 LLM keys

## 14. 给新 CLI 的"我理解当前状态" commit 模板

```markdown
chore(resume): NEW-MAIN-CLI-RESUMED · 我理解当前状态

产品 north star: <verbatim 复述 · 不缩>
6 Agent 闭环路径: <verbatim 复述>
走歪表征 top 5: <list 5 条>
当前 Phase: <Phase A · Step 2 conflict scan 中断状态 · 待续>
PM 已拍板 5 件: <列 5 条>
Codex 4 插入点: <列 4 条>
Phase A 7 worker: <列 7 条>
我下一步动作: <具体 1-2 条 · e.g. "重派 3 个 sub-agent 续 Step 2 + fire codex Round 1">

Signal: NEW-MAIN-CLI-RESUMED
```

PM 看 commit 内容 verify · 没漂 → GO · 漂了 → 退回让你重读 reset docs。

---

**End of handoff**. Welcome aboard.
