# 全盘实施 Master Plan · 2026-04-27

> User 反馈 production demo "都是糊弄"·数据 panel 不切企业 · `[object Object]` · candidate 无 detail · 5 archive 仅 Channel 部分实装。系统性 ultrathink 后写本 plan · 不再 phased "看时间" · 全盘 deliver。

## 0. 真定位 vs 现状 (Master Gap Map)

PRD 期望 = 6 Agent 各按 v2 PRD-grade 实装 · 共享 KB/Search/Matcher 底座 · 5 user RBAC enforce · IM 真 tool calling · WebSocket 实时 · features-inventory 全 captures · regression smoke 全覆盖 · 客户走访可演示。

### 12 Gap 完整表

| # | Gap | 影响 | Stage |
|---|---|---|---|
| 1 | `[object Object]` candidate.signals 渲染坏 | crash · 已 Edit 修待 deploy | A |
| 2 | mock 单 const 不切 session | "切下拉无效" · user 反馈 | B |
| 3 | panel 全 import CHANNEL_SESSION 不接 props · radar/timeline/funnel 永远 mock | 数据呈现没关联 | B |
| 4 | 后端 SSE 只返 candidates · 不返 radar/signals/funnel | 前端无源填 panel | B |
| 5 | 候选企业不可点 detail · 没 onSelect / drawer | 体验残缺 | B |
| 6 | 5 archive Workspace 仅 Channel 部分实装 | 5/6 Agent 是空架子 | C |
| 7 | 6 Agent PRD 各自不同·只读了 Channel | 跨 Agent 业务理解缺失 | C 前置 |
| 8 | Agent2/3 后端 stub 不调 LLM · Agent4/5 KB_DEMO 锁 mock | "实装" 假象 | C |
| 9 | shared/kb_scan/ 共享底座 · 现状各 Agent 各管 | 重复实现 | D |
| 10 | 5 user RBAC enforce 缺·任意 user 能访问任意 Agent | 演示穿帮 | D |
| 11 | WebSocket 实时 IM · 当前 polling 单 turn · 没 thread persistence DB | IM 系统级假 | D |
| 12 | 6 Agent Word 导出·后端只有 xlsx | PRD 要求未达 | C |

---

## 1. Skill 用法决定

| Skill | 用法 |
|---|---|
| make-plan + writing-plans | 本 doc + per-Agent spec |
| dispatching-parallel-agents | sub-agent (Agent tool) 在 main session 派活 (不用 multi-cli-mesh worker · 减 user 维护负担) |
| systematic-debugging | per-Agent gap 调研 sub-agent 跑 |
| test-driven-development | 每 feature 先写 Playwright smoke spec · 后实装 |
| verification-before-completion | 每 commit 必 tsc + smoke + curl backend 验通 才 deploy |
| smart-explore | 跨 6 Agent 代码 token-optimized 探 |
| using-git-worktrees | 高风险大改 (e.g. shared/kb_scan/ refactor) 用 worktree 隔离 |
| brainstorming | 视觉 / 交互 task 前先 explore intent |

**不用 multi-cli-mesh worker** — user 一人维护多 CLI 累 · 改 sub-agent。

---

## 2. 4-Stage Execution Plan

### Stage A · 紧急止血 + Foundation (1-2 sessions)

**目标**：production crash 修 + 后续工作 spec ground truth

- [ ] **A.1 `[object Object]` 修 deploy** (15 min) — `signals.map` 取 .title/.label · 已 Edit 待 commit
- [ ] **A.2 写本 master plan doc** (30 min) — 本文件
- [ ] **A.3 features-inventory.md 扩 F-009 ~ F-040** (1-2 hr) — 全 6 Agent + IM + Auth + Layout features 全 captures · 含 selectors / smoke / introduce/regress commits
- [ ] **A.4 shared types/contracts** (1 hr) — `docs/contracts/workspace-state-protocol.md` · `docs/contracts/im-protocol.md` · `docs/contracts/auth-protocol.md`
- [ ] **A.5 6 PRD 全 read 摘要** (1 hr) — 每 Agent PRD 关键 capability 摘出 · 写 docs/contracts/agent-{name}-spec.md (sub-agent 派活基础)

### Stage B · Channel Workspace 完整 architecture (2-3 sessions)

**目标**：Channel/Scout 一个 Workspace 真 PRD-grade · 作为其他 5 Agent 模板

- [ ] **B.1 mock_sessions.ts** — 扩 3-5 个 mock 标杆企业 · 各自完整 ChannelSession (radar / signals / candidates / funnel 都不同)
- [ ] **B.2 panel state hoist** — ChannelWorkspace 加 useState selectedSession + selectedCandidate · 5 panel function 接 props (Hero/Funnel/Radar/Candidates/SignalTimeline) · 删 import CHANNEL_SESSION
- [ ] **B.3 下拉切 session 真切全 panel** — onSelectSession setSelectedSession(id) · panel 全跟着切
- [ ] **B.4 候选 click → candidate detail drawer** — 右抽屉展开 · 该候选的 derive radar (8 维) + 该候选的 signal timeline
- [ ] **B.4b 候选 detail · "为什么像" 匹配维度明细** (gap 4 · PRD 1.2 用户故事核心) — drawer 内独立区 chip 列表 · 显示该候选 vs IdealProfile 各维度匹配 (e.g. "营收 5000 万 ✓ 匹配 P50 ±20% / 行业 SaaS ✓ 命中标杆 / 地域华东 ✓ / 阶段 B 轮后 ✓") · 每 chip 含命中证据来源 (signal id / KB ref)
- [ ] **B.4c 候选 detail · Top3 产品推荐 + 切入话术** (gap 5 · 客户经理"打开电话即用") — drawer 内独立区 · 3 张产品卡 · 每卡 含 (产品名 / 适配评分 / 切入话术 1-2 句 · 含客户姓名占位 + 关键卖点) · 复用 v1 channel_rules + scoring 评分逻辑
- [ ] **B.5 后端 SSE 扩** — `/api/channel/run` done event 加 `radar` `signals` `funnel` `match_dimensions` `product_recommendations` `pitch_scripts` 字段 · 让前端真填全 panel
- [ ] **B.5b 前端 wire 真 SSE 全字段** (gap 3 · 不只 candidates name) — Radar/Candidates/SignalTimeline/FunnelStrip 都消费 live SSE 数据 · livePayload 完整覆盖 mock · live mode 时 panel 全切到真后端数据
- [ ] **B.6 文件上传 KB** (PRD v2 必须 · gap 1) — ChannelHero 加 3 类文件上传区 (客户名录 / 政策 / 行业指引) · 后端 `/api/channel/upload_kb` 存 + 解析 · 返 KB id
- [ ] **B.6b IdealProfile 画像抽取** (gap 2) — 上传完成后 · 前端 call `/api/channel/profile` POST {kb_id} → LLM 解析 KB 抽 IdealProfile (industry / scale / geo / stage / 12 维特征) → 前端显示"理想客户画像卡" → user 确认后才"开始扫描" → 走 `/api/channel/run` SSE
- [ ] **B.7 Word 导出** (gap 6) — 后端 `/api/channel/export_docx` (python-docx) · 前端 button click 下载 · 含 Top10 候选 + 匹配明细 + 产品 + 话术 全套
- [ ] **B.8 5 Playwright smoke** — channel-mock-switch / channel-live-search / candidate-detail-drawer (含匹配明细 + 产品话术) / channel-upload-kb-profile / channel-export-docx
- [ ] **B.9 features-inventory enrich** — F-channel-* 全 entries

### Stage C · 5 Agent 复制 Channel pattern (5-7 sessions · 各 Agent 1 session)

**目标**：Forge / Credit / Alert / Compli / Report 各按 PRD v2 实装 · 复用 Channel architecture

每 Agent 一个 sub-agent 派活 (Task Prompt template)·sub-agent 输出代码·主 CLI review + merge：

- [ ] **C.1 Agent6 Report** — v16 wire + 文件上传 + 字段抽取 + Word 导出 + panel state hoist + 候选/材料 detail · sub-agent dispatch
- [ ] **C.2 Agent3 Credit** — 后端补 LLM (现 stub) + 4 维评分 + 红线判定 + panel hoist + Word 导出 · sub-agent dispatch
- [ ] **C.3 Agent4 Alert** — KB_DEMO 解锁稳定 (Tavily fallback / 缓存) + 红/黄/绿榜单 + panel hoist · sub-agent dispatch
- [ ] **C.4 Agent5 Compli** — 政策事件驱动 + 业务矩阵扫 + KB_DEMO 解锁 + panel hoist · sub-agent dispatch
- [ ] **C.5 Agent2 Forge/Riskctrl** — 后端补 LLM (现 stub) + DSL 真生成 + 真回测 + panel hoist · sub-agent dispatch
- [ ] **C.6 5 Agent 各 5 Playwright smoke** — 共 25 spec
- [ ] **C.7 features-inventory 全 enrich** — 6 Agent 各 5-8 features

### Stage D · 系统级基础 + 收尾 (3-4 sessions)

- [ ] **D.1 5 user RBAC enforce** — backend `/api/auth/login` 真 JWT + frontend AuthGate enforce ACCESS matrix · user 没权限 redirect /403
- [ ] **D.2 IM WebSocket 实时** — 后端 `/ws/im` (FastAPI WebSocket) + 前端 dispatch 用 WebSocket replace polling · 多 user 1:1 真聊
- [ ] **D.3 thread persistence DB** — sqlite or 简单 jsonl · `/api/im/threads` `/api/im/messages/{thread_id}` 后端 + 前端真 fetch
- [ ] **D.4 IM tool calling** — `/api/im/send` 升级 LLM function calling · 检测 "找/搜/扫" 真触发对应 agent endpoint · 结果回 thread (不只 chat)
- [ ] **D.5 shared/kb_scan/ 抽共享底座** — 6 Agent 共享 KB · SearchProvider · Matcher (现各 Agent 各管 · 重构合并)
- [ ] **D.6 客户走访 dry run** — 完整 e2e 走一遍 5 user × 6 Agent × 关键 path
- [ ] **D.7 ECS production verify** — features-inventory 全 entries 都 production 验证 · regression smoke 全跑通
- [ ] **D.8 走访话术 + commercial-readiness** — 已有 docs/commercial-readiness.md · 更新成最终版

### 总工程: ~12-18 sessions · 不分 day · 不算 wall clock · 一直推到 deliver。

---

## 3. Sub-Agent 派活协议

### 派活 Task Prompt 6 要素

每 sub-agent 派活必须含:
1. **目标 (Goal)** — 1 句话 deliver 什么
2. **验收标准 (Acceptance)** — Playwright smoke pass / curl 验通 / inventory 加 F-XXX
3. **边界 (Boundary)** — 只改哪些 file · 不改哪些 (PRESERVES list)
4. **依赖 (Dependencies)** — 哪些 contract / shared types / endpoint 已就位
5. **Spec ref** — docs/contracts/agent-{name}-spec.md 路径
6. **Trailer 协议** — commit message 必含 `RESTORED:` `PRESERVES:` `NEW-DOM:` `SMOKE-PASS:`

### Dispatch 模板 (复制粘贴用)

```text
项目: D:/claude code/credit_report_agent_work · 当前分支 chore/l0-infra HEAD <hash>

GOAL: <1 句话 deliver>

ACCEPTANCE:
- Playwright smoke <spec path> 跑通
- curl <endpoint> 真返 LLM reply
- features-inventory.md F-<XXX> entry 加完
- tsc --noEmit 0 error

BOUNDARY:
- 改: <file list>
- 不改 (PRESERVES): F-001 ~ F-XXX (列 inventory id)
- 共享 contract: docs/contracts/<spec>.md (必读)

DEPENDENCIES:
- <已就位 endpoint / shared type>

SPEC: docs/contracts/agent-<name>-spec.md (本文件 read 后实施)

TRAILER 协议: commit 必含
PRESERVES: F-001, F-005, ...
NEW-DOM: data-testid="..."
SMOKE-PASS: <spec>.spec.ts
```

### 主 CLI Review 流程

每 sub-agent commit 后:
1. 主 CLI 验 trailer 完整 · 缺 trailer → 阻断 merge
2. 跑 tsc --noEmit · 失败阻断
3. 跑 Playwright smoke · 失败阻断
4. ECS deploy verify · 失败 revert
5. features-inventory 加 F-XXX entry · 入 git

---

## 4. 风险 + 缓解

| Risk | Mitigation |
|---|---|
| Inter-worker file conflict (多 sub-agent 改同 file) | 派活前 read · 主 CLI 协调 · 串行做 shared file |
| sub-agent 自由发挥 → 回档 (前面问题再现) | features-inventory contract + trailer 强 enforce · 每 commit review |
| 跨 Agent shared types 改动连锁 | shared types 主 CLI 自己改 · sub-agent 不动 |
| ECS 网络抖 (GitHub→ECS pull timeout) | retry 6 次 / git bundle scp 备 fallback |
| 后端 LLM key 轮换 (handoff 教训 5) | 走访前 30 min smoke test all 6 endpoint · DashScope/Qwen 备 fallback key |
| Cloudflared tunnel 单点故障 | 走访前预备 .com 域名 fallback |

---

## 5. Success Criteria (走访前必达)

- [ ] 6 Agent Workspace 默认空白 → 选下拉 切 mock / 真输入 触发 LLM 全 panel 切
- [ ] 候选 click → drawer 详情 (radar / signals / 产品 / 话术)
- [ ] 5 user 真 login + RBAC enforce
- [ ] dispatch IM 真 tool calling + WebSocket 实时
- [ ] 6 Agent Word 导出可用
- [ ] features-inventory.md 全 captures (40+ entries)
- [ ] Playwright smoke 30+ spec 全 pass
- [ ] ECS production 全功能 e2e 通

---

## 6. 立刻执行 (本会话内)

Stage A 立刻 deliver:
1. ✓ A.1 normalize fix Edit (上 message 已 Edit) → 立刻 commit + deploy
2. ✓ A.2 master plan doc (本文件) → write
3. → A.3 features-inventory.md 扩 F-009 ~ F-040 (1-2 hr · 这 message 末做)
4. → A.4 shared contracts (next message)
5. → A.5 6 PRD 摘要 spec (next message · sub-agent 派 read)

下次 session 开 Stage B (Channel 完整 architecture)。

不再分阶段 deliver "够看就行"·按 PRD-grade 全做。

---

## 7. Session Log

- 2026-04-27 Session 1 (本): write plan doc + Stage A.1-A.2
- next: A.3-A.5
- next+: B (Channel architecture refactor)
- ...
