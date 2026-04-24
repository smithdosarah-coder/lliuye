# Session Handoff · 2026-04-25 · Phase 3-Final Planned

> 本文档是 2026-04-25 主 CLI（重开前写的）给下任主 CLI 的**交班脑图**。
> 新 main CLI resume 后读本文 + `AGENT_IDENTITY.md` 清单所有文件 → 100% 接替。
> 本文档是 PRD 级文档，不是会议纪要。如发现 gap，读源文件反推。

---

## §0. 一眼 Verdict

- **Batch 2 Product Hardening**：🟢 4/4 APPROVED + merged（data-foundation `271eb6f` · code-arch `8b66bd2` · code-urgent `bc75ed1` · evaluation `c2776b4`）+ closeout `5cf87c9`
- **Mesh 大清理**：🟢 12 worktree + 12 branch 删干净 commit `996b170`（Q-031）
- **Batch 3 (Agent2 窄 scope) 已 dispatch**：commit `f950b40 · Signal: BATCH-2-DISPATCHED-OBSOLETE-BY-PHASE-3-F`——**被本任升级推翻** · 需要新主 CLI **revert 或整合进 Phase 3-F 轨 8**
- **Phase 3-Final (P3F) 规划已锁**：本文档是 scope + 执行拓扑 · 未 dispatch · 等新主 CLI 写 8 onboarding + kickoffs
- **核心转向**：从"Agent2 窄硬化"升级到"**DoD 倒推 · 全产品交付银行前完整化**"· 8 轨并行 · 10-15 天工期（用户明示"不要在意时间"）
- **用户 PM 视角**：产品要**对外交付银行客户 RFP 级别** · 当前 DoD L3 POC 30%+（最大 gap）· Phase 3-F 后要推到 L3 85%+ L2 95%+ L1 90%+

**新主 CLI 接手后第一件事**：读本文档 §0-§9 全部 + 执行 §7 首 24 小时 playbook。

---

## §1. 当前仓库状态 · 2026-04-25

### 1.1 git log 核心 commit 链（chore/l0-infra）

```
f950b40 docs(batch-3): dispatch · 3 onboarding + kickoffs · Agent2 风控硬化   ← 本任 dispatch,被 P3F 升级推翻,见 §7 处理策略
996b170 chore(mesh): Batch 2 residual cleanup · 12 worktree + 12 branch removed · Q-031
5cf87c9 docs(batch-2): closeout · Q-030/A-030 + DF-V2-4 threshold polish
c2776b4 Merge feat/evaluation: Batch 2 real baseline + EV-12 consistency + Agent1/5 metrics APPROVED
bc75ed1 Merge feat/code-urgent: Batch 2 evidence-chain frontend APPROVED
8b66bd2 Merge feat/code-arch: Batch 2 Agent1/5 external search capability APPROVED
271eb6f Merge feat/data-foundation: Batch 2 Phase 2 Agent4 alert-pool mock APPROVED
56ccc5e docs(handoff): session-2026-04-24 · Batch 2 dispatched + 4-worker handoff brain-map
```

### 1.2 mesh.json 现状（post-cleanup）

**活跃 worktree（4）**：
- `main` · chore/l0-infra · 主 CLI 所在
- `agent1` · feat/agent1-productize · frozen:true · 30 commit 未合
- `agent3` · feat/agent3-productize · frozen:true · 11 commit 未合
- `agent6` · feat/agent6-v16 · frozen:true · 20 commit 未合

**frozen_branches_no_worktree（7）**：
- feat/agent-workspaces-v2 · feat/alert-codex-fusion · feat/compliance-codex-fusion
- feat/credit-mock-endpoint · feat/canvas-mode-toggle · feat/shell-free-drag · feat/chat-wechat-style

**Mesh 额外物理残留**（可忽略 · 不在 mesh.json 注册）：
- `demo-evaluation` 物理目录锁（Windows 文件锁 · 用户需手动 rm）
- 7 个 `credit_report_agent_work-<name>` 前端 worktree（git worktree list 可见 · 不占 mesh 标签）

### 1.3 DoD 5 层当前打分（post-Batch 2）

| 层 | 意义 | Batch 1 前 | Batch 2 后 | Phase 3-F 目标 |
|---|---|---|---|---|
| L0 工程基础 | 能运行吗 | 65% | **75%** | 90%（补 L0-12 P95 + L0-13 运维） |
| L1 Demo 完整 | 客户一眼懂吗 | 55% | **60%**（Evidence UI 前端化加分） | **90%**（L1-3 可视化 4 条全解 + L1-4 导出 5 条全解） |
| L2 金融合规 | 合规官放行吗 | 60% | **75%**（reason_codes + QC + 占位符全解 · agent6 branch 里还有 L2-12/13/14） | **95%**（agent6 branch 里的 4 条 + L2-15 本地化 + 3 Agent reason_codes 字典文件） |
| L3 客户 POC | 真数据合理吗 | 30% | **45%**（真 baseline 落地 · EV-12 cross-agent + Agent1/5 deterministic upgrade 预留） | **85%**（agent6 L3-8 飞轮 + L3-11 6 模型卡 + L3-12 6 演示脚本 + L3-9 E2E + L3-10 3 截屏） |
| L4 商业交付 | 能签合同吗 | 10% | 10% | 10%（按客户启动 · 不是 P3F 目标） |

**核心 gap 在 L3（45%）** · Phase 3-F 主攻 L1 + L2 + L3。

### 1.4 Batch 2 产出快照（评估 baseline 落盘）

`evaluation/baselines/2026-04-26-real-run.md`（2026-04-24 跑）：
- **Agent6 报告** 🔴 FAIL（template_leakage_rate 0.775 · unfilled_marker_accuracy 0.625 · quality_score_total 68.6 ≥ 65 达标）
- **Agent3 授信** 🟢 PASS（四维评分 / Top-5 reason_codes / 红线 99%+）
- **Agent1 获客** 🟡 PARTIAL（precision@10 + recall@10 stub · Tavily 无 key fallback）
- **Agent4 预警** 🟡 PARTIAL（B1 fixture · 未消费 alert-pool · Q-030 预期漂移）
- **Agent5 合规** 🟡 PARTIAL（conflict 跑通 · Tavily 降级）
- **Agent2 riskctrl** 🟡 PARTIAL（5/10 · 5 pending 指标等 Phase 3-F 轨 8）

Agent6 FAIL 表面看像要紧急补，但**根因是模板×材料错配率**，Phase 3-F **不单独改 v16**（红区），而是通过 agent6 branch 20 commit 合流带来 Phase 2 模板扩展 + QC 四维强化来缓解。

---

## §2. 3 frozen worker 明细（激活条件 + 合流策略）

### 2.1 agent6 · feat/agent6-v16 · 20 commit 未合

**worktree**: `D:/claude code/demo-agent6`
**branch tip**: `4bf8361 window-close: Phase 2 APPROVED (99%) + idle for Phase 3`
**base（最后同步 chore/l0-infra）**: 通过 `3fd57df merge: upstream/chore/l0-infra for A-013 α kernel` 同步到当时的 α kernel · 后续 main CLI 已前进多步

**20 commit 按 DoD 条目归类**：

#### 🔴 极高价值 · Phase 1 finalize（L2/L3 对外交付核心资产）
| SHA | commit | 解 DoD 条目 |
|---|---|---|
| `33d6295` | docs(agent6): model card + demo script | **L3-11** Agent6 模型卡 · **L3-12** Agent6 演示脚本 |
| `e12805c` | docs(compliance): partners register + data classification | **L2-13** 合作机构清单 · **L2-14** 数据分级标签 |
| `ee936fe` | test(agent6): feedback E2E — 5 scenarios, all passing | **L3-8** 反馈飞轮 E2E |
| `8f1cd84` | feat(agent6): audit_log hook on /api/report/fill + /api/report/refine | **L2-12** 审计日志 jsonl |
| `a13d79b` | window-close: Phase 1 finalize approved | marker |
| `5acb74b` | chore(agent6): Phase 1 finalize READY-FOR-REVIEW | marker |
| `e83b9da` | ack(agent6): Phase 1 finalize onboarding absorbed | marker |
| `5fc9f28` | chore: window close marker | marker |
| `94c04f5` | docs(proposals): corporate regression acceptance spec | 提案 |
| `bd34288` | docs(decisions): rule-16 year-prefix 治本决策档 | 决策档 |

#### 🟡 中价值 · Phase 2 硬化
| SHA | commit | 解 DoD 条目 |
|---|---|---|
| `4bf8361` | window-close: Phase 2 APPROVED | marker |
| `7a38eed` | fix(agent6): merge upstream kernel α + rerun runner PASS | rebase |
| `3fd57df` | merge: upstream/chore/l0-infra for A-013 α kernel | rebase |
| `01333c3` | chore(agent6): Phase 2 READY-FOR-REVIEW | marker |
| `5a647fd` | docs(agent6): Phase 2 Task C CONDITIONAL 解封 | docs |
| `fab3be6` | chore(agent6): Phase 2 Task D · pending_metrics 对齐 A-013 | Q-013 对齐 |
| `fe567f4` | feat(agent6): Phase 2 Task C · 模板扩展 +2 脱敏样本 + adapter | 模板扩展（**可能缓解 L3 评估 template_leakage**） |
| `2691875` | feat(agent6): Phase 2 Task B · QC Blocker 四维强化 | L2-4 QC 强化 |
| `a41bf33` | feat(agent6): Phase 2 Task A · feedback round-trip closed loop | L3-8 反馈飞轮（和 ee936fe 互补） |
| `654a4c6` | ack(agent6): Phase 2 onboarding absorbed | marker |

**rebase 风险**：
- 20 commit 跨 Phase 1 + Phase 2 两个周期 · 最近同步 main 是 α kernel 时代
- 期间 main 前进了：Batch 1 code-arch（§3.2 工具域拆分 · `agent_report/evidence_pipeline.py` 变了）+ Batch 2（code-urgent 前端 Evidence UI + data-foundation Phase 2 alert-pool 等）
- **主要冲突面预测**：`agent_report/section_generator.py`（code-arch 加了 EvidenceFirstPipeline 基类继承） + `quality_scorer.py`（红区 · 禁动 · 需确认 agent6 branch 没碰） + `evaluation/runner/adapters/agent6_report.py`（H-A 时改过 + 本 branch 可能碰）

**合流策略**：
- Phase 3-F 轨 1 · 派 worker 做 rebase + 跑 pytest 验证 + 跑 v16 pipeline 对比跑分 < 1% 漂移
- 如果 rebase 冲突超过 2 文件 · worker 回 Q-033 askout · 主 CLI 裁决
- 3 天工期预估 · 允许 REJECT-V2 返工一轮

### 2.2 agent3 · feat/agent3-productize · 11 commit 未合

**worktree**: `D:/claude code/demo-agent3`
**branch tip**: `6c5820a window-close: Phase 2 Batch 1 approved (main CLI proxy · agent3 CLI unlaunched)`

**11 commit 按 DoD 条目归类**：

#### 🔴 极高价值 · DoD 硬指标
| SHA | commit | 解 DoD 条目 |
|---|---|---|
| `4107b16` | feat(agent_credit): L1-4/L2-15 local python-docx decision letter export | **L1-4** Agent3 docx 导出 · **L2-15** 客户数据本地处理 |
| `68985dc` | feat(agent_credit): L2-7/L2-8 standard reason codes — Top-5 derived per decision | **L2-7** Agent3 Top-5 reason_codes · **L2-8** 字典文件 |
| `596283f` | feat(agent_credit): L1-3 RiskRadar thin wrapper dispatching 4-dim radar by segment | **L1-3** Agent3 雷达图可视化 |
| `8f1a35c` | feat(agent_credit): L1-11 Agent6→Agent3 handoff button + 2 demo profiles | **L1-11** 跨 Agent 联动 handoff 按钮 |
| `14a4a34` | feat(evaluation): L3-1/L3-2 Agent3 baseline first run | L3-1/2 Agent3 evaluation（Batch 2 evaluation 轨已重做 · 此 commit 可能过期） |

#### 🟡 中价值 · 工程品质
| SHA | commit | 解 DoD 条目 |
|---|---|---|
| `6c5820a` | window-close: Phase 2 Batch 1 approved | marker |
| `d67576f` | chore(handoff): Phase 2 batch complete — ready for main CLI review | marker |
| `d221115` | feat(eval): Agent3 credit adapter (Phase B) — deterministic metrics online | evaluation adapter（Batch 2 已更新 · 可能冲突） |
| `c101597` | chore(handoff): ack A-004 + Phase 1 APPROVED — rebase onto chore/l0-infra clean | rebase marker |
| `23737c4` | test(agent_credit): L0 self-check — 16 tests + ruff-clean | L0 tests |
| `83cf560` | refactor(agent_credit): migrate severity to red/yellow/green, drop is_hard | schema refactor |

**rebase 风险**：
- 最后同步 main 是 c101597 (Phase 1 APPROVED clean)· 期间 main 前进 Batch 1/2
- **主要冲突面预测**：`agent_credit/advisor_formatter.py`（code-urgent Batch 1 Task A 改了接 financial_analyzer）+ `agent_credit/scoring_model_corporate.py`（code-urgent 改了 _score_financial）+ `evaluation/runner/adapters/agent3_credit.py`（Batch 2 evaluation 重写过）

**合流策略**：
- Phase 3-F 轨 2 · rebase + 保留 Batch 1 code-urgent 的 financial_analyzer 注入（关键！）+ 吸收 agent3 branch 的 reason_codes + docx 导出 + RiskRadar + handoff button
- 1-2 天工期
- 若 agent3 evaluation adapter 改动和 Batch 2 evaluation worker 的改动冲突 · 优先保 Batch 2（已落 main）· agent3 branch 只取业务代码改动

### 2.3 agent1 · feat/agent1-productize · 30 commit 未合

**worktree**: `D:/claude code/demo-agent1`
**branch tip**: `1fc9a64 window-close: Phase 1 APPROVED + idle for Phase 2 Batch 2`

**30 commit 按价值归类**：

#### 🔴 仅 1 条高价值 · 值得 cherry-pick
| SHA | commit | 解 DoD 条目 |
|---|---|---|
| `c408b3a` | feat(feedback): Agent1 Phase 1 Task D — D2 data-flywheel E2E loop | **L3-8** 反馈飞轮 Agent1 补 |

#### 🟡 中价值 · 可能已被替代
| SHA | commit | 备注 |
|---|---|---|
| `28d094a` | ready(agent1): Phase 1 productize — 4 Task done | marker |
| `9df1466` | feat(eval): Agent1 Phase 1 Task B — yaml 单源收敛 + β adapter fix | evaluation adapter（Batch 2 evaluation 已重写 · 可能过期） |
| `19fe4b2` | docs(agent1): Phase 1 Task A — redzone gap progress doc | docs |
| `fc412d3` | chore(channel): align handoff schema with enterprise_profile.md v1.0 | handoff schema |
| `0b6eca4` | feat(channel): handoff to Agent3 + UI buttons | L1-11（Agent1→Agent3 handoff · 与 agent3 的 8f1a35c 互补） |
| `dc4c148` | feat(channel): POST /api/channel/export_xlsx | L1-4 Agent1 xlsx 导出 |
| `54d207a` | feat(channel): candidate_profile schema + handoff contract | schema |
| `f3bd9b5` | feat(channel): signal diversity >=2 enforcement + eval config | Agent1 信号多样性 |
| `f430e7f` | docs(agent1): data classification for channel lookalike v1.0 | L2-14 Agent1 补 |

#### 🔴 低价值 · 放弃（Option 2 rebase 时代 · 已被 Batch 2 code-arch 替代）
- `6379ae7` / `c4af59d` Merge remote chore/l0-infra (rebase history · no content)
- `ecfe05a` / `d17fb8b` / `d53603c` ask Q-008/Q-009/Q-013 · 问题已解决
- `d41eb49` ack onboarding marker
- `85bcf40` / `0292b94` window-close + ready markers
- `f8a4c43` eval baseline 20260419（过期）
- `65dd432` fix channel Option 2 rebase（已被替代）
- `f500389` ack Option 2 rebase marker
- `55b7265` mesh CLI window close marker
- `a7d3134` Phase 2 Batch-1 complete marker
- `697f963` feat(eval): Option 2 code-side Agent1 runner adapter（已被 Batch 2 evaluation 重写）
- `1e58487` test(channel): Option 4 handoff contract E2E smoke（可能可复用）
- `2898c96` docs(proposal): Agent1 Phase 2 scope draft · 4 candidate workflows（docs · 可能有参考价值）
- `ad0b219` eval baseline 20260418 fix（过期）
- `798f34c` chore(l0): install dev deps + bootstrap（L0 级 · 已完成）

**合流策略**：
- Phase 3-F 轨 3 · **只做 cherry-pick**，不整体 rebase
- 必 cherry-pick：`c408b3a` 数据飞轮 E2E loop · `dc4c148` export_xlsx · `0b6eca4` Agent1→Agent3 handoff button + UI
- 选择性 cherry-pick：`f3bd9b5` 信号多样性（评估一下是否已被 Batch 2 code-arch Agent1 外搜吸收）· `f430e7f` data classification
- **丢弃**：Option 2 rebase 相关的 15 个 commit
- 0.5-1 天工期（不需要 rebase · cherry-pick 独立 commit 风险低）

---

## §3. 7 frozen frontend branch 明细（融合依赖顺序）

### 3.1 各 branch scope（独立功能）

| branch | 独立功能 | 解 DoD 条目 | main 当前缺件 |
|---|---|---|---|
| **shell-free-drag** | `PanelCanvas.tsx` + `Whiteboard.tsx` 组件本体 + PANEL_PIN drop zone + MessagePinHandle 拖拽双 MIME | L1-3 shell 交互基础 | `web/src/components/shell/PanelCanvas.tsx` 不存在 · `Whiteboard.tsx` 不存在（store 都在） |
| **canvas-mode-toggle** | `CanvasModeToggle` 组件 + ⌘⇧F hotkey + localStorage 持久化 + panel-layout-store clearAgent action | L1-3 shell 交互 | `CanvasModeToggle` 组件 0 命中 main |
| **chat-wechat-style** | ConversationPanel 类微信气泡 + dispatch 左侧线程分群组/私聊 + 假聊天 pickReply + typing dot | L1-3 dispatch IM 完整化 | ConversationPanel 存在但功能浅（dispatch 的群组/私聊分段缺） |
| **alert-codex-fusion** | AlertWorkspace Codex 融合 6 step：pin + queue + heat bars + CTA 5 步进度 + 左栏扫描范围/知识库上传/监测源 | **L1-3 Agent4 红黄绿盘** | AlertWorkspace 751 行 · 无 queue-heat / 无 CTA 5 步 / 无左栏 drop zone |
| **compliance-codex-fusion** | ComplianceWorkspace Codex 融合 6 step：mock 扩展 + shell drop zone + matrix drawer 左右对照纸 + 底部修订意见栏 + pin | **L1-3 Agent5 政策矩阵** | ComplianceWorkspace 757 行 · 无 matrix drawer / 无 advice bar / 无 dual drop zone |
| **credit-mock-endpoint** | `/api/credit/mock-session` endpoint · corp/small/retail 三板块冒烟 | L1-3 Agent3 后端 mock | `/api/credit/mock-session` 0 命中 main |
| **agent-workspaces-v2** | 5 agent archive hero redesign（riskctrl KS×AUC / compliance policy ticker / alert traffic light wall / credit dashboard / report pipeline）· net -126 行 replace | **L1-3 Agent2 KS 图表 + 其他 4 agent 视觉 polish** | RiskctrlWorkspace 976 行 · 有 36 处 KS/AUC/通过率匹配（有实现）但 hero band 形态不是 v2 |

### 3.2 融合依赖顺序（硬性）

```
Stage 1 · shell 基础组件（不依赖其他）
  └─ shell-free-drag（PanelCanvas.tsx + Whiteboard.tsx）
  └─ canvas-mode-toggle（CanvasModeToggle + hotkey）
  两者可并行 cherry-pick 合流 · 组件本体冲突概率低

Stage 2 · agent workspace 单 agent 增强（依赖 Stage 1）
  └─ alert-codex-fusion（AlertWorkspace 扩）
  └─ compliance-codex-fusion（ComplianceWorkspace 扩）
  └─ credit-mock-endpoint（credit 后端 mock + CreditWorkspace 消费）
  三者可并行 · 独立 workspace 无冲突

Stage 3 · dispatch IM 扩展（与上述独立 · 可和 Stage 1/2 并行）
  └─ chat-wechat-style（ConversationPanel 扩 + dispatch 线程分群组）

Stage 4 · 视觉 polish（最后合 · 因为它是 net -126 行替换型 · 合早了会被后面覆盖）
  └─ agent-workspaces-v2（5 agent hero band redesign）
```

### 3.3 Batch 2 EvidenceTrail 兼容策略（合流时必须保留）

Batch 2 code-urgent 在 6 个 `/archive/*/_components/*Workspace.tsx` 挂了 `<EvidenceTrail>`。7 前端 branch 基线是 2 days ago（Batch 2 之前），没这个挂载。合流时：

1. **rebase 到 chore/l0-infra 新 tip（含 Batch 2 bc75ed1）**
2. **手动解冲突** · 在每个 workspace 保留 EvidenceTrail 挂载 + 吸收 branch 的新功能
3. **spec check** · `web/tests/evidence-trail.spec.ts` + `highlight-card.spec.ts` + `unfilled-marker.spec.ts` 不能因融合失败
4. **编译闸门** · `cd web && npx tsc --noEmit` 0 error · `npm run build` 0 error

### 3.4 与 CLAUDE.md §7 platform shell v2 对齐

**重要对齐检查**：
- CLAUDE.md §7 明文 `--t-*` 功能色 · Canvas/Matcha/Dusk/Ink 4 主题 · Masthead 4 tab · Desk 左抽屉
- 7 branch 要 rebase 后**仍在 §7 spec 约束内**
- 任何偏离 §7 spec 的改动（如 Letterpress 老色/crimson 主题复活）→ 立即 REJECT

---

## §4. Phase 3-F · 8 轨详细 scope

### 4.1 轨 1 · agent6 解冻 + 合流

**worker 建议**：新建 `code-agent6-unfreeze` worktree（从 feat/agent6-v16 fork）
**scope**：
- Step 0: `git fetch origin chore/l0-infra && git rebase origin/chore/l0-infra`（预期冲突 2-4 文件）
- Step 1: 解决冲突 · 重点保留 Batch 1 code-arch 的 EvidenceFirstPipeline 基类继承 · agent6 branch 的 audit_log hook / 模型卡 / 飞轮 / 数据分级
- Step 2: 跑 `py v16_pipeline.py --source samples/经纬测绘_对公成稿A.docx --material samples` · 与 Batch 2 baseline 对比 quality_score_total 漂移 < 1%
- Step 3: 跑 `pytest tests/agent_report/ -v` 全绿
- Step 4: READY-FOR-AGENT6-UNFREEZE-REVIEW
- Step 5（主 CLI）: subagent pre-review · APPROVED 后 merge

**预期 Signal 链**：
- `AGENT6-UNFREEZE-ACK` → `AGENT6-REBASE-CLEAN` → `AGENT6-V16-REGRESSION-OK` → `READY-FOR-AGENT6-UNFREEZE-REVIEW`

**解 DoD 条目**：L2-12 审计日志 · L2-13 合作机构 · L2-14 数据分级 · L3-8 飞轮 E2E · L3-11 Agent6 模型卡 · L3-12 Agent6 演示脚本 · L2-4 QC 四维 · L3-1/2 Agent6 template_leakage 预期缓解

**风险**：
- v16 跑分漂移 · 缓解：红区（financial_analyzer / quality_scorer）禁动 · 回归失败 REJECT-V2
- rebase 超过 4 文件冲突 · 缓解：worker 回 Q-033 askout · 主 CLI 决策

**工期**：2-3 天

---

### 4.2 轨 2 · agent3 解冻 + 合流

**worker 建议**：新建 `code-agent3-unfreeze` worktree
**scope**：
- Step 0: rebase origin/chore/l0-infra
- Step 1: 解决冲突 · 重点保留 Batch 1 code-urgent 的 _score_financial + financial_analyzer 注入 · agent3 branch 的 reason_codes + docx + RiskRadar + handoff button
- Step 2: 跑 `pytest tests/agent_credit/ -v`
- Step 3: READY-FOR-AGENT3-UNFREEZE-REVIEW

**预期 Signal 链**：
- `AGENT3-UNFREEZE-ACK` → `AGENT3-REBASE-CLEAN` → `READY-FOR-AGENT3-UNFREEZE-REVIEW`

**解 DoD 条目**：L2-7 Agent3 reason_codes · L2-8 Agent3 字典文件 · L1-3 Agent3 RiskRadar · L1-4 Agent3 docx 导出 · L1-11 Agent6→Agent3 handoff button

**风险**：
- agent3 evaluation adapter 和 Batch 2 evaluation 冲突 · 缓解：保 Batch 2 evaluation
- `advisor_formatter.py` 重写冲突 · 缓解：worker rebase 时谨慎合并

**工期**：1-2 天

---

### 4.3 轨 3 · agent1 cherry-pick（无 rebase）

**worker 建议**：直接在 main worktree 上操作 · 不需要独立 worker CLI（主 CLI 代理即可）或新建 `code-agent1-cherry` worktree

**scope**：
- Step 0: 必 cherry-pick：`c408b3a` 数据飞轮 E2E loop
- Step 1: 必 cherry-pick：`dc4c148` /api/channel/export_xlsx
- Step 2: 必 cherry-pick：`0b6eca4` Agent1→Agent3 handoff button + UI
- Step 3: 选择性 cherry-pick：`f3bd9b5` 信号多样性 · `f430e7f` data classification（先读 diff 判断是否被 Batch 2 code-arch 覆盖）
- Step 4: 跑 `pytest tests/agent_channel/` · READY-FOR-AGENT1-CHERRY-PICK-REVIEW

**预期 Signal 链**：
- `AGENT1-CHERRY-PICK-START` → 3 个 cherry-pick commit → `READY-FOR-AGENT1-CHERRY-PICK-REVIEW`

**解 DoD 条目**：L3-8 Agent1 飞轮补全 · L1-4 Agent1 xlsx 导出 · L1-11 Agent1→Agent3 handoff

**风险**：低（cherry-pick 独立 commit · 冲突少）

**工期**：0.5-1 天

---

### 4.4 轨 4 · 前端整合（7 branch rebase + 融合）

**worker 建议**：新建 `frontend-integration` worktree · Codex 辅助脏活（大量 tsx 改动）

**scope**（按 §3.2 Stage 顺序）：

#### Stage 1（Day 1-2）：
- rebase `feat/shell-free-drag` · 合进来 PanelCanvas.tsx + Whiteboard.tsx
- rebase `feat/canvas-mode-toggle` · 合进来 CanvasModeToggle + hotkey
- 编译闸门 `tsc && npm run build`
- Signal: `FE-STAGE-1-SHELL-BASE-DONE`

#### Stage 2（Day 3-5）：
- rebase `feat/alert-codex-fusion` · 合进来 AlertWorkspace queue-heat + CTA
- rebase `feat/compliance-codex-fusion` · 合进来 ComplianceWorkspace matrix drawer + advice bar
- rebase `feat/credit-mock-endpoint` · 合进来 /api/credit/mock-session + CreditWorkspace 消费
- **每个 rebase 必须保留 Batch 2 EvidenceTrail 挂载**
- 编译闸门 + 跑 evidence-trail.spec / highlight-card.spec / unfilled-marker.spec
- Signal: `FE-STAGE-2-AGENT-WORKSPACE-DONE`

#### Stage 3（Day 6）：
- rebase `feat/chat-wechat-style` · 合进来 ConversationPanel + dispatch 线程分群组
- 编译闸门
- Signal: `FE-STAGE-3-DISPATCH-IM-DONE`

#### Stage 4（Day 7）：
- rebase `feat/agent-workspaces-v2` · 5 agent hero band redesign（最后合 · 因为 replace 型）
- **关键决策**：v2 hero 是否和 Batch 2 EvidenceTrail + Stage 2 的 Codex 融合功能兼容 · 不兼容则 cherry-pick 单 agent 部分
- Signal: `FE-STAGE-4-HERO-POLISH-DONE`

#### Stage 5（Day 8）：
- 跨 browser 手测（Chrome/Edge 主） · 5 主题切换全通 · 截屏留证 · Signal: `FE-STAGE-5-SMOKE-DONE`
- READY-FOR-FRONTEND-INTEGRATION-REVIEW

**解 DoD 条目**：L1-3 可视化 4 条全解（Agent1 信号时间线待确认是否在 chat-wechat-style · Agent4 红黄绿盘 · Agent2 KS 图表 · Agent5 政策矩阵）

**风险**：
- 7 branch 共同基线冲突 · 缓解：严格依赖顺序 · 每 stage 编译闸门
- v2 hero 和 Codex 融合互斥 · 缓解：先 Codex 再 hero · 冲突走 cherry-pick 策略
- L1-3 Agent1 信号时间线**不在这 7 branch 里确认** · 可能需要新写（见轨 7）

**工期**：7-8 天

---

### 4.5 轨 5 · reason_codes 字典补齐

**worker 建议**：主 CLI 亲做或新 worker · 纯文档类 · 低风险

**scope**：
- 新建 `docs/reason_codes/agent4_alert.yaml`（预警 Top-5 拒因）
- 新建 `docs/reason_codes/agent5_compliance.yaml`（合规 Top-5 违规点）
- 可选 `docs/reason_codes/agent1_channel.yaml`（获客筛选 Top-5）
- 可选 `docs/reason_codes/agent2_riskctrl.yaml`（风控 DSL 解释）
- 对标 FCRA AAN 标准（Fair Credit Reporting Act · Adverse Action Notice）
- Agent3 的 `agent3_credit.yaml` 已在 agent3 branch `68985dc`（轨 2 带进来）

**预期 Signal**：`REASON-CODES-YAML-DONE` → `READY-FOR-REASON-CODES-REVIEW`

**解 DoD 条目**：L2-7 / L2-8 Agent4/5（+可选 1/2）

**风险**：低

**工期**：1 天

---

### 4.6 轨 6 · L3 POC 证据链（E2E + 截屏 + P95 + 运维）

**worker 建议**：新 worker `poc-evidence` · **硬依赖轨 4 前端整合完成**（否则 E2E 跑不了完整 UI）

**scope**：
- Task A · Playwright E2E × 3 关键路径：
  1. Agent6 handoff → Agent3 决策 → Agent5 合规检查（跨 Agent 联动）
  2. Agent1 获客 → look-alike 匹配 → 候选导出
  3. Agent4 扫描 → 红灯客户台账导出
  - 脚本落 `web/tests/e2e/*.spec.ts` · 跑通 100%
  - Signal: `E2E-3-PATHS-DONE`
- Task B · 3 张关键截屏：
  - 每条 E2E 路径取 起点 / 过程 / 终点 3 张
  - 落 `docs/screens/{agent}/*.png`
  - Signal: `SCREENSHOT-3-PATHS-DONE`
- Task C · P95 load test：
  - 100 次采样健康检查端点 + 首字节
  - 脚本 `scripts/load_test.py` · 报告 `docs/perf/p95-2026-04-XX.md`
  - P95 ≤ 1.5s 闸门
  - Signal: `P95-LOAD-TEST-DONE`
- Task D · 运维文档：
  - `docs/ops/start.md` / `stop.md` / `monitor.md` / `rollback.md`
  - Signal: `OPS-DOCS-DONE`
- Final: `READY-FOR-POC-EVIDENCE-REVIEW`

**解 DoD 条目**：L3-9 E2E × 3 · L3-10 截屏 · L0-12 P95 · L0-13 运维文档 · L3-5 P95 首字延时

**风险**：
- E2E 跑需要完整前端 + 后端联调 · 缓解：轨 4 完成后再起本轨
- P95 可能超阈 · 缓解：先跑一次看数据 · 超阈则 Q-034 askout 讨论优化方向

**工期**：2-3 天实做 + 等轨 4 完成

---

### 4.7 轨 7 · 合规文档 + 剩余模型卡/演示脚本

**worker 建议**：主 CLI 亲做（纯文档）或 doc worker

**scope**：
- **L2-15**：`docs/data-classification.md`（已由 agent6 branch 提供基础 · 补齐本地化明文）
- **L3-11 其他 5 Agent 模型卡**：`docs/model_cards/{agent1,agent2,agent3,agent4,agent5}.md`（agent6 在 agent6 branch）
  - 每份模型卡：算法概览 / 输入字段 / 输出字段 / 评估指标（引 Batch 2 baseline） / 局限 / 对标（FCRA / 同盾 / 百融）
- **L3-12 其他 5 Agent 演示脚本**：`docs/demo_script/{agent1,agent2,agent3,agent4,agent5}.md`
  - 每份演示脚本：30 分钟标准演示流程 / 话术 / Q&A 预案
- **L1-3 Agent1 信号时间线前端补全**（如果 7 前端 branch 都不含 · 新写）
  - 新组件 `web/src/app/archive/channel/_components/SignalTimeline.tsx`
  - ~200 行 · 消费 Agent1 SSE 的 signal_timeline 字段

**预期 Signal 链**：`L2-15-DONE` → `MODEL-CARDS-5-DONE` → `DEMO-SCRIPTS-5-DONE` → `AGENT1-SIGNAL-TIMELINE-UI-DONE` → `READY-FOR-DOCS-COMPLIANCE-REVIEW`

**解 DoD 条目**：L2-15 · L3-11（5 agent）· L3-12（5 agent）· L1-3 Agent1 信号时间线

**风险**：低（纯文档 + 1 个前端组件）

**工期**：2-3 天

---

### 4.8 轨 8 · Agent2 硬化（原 Batch 3 规划 · 降级到一轨）

**scope**：**完全复用**本任已写的 `docs/onboarding/batch-3-data-foundation-agent2-samples.md` + `batch-3-code-arch-agent2-hardening.md` + `batch-3-evaluation-agent2-metrics.md` 三份 onboarding 内容，**只把 Batch 名改成 P3F 轨 8**，scope 不变：
- Task A · data-foundation 产 `data/mock/agent2-samples/loans.csv` + field_dictionary.md + README.md
- Task B · code-arch 做 Agent2 adapter 探针 + baseline_ruleset + LLM-judge + Agent1/5 stub 升 deterministic
- Task C · evaluation 跑 Agent2 真 baseline + 5 pending 指标 + 6 agent 总览

**预期 Signal 链**：与原 Batch 3 一致（只是 commit message 带 P3F 标签）

**解 DoD 条目**：L3-2/3 Agent2 evaluation 5 pending · Q-030 Follow-up Agent1/5 stub → deterministic

**风险**：同原 Batch 3（已经评估过）

**工期**：5-7 天（data 2.5 · code 3 · evaluation 2 ·串行合流）

**处理已 dispatch 的 commit**：
- `f950b40` 的 3 份 onboarding 保留不删
- 新主 CLI 在 §5 下的 Kickoff 文档里把原 Batch 3 ① ② ③ 段直接复用给 P3F 轨 8
- 如需要，新主 CLI 可以 amend `f950b40` 的 commit message 把 Signal 改成 `PHASE-3-FINAL-DISPATCHED` · 或单独新 commit 引用

---

## §5. 执行拓扑 · 阶段化并行

### 5.1 并行图

```
Day 1                                     Day 15
├─ 轨 1 agent6 [━━━━━]
├─ 轨 2 agent3 [━━━]
├─ 轨 3 agent1 cherry [━]
├─ 轨 5 reason_codes [━━]
├─ 轨 7 文档 [━━━]
├─ 轨 8 Agent2 data [━━━]→ code [━━━]→ eval [━━]
│
│             ↓ 轨 1/2/3 合流后
├─ 轨 4 前端整合 [━━━━━━━]
│             ↓ 轨 4 完成后
├─ 轨 6 E2E + P95 [━━━]
```

### 5.2 合流顺序（master branch: chore/l0-infra）

**Wave 1**（轨 1/2/3 · 同时 APPROVE 时）：
1. agent3（最小风险）
2. agent1 cherry-pick（最小增量）
3. agent6（最高价值但风险略高）

**Wave 2**（轨 4 前端整合 · 一次性合）：
4. frontend-integration（合 7 branch 结果）

**Wave 3**（轨 5/7/8 · 并行合）：
5. reason_codes
6. 文档 + Agent1 信号时间线
7. Agent2 硬化

**Wave 4**（轨 6 · 最后合）：
8. POC evidence

---

## §6. 新主 CLI 首 24 小时 Hour-by-hour Playbook

### Hour 1 · Resume + 读完本文档

1. 用户粘万能指令「读 AGENT_IDENTITY.md 和里面列的所有文件」
2. 新主 CLI 自动 resume-agent skill
3. 本 handoff doc 已在 AGENT_IDENTITY.md 引用清单 §2 位置
4. 读本文档 §0-§9 全
5. 跑 `py ~/.claude/skills/multi-cli-mesh/scripts/orchestrator/scoreboard.py` 看 mesh 状态
6. 跑 `py ~/.claude/skills/contract-audit/scripts/audit.py` 漂移扫描
7. 回报用户：Resume 完 + Phase 3-F 理解确认

### Hour 2 · 处理 f950b40（原 Batch 3 dispatch）

**决策**：保留 `f950b40` 不 revert（避免 git 历史污染）· 原 3 份 onboarding 内容直接作为 P3F 轨 8 的输入。

**动作**：
- 不 revert
- 在新 `docs/handoff/phase-3-final-kickoffs.md` 里把轨 8 kickoff 直接引用原 Batch 3 那 3 份 onboarding

### Hour 3-5 · 写 8 份 onboarding

路径：`docs/onboarding/p3f-{agent6-unfreeze,agent3-unfreeze,agent1-cherry,frontend-integration,reason-codes,docs-compliance,poc-evidence}.md`（轨 1-7）+ 复用原 `batch-3-*` 三份（轨 8）

每份 onboarding 对照本文档 §4 对应轨的 scope · 按 Batch 2 onboarding 格式（Task 清单 + 硬指标清单 + 红线 + 工期）展开。

### Hour 5-6 · 写 kickoff prompts

路径：`docs/handoff/phase-3-final-kickoffs.md`

每轨一段 kickoff prompt · 包含：
- ACK step（`PHASE-3-FINAL-<TRACK>-ACK`）
- 强制前置（读 onboarding + decisions-log Q-032 + 本 handoff doc）
- 执行顺序
- 红线
- Final Signal

### Hour 6 · 更新 mesh.json

- agent1/3/6 frozen:true → 新状态 `unfreeze_in_progress:true`
- 新增 worker slot（7 个新 worktree · 按 §4 轨 1-4/6 · 轨 5/7 主 CLI 代理不占 slot · 轨 8 复用 3 worker）

### Hour 6-7 · Commit `Signal: PHASE-3-FINAL-DISPATCHED`

body 附：
- 8 轨 onboarding 路径
- kickoffs 路径
- 预计工期
- 引用 Q-032 / 本 handoff doc

### Hour 7 · 起 patrol + 告诉用户粘 kickoff

1. `Skill(skill="loop", args="5m ...")` 起 patrol
2. 告诉用户：
   - Wave 1 可粘 4 个 kickoff（轨 1/2/3/8 的 data-foundation 部分）
   - Wave 2 等 Wave 1 合完再粘（轨 4/5/7/8 code-arch）
   - Wave 3 最后粘（轨 6/8 evaluation）

### Hour 8+ · Patrol + 响应

- 每 5 min patrol 扫新 READY
- 每 READY 起 subagent pre-review
- APPROVED → merge
- REJECT-V2 → 写 v2 onboarding 返工

---

## §7. 红线 + 风险 + 用户协作 feedback（本任沉淀）

### 7.1 红线（主 CLI 自守）

- ❌ 不在 worker 分支上动代码
- ❌ 改红区（`financial_analyzer.py` / `quality_scorer.py` / `truth_fill.py` / `web/src/lib/store/*`）必须 RFC
- ❌ 不主动 spawn worker CLI（用户双击 bat 或手开）
- ❌ 不改 `demo-start.bat`（用户服务器脚本）
- ❌ **不删 `~/.claude/skills/multi-cli-mesh/scripts/mesh_launch.py`**（脆弱 shim · bat 靠它跑）
- ❌ 不绕 decisions-log 直接批示
- ✅ 批示必须 commit trailer 带 `Signal: XXX`（单行 · 多 signal 拆 commit）
- ✅ 红线 4 硬闸：GO + TaskCreate + 方案先行 + Authorized-By trailer（针对演示型前端 / 红区）

### 7.2 Phase 3-F 特有风险

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| agent6 rebase 冲突 > 4 文件 | 中 | 高 | Q-033 askout · 允许 REJECT-V2 返工 |
| v16 pipeline 跑分漂移 > 1% | 中 | 高 · 红区破线 | 立即 revert agent6 合流 · 根因分析 |
| 前端 7 branch 融合冲突过大 | 高 | 中 · 延期 | 严格依赖顺序 + 每 stage 编译闸门 + Codex 辅助脏活 |
| E2E × 3 路径跑不通 | 中 | 中 | worker 回 Q-034 askout · 允许用 Mock 模式跑 |
| Agent1 信号时间线 7 branch 里都没有 | 中 | 低 · 需新写 | 轨 7 兜底（200 行组件） |
| 工期超 15 天 | 中 | 低 · 用户明示不在意 | 维持 scope 不缩 |

### 7.3 用户协作 feedback（本任沉淀 · 新主 CLI 必读）

- **说人话**：短 + verdict 先行 + 不啰嗦（本任被纠偏 4 次 · 用户多次说"说人话""具体点"）
- **不要挂机**：主 CLI 要主动推进 · 不要被动等 signal（被纠偏 2 次）
- **子 CLI 利用起来**：有活派给 worker / subagent · 不自己闷头干脏活（被纠偏 3 次）
- **scope 对齐**：scope 模糊先问一个具体问题 · 不猜
- **方案先行**：中等以上任务动手前先方案 · 不接受无方案直接编码
- **形态真实**：mock 要像真实客户材料（文件夹 + 异构 pdf/xlsx/docx + 扫描件 + 命名混乱 + 三方数字矛盾）· yaml 形态 = REJECT-V2（Q-028 触发过）
- **环境边界**（CLAUDE.md §3.5 反结果导向第 5 条）：mock 只给"稳态内部 context" · 不替 Agent 做本该外搜的工作
- **不谄媚**：方案有问题直接说 · 不"好的"
- **PM 视角**：本任最重要的教训 —— 不要被上任规划惯性（Agent2 硬化）束缚 · 用户真正要的是"对外交付银行 RFP 级别完整产品化" · 从 DoD 倒推判断优先级
- **回避决策 = 失职**：本任差点把 7 前端 branch 一句"冻结"带过 · 用户戳破"冻结啥用"· 深挖 7 branch 发现全是"做一半"关键产出 · 差点损失 500+ commit 前端工作

### 7.4 本任踩过的具体坑

1. **Context 预设**：Resume 后不要只读 AGENT_IDENTITY 就动手 · `docs/scorecard/dod-current-status-2026-04-24.md` + `docs/product/` 是产品真相，必读
2. **git worktree remove 在 Windows**：`--force` 对部分目录仍失败（文件锁） · 补 `rm -rf` 降级 · 仍失败的接受遗留，git 端 prune 后不影响（demo-evaluation 物理残留案例）
3. **subagent pre-review 节省主 CLI context**：Batch 2 流程证明有效（3 subagent 串行 review 节省 ~10k tokens）· Phase 3-F 应继续此模式
4. **CRLF warning**：Windows 写文件 Git 会报 CRLF·可忽略
5. **mesh.json 手工维护**：scoreboard 只读不写 · `cleanup_log[]` 字段是本任加的扩展 · schema 非官方 · 新主 CLI 可保留可精简

### 7.5 旁路资产（新主 CLI 知道即可）

- **`~/.claude/skills/multi-cli-mesh/scripts/mesh_launch.py` shim**（90 行）：前任主 CLI 补的 · bat 靠它跑 · 不在 git · 机器重装需重写 · 不动
- **桌面 bat 脚本**：
  - `start_claude.bat` · 单主 CLI 启动（**新主 CLI 就用这个**）· 已设 proxy + bash path + 自动更新 CC + cd 项目 + 跑 claude
  - `mesh-credit-agents.bat` · 多 tab 启动（依赖 mesh_launch.py）
  - `demo-start.bat` / `demo-stop.bat` · 用户服务器脚本 · 禁动

---

## §8. 历史决策锚点（Q-001 ~ Q-032）

**关键决策摘要**（新主 CLI 如需深究查 `docs/handoff/decisions-log.md` 全文）：

| Q # | 主题 | 关键结论 |
|---|---|---|
| Q-004 | handoff schema v1.0 | enterprise_profile.md 锚定跨 Agent handoff 字段 |
| Q-008/009 | agent1 rebase 冲突 | Option 2 · 最终放弃并入 Batch 2 code-arch |
| Q-013 | evaluation pending metrics 语义 | α kernel 白名单机制 |
| Q-023 | Batch 1 dispatch | 4 worker 并行（code-urgent/code-arch/data-foundation/evaluation） |
| Q-024 | evaluation 路径规范 | base_evaluator.py / cli.py 禁动 · adapter 续建 |
| Q-025 | rubric schema 兼容 | agent1-5 新 schema · agent6 双写 |
| Q-028 | data-foundation v1 REJECT-V2 | yaml 形态错 · 形态真实红线确立 |
| Q-029 | Batch 1 closeout + Batch 2 dispatch + DF-V2-13 测试豁免 | 4 轨分配 · 测试阶段脱敏名 OK · 对外演示前 PM 签 |
| Q-030 | Batch 2 closeout | 4 merge SHA · 3 follow-up 状态 · Batch 3 进入规划 |
| Q-031 | Mesh 大清理 | 12 worktree + 12 branch 清 · agent1/3/6 + 7 前端 branch 冻结（本任 Phase 3-F 规划推翻此冻结方案） |
| **Q-032** | **Phase 3-F 总规划**（本任新写） | **8 轨并行 · DoD 倒推 · 推翻 Q-031 档 2/3 冻结 · 激活 3 worker + 7 前端 branch** |

---

## §9. 签名 + 交接锚

- **本任主 CLI 签名**：chore/l0-infra @ 2026-04-25（Batch 2 closeout + Mesh 清理 + Phase 3-F 规划 · 用户准备重开主 CLI）
- **交接锚 commit**：本 handoff doc 附 `Signal: ORCHESTRATOR-HANDOFF-PHASE-3-FINAL-PLANNED`
- **Phase 3-F dispatch 锚（新主 CLI 写）**：`Signal: PHASE-3-FINAL-DISPATCHED` + body 引用本 handoff
- **性格 hint**：Opus 4.7 · 承担用户 4+ 次纠偏（说人话 / 具体点 / 不挂机 / PM 视角反推 / 冻结 vs 激活决策）· 善于 subagent 并行 · 被用户教会"product 完善 = 对外银行交付 RFP 级别"

---

## §10. 新主 CLI 快速验证清单（Hour 1 用）

Resume 完立即验证以下断言，任一不符立即告警用户：

- [ ] `git log --format='%h %s' -10 chore/l0-infra` · HEAD 应是 `f950b40`（或者本任 commit HANDOFF-PHASE-3-FINAL-PLANNED 之后的 SHA）
- [ ] `git worktree list` · 应看到 main + agent1/3/6 + 7 个前端 worktree
- [ ] `git branch --list 'feat/*'` · 应看到 agent1/3/6 + 7 前端 branch（10 个） · 不应看到 feat/code-urgent / feat/code-arch / feat/data-foundation / feat/evaluation / feat/agent2-productize / feat/agent4-productize / feat/platform-* （这些已删）
- [ ] `ls docs/onboarding/` · 应看到 3 个 batch-3-* 文件（本任已写 · 用作轨 8 输入）
- [ ] `ls docs/scorecard/` · 应看到 dod-current-status-2026-04-24.md + definition-of-done.md + GLOBAL.md + L0-baseline-2026-04-18.md
- [ ] `cat docs/handoff/mesh.json | grep '"name"'` · 应看到 main / agent1 / agent3 / agent6（4 个）+ `frozen_branches_no_worktree` 数组
- [ ] `cat docs/handoff/decisions-log.md | grep "## \[Q-"` · 应能看到 Q-032（本任新写）

如果以上有不符 · 可能是前任主 CLI（本任）commit 失败或者用户操作过 · 读 git log 反推状态。

---

**END OF HANDOFF DOC**
