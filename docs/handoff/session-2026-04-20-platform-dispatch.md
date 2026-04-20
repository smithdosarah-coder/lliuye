# Session Handoff · 2026-04-20 Platform Phase 1 Batch 1 Dispatch

> 本文档是旧主 CLI（context 满前最后一次写）给新主 CLI 的**交班脑图**。
> `AGENT_IDENTITY.md` + `decisions-log.md` + `git log` 只含**结构化状态**，本文档补的是**未入库的 tacit 决策 / 讨论上下文 / 用户协作习惯**。
> 新主 CLI 读完这份 + identity 清单 → 100% 接替。

---

## 0. 一眼看当前批次

- **批次**：Platform Phase 1 · Batch 1
- **下发 commit**：`9eb3346 feat(mesh/platform): dispatch 5 platform worker worktrees + Phase 1 Batch 1`
- **前置 commit**：`c99a277 feat(platform/contracts): land Stage 1.0 shared store + RBAC + handoff catalog`
- **状态**：已下发，等 5 个 platform-* worker 各自 `PHASE-1-BATCH-1-ACK`
- **下一个里程碑**：收齐 5 个 `READY-FOR-PLATFORM-<X>-REVIEW` → 主 CLI rebase + 冒烟 + APPROVE → 进 Phase 2 跨 view 联动
- **5 Worker Kickoff Prompts**：`docs/handoff/platform-batch-1-kickoffs.md`（worker resume 完后粘给用户下发的 GO 指令）

## 0.1 Bash 工具修复（2026-04-20 补）

旧主 CLI 发现 Windows 上 Bash 工具报 `No suitable shell found` —— 因为 `CLAUDE_CODE_GIT_BASH_PATH` 只在 `mesh-credit-agents.bat` 的 `--pre-cmd` 里注入给 worker tab，没写进全局 settings。已追加到 `C:\Users\Mr.S\.claude\settings.json` 的 `env` 字段：`CLAUDE_CODE_GIT_BASH_PATH=D:\Git\usr\bin\bash.exe`。**下次任意方式启 CLI 都会自动带上**，新 main CLI session 一进来 Bash 就可用，能跑 `mesh_status.py` / `git log` 自看进度，不用让用户帮粘输出。

---

## 1. 这次改动到底做了什么（按时间顺序）

### 1.1 Stage 1.0 共享基建（c99a277）

落地 `web/src/lib/store/` 全套（都在主 CLI 的 `chore/l0-infra` 分支上完成）：

| 文件 | 内容 | 谁读谁写 |
|---|---|---|
| `types.ts` | 6 AgentId / 5 Role / Customer / AgentEvent / HandoffTicket / ImMessage | 全员读 |
| `customer-store.ts` | zustand + persist，5 企业种子（中锐/鼎川/云融/海元/同信） | 全员读，**focus/upsert/advanceStage 是唯一入口** |
| `event-bus.ts` | pub-sub + 200 事件 ring（内存，不持久化，真正审计走 `/api/audit`） | 全员 subscribe，报告/预警/合规等 publish |
| `auth-store.ts` | 5 demo 用户（王哲 RM 默认登录），ACCESS + HANDOFFS 矩阵 | login / logout 入口，`can(action)` 谓词 |
| `handoff-catalog.ts` | 6 HandoffRecipe（channel→report / report→credit / credit→report / alert→compli / alert→credit / compli→report） | worker 消费 `findRecipes(fromAgent)` |
| `index.ts` | barrel | — |

**`docs/arch/platform-contracts.md`** 同时落地——这是**新红区**，规定单写者规则 + RFC 流程 + slot 约定。

### 1.2 分派 5 个 worker（9eb3346）

- 建 5 个 git worktree：`D:/claude code/demo-platform-{dispatch,warroom,today,auth,customer}`
- 每个 worktree 根写一份 `AGENT_IDENTITY.md`（gitignore 本地文件）
- `docs/onboarding/platform-*-phase-1.md` 5 份下发单（每份 3-4 task）
- `docs/handoff/mesh.json` 追加 5 条 worktree 注册
- `docs/handoff/decisions-log.md` 追加 Q-020/A-020（自问自答为什么这么切）

### 1.3 Benchmark research（background agent）

- `docs/research/benchmark-ui-2026-04.md` ~7500 字
- 诚实承认：6 家银行 AI 产品里 5 家**无公开 UI 截图**，研究基于文字描述 + 通用金融 SaaS 模式推断
- 如果 review 时被问「为什么页面长这样」，这份文档是唯一可引的对标依据

### 1.4 桌面脚本修正（非代码，但占用了一轮交互）

- **错误**：最初把 `C:/Users/Mr.S/Desktop/demo-start.bat`（服务器启动脚本）当成 mesh launcher 改了
- **用户纠正**：正确的是 `C:/Users/Mr.S/Desktop/mesh-credit-agents.bat`
- **修复**：
  - 还原 `demo-start.bat` 为原来的 3 服务启动（FastAPI + Next.js + cloudflared）
  - 重写 `mesh-credit-agents.bat`：proxy 50088 + CLAUDE_CODE_GIT_BASH_PATH + `--exclude-names agent1,agent2,agent3,agent4,agent6,frontend`
- **用户这次不是放过**——他说"你改错了脚本，ultrathink"，新主 CLI 遇到类似"改桌面 bat"的需求要**先确认文件用途**再动

---

## 2. 用户未入库的 tacit context（重要）

### 2.1 为什么 pivot 到统一平台

起因是技术同事提的「30% 复用度」问题——旧 6 Agent 各自独立前端，风格 / 交互 / 组件各不相同，客户上手成本高、代码复用低。用户不满意现状，要求**按平台级 shell 级重新设计**而非单页美化。

这个"30%"数字是**技术同事的口头评估**，不是量化 benchmark，但它是本轮 pivot 的触发点。新主 CLI 如果遇到 worker 问"为什么要做这个平台"，要能讲清：**旧 6 Agent 是 6 个孤岛 → 统一 shell + 共享 store + 协作 handoff = 30% → 80% 体验复用度**。

### 2.2 用户的设计节奏："先搭架子，再抓质量"

用户原话意思是：**先把前端 shape（4 view + 4 主题 + 共享 shell）跑出来给客户看**，再逐轮迭代质量（字段准确率 / evidence 链 / 数据层）。所以：

- Phase 1 优先级 = 结构成型 + 冒烟跑通，不强求 Phase 2 的 evidence 字段对齐
- Worker 汇报 DONE 时，**允许 UI 占位 / mock 数据**，但**store 契约必须严格（不能偷偷改共享 store）**
- 这个优先级不要反过来！不要让 worker 把时间花在"补数据真实性"上而拖延 shape 交付

### 2.3 用户的协作模式（重要，决定你怎么回应）

- **copilot not autopilot**：重决策（分派 / RFC 裁决 / APPROVE）都要用户最终拍板。worker ACK / 常规 DONE 不用打扰用户，但 REVIEW 阶段必须停下来让他决定
- **ultrathink 触发词**：用户打 `ultrathink` 意味着"这是重决定，你给我想清楚再答，不要快速回"。遇到 ultrathink 必切深度思考模式
- **不喜欢谄媚**：用户 CLAUDE.md 明确说"不要夸想法好、不要说'这是个很好的问题'、不要'当然可以'"——给真实判断，方案有问题直接说
- **中文 + 英文代码**：所有对话中文，commit message / 变量名 / 代码注释英文
- **commit 粒度 = task 粒度**：TaskCreate 里每 task 完成立即 commit，不要攒大 commit（便于 `git revert <sha>` 精准回滚）
- **批量发调用**：≥2 独立操作必须一条消息发齐，禁止串行发

### 2.4 技术尺度

- **不让 LLM 算能确定性算的**（比率 / 红线）—— 但本批次是前端 shell，不涉及
- **绝不编字段**—— 填不了就标"未能自动填写"
- **worktree mesh 有严格纪律**——signal-await gate（trailer 带 `Signal: XXX` 才算数）、A-012.D SHA immutable、A-012.E merge-only

---

## 3. 主 CLI 自己的 in-flight state（要交代给新主 CLI）

### 3.1 当前未提交的修改（不是本次批次产物，是历史 pending）

```
M CLAUDE.md                          # 老的项目说明更新，可随下次基建一起提
M docs/scorecard/GLOBAL.md           # scorecard 文档小修，不紧急
M web/next.config.ts                 # 历史 config 微调
M web/src/components/workspace/channel/ChannelWorkspaceClient.tsx  # 旧 agent1 UI 微调
?? design_mockups/stage5/mockup-v2/  # stage 5 时期的 mockup 草稿，未决定要不要入库
?? tmp_ui_shots/                     # 调试截图，gitignore 即可
```

**都不是本批次 dispatch 的产物**，新主 CLI 不要一上来就想"我是不是漏 commit"。要就纯收，要删就问用户。

### 3.2 已 merge 到 main 分支的 commit（本批次产物）

```
506ed7a feat(archive/skin): V2 design-language wash over legacy workspaces
0e66963 feat(workspace/v2/report): merge legacy controls as IM chat + composer
1ed13d9 feat(workspace/v2/shell): add ComposerBar + PresetChip + attachment-chip primitives
dd1d632 revert(archive/[agent]): route back to legacy workspaces with working features
dd4de04 feat(workspace/v2/report): audit-strip collapses until done + live intake feedback
```

这些是 pivot 早期的 frontend 探索，**与本批次的 `c99a277` + `9eb3346` 共同构成当前 main 分支的状态**。

### 3.3 老 6 agent worktree（maintenance，不再启动）

| worktree | 分支 | 最后 signal | `mesh-credit-agents.bat` 是否启动 |
|---|---|---|---|
| agent1 | feat/agent1-productize | AGENT1-PHASE-1-WINDOW-CLOSED-CLEAN | ❌ exclude |
| agent2 | feat/agent2-productize | AGENT2-PHASE-1-WINDOW-CLOSED-CLEAN | ❌ exclude |
| agent3 | feat/agent3-productize | WINDOW-CLOSED-CLEAN | ❌ exclude |
| agent4 | feat/agent4-productize | AGENT4-PHASE-1-WINDOW-CLOSED-CLEAN-V2 | ❌ exclude |
| agent6 | feat/agent6-v16 | AGENT6-PHASE-2-WINDOW-CLOSED-CLEAN | ❌ exclude |
| frontend | feat/platform-shell | FRONTEND-STAGE-4-RE-DONE | ❌ exclude（已被 platform-* 替代）|

**用户没说要删这些 worktree**——只是不再并发启动。如果将来要跨 Agent 联动（Phase 2 阶段），可能还会临时拉回。不要主动删。

---

## 4. 新主 CLI 的「DON'T」清单

| ❌ 不要 | 为什么 |
|---|---|
| 主动改 worker 分支代码 | worker 各自独立 worktree，主 CLI 只动 main + docs + lib/store |
| 绕过 decisions-log 做决定 | 所有 RFC / Q-NNN / A-NNN 必须留痕，不然下一任主 CLI 根本 resume 不起来 |
| 擅自改 `lib/store/*` 契约 | 红区，改字段必须先开 Q-NNN 自审，最好让 worker raise RFC 后再改 |
| 一进来就 Phase 2 规划 | Phase 1 还没收到一个 REVIEW，规划早了就是空想 |
| 并发改 AppShell.tsx | platform-customer 和 platform-auth 都会碰 AppShell slot，改动前预告对方（A-020.D 提过）|
| 把 `AGENT_IDENTITY.md` 改成动态进度 | identity 只放静态指针，动态进度全靠 `git log` + `mesh_status.py` 派生 |
| 改 `demo-start.bat`（服务器脚本） | 用户的服务器启动，动了他就不能 demo 了 |
| 自己去启动 5 个 worker CLI | 主 CLI 不负责 spawn worker，用户自己双击 `mesh-credit-agents.bat` |

---

## 5. 下一个 signal 到达时怎么反应（playbook）

### 5.1 `Signal: PHASE-1-BATCH-1-ACK`（预期 5 个 worker 各一次）

**动作**：`mesh_status.py` 打出来看到就行，不需要主 CLI commit 回。ACK 只是 worker 告诉你"我 resume 完 onboarding 了"。

### 5.2 `Signal: <TASK>-DONE`（每个 worker 3-4 次）

**动作**：读 commit 差异扫一眼，不满意可提建议但不强制——Phase 1 看 shape，不是逐行 review。

### 5.3 `Signal: RFC-<topic>-RAISED` 或 `Q-021-RAISED`

**动作**：
1. 读 `decisions-log.md` 新追加段
2. 如果改红区（lib/store / HANDOFF_CATALOG / ACCESS）→ ultrathink 一次 → 追加 `A-NNN-RESOLVED` → commit trailer `Signal: A-NNN-RESOLVED`
3. 如果只是澄清问题 → 直接 A-NNN 回答
4. **紧急度**：RFC 是 blocker，worker 会停工等答案。ACK 后 ≤1 个 resume 周期必须答

### 5.4 `Signal: READY-FOR-PLATFORM-<X>-REVIEW`

**动作**：
1. `git checkout feat/platform-<x>` → rebase 到 main → 看冲突
2. `npm run dev` 起前端，手动 walkthrough 对应路由（`/dispatch` / `/warroom` / `/today` / `/login` / `/customer/[id]`）
3. 对照 `docs/onboarding/platform-<x>-phase-1.md` 的 DoD 勾验收
4. APPROVE → commit `Signal: PHASE-1-PLATFORM-<X>-APPROVED` + merge PR/FF 到 main
5. REJECT → `docs/onboarding/platform-<x>-phase-1-v2.md` 附 rationale + 新任务 → commit `Signal: PHASE-1-PLATFORM-<X>-REJECTED-V2-DISPATCHED`

### 5.5 5 个全 APPROVE 之后

**Phase 2 规划才正式启动**。主要议题：event-bus 订阅配线真跑通、HandoffTicket end-to-end、跨 view 联动冒烟。**不要提前规划**——要看 Phase 1 实际落地形状。

---

## 6. 用户可能会问的问题 + 标准答复

| 问题 | 答 |
|---|---|
| "进度怎么样" | 跑 `mesh_status.py`，告诉用户哪几个 ACK、哪几个 DONE、哪几个还没动 |
| "xx 能跑了吗" | 切对应 worktree，`npm run dev`，手试 |
| "这 5 个什么时候完" | 不承诺时间，worker 节奏各异。可以看 onboarding task 数量粗估——customer 3 task、auth 4 task 最重 |
| "我把商业化进度也做了" | **红线**：能说"客户认了"，**不能**说"签单 / 商业化"（见 `project_6agent_poc_landed.md`）|
| "老 agent 还能跑吗" | 能，worktree 还在，只是 mesh launcher 不自动开。手动 cd 进去启动可以 |
| "我要改 lib/store 里加个字段" | **主 CLI 不要自己上**——请求用户等下一个空闲批次，或让某个 platform-* worker 作为契约 owner 起 RFC |

---

## 7. 本次 session 里用户的 5 条原话（原样引用，不改写）

1. "确定下，你有用skills把，桌面有脚本这个事你知道吧，等等调用子cli，改现成的脚本，调用skills然后让我粘贴你记得把 ultrathink"
2. "开6个？新的也包括了主CLI吗？你没有把网络接口放进去，参考一下桌面的start claude"
3. "而且，你是不是改错了脚本，C:\Users\Mr.S\Desktop\mesh-credit-agents.bat，你不是应该改这个脚本吗，你改了demo strat对话，我的服务器开启脚本不就没了 ultrathink"
4. "所以有一个新的主cli可以接替接下来的活了？ ultrathink"
5. "那你就想办法让他能百分百接替你现在的工作，然后你同时把我们这段时间的工作同步到我飞书上去 ultrathink"

**解读**：
- (1) 用户纠察你是否守规矩（skill + 桌面 bat + copy-paste）——你对这三点要有知觉
- (2) 用户会补漏（主 CLI 要不要算 6 个、代理要不要带）——他自己是 vibe coder，漏了会点破
- (3) 强纠错——再次证明你不能当 autopilot，否则出事
- (4)(5) 用户在为**下一任主 CLI 的接班**做兜底——说明他对当前主 CLI 的 context 容量已没信心了

---

## 8. 新主 CLI 第一次 resume 时该做的

1. 读 `AGENT_IDENTITY.md`（本 worktree 根）+ 里面列的清单（含本文档）
2. 跑 `py C:/Users/Mr.S/.claude/skills/multi-cli-mesh/scripts/mesh_status.py` 看 5 worker 最后 signal
3. 跑 `git log --format='%h %s' -20 chore/l0-infra`
4. 回报格式（给用户看的）：

```
Resume 完成。
- 我是：main CLI（orchestrator，chore/l0-infra）
- 当前批次：Platform Phase 1 Batch 1（2026-04-20 下发）
- 上一主 CLI 交接：docs/handoff/session-2026-04-20-platform-dispatch.md
- 5 worker 状态：<mesh_status 摘要>
- Pending：等 ACK / DONE / 可能的 RFC
等你指令。
```

---

**旧主 CLI 签名**：chore/l0-infra @ 2026-04-20（context 即将满前写）
**接力 anchor commit**：（本文件 commit 之后将附 `Signal: ORCHESTRATOR-HANDOFF-READY`）
