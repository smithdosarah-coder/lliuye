# Decisions Log

**协议**：`docs/contracts/decision-log-protocol.md`
**使用**：append-only。子 CLI 发起 `## [Q-NNN]`，主 CLI 紧邻 append `### [A-NNN]`。
**发布**：2026-04-18

---

## [Q-001] 2026-04-18 15:30 · report(v16) · section_generator 年份前缀 regex 补丁

**CLI**: report
**Priority**: P1
**Blocking**: yes
**Related**: stash@{0} `v16-section-gen-regex-polish-park`

### 选项
- **A** 治本：stash 掉下游 regex 补丁 + 在 V16 REWRITE prompt 加硬约束禁止前置年份同比
- **B** 治标：RFC 补 regex 到 `section_generator.py`（红区变更）
- **C** 现场 RFC 扶正 B 方案

### 推荐
A —— 符合 CLAUDE.md §12"不写关键词/正则黑名单兜底幻觉"

### 上下文
LLM 输出 "2025年同比增长 14.9%" 这种前置年份格式，下游 regex 漏抓。

### [A-001] 2026-04-18 15:45 · 主 CLI

**Decision**: A
**Rationale**: 治本路径符合 CLAUDE.md §12 + §3.1 确定性/概率性计算边界；下游 regex 打补丁永远列不全变体（2025 年后还有 FY2025 / 去年 / 上年等）；骨架型 QC 88.5 非 blocker。
**Follow-up**: v16 CLI 在 REWRITE prompt 加 Rule 16，stash regex 待 Rule 16 回归确认后 drop。已落 `b1c4d13`。

---

## [Q-002] 2026-04-18 23:30 · report(v16) · Phase 1 DoD 调整（评估 runner + 对公素材）

**CLI**: report
**Priority**: P1
**Blocking**: no

### 坑 1
`evaluation/` 无 runner 实现，`agent6_report.yaml` 里的 halluc/evidence 阈值无基线数据可跑。
写 evaluator 是 0→1 建基线（~0.5-1 天），跨 Agent 有复用（Agent2 风控回测）。

### 坑 2
`customer/` 不存在，samples/ 只有模板 docx。对公 matched 真实材料需业务侧提供。

### 推荐
- 坑 1：单独 RFC 派发，不占 v16 Phase 1
- 坑 2：放宽 DoD 到骨架型 QC ≥ 75，对公推 Phase 2

### [A-002] 2026-04-18 23:40 · 主 CLI

**Decision**:
- 坑 1 → 单独 RFC `docs/contracts/rfc/20260418-evaluation-runner.md`，跨 Agent 形态（base_evaluator + per-agent adapter），不占 v16 Phase 1
- 坑 2 → 选 C（放宽 DoD 至骨架型），对公 matched 推 Phase 2 由业务方提供材料

**Rationale**: 评估 runner 是共享基础设施，让 v16 单独写会跟 Agent2 回测重复实现；对公材料不在 CC 边界。

**新 v16 Phase 1 DoD**：
- [ ] 骨架型样本 QC ≥ 75 的完整输出
- [x] prompt 治本 commit（`b1c4d13`）
- [ ] work tree clean

---

## [Q-003] 2026-04-18 23:45 · report(v16) · RESCUE-COMMIT 迁移前后续

**CLI**: report
**Priority**: P0
**Blocking**: no
**Related**: `fa01e89` `b1c4d13`

rescue commit landed on chore/l0-infra 尾部。请示：
1. 留在 chore/l0-infra OK 还是 cherry-pick 到 feat/agent6-v16？
2. demo-agent6 的 samples/ / customer/ 空，如何同步？

### [A-003] 2026-04-18 23:55 · 主 CLI

**Decision**:
1. 留在 `chore/l0-infra` ✅ 不 cherry-pick。等 `feat/tiered-search` 合并或 rebase `feat/agent6-v16` 时自然带过去。
2. samples/ 由主 CLI 的 Pre-Phase-0 assets commit 承载，落到 `chore/l0-infra` 后 `demo-agent6` pull 即可取到。`customer/` 是客户真实材料（合规不入 repo），走 .env 外部挂载。

**Rationale**: 避免分支分裂造成轨迹混乱；samples 属于主 CLI Pre-Phase-0 资产，跨 Agent 共用。
**Follow-up**: 主 CLI 跑完 §P1 5 commit 后发 migration signal 给 v16 CLI。

---

## [Q-004] 2026-04-19 · credit(agent3) · enterprise_profile 契约三方背离裁决

**CLI**: credit
**Priority**: P1
**Blocking**: no（Agent3 当前 demo 端到端已跑通，但 Agent6 真实 handoff 会失配）
**Related**: `docs/contracts/enterprise_profile.md v1.0` · `shared/enterprise_profile.py` · `agent_credit/feature_extractor.py:L72-77` · `demo_data/agent_credit/corp_dingsheng_trade.json`

### 背景
按 UPSTREAM-CONFIGURED 指示 merge `upstream/chore/l0-infra` 拿到契约后做三方对齐，结论三方两阵营：

**阵营 A（嵌套结构，契约 + Agent3 + fixture 对齐）**：
契约 v1.0、`agent_credit/feature_extractor.py` 的 `_extract_corporate`、`demo_data/agent_credit/*.json` fixture 全按 `profile_id` + `business_line` + `financial_anchors.{...}` + `guarantee_info.{...}` + `related_party_info` + `existing_credit.{...}` + `chapters` 嵌套结构消费。

**阵营 B（扁平旧结构，shared/ Pydantic）**：
`shared/enterprise_profile.py` 的 `EnterpriseProfile` 扁平字段（company_name / revenue_latest:str / profit_latest:str / financial_summary:dict / upstream_top5 / controller_share_pct / risk_tags / source_files / updated_at），**无** profile_id / business_line / financial_anchors（子结构）等。`from_kb` 工厂仍产出扁平对象。

**事实核对**：
- Agent3 的 `handoff_demo` 端点直接返回 `json.load(fixture)`，**不经过** `EnterpriseProfile.model_validate()`，所以当前 demo 跑通
- 若 Agent6 真的用 `EnterpriseProfile.model_dump()` 作为 handoff 载荷，Agent3 的 `_extract_corporate` 会读到空 dict → 所有财务 feature 归零 → 决策全错但不报错

### 选项
- **A** 升级 `shared/enterprise_profile.py` 为契约 v1.0 的嵌套结构。破坏性变更，红区 RFC + Agent6 配合改 `from_kb`。
- **B** 契约 v1.0 降级成面向现状的扁平结构。Agent3 / Agent1 / Agent5 全部按旧扁平字段重新接线。
- **C** 契约 v1.0 保留作为"Agent6 ReportJSON 的新形态"（Agent6 v16 产出的 dict/JSON，不是 `shared.EnterpriseProfile` Pydantic 实例）；`shared.EnterpriseProfile` 是 Agent6 **内部**扁平画像，与 handoff payload 是两件事；仅需契约文档顶部加一行澄清。

### 推荐
**C** —— 成本最低、合规 CLAUDE.md §12"不改红区"、不阻塞 Phase 1 交付。

### 当前处置
- Phase 1 交付物按阵营 A 已全绿（16 tests passed + 三红线闸门 PASS）
- 本 Q-004 不 blocking，等主 CLI 裁决后按 A/B/C 调整
- merge commit = `92227f1`；`feat/agent3-productize` 已 push 到 upstream mesh

### [A-004] 2026-04-19 · 主 CLI

**Decision**: C（立即执行）+ Phase 2 启 A 渐进迁移 RFC（延迟执行）

**Rationale**:
1. 契约 v1.0 §一已写"来源：Agent6 报告助手" —— 语义本意就是指 Agent6 v16 的 ReportJSON 产物，不是 `shared/` 那个旧 Pydantic。此三方分歧是历史遗留语义模糊，不是设计错误。
2. 红区不直接改（shared-change-protocol v1.1 §1.1）。B 方案（契约降级）等于废弃主 CLI 已批工作 + 让 Agent1/3/5 已验收交付倒退，不可取。A 方案（shared Pydantic 升级）Phase 1 扛不住长流程。
3. C 是"治标"但**治标正确** —— 明确契约载体边界即可让三方（契约 ↔ Agent3 feature_extractor ↔ fixture）逻辑自洽，零代码改动。
4. `shared.EnterpriseProfile` 孤儿类问题不假，但 Agent6 内部 KB 层 `from_kb` 仍在用，Phase 1 不急于推倒。

**立即执行**：
- 主 CLI 已在 `docs/contracts/enterprise_profile.md` 顶部追加 §〇 语义澄清章节
- 明确消费约束："禁止 `from shared.enterprise_profile import EnterpriseProfile` 作为 handoff 载体反序列化"
- Commit 落 `chore/l0-infra` 后 Agent3 rebase 自取

**Phase 2 延迟执行**：
- 主 CLI 发 RFC 评估 A 方案：`shared.EnterpriseProfile` 嵌套升级 vs 彻底废弃 + 走 runtime JSON schema 校验
- 不早于 evaluation runner Phase A 收尾（避免治理带宽过载）
- 启动前再 RFC，不预定路径

**Agent3 Phase 1 裁决**：
- T1-T7 全绿 + L0 自查 + 三红线闸门 PASS + upstream mesh 配置 → **Phase 1 APPROVED**
- BLE001 lint 债独立 chore PR 已批，不纳 Phase 1，不阻塞
- 授权 `feat/agent3-productize` 继续流转（已 push 到 upstream mesh）

**Follow-up**：
- Agent3 rebase `upstream/chore/l0-infra` 后，他分支的 1113e46（纯 Q-004 append）会与主干冲突；处理方式：preserve 主干版（因为含 A-004），他的 1113e46 可 `git rebase --skip` 或自动消解为空 commit
- Agent3 收到本 A-004 后 commit trailer 带 `Signal: A-004-ACK`

---

## [A-005] 2026-04-19 · 主 CLI · Phase 2 Batch 1 Review 裁决

**性质**：主 CLI 自主 review（非 worker 发问），记录 Phase 2 Batch 1 对 Agent1 / Agent3 的裁决。
**Targets**: `feat/agent3-productize` @ d67576f · `chore/agent3-lint-cleanup` @ 50cf2a7 · `feat/agent1-productize` @ e7ddd86
**Review 文档**：`docs/review/agent3-phase-2-review.md` · `docs/review/agent1-phase-2-batch-1-review.md`

### Agent3 Phase 2 Batch 1 — **APPROVED**

- Task A (d221115)：`py -m evaluation.runner --agent credit` 8/9 PASS（1 Phase C stub），红线闸门全绿，pytest 16/16，无红区改动
- Task B (50cf2a7 on chore/agent3-lint-cleanup)：ruff 全清（--select BLE001 + 全量 passed），2 文件 12+/13- 纯 except 收窄
- `chore/agent3-lint-cleanup` 授权 fast-forward merge 进 `chore/l0-infra`

### Agent1 Phase 2 Batch 1 — **CONDITIONAL-APPROVE**

- Option 4 (d1df143)：handoff contract 8/8 + full suite 29/29，A-004 §〇 合规（无 Pydantic.validate）→ APPROVED
- Option 2 (f2bee8c)：sampling CSV 能跑但 `py -m evaluation.runner --agent channel` 报 `No module named evaluation.runner.__main__` —— **feat/agent1-productize merge base 停在 e9eeaf0，未 rebase 到主 CLI 705326d runner framework**
- commit message 声称能跑的冒烟命令与实测不符

**Required actions (Agent1)**：
1. `git fetch upstream && git rebase upstream/chore/l0-infra`
2. 解 `evaluation/runner/__init__.py` 冲突（保主 CLI framework 版）
3. 重跑冒烟 `py -m evaluation.runner --agent channel`
4. commit trailer `Signal: OPTION-2-REBASE-FIXED`
5. 主 CLI 二次验 → APPROVED

### 质量尾巴

Agent1 的"声称能跑但实测不通"暴露一个协议盲点：commit message 里的冒烟命令未被强制在提交分支上实测。下批 onboarding 增加软规则"冒烟命令必须在提交分支本地实测过再入 commit"。

### Signal

- `Signal: PHASE-2-APPROVED` on Agent3（08f9f6d commit trailer 带）
- `Signal: PHASE-2-BATCH-1-CONDITIONAL-APPROVE` on Agent1（补发，见下面 Q-006）

**注**：08f9f6d 一次 commit 塞两个 signal 违反 `commit-signal-registry.md` §红线。见 Q-006 协议复盘。

---

## [Q-006] 2026-04-19 · 主 CLI 自问 · Phase 2 Batch 1 review 暴露的三个协议盲点

**CLI**: main (self-audit)
**Priority**: P2
**Blocking**: no（历史损伤不修，新规生效前向有效）

### 盲点 1：commit message 声称的冒烟命令未被强制实测
Agent1 Option 2 的 f2bee8c 在 commit message 里写 "冒烟: py -m evaluation.runner --agent channel"，实测报 ImportError（缺 runner framework，f2bee8c 所在分支没 rebase）。commit message 成了"看起来能跑"的幻觉证据。

### 盲点 2：一 commit 多 Signal 违反 registry §红线
主 CLI 自己的 08f9f6d 一次 commit 同时塞 `PHASE-2-APPROVED` 和 `PHASE-2-BATCH-1-CONDITIONAL-APPROVE` 两个 signal。mesh_status.py 只抓最后一条，后者被吞。Agent1 若根据 mesh 看板判断批示会错位。

### 盲点 3：cherry-pick 保留 worker trailer → 主 CLI last signal 语义错
主 CLI 把 chore/agent3-lint-cleanup 的 50cf2a7（trailer `PHASE-2-ONBOARDING-ACK`，worker 语义）cherry-pick 进 chore/l0-infra，导致 mesh_status 显示 main 的 last signal 是 `PHASE-2-ONBOARDING-ACK`——主 CLI 不会 ACK 自己的 onboarding，这是语义污染。

### [A-006] 2026-04-19 · 主 CLI 自决

**立即执行**（本次补救）：
1. Amend 5277a12 → 3febf0f trailer 改为 `Signal: TASK-B-MERGED-TO-L0`（§2 自由命名规则下合法）
2. 补一个独立 commit 带 `Signal: PHASE-2-BATCH-1-CONDITIONAL-APPROVE`（本 Q-006 + Agent1 fix onboarding 同 commit）
3. 08f9f6d 历史损伤不修（已经进 mesh 视野，amend 会 orphan 依赖，得不偿失）

**协议改进**（下一批次起生效）：
- **新硬规则 R-A**：commit message 声称的冒烟命令必须在**提交分支当前 HEAD** 上实测过再入 commit。违反 → review 自动 CONDITIONAL
- **新硬规则 R-B**：一 commit 一 signal（registry 本来就有，但缺强制机制）。主 CLI 自己 commit 前 `git log --format='%b' HEAD` 自检 trailer 数量
- **新硬规则 R-C**：Cherry-pick 主 CLI 必须 amend trailer，从 worker signal 改为主 CLI 视角的 signal（新增 `TASK-<X>-MERGED-TO-L0` / `CHERRY-PICKED-FROM-<SHA>` 类，§2 自由命名已覆盖）

**skill 层改动**（稍后评估，不本次做）：
- `~/.claude/skills/multi-cli-mesh/protocols/commit-signal-registry.md` 增补 R-A / R-B / R-C 示例
- `mesh_status.py` 增 "一 commit 多 signal" 检测告警
- 不本次做的原因：skill 跨项目基础设施，本项目单独证据不足以推全局协议；等 Agent2/4/5 启动再复盘是否持续暴露同类盲点

**落地**：本 A-006 commit 同时补发 Signal: PHASE-2-BATCH-1-CONDITIONAL-APPROVE（补上 08f9f6d 丢失的那个）+ 向 Agent1 下发 fix onboarding。

---

## [Q-010] 2026-04-19 14:30 · shell · archive 动态路由 Stage 2 用 placeholder 而非 import 现有 page 组件

**CLI**: shell（frontend worker · feat/platform-shell）
**Priority**: P2
**Blocking**: no（补录 · Stage 2 实装已按 A 落地于 `e5dad4b`）
**Related**: docs/onboarding/frontend-shell-phase-1.md L78、docs/review/frontend-stage-2-review.md Task C "DEVIATION" 行

### 选项
- **A** `app/archive/[agent]/page.tsx` 是 placeholder stub，Stage 3 再接业务
- **B** onboarding 原方案：`import CreditPage from "@/app/credit/page"` 等六路直接 import
- **C** 抽 `components/workspaces/<Agent>Workspace.tsx` business 组件再挂载

### 推荐
A（已执行）

### 上下文
onboarding L78 原文：「archive/[agent]/page.tsx 直接 import 现有 page 组件」。实装评估时发现三个问题使 B 不可行：
1. 六路现有 `app/<agent>/page.tsx` 全部带 `"use client"` 且在组件内部自行渲染了老顶栏容器，直接 import 会在 platform-shell Masthead 外嵌套一层老顶栏（壳套壳）
2. 老页面全量消费 `--color-paper` / `--color-ink` / `--color-brass`（legacy ink 主题），与 canvas/matcha/dusk/crimson 新壳色系视觉打架
3. 老页面部分依赖 `next/navigation` 的 `usePathname` 作高亮，嵌进 `/archive/[agent]` 路径后语义错位

C 干净但工作量 = 6 agent × ~1-1.5 day 解耦/迁移，属 Stage 3 业务迁移范畴。Stage 2 DoD 只要求「结构完整可导航 + /archive/[agent] 可达」，A 满足即可。

**副作用**（需主 CLI 知晓）：next.config.ts 的 `/credit /channel /alert /compliance /report /riskctrl` 六条 307 redirect 生效后，**Stage 2→3 过渡期老页面实际离线**——直访 `/credit` 会被踢到 placeholder。若此期间需保留老页访问，可临时摘 redirect 或挪到 `/archive-legacy/*`，待决。

### [A-010] 2026-04-19 14:50 · 主 CLI（shell 自决 · review 已裁定 CONDITIONAL 认可方向）

**Decision**: A
**Rationale**: 与 `docs/review/frontend-stage-2-review.md` Task C DEVIATION 行判词一致——"方向合理，现有页面有 `"use client"` + 顶栏耦合，直塞会破壳"。未走 Q/A 是流程瑕疵，不是方向错误；本 Q-010 为事后补录，解 CONDITIONAL。
**Follow-up**: Stage 3 window 首批任务即"六 agent workspace 按 C 方案解耦"，纳入 Stage 3 onboarding DoD。过渡期老页面离线问题若客户 demo 前暴露则回退 redirect，待下一次 review 决定。

---

## [Q-011] 2026-04-19 14:35 · shell · Google Fonts `@import url` 与 Tailwind v4 顺序冲突 → `<link>` 注入

**CLI**: shell（frontend worker · feat/platform-shell）
**Priority**: P2
**Blocking**: no（补录 · Stage 2 实装已按 A 落地于 `e5dad4b`）
**Related**: commit `a4e609e` (Task A 原方案)、`e5dad4b` (Task C 修正)、docs/design/platform-shell-v1.md §3.2 字体策略

### 选项
- **A** 移除 tokens.css 内 `@import url(fonts.googleapis.com/...)`，改 `app/layout.tsx <head>` 内 `<link rel="stylesheet">` 注入（含 preconnect）
- **B** 提前到 Stage 6 自托管 woff2 到 `web/public/fonts/`
- **C** 保留 `@import url` 但全局压到 `globals.css` 第一行（早于 `@import "tailwindcss"`）

### 推荐
A（已执行）

### 上下文
Task A 原方案：tokens.css 顶部 `@import url('https://fonts.googleapis.com/css2?family=Funnel+Display...')` 一行加载 3 family。在 dev 跑起来后 Next.js/Turbopack 报错：
```
@import rules must precede all rules aside from @charset and @layer statements
```
且所有路由 500。

成因：Tailwind v4 的 `@import "tailwindcss"` 在编译阶段会把自身 @import 规则展开到产物 CSS 的最前部（绕过 1-N 万行），外层任何 `@import url()` 即使在源码里写在更靠前位置，展开后会被推到 Tailwind reset 规则之后，触发 CSS @import 语法硬约束（必须先于所有 rule）。

试过的 C 方案（把 `@import url` 写在 `globals.css` 第 1 行、早于 `@import "tailwindcss"`）仍 500——Turbopack 处理 Tailwind v4 inline 展开时不尊重源码位置。

B 干净但属 Stage 6 范畴（银行私有化部署前收敛），现在做相当于提前 4 stage。

A 是最小修复：HTML `<link>` 绕过 CSS 层 @import 约束，字体策略（Stage 2 CDN / Stage 6 自托管）不变，只改加载介质。layout.tsx L66-73 + 预连接 `fonts.googleapis.com` / `fonts.gstatic.com` 已加，首屏字体命中延迟 < 1 跳。

### [A-011] 2026-04-19 14:50 · 主 CLI（shell 自决 · review 已裁定 CONDITIONAL 认可方向）

**Decision**: A
**Rationale**: 与 `docs/review/frontend-stage-2-review.md` Required Actions §3 一致——"字体策略 §3.2 不变"。review 明确只要求补 log、未质疑技术判断。Tailwind v4 inline 展开是 upstream 行为，CSS 源码层无法绕过；A 是现阶段唯一不改字体策略的修法。
**Follow-up**: Stage 6 私有化部署时统一自托管 woff2，届时 `<link>` 与 `@import url` 都不再需要，本决策作废。CLAUDE.md §7 字体栈六变量声明不动。

---

