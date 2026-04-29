# State Snapshot · Reset 工程现状

> 本文件 timestamped 段落 append-only · 主 CLI 每 PM checkpoint / worker DONE / 阶段转换 / **每次迭代** 时必须更新。

## 更新硬规 (PM 2026-04-29 立)

**Reset 工程任何迭代 · 无论大小 · 必须同步更新本文件**。

**触发清单**:
- 任何 worker DONE signal cherry-pick → 主 CLI 同 commit 加段
- 任何 codex review 出 verdict → 主 CLI 写 audit doc 时同更
- 任何 PM 拍板 / decisions-log Q-NNN → 主 CLI 同更
- 任何 cleanup batch / fix / refactor commit → 主 CLI 同更
- 任何阶段转换 (Phase A → Phase B / Week N → Week N+1)

**段格式**:
```markdown
## YYYY-MM-DD HH:MM · <事件 一行>

### What happened
- <list>

### Triggered by
- <PM / worker-XX / codex review / scheduled / 自发>

### State change (delta)
- <key change · old → new>

### Next
- <implied next 1-2 step>
```

**违反 = stop the line**: 任何触动产品 / 架构 / 决策的 commit 未同步本文件 · 主 CLI 必须 amend / 补 commit。

**意义**: 本文件 + decisions-log = 长周期工程的 ground truth · compression / 新 CLI / 未来的我 全靠它还原。本文件漂 = reset 工程迷失。

---

---

## 2026-04-29 (本批次 2) · Step 2 Charter 补 + 答 fresh CLI 8 题

### What happened
- fresh main CLI 启动后读完 6 reset docs · 提 8 个 critical 澄清 (17 类完整定义 / 4 sub-agent 输出在哪 / Step 2 flow / Codex Round 1 template / anti-bias rule 1 衔接 / PRD 取证 / register schema / 调度方式)
- 诊断: 前任 main CLI 写的 reset docs 仍有 4 处"心里有但没写出来"的 gap (compression 写法典型病)
- 修复: 新建 `docs/reset/step2-conflict-scan-charter.md` (Step 2 SOP self-contained · 含 17 类完整 + flow + schema + sub-agent template) + codex-mesh-protocol.md 加 §4.5 (Step 2 codex template) + §5.b (audit dir) + §6 引用 charter §2 · anti-bias-rules.md 加 §1.1 (fresh CLI 接手处理) · CLAUDE.md §14 必读列表加 step2 charter · RESET_MASTER_PLAN 文档地图加 step2 charter

### Triggered by
- fresh main CLI 提 8 题 verify reset doc self-containment (健康 verify 信号)

### State change (delta)
- 新文档: `docs/reset/step2-conflict-scan-charter.md` (10 节 · 含 17 类 SSOT verbatim)
- 编辑: codex-mesh-protocol.md / anti-bias-rules.md / CLAUDE.md / RESET_MASTER_PLAN.md
- reset 必读 docs 从 5 份 → 6 份 (加 step2 charter)

### Next
- commit + push · ECS sync
- 通知 fresh main CLI 重读 step2-conflict-scan-charter.md · 8 题应自答 · 然后 fire 6 路并行 (5 sub-agent + Codex Round 1)
- 沿用 anti-bias rule 1.1: 前任 main CLI 4 sub-agent 输出弃用 (compression 后未 verbatim 还原) · 重派

---

## 2026-04-29 · Reset 启动 · 由当前 main CLI handoff (本次迭代 · 遵守 §14.1 状态更新硬规)

### What happened
- 当前主 CLI 完成 reset 工程承接文档全集落地
- 写 8 份新 doc · 改 4 份 doc · 加 1 个桌面启动脚本
- PM 加 1 条新硬规 (§14.1 · state-snapshot 必须每迭代同步更新)

### Triggered by
- PM 2026-04-29 决议进 reset 长周期工程 + 加状态更新硬规

### State change (delta)
- 文档:`RESET_MASTER_PLAN.md` 新建 · `docs/reset/{north-star, phase-a-charter, phase-b-charter, codex-mesh-protocol, state-snapshot, anti-bias-rules}.md` 新建 · `docs/handoff/HANDOFF_TO_NEXT_MAIN_CLI_2026-04-29.md` 新建
- CLAUDE.md: 加 §14 (新 session 必读 + compression 恢复) + §14.1 (state-snapshot 实时更新硬规)
- 桌面: `C:\Users\Mr.S\Desktop\start-reset-mesh.bat` 一键启 main + A1 + A2 worker
- decisions-log: 待新 CLI 接手后写 PM 5 拍板 Q-NNN entries

### Next
- 当前 CLI commit `RESET-HANDOFF-PREPARED` + push + ECS sync · 然后 graceful shutdown
- PM 双击桌面 start-reset-mesh.bat → 3 cmd window 启 → 在 main CLI window 启 claude → paste resume 提示
- 新 CLI 走 NEW-MAIN-CLI-RESUMED 流程 verify

---



### 已完 (Phase B Cleanup batches 0-6 + 散修)

```
b73b15c security(redact): 批 0 · ECS handoff doc + decisions-log secret redact
523efd0 fix(demo): 批 2 · 4 demo坑修复 (forceMock + silent fallback × 3)
e2ec0c5 chore(cleanup): 批 1 · delete 38 dead files + agent-channel-session refactor
99650a9 refactor(routes): 批 4 · delete 8 dead backend routes
ddb565b refactor(framework): 批 5 · Gradio + form_filler + narrative_pipeline 退役
40d8b2c docs(sync): 批 6 · 11 处文档漂移修复
37ff24a chore(workspace): B-2 · dropdown click-to-fire across 4 workspaces
78d28d6 fix(workspace): B-banner · inline error → top banner (4 workspaces)
94e2e88 fix(report): B-cta · Report 删模板库 placeholder + 收紧 launch buttons
a9370a3 fix(pin-ref): B-pin · pin thumbnail real e2e fix
8f8e378 fix(report): EmptySkeleton 撑满 viewport · 修底部空白
97663e7 fix(report): handleApplyLaunch 真 fire SSE · 不再只切 UI 留主列空白
```

**安全**:
- 3 LLM key (DeepSeek / Tavily / DashScope) rotated 2026-04-29 · ECS .env 同步 · backend restart
- handoff doc + decisions-log:1272 + :2364 redacted
- ECS SSH password / Cloudflare tunnel / 5 demo passwords 仍未 rotate (PM 决议: 演示后再处置)

**production**: ECS 139.196.30.69 · domain liuye.me · main 分支 · 4 services active (nginx / cloudflared / lliuye-frontend / lliuye-backend)

### 在跑 (Step 2 conflict scan · 中断状态)

主 CLI 在派 5 sub-agent + Codex Round 1 时 · PM 切换到本文档 reset planning · 已收到的:
- ✅ 架构层 sub-agent (类 1/2/3/4/11) — 7 处 dirty 找到
- ✅ 数据层 sub-agent (类 5/12) — 数据 mock 形态分层 OK · evaluation 6 yaml 对齐
- ✅ 指令层 sub-agent (类 1/6/7) — 3 套 LLM caller 并行 + 多个 active decision 未回写 root CLAUDE.md
- ✅ 命名路由层 sub-agent (类 8/9/10/16) — `compliance` vs `compli` dual-id 全栈分裂 + 4 角色 vs 5 角色文案漂

**未收 / 中断**:
- ❌ 生产同步层 sub-agent (类 0/13/14/15) — 用户中断
- ❌ PRD 取证 sub-agent — 用户中断
- ❌ Codex Round 1 全 17 类 — 用户中断

**整合 conflict register**: 待新 main CLI 接手后完成 (调用上面 4 sub-agent 已收数据 + 重派剩余 + Codex Round 1)。

### 待启 (Phase A worker mesh + Codex 工具化)

- worker-A1 contracts (Week 1)
- worker-A2 shared infra (Week 1)
- worker-A3 Channel pilot (Week 2-3 · 依赖 A1+A2)
- worker-A4 5 子 thin adapter (Week 4-5 · 依赖 A3)
- worker-A5 Letterpress (Week 2-3 并行)
- worker-A6 6 Agent handoff contract (Week 2-3 并行)
- worker-A7 PRD 取证 + draft (Week 2-3 并行 · 与 PM 飞书协作)
- 工程化: `scripts/orchestrator/codex-peer.py` (Week 1-2 后期由主 CLI 抽空写)

### PM 已拍板 (本次 reset 启动)

1. **杜绝拖死 4 机制**: 强制输出 schema / ≤ 3500 词 / 单 issue 最多 2 round 辩论 / dissent 反增即 escalate PM
2. **Phase A/B 严切阶段**
3. **active decision 回写 root CLAUDE.md**: 谁改决策谁回写 + CI lint
4. **命名 SSOT 8 列单表**: agent_id / 中文 / 业务名 / UI brand / route / 色彩 token / RBAC role / eval baseline
5. **Step 3 PRD 取证 Step 2 中并行启动**

### 当前 mesh 状态

11 个 worktree · 见 `docs/handoff/mesh.json` + `py scripts/orchestrator/scoreboard.py`。

```
main · chore/l0-infra · 主 CLI (本次将交班 · Signal: RESET-HANDOFF-PREPARED 后关窗)
A1-inventory · feat/inventory-expand-A1 · idle (将复用为 worker-A1 contracts)
A2-contracts · feat/contracts-bootstrap-A2 · idle (将复用为 worker-A2 shared infra)
A3-prd · feat/prd-summaries-A3 · idle (将复用为 worker-A7 PRD)
其他 7 个 worktree (agent1/agent3/agent6/code-frontend-integration 等) · 长期 idle · 后续按需复用
```

### 5 项 dissent 已闭环 (Phase A 启动前不再争辩)

- 命名 8 列 (PM 选 8) ✓
- Phase A/B 切阶段 (PM 选切) ✓
- 杜绝拖死机制 (PM 选 4 条全要) ✓
- 回写机制 (PM 选谁改谁回写) ✓
- Step 3 取证时机 (PM 选 Step 2 中并行) ✓

### 风险预警

- **decisions-log 长 2400+ 行** · compression 后新 CLI 难以全读 · 关键 active rule 必须回写 root CLAUDE.md (规则 3)
- **`shared/llm/`已建但 0 agent 用** · worker-A2 shared infra 启动时必须接管 + 6 agent 迁
- **Letterpress 12 consumer** · worker-A5 单 sprint · 视觉验收需 PM 看
- **Agent6 → Agent3 handoff data flow 没真做** · worker-A6 必须正面对待这个 pivot

---

## 2026-04-29 04:10 · Step 2 fire 7 路并行 (DISPATCHED · fresh 重派)

### What happened
- 新主 CLI 接手 reset 工程 · 走 anti-bias §1.1 → 弃用前任 4 sub-agent 高层总结 (chat-only · 不可信) · fresh 重派
- 一次 fire 7 路并行 (charter §3 + §9 verbatim):
  - 5 sub-agent (architecture / data / instruction / naming-route / production-shape) → docs/audit/sub-agent-step2-round1/*.md
  - 1 PRD 取证 sub-agent (Step 3 范围 · Step 2 中并行启) → docs/audit/prd-evidence-frozen.md
  - 1 Codex Round 1 background (codex-mesh §4.5 template · 独立扫全 17 类 · 不见 sub-agent 输出) → docs/audit/codex-step2-round1.md
- audit dir docs/audit/sub-agent-step2-round1/ 已建

### Triggered by
- PM 2026-04-29 答 fresh CLI 8 题 → 新加 docs/reset/step2-conflict-scan-charter.md (10 节 · 17 类 SSOT + flow + schema + sub-agent template + Codex template + PRD 取证 + 退出标准)
- codex-mesh-protocol.md 加 §4.5 (Step 2 专用 Codex template) + §5.b (Step 2 audit dir) + §6 引用 SSOT
- anti-bias-rules.md 加 §1.1 (fresh CLI 接手处理 · 前任未 commit sub-agent 输出弃用)

### State change (delta)
- Step 2 状态: 中断 (handoff §7) → IN-FLIGHT (fresh 重派 · 7 路并行)
- 前任 4 sub-agent (架构层/数据层/指令层/命名路由层): chat-only summary → 视为不存在 (per anti-bias §1.1)
- audit dir: 不存在 → docs/audit/sub-agent-step2-round1/ + docs/audit/{codex-step2-round1, prd-evidence-frozen, conflict-register-v1}.md (后 3 个待 fire 完落)

### Next
- 6 sub-agent foreground 全 done + Codex background notification → Read 7 份 audit doc
- 合成 conflict-register-v1.md (charter §8 schema · Cat / file:line / 证据 / Owner-Phase A worker / Keep-Revert-Rewrite · 含 dissent appendix per anti-bias rule 4)
- Commit STEP-2-CONFLICT-REGISTER-V1-PREPARED + 通知 PM 拍板
- PM 拍板 (Signal: STEP-2-PM-RULED) → 进 Step 1 Phase A worker mesh

---

(下次更新模板)

## YYYY-MM-DD · <事件>

### Worker 状态变更

### 决策变更

### 风险预警
