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

## [Q-007] 2026-04-19 · channel(agent1) · Option 2 rebase 遇到 agent_channel/__init__.py 非 onboarding 约定冲突

**CLI**: channel | **Priority**: P1 | **Blocking**: yes
**详见**：agent1 worktree commit `23272cf`（raised with Signal: NEED-DECISION Q-007）

### 三方分歧

| 来源 | 内容 |
|---|---|
| 合并基 `40a96af` | 仅 `# -*- coding: utf-8 -*-` |
| upstream `c99544f`（lint zero-baseline） | 整文件清空（UP009 删 coding 声明） |
| agent1 `62e7436` | 扩写 Agent1 工具域 docstring |

**选项**：A 保空 / B 保完整 docstring / C 合并版（保 docstring 主体 + 去 coding 行）

### [A-007] 2026-04-19 · 主 CLI

**Decision**: **C**

**Rationale**:
1. docstring 是 CLAUDE.md §3.2 要求的工具域语义资产，不是 lint 能顺手清掉的
2. `c99544f` 删的本意是 UP009 的 coding 声明，不是 docstring
3. C 同时满足 lint zero-baseline + 文档价值，无副作用
4. 操作员轮次已口头裁决同 C，本条正式补录

---

## [Q-008] 2026-04-19 · channel(agent1) · Option 2 rebase 第二次非约定冲突 + 批量策略请示

**CLI**: channel | **Priority**: P1 | **Blocking**: yes
**详见**：agent1 worktree commit `e5db230`（raised with Signal: NEED-DECISION Q-008）

### Q-008.A · evaluation/agent1_channel.yaml add/add 冲突

| 来源 | 形态 |
|---|---|
| upstream `544852d` | 骨架占位（common/domain + baseline stub） |
| agent1 `1e8c770` | 完整型（scenarios + 5 specialized_metrics 含 signal_diversity≥2 硬闸） |

**选项**：A 保完整 + 折叠 upstream baseline / B 保骨架（丢 signal_diversity 硬闸） / C 全手工 merge

### Q-008.B · 批量策略

onboarding 只承诺 1 个预期冲突，实测已 2 个非约定。剩余 13 commits 很可能有同类。
三策略：1 per-file Q / 2 批量授权 / 3 主 CLI 代 rebase。

### [A-008] 2026-04-19 · 主 CLI

**Decision A**: **A**（保完整 + 折叠 upstream baseline 字段）

**Rationale**: upstream `544852d` 是早占位，`1e8c770` 是真实落地；骨架是完整的占位前驱，保完整是合法演进；baseline 字段 3 行融合 0 成本。

**Decision B**: **策略 2 批量授权**

**Rationale**: 策略 1 拖工期（预计 N 次往返）；策略 3 丢 linear history 且破坏"worker 拥有自己分支"原则；策略 2 在红区保护下预授权可预测模式，是效率 vs 安全的帕累托点。

**批量授权规则**（agent1 可直接应用，无需再 abort）：

| 冲突位置 | 处置 |
|---|---|
| `agent_*/__init__.py` / `agent_*/*.py` docstring 级别 | 保 agent1 的 docstring 内容主体，丢 coding 声明等 lint-only 变更 |
| `evaluation/agent1_*.yaml` / `evaluation/agent1_*.{yml,json}` | 保 agent1 的完整配置 + 折叠 upstream 的 `baseline: {last_run, commit}` 等 tracking 字段 |
| `evaluation/runner/**`（adapter 注册、registry） | 保 upstream 的 framework 版 + 合并 agent1 侧新增 agent1 adapter |
| `docs/onboarding/**` / `docs/review/**` / `docs/progress/**` | 保 agent1 的版本（worker 自己的 progress）或 upstream 的（main 写的），按文件命名约定自动判断；二义性仍 abort+Q |
| `shared/**` | **仍 abort + Q**（红区不可自决） |
| `docs/contracts/**` | **仍 abort + Q**（契约红区） |
| `api_server.py` / `agent_*/api/**` | **仍 abort + Q**（agent 间路由红区） |
| 其他未列 | **仍 abort + Q** |

**落地协议**：
- agent1 `git fetch upstream` 拉到本 A-007/A-008 commit
- 按 A-007 C / A-008.A A 先应用已知冲突的解
- `git rebase upstream/chore/l0-infra` 继续，命中红区 abort+Q，命中授权区直接解 + continue
- commit chain: 每个 rebase commit 按原 message 保留；rebase 完抛 `Signal: OPTION-2-REBASE-FIXED`
- 后续 smoke + baseline 同原 onboarding

**审计补偿**（回应 worker 担心）：批量授权不等于无审计——每个实际应用规则的 rebase commit 保留冲突前后 diff，最终 review 我会 spot-check 5 个 resolved conflict 看是否越出规则。越出即 CONDITIONAL-APPROVE。

---

## [Q-009] 2026-04-19 · channel(agent1) · `.gitignore` 冲突（A-008 "其他未列" 触发）+ 规则矩阵扩充请示

**CLI**: channel | **Priority**: P1 | **Blocking**: yes
**详见**：agent1 worktree commit `32fb7ea`（Signal: NEED-DECISION Q-009）

agent1 严格遵守 A-008 遇非授权冲突 abort，第三次卡在 `.gitignore`（两边都是 add-only，upstream 加 `evaluation/results/**/*.json` 规则、agent1 加 `!evaluation/results/1_20260418.yaml` 放行）。剩余 10 commits 很可能继续卡同类良性根文件。

Q-009.A: `.gitignore` 选项 A/B/C（推荐 A：两边并存）
Q-009.B: 扩 A-008 规则矩阵 or 一次性 ACK 剩余非红区冲突

### [A-009] 2026-04-19 · 主 CLI

**Decision A（.gitignore 具体）**: **A** 两边并存

**Rationale**: upstream 加的是全局规则扩展，agent1 加的是单行 baseline 放行；add-only 语义正交，合并零冲突。

**Decision B（规则矩阵扩充）**: **同时采纳"扩矩阵" + "非红区 add-only 自决"**

worker 的纪律是对的（每次停下问）但我矩阵太窄。扩充如下：

#### A-008 规则矩阵扩展版（2026-04-19 起生效）

| 冲突位置 | 处置 | 备注 |
|---|---|---|
| **新增行**（相对 A-008）| | |
| `.gitignore` / `pyproject.toml`（非结构破坏）/ `README.md` / 根目录 `.md` `.cfg` `.toml` `.ini` 等非代码配置 | 两边增补并存（add-only），worker 自决 | `.gitignore` 见 Q-009 范式 |
| **所有其他非红区 add-only 冲突**（两边 diff 只有新增行，无删除/修改） | worker 自决并存，审计侧 spot-check | 兜底条款，避免再为根文件卡 |
| **原 A-008 条目**（保留不变） | | |
| `agent_*/__init__.py` docstring | 保 agent1 主体，丢 lint-only 变更 | |
| `evaluation/agent1_*.yaml` | 保完整 + 折叠 upstream baseline 字段 | |
| `evaluation/runner/**` | 保 framework 版 + 合并 agent1 adapter | |
| `docs/{onboarding,review,progress}/**` | 按文件归属判断 | |
| `shared/**` | **仍 abort + Q** | 红区 |
| `docs/contracts/**` | **仍 abort + Q** | 契约红区 |
| `api_server.py` / `agent_*/api/**` | **仍 abort + Q** | 路由红区 |
| 红区之外任何**非 add-only**（含删除或修改现有行） | **仍 abort + Q** | 风险不对称 |

**兜底条款的 spot-check 加重**：最终 review 我在 10 个 resolved conflict 里抽 5 个，原"越出规则即 CONDITIONAL" 升级为"越出规则或出现 add-only 误判即 REJECTED，整轮 rebase 重做"。worker 被授权更大 → 审计刀更重，对称。

**落地协议**（给 agent1）：
- `git fetch upstream` 拉本 A-009 commit
- Q-009.A `.gitignore` 按 A 合并两边 add-only
- 继续 rebase，按**扩展后矩阵**处理剩余 10 commits
- 所有 add-only 非红区冲突自决（包含 `.gitignore` 及其他根目录非代码文件）
- 红区或非 add-only 仍 abort + Q
- 全绿抛 `Signal: OPTION-2-REBASE-FIXED`，随后原 onboarding 的 smoke + baseline + final Signal

---

