# Instruction Source of Truth (SSOT) Priority v1.0

**Status**: 🟢 RATIFIED
**Owner**: 主 CLI · 修改走 RFC (`docs/contracts/shared-change-protocol.md`)
**生效**: 2026-04-29 (Phase A worker-A1 ratified)
**Author**: Phase A worker-A1

---

## 0. 为什么有这份契约

走歪诊断 (`docs/audit/conflict-register-v1.md` Cat 1 · 9 entries · `docs/reset/north-star.md` §3.5):

同一个 fact 在 5 处声明 → 4 处 stale + 1 处 active · 任何 worker 不知该信哪份。具体例:
- CLAUDE.md:184 "agent_report unreleased" — 但 api.py 已全量 mounted (audit verdict: stale)
- CLAUDE.md:165 "legacy_gradio 已归档" — 之前 stale · 2026-04-29 已 fix-forward
- decisions-log Q-040/Q-041 active 决议 (MAX_ROWS=50000 / candidate metadata 4 字段) · 代码已改但 CLAUDE.md 未回写
- `docs/contracts/workspace-state-protocol.md:13` 引 `ChannelWorkspace.tsx:67-254` (实际 line 已漂到 115/124/129/134)
- 6 spec doc 都标 "workspace-state-protocol.md (待 A2 worker 产出)" · 但 protocol v1.0 已存在

无 SSOT 优先级 + active decision 回写规则 → 项目长期被 stale 拖死。本 doc = 任何指令冲突时**唯一权威裁决表**。

---

## 1. 优先级阶梯 (5 tier · 高 → 低 · + 1 meta 例外)

冲突时 · **数字小者赢**。本 SSOT 是 ladder 之外的 **meta 例外** (见 §1.0)。

```
┌──────────────────────────────────────────────────────────────────────┐
│  Meta (例外 · ladder 之外 · 仅本 1 个文件):                            │
│    docs/arch/instruction-source-of-truth.md  ← THIS file              │
│    含义: 当本 SSOT 自身规则与 Tier 1-5 冲突时 · 以本 SSOT 为准         │
│    (因为 Tier 1-5 怎么排序就是本 SSOT 定的 · 不能用 Tier 内文件改 SSOT) │
└──────────────────────────────────────────────────────────────────────┘
┌──────────────────────────────────────────────────────────────────────┐
│  Tier 1 · docs/contracts/*.md                                        │  ← 接口契约 (红区 · RFC 改)
├──────────────────────────────────────────────────────────────────────┤
│  Tier 2 · root CLAUDE.md                                             │  ← 工程行为 + 全局规则
│    其他 docs/arch/*.md (e.g. platform-contracts.md) sit here as       │
│    supporting docs · 当与 root CLAUDE.md 冲突 → root CLAUDE.md 赢      │
├──────────────────────────────────────────────────────────────────────┤
│  Tier 3 · scoped child CLAUDE.md (e.g. agent_*/CLAUDE.md)            │  ← 子域行为 (only-narrower)
├──────────────────────────────────────────────────────────────────────┤
│  Tier 4 · docs/onboarding/*.md                                       │  ← worker 任务 brief (一次性)
├──────────────────────────────────────────────────────────────────────┤
│  Tier 5 · docs/handoff/decisions-log.md                              │  ← Q/A 历史 (active rule 必上回写)
└──────────────────────────────────────────────────────────────────────┘

代码 (Tier 0 · 非文档): 当代码与所有 Tier 文档全冲突时 · "代码胜" 但**必须**当 commit 把代码漂回 Tier 1-2 描述的 contract · 或开 Q-NNN 改 contract。代码不允许成为 stable 的 source of truth (会被 refactor 抹掉)。
```

### 1.0 Meta 例外 · 仅本 SSOT 一个

**本 doc 之所以是例外**: Tier 1-5 的优先级排序本身**由本 SSOT 定义**。如果允许 Tier 内文件 (e.g. `docs/contracts/foo.md` 或 `root CLAUDE.md`) 改本 SSOT 的 §1 阶梯 · 等于"被排序的对象决定排序规则" · 循环依赖。所以本 SSOT 是元规则 · 必须独立于 ladder。

**修改本 SSOT 的特殊路径**:
- 仍走 RFC (`docs/contracts/shared-change-protocol.md`)
- 但**只 PM 可批 (worker / Codex 不批)** · 因为 meta-rule 改动影响整个项目
- 改后所有 worker / Codex / main CLI 重读

### 1.1 判定细则

- **Tier 1 (contracts/) vs Tier 2 (CLAUDE.md)**: contracts 直接定义跨 agent / 跨 worker 接口 · CLAUDE.md 是项目级行为规则。冲突时 contracts 赢 · 但 contracts 改时必须**回写** CLAUDE.md (per §3 active decision rule)。
- **Tier 2 内 root CLAUDE.md vs 其他 docs/arch/\*.md**: root CLAUDE.md 是单文件 SSOT · 其他 arch docs 是 supporting (e.g. `platform-contracts.md` v1 是 platform shell 红区契约 · 但其内容应被 root CLAUDE.md §7 / §13 引用 / 镜像)。冲突时 root CLAUDE.md 赢 · arch docs 必须 fix-forward 对齐 root。
- **Tier 3 scoped child CLAUDE.md**: 仅在子域内有效 (e.g. `agent_report/CLAUDE.md` 仅约束 `agent_report/` 代码) · 不允许声明与 root CLAUDE.md 矛盾的全局规则 · 仅 narrow (per §2)。
- **Tier 4 onboarding**: fire-and-forget 任务 brief · worker DONE 后即过期 · 不能用 onboarding 推翻 Tier 1-3 已锁的契约。如 onboarding 与 Tier 1-3 矛盾 · worker 按 Tier 1-3 行 · 写 Q-NNN 反映 onboarding 错。
- **Tier 5 decisions-log**: Q/A 历史归档 · 任何 active rule (A-NNN APPROVED) 必须 ≤ 24 小时**回写**到 Tier 1-3 (见 §3) · 否则 worker 不必 honor。

---

## 2. 子域 child CLAUDE.md 规范

**当前状态** (2026-04-29 audit): 项目 0 个子域 CLAUDE.md · 6 个 agent_*/ 子目录均无 CLAUDE.md。

**未来如建** (e.g. `agent_report/CLAUDE.md`):
- 仅声明本子域**额外**约束 (per CLAUDE.md §3.2 MCP 域)
- 不重复 root 已声明的全局规则 (DRY)
- 不允许 override root (e.g. 不允许 `agent_report/CLAUDE.md` 声明 "本 agent 不走 Evidence-First")
- 顶部必带 header `> Inherits: ../CLAUDE.md · 本文档仅声明 agent_report 域内 narrower 约束`

---

## 3. Active Decision 回写规则 (PM 2026-04-29 拍板)

### 3.1 定义

**Active decision** = 一个改变 future worker 行为 / 代码约束 / 命名 / 接口的决议 · 当前 (即时起) 应被遵守。

**判定**:
- decisions-log Q-NNN 有 A-NNN 标 APPROVED / RESOLVED · 且影响 worker behavior → active
- A-NNN 标 REJECTED / SUPERSEDED → 非 active (但保留历史)
- 无 A-NNN 答 (Q-NNN-RAISED 状态) → pending · 不是 active

### 3.2 回写硬规

> 任何 active decision · 必须在**同 commit** 或**下一个 commit (≤ 24 小时)** 内回写到 Tier 1-3 (合 contracts / arch / root CLAUDE.md) 之一对应章节。

**回写责任**:
- 主 CLI 拍 A-NNN 时同 commit 改 contract / CLAUDE.md
- worker 改 contract 时同 commit 改 root CLAUDE.md 链接 (per worker-A1 onboarding §3 #3)
- worker 改 root CLAUDE.md 时不需要再回写 (本身就是 SSOT 之一)

**违反 = stop the line** (per RESET_MASTER_PLAN §6 红线 + CLAUDE.md §14.1 state-snapshot 同等优先级):
- audit 扫到"active rule 未回写" → 主 CLI 立刻 fix-forward · 不允许积压

### 3.3 回写 commit trailer 标识

```
ACTIVE-DECISIONS-BACK-WRITTEN: <count>
```

每次涉及 contract / arch / CLAUDE.md 的 commit · trailer 列回写计数 (含 0)。`0` = 本 commit 没引入新 active decision · 是允许值 (e.g. 文档 spelling fix)。

### 3.4 当前未回写积压 (audit Cat 1 fix-forward 任务 · 主 CLI owner)

| Q-NNN | active rule | 应回写到 | 状态 |
|---|---|---|---|
| Q-040 | MAX_ROWS=500→50000 backtest 样本上限 | CLAUDE.md §11 (Agent2 v3.1) 或 agent-forge-spec.md | 待主 CLI fix-forward |
| Q-041 | candidate metadata 4 字段 (industry/geo/scale/similarity) | sse-envelope.md §3.1 已涵盖 ✅ + CLAUDE.md §11 (Agent1) 或 agent-channel-spec.md | 部分 done (sse-envelope) · CLAUDE.md 待主 CLI |
| (no Q) | PIPL 境内优先 LLM fallback chain (`shared/llm/__init__.py:25` · 2026-04-28) | CLAUDE.md §3.x 或 agent-naming-ssot.md | 待主 CLI fix-forward |
| (no Q) | `agent_riskctrl/llm_judge.py:24-25` "spec 分歧由主 CLI Task D 裁决" 悬空 | decisions-log 写 Q-NNN-RESOLVED | 待主 CLI fix-forward |

---

## 4. Stale Marker 约定

任何 Tier 1-3 文档**自检**为 stale (引用过时 line / API / 文件) 时 · 不允许默默留着 · 必须:

### 4.1 标记格式

```markdown
> ⚠️ **STALE** (since YYYY-MM-DD): <原因 · ≤ 80 字>
> Fix-forward owner: <主 CLI / worker-AN / Q-NNN> · ETA: <Phase A / 立刻>
```

放在该段开头 · 不删原内容 (历史可读)。

### 4.2 修复路径

- **行号 stale** (e.g. workspace-state-protocol.md:13 引 ChannelWorkspace.tsx:67-254): grep approach (用 `grep -n "useState<"` 定位) 或泛用描述 ("顶层 component 4 useState · 见 file") 替代具体行号。**避免**绑定具体 line 号 (会随 refactor 漂)。
- **文件名 stale** (e.g. 引 `agent-channel-session.ts` 但已改为 `-sessions.ts`): 全局 grep + 同 commit 修。
- **API 名 stale** (e.g. backend SSE event 名标 "V14-B 约定" 但实现已 v16): 改 spec + 同 commit 改 code 注释。
- **概念 stale** (e.g. CLAUDE.md 说 "shared/ 没 llm_caller" 但 Stage E.3 已建): 立刻 fix-forward · 不允许等。

---

## 5. 冲突解决流程 (3 步)

worker 发现 Tier N 与 Tier M 矛盾时:

### 步骤 1 · 验证两边都是当前
- Tier 高的若标 STALE → 先 fix-forward stale (per §4) · 然后再判
- 两边都 active → 进步骤 2

### 步骤 2 · 按 Tier 优先级判
- 高 Tier 赢 (per §1 阶梯)
- worker 按高 Tier 行为 · 提交 commit

### 步骤 3 · 若高 Tier 错 (worker 强意见)
- worker 不允许在自己 commit 改高 Tier (违跨域红线 · per Phase A charter §4)
- worker 提 Q-NNN-RAISED · trailer `Signal: Q-NNN-RAISED` · 等主 CLI A-NNN
- A-NNN APPROVED 后 主 CLI 改高 Tier · 同 commit 把 active decision 回写 (per §3)

---

## 6. Cross-reference

- `RESET_MASTER_PLAN.md` §6 红线第 3 条 · "active decision 改了不回写 CLAUDE.md" → 本 SSOT §3 是其落地规则
- `CLAUDE.md` §14 (新 session / compression 后必读) · 与本 SSOT 互补 · §14 管"读哪些" · 本 SSOT 管"信哪些"
- `CLAUDE.md` §14.1 (state-snapshot 实时更新) · 与本 SSOT §3 同等级 · 都是 PM 2026-04-29 硬规
- `docs/arch/platform-contracts.md` · v1 platform shell 红区契约 · Tier 2 supporting doc (under root CLAUDE.md · per §1.1) · 本 SSOT 是 meta · 优先于 platform-contracts.md (但 platform-contracts.md 与 root CLAUDE.md 冲突时 · root CLAUDE.md 赢)
- `docs/contracts/shared-change-protocol.md` · 所有 contract 修改的 RFC 流程 · 本 SSOT §3 RFC pointer
- `docs/contracts/decision-log-protocol.md` · Q-NNN/A-NNN 格式 · 本 SSOT §3 decision 格式锚
- `docs/contracts/agent-naming-ssot.md` v1.0 · 6 Agent 命名 SSOT · 本 SSOT 通用规则的 first instance
- `docs/handoff/decisions-log.md` · Tier 6 · 历史归档 · 任何 active 必上回写

---

## 7. 验收 (Phase A 硬线)

- ✅ 5 Tier 优先级锁 (§1)
- ✅ child CLAUDE.md 规范 (§2)
- ✅ active decision 回写硬规 + commit trailer 标识 (§3)
- ✅ stale marker 约定 (§4)
- ✅ 冲突解决 3 步 (§5)
- ⏳ 主 CLI fix-forward 4 处积压 (§3.4 表) → Phase A 启 worker 前清完
- ⏳ 后续 commit trailer 含 `ACTIVE-DECISIONS-BACK-WRITTEN: <N>` 全员遵守
- ⏳ CI hook validator 加 trailer 检测 (Phase A 中段加固 · per phase-a-charter §1 #8 hardline 同款)

---

## 8. 反校准 (避免改歪)

- ❌ 不要把本 SSOT 替代 root CLAUDE.md · 本 SSOT 是 *meta-rule* (Tier 之外) · CLAUDE.md 是 *project rule* (Tier 2)
- ❌ 不要把 Tier 1 contracts 当成"什么都能放进去" · contracts 仅是**接口契约** (跨 worker / 跨 agent 共形规则) · 单 agent 内部行为放 agent_*/CLAUDE.md (Tier 3) 或代码注释
- ❌ 不要把 decisions-log 当成"决策 source of truth" · 它是历史归档 (Tier 5) · active rule 必须上回写到 Tier 1-3
- ❌ 不要在 worker 任务里夹带 SSOT 修改 · SSOT 改走 RFC · worker 仅引用
- ❌ 不要因为某个 Tier 1 contract "看起来过时" 就直接改 · 先标 STALE (§4) + 提 Q-NNN
- ❌ 不要把其他 docs/arch/* 文件当 Tier 1 (跨 worker 接口契约层) 用 · 它们是 Tier 2 supporting doc · 当与 root CLAUDE.md 冲突时 root CLAUDE.md 赢
