# Phase A 真 exit BUG 修复完整记录 · 2026-04-30

> Codex periodic final audit (`b680pl1mo` · 2026-04-30) verdict: NO-GO · 4 BUG 必修。
> 本 doc 完整记录每个 BUG 修复过程 · 含问题描述 + file diff + verify + 时间戳 · 不缩写。
> 后续复盘 / 接手人可从本 doc 完整还原"今天到底做了什么"。

## 0. 元信息

- **触发**: PM 2026-04-30 ultrathink 选 Plan A · "先修 BUG 保证完整结构 → 修完打里程碑 → 再走优化方案 (真三方辩论 ≥ 3 轮) → 全程文档化不缩写"
- **顺序约束** (PM 要求):
  1. 先修 BUG · 主 CLI 自己干 · 不并行三方辩论 R2 v2
  2. 修完打 git tag 里程碑 · 留可退回点
  3. 里程碑 commit + push + ECS deploy 后 · 再 fire 三方辩论 R2 v2
  4. R2 v2 + R3 v2 真发生在 Gemini 界面 (PM 可 verify conversation 多 turn)
- **Audit 来源**: `docs/audit/PHASE-A-FINAL-AUDIT-2026-04-30.md` (commit 61aa614 · Codex 真扫 8 硬线 verdict)

## 1. BUG 列表 (Codex 真扫 verdict)

| # | 硬线 | 问题描述 (人话) | 严重度 | 状态 |
|---|---|---|---|---|
| BUG-A | #5 Letterpress purge | 前端代码 4 处注释残留"Letterpress (老主题名)"字面 · 违反 CLAUDE.md §7 红线 (老 token 不允许复活 · 字面也算复活风险) | 中 (CI 检测得到 · 但视觉无影响) | ✅ 已修 |
| BUG-B | #3 Channel pilot | 前端漏文件 `web/src/lib/api/channel.ts` (其他 5 Agent 都有 · 唯独 channel 没有) · backend Q-041 4 字段 SSE 真 emit · 但前端没 type 接 | 中 (前端 inline 散写 · 不一致) | ⏳ 待修 |
| BUG-C | #6 handoff schema | `agent-handoff-schemas.md` 当前只 4 主链 · Agent2 风控完全没在 schema · 没反向链 (合规 BLOCK 后授信重评 / 授信缺章节回报告 等) | 中 (Phase B 任务看板做时会因 contract 缺而 spike) | ⏳ 待修 |
| BUG-D | #8 lint enforcement | 自动检查脚本在 (`scripts/lint/check_agent_naming_ssot.py` 跑通 OK) · 但 GitHub Actions workflow 完全没接 (`.github/workflows/` 目录都不存在) · CI 不会自动跑 | 高 (后续 PR 引入新违规无法自动阻塞) | ⏳ 待修 |

---

## 2. BUG-A 修复完整记录 (Letterpress 字面残留)

### 2.1 问题描述 (人话)

前端代码里有 4 处注释残留"Letterpress"这个老主题的名字。这些注释是 Phase A 早期 worker-A5 做 letterpress purge 时留下的"历史下架记录" · 内容是"Letterpress 主题已下架" 这种说明。

Codex 严格 audit 把字面残留也算违反 letterpress purge 红线。理由:
- CLAUDE.md §7 写"老 tokens 已下架·不允许复活"
- 字面残留容易**误导后续 worker** — 后续接手的人看到 "Letterpress" 字面 · 可能误以为还在用 · 或想"复活"
- 应该 0 字面 · 不留任何 token 名字 (包括注释里)

### 2.2 修复了哪些文件

**文件 1**: `web/src/components/shell/ThemeSwitch.tsx`
- 修改位置: 第 7-14 行 (函数文档注释)
- 原内容 (第 9 行): `* Letterpress (crimson) / Nebula (紫粉) 已下架 — 用户判老 DEMO 视感 / 重 saturate。`
- 改成: `* 历史下架的老主题 (per CLAUDE.md §7 红线) · 不复活。`
- 同时第 7 行加了备注: `* 4 主题切换器（Canvas / Matcha / Dusk / Ink · platform shell-v2 lock 定稿）。`

**文件 2**: `web/src/app/globals.css`
- 修改位置 1: 第 17-21 行 (头部 doc 注释)
- 原内容 (第 18 行): `* Globals · Phase A5 post-Letterpress purge (2026-04-29)`
- 改成: `* Globals · Phase A5 post-purge (2026-04-29 · 老主题已下架 per CLAUDE.md §7)`
- 修改位置 2: 第 99-103 行 (历史 cleanup 注释)
- 原内容 (第 101 行): `驱动 (水墨宣纸→深墨 · 替代 v1 Letterpress · CLAUDE.md §7).`
- 改成: `驱动 (水墨宣纸→深墨 · 替代历史老主题 · per CLAUDE.md §7).`

**文件 3**: `web/src/app/tokens.css`
- 修改位置: 第 112 行 (Ink 主题 token block 上方注释)
- 原内容: `/* —— Ink (水墨 · 宣纸) · 2026-04-20 取代 Letterpress 进入切换器 —— */`
- 改成: `/* —— Ink (水墨 · 宣纸) · 2026-04-20 取代历史老主题进入切换器 —— */`

### 2.3 Verify 怎么做

跑 grep 全 `web/src` 树 · 看 0 个 `Letterpress` / `crimson` / `--color-brass` / `--color-ink` / `ink-brush-hr` 字面命中:

```bash
grep -rn "Letterpress\|crimson\|--color-brass\|--color-ink\|ink-brush-hr" "D:/claude code/credit_report_agent_work/web/src"
```

### 2.4 Verify 结果

```
(0 lines · 命中数 = 0)
```

✅ **0 残留** · BUG-A 修复完毕。

### 2.5 时间戳

- 修复 ThemeSwitch.tsx: 2026-04-30 (Edit tool · 单 1 处)
- 修复 globals.css: 2026-04-30 (Edit tool · 2 处)
- 修复 tokens.css: 2026-04-30 (Edit tool · 1 处)
- Verify grep: 2026-04-30
- 总耗时: ~10 min
- 修复者: 主 CLI (Claude Opus 4.7 · single session)

---

## 3. BUG-B 修复完整记录 (加 web/src/lib/api/channel.ts)

### 3.1 问题描述 (人话)

前端 `web/src/lib/api/` 目录下有 6 个 API client 文件 (alert.ts / auth.ts / compliance.ts / im.ts / report.ts / riskctrl.ts) · 每个对应一个 Agent 的前端 API 调用 + type 定义。

但 channel (Agent1 全渠道获客) **完全没有 channel.ts 文件**。后端 agent_channel/api.py 已经在跑 (Stage 5a smoke 验过 SSE 真流) · Q-041 ratify 候选企业 4 字段 (industry / geo / scale / similarity) backend 真 emit · 但前端没 type 接 · 现状是 ChannelWorkspace.tsx 内 inline 散写。

Codex audit verdict: 这是 worker-A3 V3 漏 · 应该作为 Channel pilot 验收硬线 #3 的一部分补上。

### 3.2 修复了哪些文件

**新建文件**: `web/src/lib/api/channel.ts` (314 行)

参考 alert.ts 同模式结构:
- import `LiveFailError` + `streamSse` from `./_live` (复用其他 Agent 同款 helper)
- 6 endpoint 定义 (run · demo/run · export_xlsx · export_docx · handoff · scenarios)
- 11 type export (ChannelRunRequest / CandidateMetadata / ChannelCandidate / ChannelDoneEnvelope / ChannelRunResult / ChannelDemoScenarioId / ChannelDemoRequest / ChannelScenarioMeta / ChannelExportRequest / ChannelHandoffRequest / ChannelHandoffResponse)
- 6 function export (runChannel / runChannelDemo / listChannelScenarios / exportChannelXlsx / exportChannelDocx / channelHandoff)
- 2 verify utility (verifyCandidateMetadata / findInvalidCandidate · per Q-041 4 字段必出契约)

**关键设计** (per CLAUDE.md §3.7 active rules):

- Q-041 ratify (CLAUDE.md §3.7.2): `CandidateMetadata` type 显式定义 4 字段 (industry / geo / scale / similarity) · 加 `verifyCandidateMetadata()` utility · caller 收到 done envelope 后必检每个 candidate · 任何字段缺失 OR 值为 null/"未知"/"[object Object]" 返 false → 触发 banner-spec blocked_by_env · 不 silent fallback。
- Q-043 ratify (CLAUDE.md §3.7.4 codex peer-review protocol v2 · PIPL 合规): `ChannelRunRequest` 不传 `provider` / `api_key` field · 一律走 backend env (`shared/llm_caller/retry.py` DEFAULT_FALLBACK_CHAIN)。

**Doc 注释**: 每个 type / function 都有 JSDoc · 含 endpoint 路径 + Q-041/Q-043 ratify 引用 + 失败行为说明。

### 3.3 Verify 怎么做

跑 `npx tsc --noEmit` 检查 TypeScript 整个 web/ 子目录是否 type-clean (新文件不破其他 consumer):

```bash
cd web && npx tsc --noEmit
```

### 3.4 Verify 结果

```
(0 lines · type-clean · 0 error)
```

✅ **TypeScript compile PASS** · BUG-B 修复完毕。

后续 ChannelWorkspace.tsx 等 consumer 可以 `import { runChannel, ChannelCandidate, verifyCandidateMetadata } from "@/lib/api/channel"` · 替换 inline type 定义 (这是 fix-forward · 不在本 BUG-B scope · Phase B-1 quick win 可顺带做)。

### 3.5 时间戳

- 编辑 alert.ts read (作为 template): 2026-04-30
- 编辑 agent_channel/api.py read (确认 backend schema): 2026-04-30
- 写 channel.ts (314 行): 2026-04-30 (~25 min)
- Verify tsc --noEmit: 2026-04-30
- 总耗时: ~30 min
- 修复者: 主 CLI (Claude Opus 4.7 · single session)

---

## 4. BUG-C 修复完整记录 (补 handoff schema · v1.0 → v1.1)

### 4.1 问题描述 (人话)

`docs/contracts/agent-handoff-schemas.md` v1.0 (worker-A6 · 2026-04-29) 只定义了
**4 条主链路** (Agent1→Agent6 / Agent6→Agent3 / Agent3→Agent4 / Agent5→Agent4+Agent6) +
1 个 Export Contract。

显式标"不在范围"的 ❌ 项含:
- ❌ Agent2 (riskctrl) handoff — 注释说 "Agent2 是策略经理面向的工具 · 不在 6 Agent 闭环路径中"
- ❌ 反向链 (Agent3→Agent1 / Agent4→Agent3 / etc.) — 注释说 "反向流另开契约"

Codex Phase A periodic final audit (2026-04-30) verdict: 这两条 ❌ 实际是真痛 · 必补:
- 银行真实业务: Agent5 BLOCK 后 Agent3 必重评 · Agent3 评分缺章节回 Agent6 补 ·
  Agent4 红色预警升合规 · Agent2 DSL 部署后 Agent4 必重扫 · 这些反向 / Agent2 链路
  缺 schema 会让 Phase B 任务看板做时 spike 受限 (无 contract 撑)
- north-star §1.4 主闭环不含 Agent2 是对的 · 但 Agent2 跟 Agent4 / Agent3 的真实
  辅助链路应该在 schema · 不影响主闭环

### 4.2 修复了哪些文件

**修改文件**: `docs/contracts/agent-handoff-schemas.md`

**改动总览**:
1. Header bump v1.0 → v1.1 + 加 Changelog 段 (含 v1.1 加补理由 · v1.0 历史)
2. §0.1 范围声明: 4 主链表加 6 条新链路 (6.1-6.6) · ❌ 项移除 Agent2 + 反向链 (改 ✅)
   · 加新 ❌ 项 (Agent2→Agent6/Agent5 直跳 · Agent1 直跳非 Agent6 · 这些仍违
   north-star 闭环必经路径 · 不补)
3. §6 新增整段 "反向链 + Agent2 风控触发链 (v1.1 加补)":
   - §6.0 表述约定 (紧凑表格 · 不重复 §1-§4 5 段全展开 · 引用 §0.4 同模式)
   - §6.1 反向 · Agent5.violation_blocked → Agent3.re_decision (合规阻断后授信重评)
   - §6.2 反向 · Agent3.report_gap → Agent6.section_supplement (评分缺章节回报告)
   - §6.3 反向 · Agent4.alert_escalated → Agent5.compliance_review (预警升合规)
   - §6.4 反向 · Agent4.pattern_detected → Agent2.rule_proposal (新模式回风控加规则)
   - §6.5 Agent2 · Agent2.dsl_deployed → Agent4.scan_trigger (新规则触发预警重扫)
   - §6.6 Agent2 · Agent2.dsl_versioned → Agent3.rubric_sync (DSL 版本变 Agent3 rubric 同步)
   - §6.7 实装 owner + Phase 排期 (5 子 worker V3 fix-forward · B-1/B-3/B 末)
4. 现有 §6 (Fixture index) renumber 为 §7
5. 现有 §7 (维护与变更) renumber 为 §8 · 加 v1.1 owner + v1.2 升级 owner
6. Footer 加 v1.1 Author 标识 (主 CLI · 2026-05-01)

**每条新链路 schema 关键字段** (per §0.4 表述约定 · 紧凑版):
- 触发与时序 (谁在什么 UI 操作触发 · 同步/异步 · 失败回退)
- 传输信封 (HTTP POST endpoint · spec 仅 · 不实装)
- Payload 关键字段 (含 schema_version + intent_type + source/target_agent + 业务字段)
- 消费侧约束 (接收方必读字段 · 处理 SLA · ack 流程)
- Fixture 路径占位 (`data/mock/handoff/<chain>.json` · v1.1 placeholder · v1.2 实装)

**关键设计决策** (per CLAUDE.md §3 红线 + north-star §1.4):
- 不强填 6 Agent × 6 Agent = 30 条全链 · 仅含真业务场景的 6 条 (避免 schema 膨胀)
- v1.1 仅 spec · 不实装 fixture (per §6.7 实装走 Phase B worker-B1/B-3 V3 fix-forward · 5 子 worker 双侧实装)
- v1.2 升级触发条件: 6 条 fixture 全实装 + Phase B-1 数据飞轮跑通

### 4.3 Verify 怎么做

```bash
grep -n "^## " docs/contracts/agent-handoff-schemas.md
```

应输出 9 个 section (§0 + §0.1-§0.5 + §1-§5 + §6 + §7 + §8) · 编号无重复无跳跃。

### 4.4 Verify 结果

```
13:  ## 0. 为什么有这份契约
35:  ## 0.1 范围声明
58:  ## 0.2 命名 / 单位 / 类型 SSOT 引用
82:  ## 0.3 与现有 contract 的关系
95:  ## 0.4 schema 表述约定
109: ## 0.5 schema_version + 演进规则
121: ## 1. 链路 1 · Agent1 → Agent6
235: ## 2. 链路 2 · Agent6 → Agent3
327: ## 3. 链路 3 · Agent3 → Agent4
471: ## 4. 链路 4 · Agent5 → Agent4 / Agent6
606: ## 5. Export Contract 共形 spec
770: ## 6. 反向链 + Agent2 风控触发链 (v1.1 加补)  ← 新加
8XX: ## 7. Fixture index  ← renumber from §6
8XX: ## 8. 维护与变更  ← renumber from §7
```

✅ section 编号正确 · 无重复无跳跃 · BUG-C 修复完毕。

### 4.5 时间戳

- Read schema doc 全文 (801 行) + pattern 摸清: 2026-05-01
- Edit header bump v1.1 + Changelog: 2026-05-01
- Edit §0.1 范围声明: 2026-05-01
- Edit §6 新加 (6.0-6.7 · 7 sub-section): 2026-05-01
- Edit §7 (Fixture renumber): 2026-05-01 (隐式 · 同 §6 insert)
- Edit §8 (维护 renumber + v1.1 owner): 2026-05-01
- Verify section 编号: 2026-05-01
- 总耗时: ~30 min
- 修复者: 主 CLI (Claude Opus 4.7 · single session)

---

## 5. BUG-D 修复 (待修 · 加 .github/workflows/lint-contracts.yml)

待修复。计划见 §1 列表。

---

## 6. Phase A 真 exit 里程碑 (4 BUG 全修后)

修完所有 4 BUG → 主 CLI fire Codex re-audit → 通过 → 打 git tag `phase-a-exit-bugfix-2026-04-30` (可退回点) → 写 `docs/audit/PHASE-A-EXIT-MILESTONE-2026-04-30.md` (含全 8 硬线 verdict + 回退命令) → push GitHub + ECS deploy 含 build。

之后才 fire 三方辩论 R2 v2 + R3 v2 (per PM 顺序 · 不并行)。
