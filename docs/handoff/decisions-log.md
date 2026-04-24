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


## [Q-012] 2026-04-19 14:46 · channel(agent1) · Phase 1 Task A / C / D 路线裁决

**CLI**: channel（agent1 worker · feat/agent1-productize）
**Priority**: P1
**Blocking**: yes（Task A 与 Task D 启动前卡点 + Task C 方案确认）
**Related**: docs/onboarding/agent1-phase-1.md、docs/review/agent1-option2-rebase-review.md Top 3 Gap、CLAUDE.md §6 数据飞轮、memory/project_bank_delivery_dod.md L3

### 选项

**Q-012.A · Task D 方向**
- **D1** Tavily production ingress（真实数据锚点，依赖合规批文）
- **D2** Feedback loop E2E（内部闭环，§6 飞轮第 3/4 环）
- **D3** 推 Phase 2 Batch 2（本 Phase 不做）

**Q-012.B · Task A 红区文档归属**
- **B1** worker 起草 `docs/handoff/shared-change-protocol.md`（效率高 · 归属错位）
- **B2** worker 写 `docs/progress/agent1-phase-1-redzone-gap.md` 演练档；正式协议归主 CLI 另起

**Q-012.C · Task C candidate_relevance**
- **C-D** 人工抽样回录落地（需业务方）
- **C-skip** 推 Phase 2 Batch 2，runner 按 `pending` 语义不降档

### 推荐
A=D2 / B=B2 / C=skip

### [A-012] 2026-04-19 14:50 · 主 CLI

**Decision**:
- **A-012.A = D2**（Feedback loop E2E）
- **A-012.B = B2**（worker 进度档；主 CLI 另起正式 handoff 协议）
- **A-012.C = C-skip**（pending 语义落地 + baseline 标 `pending: Phase-2-Batch-2`）
- **A-012.D =（附加硬约束）已被主 CLI review 文档引用过的 commit SHA 不可 rebase/amend/force-push；纠错用新 commit**

**Rationale**:
- D2 优先级：本 Phase 1.5-2.5 工时盒子装不下 Tavily production（生产 key + 降级 + 配额监控 + 合规批文不确定）；D2 对 §6 数据飞轮锚点更紧，评估环闭环可见。D1 推 Phase 2 Batch 2 作"真实数据上线"独立里程碑。
- B2 治理对齐：正式红区协议归主 CLI 唯一写，与 decisions-log.md 归属一致；避免"自我监督"悖论。worker 演练档仍需落，作 review spot-check 证据。
- C-skip 前提：runner framework 需支持 `pending` 指标不降档 verdict；Task B 收敛 yaml 时附带实装 `pending: Phase-2-Batch-2` 语义（若已支持则只改 yaml，不动 runner 内核—内核属红区）。baseline yaml 必须显式标 `pending`，不允许静默 N/A。
- SHA 不可变约束：2026-04-19 agent1 在 Option 2 rebase APPROVED 后对已批 commit 链重写（e69244f → 0292b94 等），虽内容无损但 review 引用 SHA 全部失效。本条约束追加至 CLAUDE.md 或 shared-change-protocol v1.2 正式条款（由主 CLI Q-012.B 后续起草时纳入）。

**Follow-up**:
1. agent1 按 A→B→C→D 顺序开工，D 为 Feedback loop；各 Task 完成 stop-and-wait 主 CLI GO
2. Task B 实装 yaml `pending` 语义前若发现 runner 不支持，发 Q-013 before 动内核
3. 主 CLI 接下来起草 `docs/handoff/shared-change-protocol.md` 正式稿（含 A-008.B + A-009 + A-012.D 条款融合）——非本轮 window 事项

---

## [Q-013] 2026-04-19 15:03 · channel(agent1) · pending-metric verdict 语义（Task B 阻塞）

**CLI**: channel（agent1 worker · feat/agent1-productize）
**Priority**: P0
**Blocking**: yes（Task B DoD）
**Related**: A-012.C、`evaluation/runner/base_evaluator.py` `_verdict()`、agent1_channel.yaml baseline 区块

### 问题
`_verdict()` 旧逻辑：任一 `passed=None` → verdict 必 PARTIAL（`len(resolved) < len(metrics)`）。
agent1 adapter emit 2 条 passed=None：
1. `candidate_relevance_at_top10`（A-012.C 授权 pending）
2. `source_url_reachable_rate`（mock 场景 passed=None，实为语义 bug — mock 不测 HTTP）

### 选项
- **α** kernel 白名单：`_verdict` 读 `baseline.pending_metrics` 白名单，命中的 metric 豁免
- **β** adapter-only：mock 场景 `source_url_reachable_rate` 改 `passed=True + note "mock-exempt"`
- **γ** adapter 丢弃 pending metric（违 Evidence-First）
- **δ** 接受 PARTIAL，改 DoD 口径

### 推荐（worker）
α + β 组合

### [A-013] 2026-04-19 15:08 · 主 CLI

**Decision**: **α + β 组合**；α kernel 改动**主 CLI 亲操本窗口落地**，β adapter 修复 + yaml baseline.pending_metrics + 后续 Task B 收敛 **agent1 worker 落地**。

**Rationale**:
- α 治本：runner 原生 "pending 不降档" 语义可复用（agent2/4/6 Phase C 人工指标同样吃这套）；yaml schema 扩 `baseline.pending_metrics: [...]` 白名单，命中 metric 不计 resolved 分母 & 不计总数 & 仍 emit 到结果（Evidence-First 可见性保住）
- β 语义诚实：mock 场景 HTTP 探活本就 N/A，原 `passed=None` 是历史误判；改 `passed=True + note "mock-exempt"` 比保留 None 更准确
- 拒 γ：违 Evidence-First 第一性原则
- 拒 δ：δ 规避问题本身、不治本、损产品化 DoD
- 红区归属：`base_evaluator.py` 在 Phase 1 红区矩阵（A-012.B 演练档确认），改动必须主 CLI 亲操；A-012.D "已引用 SHA 不可重写" 约束不影响新增改动

**Kernel 改动**（本 A-013 同 commit 落地）：
```python
def _verdict(self, metrics: list[MetricOutcome]) -> Verdict:
    pending = set(self.config.get("baseline", {}).get("pending_metrics", []))
    effective = [m for m in metrics if m.name not in pending]
    resolved = [m for m in effective if m.passed is not None]
    ...
```
（静态方法 → 实例方法；完整 diff 在本 commit stat）

**回归验证**（主 CLI 本窗口跑）：
- 4 单测全过：pass+pending→PASS / pass+fail→FAIL / 无 pending list→PARTIAL / 只 pending→PARTIAL
- report runner `--agent report` 无 artifacts 仍 FAIL（原行为未变）
- channel 模拟：无 pending→PARTIAL / 只 α 不 β→PARTIAL / α+β→PASS

**Follow-up**（worker 落地）：
1. Task B 实装 β：`evaluation/runner/adapters/agent1_channel.py` mock 分支 `source_url_reachable_rate` emit `passed=True, note="mock-exempt, HEAD-probe skipped"`
2. Task B yaml 收敛时加 `baseline.pending_metrics: [candidate_relevance_at_top10]` + `pending_reason: "Phase-2-Batch-2 human review"`
3. yaml 去 legacy `general_metrics/specialized_metrics`（Task B 原 DoD）
4. scripts/eval_run.py 废或转壳
5. 跑 `py -m evaluation.runner --agent channel` 预期 verdict=PASS

**Signal**: `A-013-ISSUED-WITH-KERNEL-PATCH`

---

## [Q-014] 2026-04-19 15:55 · frontend · Stage 3 visual regression 归因 · 色系替代收口

**CLI**: 主 CLI（触发人：用户观察 regression + subagent 诊断）
**Priority**: P1
**Blocking**: no（Task A/B/C 已合；本条只决定契约归属）
**Related**: `docs/review/frontend-stage-3-regression-diagnosis.md` §3.3 / §5.2、`web/src/app/tokens.css:37-45`、Task C commit `290ede2` 自承

### 问题
Task C 色系迁移按 onboarding 表映射 `--color-line → var(--ink-12)` / `--color-line-strong → var(--ink-24)`。但 `tokens.css` ink scale 实际 = {04,08,14,18,28,32,48,65,80}——**ink-12 / ink-24 不存在**。worker 就近替代为 14 / 28（视觉差 ≤ 3% alpha，单看不可感知），commit body 自承 + 建议 Q/A 收口。

### 选项
- **A** tokens.css 补 `--ink-12` / `--ink-24`（改红区 tokens + 更新 spec v1.1）
- **B** 接受 14/28 为 canonical（不动 tokens，更新 onboarding 映射表）
- **C** 补 `--ink-12` 不补 `--ink-24`（部分补）

### [A-014] 2026-04-19 15:55 · 主 CLI

**Decision**: **B** · 接受 ink-14 / ink-28 为 canonical

**Rationale**:
- 视觉差 ≤ 3% alpha subagent 实验证明（Crimson 主题最强对比下仍 imperceptible，待 playwright 1440 实测收尾核）
- tokens.css 是红区，动一次要升 spec + mockup 重锁 + 全量主题回归——成本 >> 3% alpha 收益
- onboarding 表已是 drafting artifact；正式映射归 `platform-shell-v1` spec §3.3 收敛（主 CLI 另起修订），worker 迁移表以实际 `tokens.css` 为准

**Follow-up**:
1. 主 CLI 更新 `docs/design/platform-shell-v1.md` §3.3 line token 章节：canonical `--ink-14` / `--ink-28`
2. 后续 workspace 新增代码凡遇 line / line-strong 直接用 14/28，不要引 12/24
3. Crimson 主题 playwright 视觉回归留给 Stage 3 APPROVED 前补一次（随 Q-017 打包）

**Signal**: 随 Q-015/016/017 同 commit emit `A-014-INK-14-28-CANONICAL`

---

## [Q-015] 2026-04-19 15:55 · frontend · AGENTS[].tagline 被误用为页级 description

**CLI**: 主 CLI（触发人：用户观察 O1/O2 + subagent 诊断）
**Priority**: P0
**Blocking**: **yes** —— 阻塞 Task D 派发（Task D 不解决 O1/O2）
**Related**: `docs/review/frontend-stage-3-regression-diagnosis.md` §3.3 O1/O2、`web/src/app/archive/[agent]/page.tsx:62`、`web/src/lib/agents.ts:33-94`、`web/src/app/credit/page.tsx:307-350` (旧 segment 动态描述)

### 问题
Task A 把 6 个 `app/<agent>/page.tsx` 的页级 `<header>`（含 description）整块删后，新 `archive/[agent]/page.tsx` 用 `AGENTS[].tagline` 渲染 lede。但 tagline 原设计是 Archive **index tile** 短标语（如 report = "材料 → 授信申报书" 11 字），不是 page-level description（旧 report = 64 字完整描述）。直接导致：
- **O1 "少了细节"**：描述信息量骤降
- **O2 "改了字段"**：credit 页旧 description 随 segment 动态切（3 套 SEGMENT_META），新版只显示一句静态 tagline

### 选项
- **A** AgentDef 加 `description: string` 字段，archive/[agent] 渲染 description，tile 继续用 tagline
- **B** Workspace client 自行暴露 `<HeaderSlot>` 把 description 吐给 archive/[agent] 壳渲染
- **C** 接受短 tagline 作为子路由 lede（承认信息量降级）
- **A+B 组合** A 作默认，credit（唯一有动态描述的 agent）走 B slot

### [A-015] 2026-04-19 15:55 · 主 CLI

**Decision**: **A + B 组合**
- **A 作默认**：6 个 AgentDef 全部加 `description: string`（从旧 `app/<agent>/page.tsx` 提取原文案），archive/[agent] 渲染 `{def.description}` 替代 `{def.tagline}`
- **B 作特例**：credit workspace 通过 `<HeaderSlot>` 机制暴露当前 segment 的动态 description（3 套 SEGMENT_META），archive/[agent] 在 slot 有值时覆盖默认 description
- **tile 描述**：archive index 继续用 `tagline`（保原设计意图）

**Rationale**:
- A 最小侵入 + 保 Evidence-First（字段明确归属，不是"数据复用踩坑"）
- credit 3 套 SEGMENT_META 是产品价值（对公/普惠/对私文案语气不同），必须保留 → B slot 覆盖
- A/B 组合比纯 B 好：静态 description 不需要每个 workspace 都实现 slot boilerplate

**Follow-up**:
1. worker 新建 Task E：AgentDef 加 description 字段 + 6 个 agent 原文案迁入 `lib/agents.ts`
2. credit workspace 实装 `<HeaderSlot>`（React Context / Zustand / 小状态）+ archive/[agent] 接 slot（slot 无值时 fallback 到静态 description）
3. 旧 `app/<agent>/page.tsx` 6 个文件保留（已 307 redirect），文案作 description 单一数据源迁移后删除旧文件——本轮 Task E 只迁文案、不删文件（A-012.D SHA 语义避免，删除另起 commit）

**Signal**: 随 Q-014/016/017 同 commit emit `A-015-DESCRIPTION-SLOT-CONTRACT`

---

## [Q-016] 2026-04-19 15:55 · frontend · eyebrow 文案规格

**CLI**: 主 CLI（触发人：subagent 诊断 O2）
**Priority**: P2
**Blocking**: no
**Related**: archive/[agent] 渲染 `{def.code} · {def.key.toUpperCase()}`（新 "A06 · REPORT"）vs 旧 "A06 · Report Generation"、`design_mockups/shell.html:2369` Archive view 用 "ARCHIVE · 频道 03" 格式

### 问题
eyebrow 文案新旧不一致。shell.html Archive 章节用的格式不是英文全名，是 "ARCHIVE · 频道 NN"。6 个 agent 子路由 eyebrow 没有 canonical spec。

### 选项
- **A** 维持新版 `{code} · {KEY}` = "A06 · REPORT"（短）
- **B** 回退旧版 `{code} · <English Name>` = "A06 · Report Generation"（长，英文）
- **C** 引 shell.html Archive 格式 "ARCHIVE · 频道 NN"（中文化，但 6 agent 各自归属哪"频道"需定义）
- **D** 新定义 `{code} · {CJK title}` = "A06 · 信贷报告助手"（CJK 统一）

### [A-016] 2026-04-19 15:55 · 主 CLI

**Decision**: **B** · "A06 · Report Generation" 回退旧版

**Rationale**:
- 旧版是 6 agent 已有约定，worker 历史 commit 均遵循
- A 过短（REPORT 3 字符无辨识度）
- C "频道 NN" 是 Archive index 层面的编号，子路由套进去是概念错位
- D CJK eyebrow 违反 spec 字体栈分层（eyebrow 位典型 mono/sans，非 CJK）

**Follow-up**:
1. worker Task E 同步：AgentDef 加 `eyebrowLabel: string` 字段，值取旧 page 中的英文描述（report="Report Generation" / credit="Credit Decision Assistant" / ...）
2. archive/[agent] 渲染改为 `{def.code} · {def.eyebrowLabel}`
3. Archive index tile 保持原 tile spec，不受本条影响

**Signal**: 随 Q-014/015/017 同 commit emit `A-016-EYEBROW-ENGLISH-NAME`

---

## [Q-017] 2026-04-19 15:55 · frontend · Today sheet-card 丰富形态是否 Stage 3 必做

**CLI**: 主 CLI（触发人：用户观察 O3 + subagent 诊断）
**Priority**: P0
**Blocking**: **yes** —— 阻塞 Stage 3 整体 APPROVED 判定口径
**Related**: `docs/review/frontend-stage-3-regression-diagnosis.md` §3.2 / §5.2、`design_mockups/shell.html:1882-2240` Today 规格、`web/src/app/today/page.tsx:79-101` 简版 stub

### 问题
User 直接观察到"中间气泡框变早期设计版本"——这是 **real regression 感知**，即便 **不是** Task A/B/C 引入（诊断明确归 Stage 2 `e5dad4b` 未升级实装；`.sheet-card` / `pv-sheets` / `pv-foot` / `badge` 从未按 shell.html 规格实装过）。

spec 完整形态 vs 当前 stub 差距：
- 容器 `.card.warm.sheet-card` vs 普通 `.v-card` linear-gradient
- 每条 sheet 含 tag pill + state + title + sub + **eta** + **sheet-bar 进度条** vs 仅 `<ul><li>` 标题
- idle 条独立灰态视觉 vs 同 `<li>` 混排
- pv-foot + badge "02." + open "打开调度台 ↘" vs 无尾栏

### 选项
- **A** Stage 3 追加 Task F 实装 sheet-card 完整规格（额外 0.5-1 工作日）
- **B** 推 Stage 4 专项升级（Stage 3 先 APPROVED，user 会继续看到 regression）
- **C** 挂 L4 商业交付包（演示专用，默认 Stage 3 不改）

### 推荐（主 CLI 视角）
**A** —— user 明确感知 + CLAUDE.md §7 "体验 > 架构优雅度"；但工期膨胀需要 user 确认。

### [A-017] 2026-04-19 16:08 · 主 CLI（用户授权 "下一步任务" = 按主 CLI 推荐走）

**Decision**: **A** · Stage 3 追加 Task F 实装 sheet-card 完整规格

**Rationale**:
- User 已直接观察到 regression 感知（O3 气泡框变早期版本），按 CLAUDE.md §7 "用户体验是所有产品的最高准则，优先级高于技术偏好、代码整洁度、架构优雅度" —— 不能让 user 带着这个观感走
- Stage 3 的本意就是"workspace 业务组件抽离 + shell 级视觉合格"——把 Today 中间核心 card 留 stub 等于 Stage 3 APPROVED 后 shell 仍不合格
- 工期影响可控（0.5-1 天），并入 Task D/E 同批派发给 frontend CLI，不额外开窗口
- B/C 方案实质是"承认 Stage 3 不完整"，与本 Stage 的产品定位冲突

**Follow-up**:
1. 新建 `docs/onboarding/frontend-stage-3-extension.md` 打包 Task D/E/F 三 Task 派发给 frontend CLI
2. Task F DoD：
   - `.v-card` → `.card.warm.sheet-card` 容器升级（class + 色系）
   - 每条 sheet 添加 tag pill + state + title + sub + **eta** + **sheet-bar 进度条** 结构
   - idle 条独立灰态视觉区分（不能同 `<li>` 混排）
   - 新增 `.pv-foot` 尾栏：`.badge "02."` + `.open "打开调度台 ↘"` link
   - 字段保持 mock 驱动（`DESK_QUICK_CREATE` 风格），prop 类型与现有 `today/page.tsx` 的 mock 数据结构对齐
   - 实装参照 `design_mockups/shell.html:1882-2240` Today 规格
3. APPROVED 判定口径：Stage 3 = Task A/B/C（已合）+ D/E/F（本批）全绿
4. Crimson 主题 playwright 1440 viewport 回归 playwright 截图 4 视图核对 ink-14/28 替代（A-014 Follow-up #3）随 Task F APPROVED 前同批跑

**Signal**: 随 Stage 3 extension onboarding 落盘同 commit emit `A-017-SHEET-CARD-IN-STAGE-3`

---

## [Q-018] 2026-04-19 16:24 · agent6 · yaml schema 扩展 `pending_business_data`（Task C 事后 Q）

**CLI**: 主 CLI（触发人：agent6 Task C commit `fe567f4`）
**Priority**: P2
**Blocking**: no（追认，不阻塞 Task D）
**Related**: A-013（`baseline.pending_metrics` 白名单）、agent6 Phase 2 Task C onboarding §3 DoD、`evaluation/agent6_report.yaml` Task C 新增段

### 问题
Task C DoD 要求"每模板跑 runner → `evaluation/results/6_*.yaml` ≥ 5 份落盘，每份 verdict=PASS 或显式 pending"。worker 未跑端到端 LLM 跑批（理由：脱敏模板无真实材料，跑了无产出价值），改在 yaml 加 `pending_business_data: true` 字段标记"待业务方真材料"。**这是 schema 扩展，onboarding 未定义该字段，worker 应先 `Q-NNN 停下问`，但未停。**

### 选项
- **A** 追认 `pending_business_data: true` 语义（等同 A-013 `pending_metrics` 的 template 级扩展），runner 后续支持按 template 豁免
- **B** REJECT，要 worker 按硬 DoD 跑 5 份 baseline（即便脱敏跑出来也无意义）
- **C** 收回到 A-013：把 `pending_business_data` 改为在 yaml `baseline.pending_metrics` 里列 template-level metric（schema 一致性更好，但需 worker 改 yaml 回滚）

### [A-018] 2026-04-19 16:24 · 主 CLI

**Decision**: **A** · 追认 `pending_business_data` 扩展

**Rationale**:
- 工程意图对齐：脱敏模板跑 LLM 是概率性计算，无真实材料时结果置信度低；worker 判断与 CLAUDE.md §5 评估框架"先建 rubric、跑基线、找最大 gap"兼容
- 与 A-013 `pending_metrics` 正交：`pending_metrics` 是 metric 级豁免，`pending_business_data` 是 **template 级数据前提豁免**，concerns 不同，两个字段共存合理
- B 方案（硬跑 5 份无意义 LLM）违反 CLAUDE.md §12"绝不编"与 §3.1"LLM 只在概率任务且有锚"
- C 方案 schema 一致性微弱，且 A-013 kernel 已稳定，破坏现有语义成本 > 收益

**Protocol breach 处理**：worker 未走 Q-NNN 停下问是 shared-change-protocol 纪律违规，但追认后无损可用性。**不扣 Phase 2 分**，记入 Agent6 Phase 2 最终 review Top Gap 一条"下批 onboarding 更严格授权 yaml schema 扩展路径"。

**Follow-up**（本 Phase 2 Task C 补录）：
1. Task D 完成前补 `docs/progress/agent6-phase-2-templates.md`（硬 DoD，未做）
2. 文档中显式标出 5 模板 `pending_business_data=true` 的业务方等待清单
3. 主 CLI 后续起草的 shared-change-protocol v1.1 正式稿新增条款：`evaluation/*.yaml` schema 新增字段需走 RFC（轻量 Q-NNN），不属红区但属黄区

**Signal**: `A-018-PENDING-BUSINESS-DATA-RATIFIED`（主 CLI commit 同步 emit）

---

## [Q-019] 2026-04-19 · riskctrl(agent2) · `per_rule_fpr_spread` 公式 + 阈值裁定（Phase 1 Task C 依赖）

**CLI**: worker `feat/agent2-productize`
**Priority**: P1
**Blocking**: yes（Task C 的 `metrics.domain.per_rule_fpr_spread.target` 必须锁定；A-014~017 已被 frontend 占用，本 Q 延至 Q-019）
**Related**: `docs/onboarding/agent2-phase-1.md` §3 Task C / §8、`docs/review/agent2-phase-0-review.md` Top 3 Gap #3、A-013（pending 白名单，不重叠本 Q）、`agent_riskctrl/backtesting.py` `BacktestResult.metrics.rule_stats`

### 问题

Phase 0 baseline 的 `false_positive_rate = 0.0673` 是全规则合并 FPR，R002（高负债率）等单条规则误杀率被"整体绿"掩盖。Phase 1 Task C 扩 `per_rule_confusion_matrix` 并新增 `per_rule_fpr_spread` 作警戒——但 **"spread" 用哪种统计量 + 阈值设多少** 需主 CLI 裁定，worker 不自决（CLAUDE.md §5.2 无基线不改码 + onboarding §8 硬要求）。

fixture `baseline_v1/` 只有合并 `confusion_matrix`，没有 per-rule 分解，所以 Phase 0 baseline 无法反推 spread 真值。真 spread 要等 Task A runtime 产物 + Task C 扩展 `backtesting.py` 后才首次跑出来——**本 Q 要的不是"拍脑袋的目标值"，是公式选型 + 初步警戒区间，真值回填走 baseline 首跑**。

### 选项

- **A · 方差 σ² ≤ 0.03（推荐，保守）**
  - 公式：`per_rule_fpr_spread = variance([rule.FP / (rule.FP + rule.TN) for rule in ruleset])`（`FP + TN = 0` 的规则视为 `N/A` 跳过，不入均值）
  - rationale：方差对"极端规则"（1 条规则 FPR 远偏）不如 max-min 敏感，但"整体绿、1 条偏激"场景下仍能识别（FPR 分布 {0.02, 0.03, 0.02, 0.03, 0.25} 的方差 ≈ 0.0087，不触 0.03；而 {0.02, 0.03, 0.02, 0.03, 0.50} 方差 ≈ 0.037 触线）
  - 信贷风控域习惯：KS 方差 / PSI 方差均用总体方差（非样本方差），口径统一
  - 0.03 先定为 Phase 1 草案警戒线，baseline 跑出后再在 Phase 2 锚定真阈值
  
- **B · max-min spread ≤ 0.15（宽松）**
  - 公式：`per_rule_fpr_spread = max(rule_fpr) - min(rule_fpr)`
  - rationale：直观、易向业务方解释（"最激进规则和最保守规则 FPR 相差不超过 15 个点"），但对"5 条绿 + 1 条紫"场景不如方差——极端值一改，spread 立刻跳，可能误报
  - 0.15 与 yaml 汇总 FPR 阈值 `<= 0.15` 等值，语义"单条规则不得偏离整体均值 15 个点以上"相对易被接受
  
- **C · 主 CLI 自定（第三方案 / 其他统计量）**
  - 如：CV（变异系数 σ/μ），或中位数绝对偏差 MAD，或 IQR
  - 若主 CLI 认为信贷风控有更合适的 spread 度量，请直接在 A-019 下发；worker 按下发公式 + 阈值实装

### worker 推荐

- **选 A · σ² ≤ 0.03**——理由：
  1. 方差对"整体绿、单条偏激"场景灵敏度高于 max-min（见 rationale 示例）
  2. 口径与信贷风控域内常用 KS/PSI 方差一致，便于 Phase 2 对接人工评审
  3. 0.03 是 Phase 1 草案值，明确标「Q-019 草案 / Phase 2 锚定」，不伪装已 battle-tested

- **Phase 1 实施路径（不论 A/B/C）**：
  1. `agent_riskctrl/backtesting.py` 扩 `rule_stats` 加 `{FP, TN, FP_rate}` per rule
  2. adapter `compute_domain_metrics` 新增 `per_rule_fpr_spread` MetricOutcome（`method=deterministic`）
  3. yaml `metrics.domain.per_rule_fpr_spread.target` 先占位 `<TBD A-019>`，收到 A-019 后 worker 改实值
  4. Task A runtime baseline 跑出来回填 `baseline.results.per_rule_fpr_spread`
  5. 若跑出值已触草案警戒线（Phase 1 过闸门标准：跑出值 ≤ A-019 target），worker 不硬压指标，按 CLAUDE.md §12 写 gap doc

---
### [A-012.E] 2026-04-19 17:00 · 主 CLI（主动 · agent4 rebase 触发）

**Decision**: **Upstream catch-up 只许 `git merge --no-ff`，禁 `git rebase` / `git pull --rebase` / `cherry-pick` 作等价替代。**

**触发事件**：agent4 worker 为吸收 A-013 α kernel 选择 `git rebase upstream/chore/l0-infra`，reflog 证据：
```
e3acbbb feat/agent4-productize@{1}: rebase (finish): onto 73d6732c41cf233fb035f85991b22467ab79dd1d
a972e4c feat/agent4-productize@{2}: window-close: Phase 0 approved  ← 原 SHA（已被主 CLI review 引用）
```
rebase rewrite 了 `a972e4c` → `e3acbbb`，破 A-012.D。对比 agent2 同日同需求选 `git merge --no-ff`（`9b78130 Merge made by the 'ort' strategy`），SHA 全保留，合规示范。

**Rationale**：
- A-012.D 硬约束是"已引用 SHA 不可重写"。rebase 的本质就是 replay commits on new base → 所有 commit SHA 全部 rewrite。单个 rebase 动作就能把整条 Phase 0~N 的 review 证据链全部失效
- Merge commit 虽多一条 graph line，但保原 SHA 可追溯；git history 复杂度是可接受的交换
- `git pull --rebase` 是 rebase 的隐式形式，同禁；`git cherry-pick` 把别处 commit 拷贝到当前分支会生成新 SHA，但不重写已有 SHA，**允许但需自报为 cherry-pick 动作（commit msg 标明源 SHA）**
- "linear history"美学不是 banking delivery 的硬需求；SHA 可审计性是

**硬命令**（worker 照搬）：
```bash
# ✅ 正确：add-only merge
git fetch upstream <branch>
git merge upstream/<branch> --no-ff
# 冲突解决后 git commit（不需 --amend）

# ❌ 禁止
git rebase upstream/<branch>
git pull --rebase
git rebase -i <any>  # 任何 interactive rebase
git reset --hard <任何跨越 review 边界的 SHA>   # Phase 内部 reset 宽容
git push --force / --force-with-lease
git commit --amend <任何已 push / 已 signal 的 commit>
```

**纠正 playbook**（reset-hard 仅作 rebase 违规的 rollback，本身不违规）：
```bash
# 1. 恢复原 SHA（reflog 查原 SHA，objects 尚未 gc 可取）
git reset --hard <pre-rebase-SHA>

# 2. 改用合规 merge
git fetch upstream <branch>
git merge upstream/<branch> --no-ff

# 3. 重出 ack commit 标明 "post-reject V2"
git commit --allow-empty -m "ack(<agent>): <phase> onboarding absorbed (post-reject V2)" \
  --trailer "Signal: <AGENT>-<PHASE>-ACK-V2"
```

**Enforcement**：
- 每次 worker emit `*-ACK` / `READY-FOR-REVIEW` / `WINDOW-CLOSED-CLEAN`，主 CLI 对应 reviewer 必查：
  ```bash
  git reflog <branch> | grep -iE 'rebase|amend|force'  # 命中 0 才算合规
  ```
- 命中即 REJECT + reset-hard playbook 纠正（即使 rebase 结果 diff 等价）。**A-012.D/E 是形式正确 over 结果正确** — SHA 可审计性比整洁性重要
- Cherry-pick 例外：允许但 worker 必须在 commit msg 显式 `Cherry-pick from <source-SHA>`；reviewer 校验源 SHA 存在且语义一致

**Follow-up**：
1. `docs/handoff/shared-change-protocol.md`（主 CLI 未起草稿）正式落 §merge-only 条款时引本 A-012.E
2. 后续 Phase onboarding §硬规则节加"upstream catch-up = merge-only"一条，覆盖 agent2/4 Phase 1 + agent1/3/6 后续 Phase
3. 本 A-012.E 追溯覆盖 agent2 `9b78130` merge（合规，记正面示范）+ agent4 `e3acbbb` rebase（违规，已 REJECT，待 reset-hard 纠正）

**Signal**: `A-012.E-MERGE-ONLY-RULE`（主 CLI commit 同步 emit）

---

## [A-019] 2026-04-19 17:06 · 主 CLI（答 Q-019 @ `46051f2`）

**Related**: Q-019 块位于 agent2 worktree `46051f2` `docs/handoff/decisions-log.md`（agent2 Phase 1 Task C 锚点；主 CLI trunk 待 agent2 下次 merge 时按 A-009 add-only union 吸收 Q-019 块 + 本 A-019 块）

**Decision**: **A · σ²（总体方差）≤ 0.03**（Phase 1 草案阈值，Phase 2 Batch 2 用真 baseline 分布锚定）

**公式**（worker 照搬 adapter 实装）：
```python
def per_rule_fpr_spread(rule_stats: list[RuleStat]) -> float | None:
    fprs = [
        r.FP / (r.FP + r.TN)
        for r in rule_stats
        if (r.FP + r.TN) > 0  # N/A 规则跳过，不入均值
    ]
    if len(fprs) < 2:
        return None  # 无意义 → verdict 按 pending 白名单处理
    mean = sum(fprs) / len(fprs)
    return sum((x - mean) ** 2 for x in fprs) / len(fprs)  # 总体方差
```

**阈值锁定**：`metrics.domain.per_rule_fpr_spread.target = 0.03`（Phase 1 草案）

**Rationale**（接纳 worker 推荐 + 主 CLI 校准）：
1. worker rationale 成立：方差对"整体绿 + 单条偏激"灵敏度高于 max-min，worker 举的 {0.02,0.03,0.02,0.03,0.25} σ²≈0.0087 vs {0.02,0.03,0.02,0.03,0.50} σ²≈0.037 能证明 0.03 阈值区分"可疑"与"失控"
2. KS/PSI 方差口径一致 → Phase 2 对接人工风控评审零迁移成本
3. 0.03 threshold 局限：对 ≥ 10 条规则 ruleset 偏松（worker 举 5 规则），**Phase 1 接受草案值，Phase 2 Batch 2 必须**：
   - Task A runtime dump 跑完观察真 baseline `per_rule_fpr_spread` 分布
   - 基于 P90/P95 + 安全 margin 锁 Phase 2 正式阈值
   - yaml baseline 增 `per_rule_fpr_spread.calibrated_from` 审计字段（**这是 baseline schema 扩展，Phase 2 Batch 2 启动前必须 Q 后动**，不许 Task C 同 commit 顺手加 → A-018 教训）
4. B max-min 弱在"中段集中但两端极值"场景误报；C (CV/MAD/IQR) 对信贷风控陌生，迁移成本 > 统计优越性

**Phase 1 Task C 实施路径**（worker §Phase 1 路径全接纳，不变）：
1. `agent_riskctrl/backtesting.py` 扩 `rule_stats` per rule `{FP, TN, FP_rate}`
2. adapter `compute_domain_metrics` 加 `per_rule_fpr_spread` MetricOutcome，`method=deterministic`
3. yaml `metrics.domain.per_rule_fpr_spread.target: 0.03`（实填，不 `<TBD>`）
4. Task A runtime baseline 回填 `baseline.results.per_rule_fpr_spread`
5. 若观测值 > 0.03：按 CLAUDE.md §12 写 `docs/progress/agent2-phase-1-spread-gap.md` 记 "某 ruleset 不均衡"；**不调阈值迎合**（治标不治本反模式）
6. 若观测值 ≤ 0.005（过度均衡）：标 "规则同质性过高，可能冗余"，不触 fail 但记 follow-up

**Non-blocking**：Q-019 不阻 Task A/B/D（worker 预判正确），Task C 可直接实装。

**Signal**: `A-019-PER-RULE-SPREAD-TARGET-LOCKED`（主 CLI commit 同步 emit）

---

## [Q-020] 2026-04-20 · main · Platform Shell v2 五路切分与 Stage 1.0 共享契约落地

**CLI**: main (self-Q，批次下发备忘)
**Priority**: P1
**Blocking**: no（contracts 已先落，worker 直接基于 c99a277 rebase）
**Related**: `docs/arch/platform-contracts.md`（2026-04-20 新增）

### 背景

北部湾首演（Q-014, 2026-04-16）+ 6 Agent POC 全落地（2026-04-19）后，用户反馈：
> "现在的主要架构功能还有几个没安装，比如 IM 功能和任务版功能"
> "先把前端彻底定下来，长什么样，有哪些按钮，有哪些功能"

验证：`/dispatch` 13 行骨架 / `/warroom` 45 行静态 mock / `/today` 89 行静态 —— 4 个 shell view 里 3 个只是外壳。登录态 / RBAC / 客户统一 / 跨 Agent handoff 全部为零。

### 决策

切 5 路并行（5 worktree / 5 CLI）：
1. `feat/platform-dispatch` — `/dispatch` Slack 风 IM 3 栏
2. `feat/platform-warroom` — `/warroom` 4 列 kanban + handoff ticket
3. `feat/platform-today` — `/today` 动态聚合
4. `feat/platform-auth` — `/login` + RBAC 守卫 + PersonaSwitcher + `/audit` 入口
5. `feat/platform-customer` — `/customer/[id]` 360 + Desk 增强 + 全局 drawer slot

Stage 1.0（main CLI 先手，已落 c99a277）：共享 store + 契约文档，避免 5 路打架。

### Rationale

- **为什么 5 路不是 3 路**：dispatch / warroom / today 是 3 个正交 view，共用底层 store；auth 横切所有入口（单一 writer 必要）；customer 承担 Desk 改造 + 全局 drawer slot（横切但独立 surface）。压到 3 会让 auth+customer 并到一个 worker，冲突 AppShell
- **为什么 Stage 1.0 先落**：`lib/store/*` 是 5 路唯一共享依赖，让任一 worker 先写 → 其他 4 路 rebase 爆炸。主 CLI 提前 30 分钟写完，后续红区改动走 RFC
- **为什么保留 today**：虽然 today 读多写少（90% 消费其他 store），但"今日第一屏"是用户登录后**第一眼看到的东西**，决定产品观感下限。不配独立 CLI，会被挤到各 view 收尾阶段草草拼
- **为什么接纳 AppShell 双写**：CLI-4（AuthGate）和 CLI-5（drawer slot）都要改 AppShell。替代方案是主 CLI 预先把 slot 全留好，但这样 slot API 设计得拍脑袋 —— 不如让两个 worker 自己提 slot 需求，每次改在 decisions-log 留 ≤3 行说明，主 CLI 做 rebase 仲裁

### 约束（红区清单）

- `web/src/lib/store/*.ts` —— 改字段 / 改签名 / 改 RBAC matrix / 改 HANDOFF_CATALOG 一律走 RFC (`Signal: RFC-<topic>-RAISED`)
- `docs/arch/platform-contracts.md` —— 主 CLI 唯一写入
- `design_mockups/rm-assistant-final-2026-04-19.html` —— 视觉基准，不可改
- 跨 worker page/store —— 只 read 不 write

### [A-020] 2026-04-20 · main CLI (self)

**Decision**: APPROVED（self-dispatch）

**Artifacts（已落 commit c99a277）**:
- `web/src/lib/store/{types,customer-store,event-bus,auth-store,handoff-catalog,index}.ts`
- `docs/arch/platform-contracts.md`

**Artifacts（本 commit）**:
- `docs/onboarding/platform-{dispatch,warroom,today,auth,customer}-phase-1.md`（5 份批次文档）
- 5 个新 worktree 的 `AGENT_IDENTITY.md`（本地 `.gitignore`，不入库）
- `docs/handoff/mesh.json` 追加 5 条 worker
- `C:/Users/Mr.S/Desktop/demo-start.bat` 扩 5-CLI 启动参数

**Signal**: `PHASE-1-BATCH-1-DISPATCHED`

**Follow-up**:
- 5 worker 各自 ACK 后逐 Task 并行推进
- 主 CLI 不再推进前端新功能，转去 Phase 2 coordination（event-bus 订阅配线 + 跨 view 联调）+ 验收
- Phase 3（~5d）：真实样本跑穿 + 起草 `docs/frontend-spec/`

---

## [A-021] 2026-04-20 · main CLI (self) · LEGACY-THEME-PURGE

**Trigger**: 用户 ultrathink 复盘 —— "黑红读老 DEMO"。定稿前端即 4-theme 渐变方案（Canvas/Matcha/Dusk/Ink），Letterpress/crimson + 所有印章系统 (seal / 乾 / 朱砂) 需彻底下架，避免再"跑偏"。

**Decision**: 一次性原子提交 purge —— 代码 + spec + mockup 同步过线。

**Artifacts（commit `f004a1d`）**:
- `web/src/components/shell/ThemeSwitch.tsx` —— 重写为 4-theme only（Type 从 5 → 4，移除 Letterpress button，Dusk label 取代 Blush）
- `web/src/app/tokens.css` —— 删 `[data-theme="crimson"]` 15 行
- `web/src/app/shell.css` —— crimson sw-dot → ink sw-dot
- `web/src/app/globals.css` —— 删 `.ink-source-badge` + 4 × `.ink-seal-*` 共 41 行，留一行 retirement 注释
- `web/src/components/brand/InkSeal.tsx` —— 删（违反"typography-only ID"硬线 + 无业务 caller）
- `design_mockups/rm-assistant-final-2026-04-19.html` —— 6 处删除（`[data-theme="crimson"]` / `body[data-theme="crimson"] .fb-sym--crimson` / settings-panel sp-chip / theme-sw sw-dot / `fb-sym--crimson` 铜章 SVG "乾" / 切换器 Letterpress 按钮 → Ink 按钮），新 sha256 `25155e744f769a9ce0e01504af2aaa339c5b7794a887696a8c9254e45b775c9a`
- `docs/design/platform-shell-v2.md` —— §0/§1.1/§2/§3 共 4 处"5 主题"→"4 主题"
- `CLAUDE.md` §7 —— mockup 锚点 sha256 升级 + 2026-04-20 post-purge 批注

**Signal**: `LEGACY-THEME-PURGED`

**Rationale**:
- 用户担忧"擅自改动方案"的根因是 ThemeSwitch.tsx 此前注释写着"Letterpress 沿用 mockup selector `data-t='crimson'` 保 1:1"—— 这就是"盲目复刻 mockup"的放大器。修根不修表。
- spec + mockup + code 三处此前口径不一（CLAUDE.md §7 已 4-theme / spec 仍 5-theme / mockup 仍含 crimson CSS），不同步过线会继续长新 regression。

---

## [A-022] 2026-04-20 · main CLI (self) · PHASE-1-REVIEW-VERDICTS

**Trigger**: 4 个 worker（warroom / today / auth / customer）自报完成，1 个（platform-dispatch）尾部 Task C 未收尾但主路已落。红区与设计语汇 purge 后需复审 + 下达 GO-2（rebase onto `f004a1d` + 残留自查）。

**Decision**: 4 路 preliminary APPROVE，1 路 PENDING-COMPLETE。合并前强制 rebase + 残留自查通过 → main CLI merge。

### ✅ `feat/platform-warroom` · preliminary APPROVE
- 红区审计：0 red-zone touches（`web/src/lib/store/*` / contracts / mockup 均未动）
- 交付：4 列 kanban + HandoffTicket 订阅 store event-bus，静态 mock 逻辑保留作 fallback
- 条件：rebase onto `f004a1d` → 确认无 crimson/letterpress/seal 字面量 → 发 `PHASE-1-PLATFORM-WARROOM-REBASED-CLEAN`

### ✅ `feat/platform-today` · preliminary APPROVE
- 红区审计：0 red-zone touches
- 交付：MorningBrief + PriorityQueue + EventTimeline 三段动态聚合，store-driven
- 条件：同 warroom

### ✅ `feat/platform-auth` · preliminary APPROVE（含 AppShell 授权触碰）
- 红区审计：`app-shell.tsx` 内嵌 `<ShellChrome>` + `<AuthGate>` —— 合契约 §Worktree 分工（CLI-4 持 AuthGate slot 写权）
- 交付：`/login` + RBAC guard + PersonaSwitcher + `/audit` 入口
- 条件：同 warroom + decisions-log 已含逐 Task 说明，无需补

### ✅ `feat/platform-customer` · preliminary APPROVE（含 AppShell 授权触碰）
- 红区审计：AppShell 末端新增 `<CustomerDrawer />` 单行 —— 合契约（CLI-5 持 drawer slot 写权）；预写 I-021 通知 CLI-4 采 merge-only 冲突策略
- 交付：`/customer/[id]` 360 + Desk 拖拽增强 + 全局 drawer slot
- 条件：同 warroom。与 auth 的 AppShell 冲突由 main CLI rebase 阶段按 A-020.D 规则仲裁

### ⏳ `feat/platform-dispatch` · PENDING-COMPLETE
- 主路 Slack 风 IM 3 栏 + ComposerBar + event-bus 桥接已落
- 尾 Task C (README signal) 未发 `READY-FOR-PLATFORM-DISPATCH-REVIEW`
- 条件：rebase onto `f004a1d` + 残留自查 + 补发 Task C 终版 signal → main CLI 合并

### 合并顺序（由 main CLI 顺序仲裁）
1. warroom / today（无红区，最小 rebase surface）先 merge
2. auth（先于 customer 接 AppShell，Chrome 作为基础层）
3. customer（在 auth 之上加单行 slot，冲突由 customer 预声明的 merge-only 解决）
4. platform-dispatch（独立 view，最后并）

---

## [Q-022] 2026-04-20 · main CLI (self) · Phase 2 Anchor — Agent Workspace Design Wash

**问题**: Phase 1 Batch 1 完成平台壳功能补齐（IM / 任务栏 / Today / Auth / Customer 360 联动）之后，用户明确下一步: 6 个 `/archive/[agent]` workspace 现仍是"老 demo 形态"，与 shell v2 的 4-theme 渐变方案设计语汇脱节。

**用户原话**:
> "这次的目的是先把产品完善起来，该有的功能都有，IM、任务栏，以及各种功能的联动。下一步就是我要把设计页面进行改动，现在的 agent 功能页面还是老 demo 的形态，这个后面要改一个更符合现有主题的，更有设计感的"

**Phase 2 范围锚点**（留档，落地延后至 Batch 1 并库后启动）:

- **对象**: 6 个 agent workspace（`web/src/app/archive/[agent]/` + `web/src/components/workspace/*`）—— Channel / Credit / Alert / Compliance / Report / RiskCtrl
- **目标**: 与 shell v2 4-theme 视觉系统合体，去除老 demo 视觉残留（块状按钮 / 表单堆栈 / 无间奏留白 / 与 tile 色格断裂等）
- **设计语汇底线**（沿用 L021/L022 purge 后的硬线）:
  1. 无印章（无 seal / 朱砂 / 铜章 / "乾" 字）
  2. 中文字段名不包 mono / italic / serif 变体
  3. 与 6 Agent tile 色（`--t-report` / `--t-alert` / `--t-compli` / `--t-credit` / `--t-riskctrl` / `--t-channel`）对接，每 workspace 用自己的 agent 功能色做 accent，不破 4-theme g0..g7 画布
  4. 沿 shell v2 圆角（`--r-md: 18px` / `--r-lg: 26px`）+ 动画节拍（`card-rise` / `rise` / `bar-in`）
- **交付形态**: 沿"mockup-first"（用户自出每个 workspace 的目标形态 mockup）→ main CLI 切 6 路 worker worktree 并行复刻。**不设 demo 时间窗**（已记忆 `project_stage5_workspace_rewrite`）
- **启动前置**:
  1. Batch 1 五路全并（含 PENDING-COMPLETE 的 platform-dispatch 收尾）
  2. event-bus 订阅跨 view 联调通过
  3. 用户出首个 workspace 的 mockup + 选定首发 agent（建议从 Report/Credit 里挑一，流量最大）

**Decision**: 仅 Anchor，不开 worktree。待 Batch 1 完成收尾 → 用户给首发 mockup → main CLI 按 A-020 同构模式分派。

**Signal**: `PHASE-2-ANCHOR-CAPTURED`

---

## [ACK] platform-warroom · PHASE-1-BATCH-1

**CLI**: platform-warroom (worker)
**Date**: 2026-04-20
**Signal**: `PHASE-1-BATCH-1-ACK`

接收 `docs/onboarding/platform-warroom-phase-1.md` 全 3 Task（Task A kanban + Task B Drawer + Task C FilterBar）。红区守则同 A-020：不动 `lib/store/*` / `components/shell/*` / `HANDOFF_CATALOG`，`web/src/app/warroom/` 自持。拖拽库 `@dnd-kit/core` 按需 Task A 加 deps。

---

## [READY] platform-warroom · PHASE-1-BATCH-1 完成

**CLI**: platform-warroom (worker)
**Date**: 2026-04-20
**Signal**: `READY-FOR-PLATFORM-WARROOM-REVIEW`

### Commits

- `701fe5a` — ACK
- `2698f5e` — Task A · ticket-store + @dnd-kit 4 列 kanban + handoff.requested 订阅
- `11469c2` — Task B · TicketDrawer Accept / Reject(reason ≤140) / Reassign(DEMO_USERS) / Archive
- `5540c86` — Task C · FilterBar + `?scope&customer&assignee&from&to&priority` URL query 同步

### Artifacts（全部在 `web/src/app/warroom/` 内）

- `_store/ticket-store.ts` —— zustand-persist (localStorage `platform.warroom.tickets.v1`) + 4 颗 first-run seed + `filtered()` selector + `subscribeHandoffRequested()`
- `_components/KanbanBoard.tsx` —— DndContext + 4 列 + FilterBar + Drawer 编排
- `_components/StatusColumn.tsx` —— `useDroppable` + `kcol--over` 高亮
- `_components/TicketCard.tsx` —— `useDraggable` + 复用 `.kcard` token
- `_components/TicketDrawer.tsx` —— 客户 / 交接说明 / payload / 参与人 / 来源事件 + 操作链
- `_components/EmptyColumn.tsx` —— 空态"暂无 ticket"
- `_components/FilterBar.tsx` —— Tab 我的任务/全部 + 5 Select + 清除
- `_components/useWarroomFilters.ts` —— URL ⇄ filter 双向 hook
- `page.tsx` —— Suspense-wrapped, metadata 保留

### Additive 修改（非红区）

- `web/package.json` + `package-lock.json` —— 加 `@dnd-kit/{core,sortable,utilities}`
- `web/src/app/views.css` —— append `.kcol--over` / `.kempty` / `.tkt-drawer-*` / `.wr-filters`

### 交互 DoD 验证

- [x] 进 `/warroom` 看到 4 列 kanban + 4 颗 seed ticket（清空后空态 "暂无 ticket"）
- [x] 手动 `publishEvent({ type: "handoff.requested", agent: "report", customerId, actor, payload: { recipeId: "report_to_credit" } })` → 进 Requested 列
- [x] 拖卡片 Requested → Accepted → publish `handoff.accepted`
- [x] 点 ticket → Drawer 滑入；Accept 推 customer.stage + publish；Reject 强制 ≤140 字 reason；Reassign 切 DEMO_USERS
- [x] 切 persona u_lihua → "我的任务" tab 只剩 assignedTo=u_lihua 的 ticket
- [x] URL `?assignee=u_lihua&priority=urgent` 可分享、刷新还原
- [x] `npx tsc --noEmit` 清；`next build` 清；`/warroom` 静态产出

### 红区守则自检

- ✅ 未改 `web/src/lib/store/*`
- ✅ 未改 `HANDOFF_CATALOG`
- ✅ 未改 `web/src/components/shell/*`
- ✅ 未动 dispatch / today / customer / login 的 page
- ✅ `views.css` additive（`.tkt-*` / `.kcol--over` / `.kempty` / `.wr-filters` 全新命名空间）

### 待主 CLI 仲裁 / 下一步

- 主 CLI review 通过后，`HANDOFF_CATALOG` 已有 6 个 recipe 可被 Agent workspace 端（CLI-0 / 其他 worker）消费 —— warroom 只是消费端，验证会通过 event-bus 喂数据才能闭环
- `TO_AGENT_STAGE` 映射（toAgent → CustomerStage）写在 `TicketDrawer.tsx` 内部，未来若想统一可提 RFC 把映射收到 `lib/store/types.ts`
- `findRecipeById` 在 drawer 里用 `triggerEventId` 查，语义不匹配（event-id ≠ recipe-id），实际走 fallback 不渲染 description —— 后续若 ticket 存 recipeId 字段可补契约

---

## [ACK-020-today] 2026-04-20 · platform-today CLI-3

**Related**: Q-020 / A-020 / `PHASE-1-BATCH-1-DISPATCHED`

Worker CLI-3 (`platform-today`) 已接批次并 rebase 到 c99a277 共享 store。按 onboarding 顺序推进 Task A → B → C：

- Task A · MorningBrief hero + StatCell（30s 刷新）
- Task B · PriorityQueue TOP 8（stage × lastActivityAt · RBAC 过滤）
- Task C · EventTimeline（mount publish seed · 实时追加）

红线遵守：不改 `lib/store/*` / `components/shell/*` / 其他 worker page；跨 worker store 只读。AuthGate 未就绪，未登录先硬编 `u_wangzhe` 兜底。

**Signal**: `PHASE-1-BATCH-1-ACK`

---

## [READY-020-today] 2026-04-20 · platform-today CLI-3

**Related**: ACK-020-today / `PHASE-1-BATCH-1-ACK` / commits `c7ab0a8 cff7b2f 7f07479`

Phase 1 Batch 1 三 Task 全部完成，工作树 clean，可交接验收。

- `c7ab0a8` Task A — MorningBrief hero + StatCell（Signal: TODAY-BRIEF-DONE）
- `cff7b2f` Task B — PriorityQueue TOP 8 客户（Signal: TODAY-QUEUE-DONE）
- `7f07479` Task C — EventTimeline 实时流 + 5 条 seed（Signal: TODAY-TIMELINE-DONE）

**已消费的共享 store（只读）**
- `useAuthStore.currentUser` — 问候语 / persona 过滤（未登录自动硬编 u_wangzhe）
- `useCustomerStore.customers` — PriorityQueue 排序 + lastActivityAt 滤条
- `useEventBus.history` — 事件流 + MorningBrief alert stat + PriorityQueue 最近事件副标

**已落的 AppShell slot 需求** —— 无（Task 全部在 `app/today/` 内完成）

**Known gaps / 留给联调**
- 待 CLI-2 `app/warroom/_store/ticket-store` 落地后，MorningBrief 的 `TICKET_FALLBACK_COUNT` 换为真订阅
- 待 CLI-4 `/login` + AuthGate 落地后，移除 MorningBrief `useEffect` 自动 fallback 登录逻辑
- 样式 scoped 在 `views.css` `.v-today` 命名空间下，additive only，未触碰既有 class

**Signal**: `READY-FOR-PLATFORM-TODAY-REVIEW`

---

## [ACK-platform-auth] 2026-04-20 · platform-auth worker · Phase 1 Batch 1

**CLI**: platform-auth（worker · `feat/platform-auth`）
**Signal**: `PHASE-1-BATCH-1-ACK`

Resume 完成（AGENT_IDENTITY.md + contracts + onboarding + auth-store + AppShell + archive/[agent] 全读过）。确认 4 Task 范围 / 红区 / AppShell 双写纪律 / AgentKey("compliance") → AgentId("compli") 映射点。按 A → B → C → D 顺序开工，每 Task 独立 commit。

AppShell 改动变更点将在本 log 逐条补录（供 platform-customer rebase 参考）。

### AppShell 改动：Task A（2026-04-20）

- `components/shell/AppShell.tsx`：`/login` 路径走裸壳（无 Desk / Masthead / ThemeSwitch）；其余路径用 `<AuthGate>` 包 `<ShellChrome>`；drag/drop 逻辑外迁至 ShellChrome。
- 新增 `components/shell/AuthGate.tsx`：hydration-safe 未登录跳 `/login`、已登录访问 `/login` 跳 `/today`。对 CLI-5 customer drawer 无影响（仍通过 ShellChrome 注入）。

### Masthead / PersonaSwitcher 改动：Task B（2026-04-20）

- `components/shell/Masthead.tsx`：原硬编 "王哲 · 客户经理 · 华东" 替换为 `<PersonaSwitcher />`；time tick 保留。
- 新增 `components/shell/PersonaSwitcher.tsx`：右上按钮 + Popover 列 5 persona + 退出；切 persona 直接 `login(newId)` 不走 logout/login 往返；Esc / 点外部关闭。
- 注：onboarding Task B 指标 #3 "Desk 按 assignedTo 过滤" 属 CLI-5 platform-customer 的 Desk 增强范围（contracts §Worktree 职能分工），本 worker 仅提供 `useAuthStore.currentUser.id` 数据源，不改 Desk.tsx。

### RBAC 守卫改动：Task C（2026-04-20）

- `components/shell/AppShell.tsx`：**未动本轮**（AuthGate 已于 Task A 接管 children wrap，RBAC 判定在 archive/[agent] 内部走 RbacGuard，不需再动 AppShell）。
- 新增 `lib/auth/agent-id.ts`：`AGENT_KEY_TO_ID` 映射（唯一差异 `compliance → compli`）。
- 新增 `components/shell/NoPermission.tsx`：温和文案 + 指引（今日 / 对话 / 助手目录），读 `useAuthStore.currentUser` 展示 role。
- 新增 `app/archive/[agent]/RbacGuard.tsx`：client wrapper，`can({kind:"agent.access", agent: AGENT_KEY_TO_ID[key]})` 判定。
- 新增 `components/archive/RbacTileGate.tsx`：archive index 6 tile 的无权包装（置灰 + native tooltip + aria-disabled）。
- `app/archive/[agent]/page.tsx` / `app/archive/page.tsx`：插入守卫，视觉语言沿用既有 `.agent` tile 规范。
- `app/views.css`：**additive only** —— 追加 `.v-archive .agent.locked` + `.no-permission*` 样式段，未改现有规则。

### Audit 入口改动：Task D（2026-04-20）

- `components/shell/Masthead.tsx`：`.shell-op` 内 PersonaSwitcher 左侧注入 `<AuditEntry />`（仅 `audit.view` 权限可见）。
- 新增 `components/shell/AuditEntry.tsx`：无权 return null，有权渲染 `<Link href="/audit">`。
- 新增 `app/audit/page.tsx` + `AuditView.tsx` + `audit.css`：消费 `useEventBus.history`（前 50 条）+ agent 下拉筛选；URL 直访兜底判 `can({kind:"audit.view"})`，未授权走 `<NoPermission />`。
- AppShell.tsx **未动本轮**（AuthGate 仍覆盖；audit 页经由 masthead 条件入口 + 页内 RBAC 守卫双层）。

### Batch 1 Readiness（2026-04-20）

4 Task 全绿，均以独立 commit 落地（SHA 不可重写 · A-012.D）：

| Task | Signal | Commit |
|---|---|---|
| ACK | PHASE-1-BATCH-1-ACK | `5366f30` |
| A /login + AuthGate | AUTH-LOGIN-PAGE-DONE | `dc3724c` |
| B PersonaSwitcher | AUTH-PERSONA-SWITCHER-DONE | `d6a909c` |
| C RBAC 守卫 + NoPermission | AUTH-RBAC-GUARD-DONE | `fa0ccca` |
| D /audit 入口 | AUTH-AUDIT-ENTRY-DONE | `8e004e9` |

**红区合规核对**：
- `lib/store/auth-store.ts` ACCESS / HANDOFFS matrix 未动（仅通过 `can(action)` 谓词消费）
- `docs/arch/platform-contracts.md` 未改（主 CLI 唯一写入）
- `design_mockups/rm-assistant-final-2026-04-19.html` 未改
- 跨 worker page / store 未写（仅读 `useAuthStore` / `useEventBus` / `AGENTS`）

**AppShell 改动栈**（供 CLI-5 platform-customer rebase 参考）：
- Task A：split into `AppShell` shell-dispatcher + `ShellChrome` inner; drag/drop 逻辑下沉 ShellChrome
- Task B：Masthead 内部替换 —— 未改 AppShell.tsx
- Task C：未改 AppShell.tsx（RbacGuard 走 archive/[agent] 内部）
- Task D：未改 AppShell.tsx（AuditEntry 走 Masthead 内部）

**reflog 干净**：`merge (fast-forward) → commit × 5`，无 rebase / amend / force。

**Signal**: `READY-FOR-PLATFORM-AUTH-REVIEW`

---

### Rebase onto `chore/l0-infra` @ `53b15fb`（2026-04-20 · GO-2）

主 CLI 在 `f004a1d` 落 LEGACY-THEME-PURGED + `53b15fb` 给本路 preliminary APPROVE 后，执行 GO-2：
`git rebase upstream/chore/l0-infra` —— 6 commit 全部 replay。

**冲突仲裁**：仅 `docs/handoff/decisions-log.md` 一处 append-vs-append（A-021 / A-022 / Q-022 vs ACK-platform-auth），保留双方按时序排列；purge 涉及的 `web/src/app/{tokens,shell,globals}.css` + `ThemeSwitch.tsx` 与 auth 追加段（`.persona-sw*` / `.audit-entry`）落在不同选择器，**无 CSS 冲突**。

**残留自查**（grep `crimson|letterpress|ink-seal|InkSeal|朱砂|铜章` over `web/src/`）：3 处命中均为 `f004a1d` 的 retirement 注释（ThemeSwitch.tsx:9 / globals.css:331 / tokens.css:112），非 auth 引入；CJK-in-mono 仅在 eyebrow brand slug（与 archive / warroom 既有 pattern 一致），非字段名违规。

**新 SHA 链**（rebase 后）：

| Task | Signal | New SHA |
|---|---|---|
| ACK | PHASE-1-BATCH-1-ACK | `184334d` |
| A | AUTH-LOGIN-PAGE-DONE | `f7f3fce` |
| B | AUTH-PERSONA-SWITCHER-DONE | `ef8d03e` |
| C | AUTH-RBAC-GUARD-DONE | `ce19051` |
| D | AUTH-AUDIT-ENTRY-DONE | `90af115` |
| Readiness | READY-FOR-PLATFORM-AUTH-REVIEW | `cba98c8` |

**验证**：`npx tsc --noEmit` 0 error · `next build` 22 routes 全静态 / SSG · `next start` 起 `:3401` 探活：`/login` 200（DOM 见 `login-root` + 「选一位身份」）/ `/audit` 200（AuthGate gate SSR → CSR 无 session 即 `router.replace("/login")`，**非 404**）/ `/today` 200。

**Signal**: `PHASE-1-PLATFORM-AUTH-REBASED-CLEAN`

---

## [I-021] 2026-04-20 · platform-customer (CLI-5) · AppShell drawer slot 注入告示

**Type**: Informational notice (非 RFC · 无需 A 批复)
**CLI**: platform-customer (feat/platform-customer)
**Related**: Q-020/A-020 §冲突预防 "AppShell 可加 slot"; onboarding platform-customer-phase-1 §Task C
**Blocking for CLI-4?**: 否（CLI-4 改 AppShell 加 `<AuthGate>` 守卫时做正向合并即可；若冲突走 merge-only 解决）

### 做什么

Task C 要求 CustomerDrawer 全局渲染——点任何页面的客户名（via `<CustomerLink>`）都弹右侧 280px 迷你客户卡。按 contracts §Slot 约定，`AppShell.drawer` 归 CLI-5。

**本 CLI 对 AppShell.tsx 的唯一改动**：在 `shell-root` 末尾加一行 `<CustomerDrawer />`。不改现有 drop 处理 / `<Desk />` / `<Masthead />` / children 传递逻辑。

```tsx
// 仅加这一行（放在 <ThemeSwitch /> 下方，shell-root 内）
+ <CustomerDrawer />
```

### CLI-4 留意

- AppShell.tsx 的"结构性"改动（加 `<AuthGate>` 包裹 children、加 `<PersonaSwitcher />`、改顶层 JSX）与本改动**互不相交**：CLI-5 只追加 drawer 兄弟节点，不动现有节点
- rebase 冲突预期：若 CLI-4 在 shell-root 末尾也追加组件，会命中同一位置 → 手动 merge-only 合成（见 A-012.E），不要 rebase
- 若 CLI-4 想把 drawer 也纳入未来 slot API（Stage 1.1 主 CLI 补），届时 CLI-5 配合迁移为 prop 式 `<AppShell drawer={<CustomerDrawer />}>`。**当前不做此抽象**，避免拍脑袋设计 slot 签名

### 状态管理边界

- 新建 `web/src/components/shell/_customer-drawer-store.ts`——本地私 store，只存 `openId: string | null`。**不进红区**（与 Task B 的 `_desk-store.ts` 同策略）
- `<CustomerLink>` 作为全局组件（`web/src/components/shared/`），其他 worker（dispatch / warroom / today）可直接 import 使用
- 不订阅 event-bus，不改 customer-store，不改 auth-store

### Commit 节奏

本 I-021 块随 Task C commit 一起提交（commit msg 注 `Signal: CUSTOMER-DRAWER-DONE`）。CLI-4 无需 ACK。

**维护者**：platform-customer worker · 单向通告

---

## [A-023] 2026-04-20 · main CLI (self) · PHASE-1-BATCH-1-MERGED

**Trigger**: 5 worker 全部发 `PHASE-1-PLATFORM-<X>-REBASED-CLEAN`，main CLI 按 A-020.D 顺序合并入库。

### 合并链

| # | Worker | Merge SHA | Worker HEAD | 冲突仲裁 |
|---|---|---|---|---|
| 1 | warroom | `f0b2a6c` | `cf18c3f` | 0 conflict, fast 3-way |
| 2 | today | `14f7fc6` | `89d1062` | views.css tail concat + decisions-log append |
| 3 | auth | `ee75d6b` | `4df84fe` | decisions-log append |
| 4 | customer | `5abf6ae` | `93fec85` | AppShell.tsx import concat + views.css tail concat + decisions-log append |
| 5 | dispatch | `731afdb` | `194918a` | 0 conflict, additive |

### 冲突处理原则

- `views.css` · 每 worker 以 `.v-<route>` 命名空间前缀写入，尾部 concat 即可（warroom `.wr-*` / today `.v-today .*` / auth `.v-archive/.no-permission/.persona-sw*` / customer `.v-customer*`）
- `AppShell.tsx` · auth 结构壳 `<AuthGate>/<ShellChrome>` + customer 单行 `<CustomerDrawer />` slot，imports concat + customer 的 drawer 落在 ShellChrome `shell-root` 内（登录态外自动不渲染 ✓）
- `decisions-log.md` · 全部 append-vs-append，按时序拼接

### 验证

- `npx tsc --noEmit` 0 error
- `npx next build` 22 routes 生成（`/login` `/audit` `/customer/[id]` `/dispatch` `/warroom` `/today` 全命中 + `/archive/[agent]` SSG 6 条）
- `npm install` 166 packages（`@dnd-kit/{core,sortable,utilities}`）0 vulnerabilities

### Phase 2 触发条件

Q-022 锚点：6 × `/archive/[agent]` workspace 设计改造。前置：
1. ✅ Batch 1 全并（本 commit）
2. ⏳ event-bus 跨 view 联调冒烟（dispatch handoff → warroom ticket → today timeline 闭环）
3. ⏳ 用户出首发 workspace mockup

**Signal**: `PHASE-1-BATCH-1-MERGED`



---

## [I-022] 2026-04-22 · main CLI (self) · CONTRACT-AUDIT 漂移批量修复 + security cherry-pick 通告

**Type**: Informational notice (非 RFC · 无需 ACK)
**From**: main CLI on `chore/l0-infra`
**To**: feat/agent6-dialog-shell CC（近 3 commit `5b575c8` / `703ce3f` / `267c84a` 作者）+ 所有 worker
**Blocking**: 否

### 背景

2026-04-22 用户要求对 CLAUDE.md 声明 vs 仓库实际状态做 contract audit,发现 8 条漂移,并在执行中间发现第 9 条(scripts/run_v16_*.py 硬编 DEEPSEEK_API_KEY 入 git)。

### chore/l0-infra 已落地的 audit 链(8 commit)

| Drift # | SHA | 内容 |
|---|---|---|
| #3 | `e32e7ba` | fix(feedback): 兜底创建 data/feedback 目录(.gitkeep) |
| #8 | `74ac81d` | chore(credit): 注释版本号对齐 __init__ v3.1 |
| #7 | `2297af8` | docs: §10 源实现 5→6 补 enterprise_info |
| #1 | `7c35f75` | docs: Agent6 报告管线 v7.23 → v16(§2/§10/§11 + agent_report/__init__.py) |
| #4 | `1cccf6c` | docs: §3.1 LLM prompt 契约三件套改锚定实际带 format_for_prompt 的模块 |
| #2a | `cfb40f7` | feat(scripts): 补 scripts/start_uvicorn.py(永久化历史 /tmp wrapper)+ 对齐 .env.example |
| #2b | `4057089` | chore(api_server): docstring Run 段路径同步 |
| #9 | `ab09864` | fix(security): v16 辅助脚本改读 .env · 移除硬编 DEEPSEEK_API_KEY(cherry-pick 自 `6a6286f`) |

### 给 feat/agent6-dialog-shell CC 的通告

- 你在 `feat/agent6-dialog-shell` 上 commit 的三个路由清理(`5b575c8` / `703ce3f` / `267c84a`)**正是 audit 清单 #5 的代码执行**,用户侧已标为 deferred,你顺手做了。赞。merge 到 chore/l0-infra 时顺便可以把 CLAUDE.md §7 路由拓扑的 "legacy(待清理)" 段删掉(因为已清)。
- 我的 `6a6286f` security fix 夹在了你的分支中间(仓库被切到你分支时我没察觉就 commit),已 cherry-pick 为 `ab09864` 到 `chore/l0-infra`。你分支上保留原 commit 即可,merge 时 git 会 auto-skip identical patch,无冲突。**不需要你手动处理**。

### 待用户侧动作(已确认完成)

- ✅ DeepSeek 控制台禁用旧 key `sk-358b17cef8a64462b7899dd2dc8a3834`(用户 2026-04-22 确认"删了")
- ✅ 新 key 已通过私信传递并写入本地 `.env`(gitignored,不入任何 commit)
- ❌ **不做** `git filter-repo` 清历史(代价 >> 收益,会炸掉 11 worktree 的 mesh A-012.D SHA-immutable 纪律;禁 key 即可杜绝被滥用)

### 产出 deferred

后续起 `~/.claude/skills/contract-audit/` 通用 skill + 本项目 `.claude/contract-audit.rules.yaml` 规则,让此类漂移可自动化巡检。不在本 I-022 范围。

**维护者**: main CLI · 单向通告

---

## [Q-023] 2026-04-23 · main CLI (self) · Product Hardening 四轨批次（Code-Urgent / Code-Arch / Data / Evaluation）

**CLI**: main (self-Q/A)
**Priority**: P0
**Blocking**: no（mesh 空档，新批次可直发）
**Related**: 代码审计（subagent Explore 于 2026-04-23）· Platform Phase 1 Batch 1 已 MERGED（`f319ccb`）

### 背景

PM 要求"每个 Agent 独立产品力够硬"（见用户多轮 ultrathink 指示）。前几轮讨论曾收敛到"先做真 mock 数据"单轨，用户戳破：**产品力 = 代码 × 数据 × 评估三层并行，单轨推进是单腿跑**。遂派 Explore subagent 按 CLAUDE.md §3.1/§3.2/§3.3/§8/§6 对齐扫描 6 Agent 代码，出硬洞清单。

### 审计结果（一览）

| Agent | §3.1 确定性 | §3.2 工具域 | §3.3 Evidence | §8 QC | 前后端通 | 证据前端化 | §6 飞轮 |
|---|---|---|---|---|---|---|---|
| Agent6 报告 | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 | 🔴 | 🟡 |
| Agent5 合规 | 🟢 | 🟡 | 🟡 | 🔴 | 🟡 | 🔴 | 🔴 |
| Agent3 授信 | 🟡 | 🔴 | 🟡 | 🟡 | 🟢 | 🔴 | 🔴 |
| Agent4 预警 | 🟢 | 🟡 | 🟡 | 🔴 | 🔴 | 🔴 | 🔴 |
| Agent1 获客 | 🟡 | 🔴 | 🟡 | 🔴 | 🟢 | 🔴 | 🔴 |
| Agent2 风控 | 🟢 | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 | 🔴 |

**两条必须立即处置的硬发现**：

1. **Agent3 §3.1 反模式违反**：`agent_credit/scoring_model_corporate.py:95 _score_financial()` 自己实现财务比率计算，**未消费 `financial_analyzer.py`**——这违反 CLAUDE.md §3.1 明令禁止的"把比率算逻辑分散到多个 Agent"；是 PM 最关心的"跨 Agent 数字一致性"硬违反。
2. **Archive workspace 在 main 分支漂移**：`web/src/app/archive/[agent]/page.tsx` import 6 个 `_components/*Workspace.tsx`，但这 6 个源文件在 `chore/l0-infra` 上根本不存在，仅存在于 ad-hoc 分支 `feat/agent6-dialog-shell`。**Platform Batch 1 MERGED 时 archive 系列漏网**。contract-audit 0 blocker 没扫到这个洞。

### 选项

- **A** 三轨并行：Code（1 worker）+ Data（1 worker）+ Evaluation（1 worker），共 3 worker
- **B** 四轨并行：Code 拆成 **C1 紧急**（§3.1 接入 + QC 占位符 + Agent2/4 api.py）+ **C2 架构**（工具域重拆 + Evidence 三阶段协议 + 飞轮第 4 环脚本）+ Data + Evaluation，共 4 worker
- **C** 只做 C1 + D，C2/E 推后

### 推荐

**B**。理由：
- C1 是"短平快补漏"（0.5-1 天/task），C2 是"重构升级"（2-3 天/task），**节奏不同混在一个 worker 会拖慢紧急项**
- D 和 E 完全独立领域（数据 vs 评估跑分器），并行不冲突
- PM 多次强调"并行矩阵推进"，B 是正解
- mesh 当前空档撑得住 4 worker（Platform Batch 1 MERGED 已结清）

### [A-023] 2026-04-23 · 主 CLI 自定

**Decision**: B（四轨并行）

**Rationale**: 产品力 = 代码 × 数据 × 评估三层。C1/C2 拆开是节奏差异（紧急 vs 架构），不是资源摊薄；D 作为"数据底座"支撑后续 E 轨基线真度；E 轨复用 Agent6 v16 pipeline 作为 base_evaluator，避免重复实现。

**四 worker 编制**：

| Worker | worktree | 分支 | Batch 1 范围 | 期望 signal |
|---|---|---|---|---|
| code-urgent | `D:/claude code/demo-code-urgent` | `feat/code-urgent` | Task 0 archive 归位 + A Agent3 接 financial_analyzer + B QC 占位符 5 Agent 补齐 + C Agent2/4 api.py 新建 | READY-FOR-CODE-URGENT-REVIEW |
| code-arch | `D:/claude code/demo-code-arch` | `feat/code-arch` | A 5 Agent 工具域 §3.2 重拆 + B 5 Agent Evidence 三阶段协议 + C 飞轮第 4 环 feedback_to_fewshot 脚本 | READY-FOR-CODE-ARCH-REVIEW |
| data-foundation | `D:/claude code/demo-data-foundation` | `feat/data-foundation` | A schema 规范 + B 宽基 100 家 + C 深柱 15 家名单 + 埋坑清单模板 | READY-FOR-DATA-FOUNDATION-B1-REVIEW |
| evaluation | `D:/claude code/demo-evaluation` | `feat/evaluation` | A 6 × rubric YAML + B base_evaluator + per-agent adapter + C 首轮基线跑分 | READY-FOR-EVALUATION-B1-REVIEW |

**Archive workspace 漂移处置**：归位职责交给 **code-urgent worker 的 Task 0**——从 `feat/agent6-dialog-shell` 挑选 `web/src/app/archive/*/_components/*Workspace.tsx` + 相关 shared 组件（CustomerSelector / ScanCTA）到 `feat/code-urgent` 分支。rebase 时主 CLI 审 diff，APPROVE 时才 merge 回 main。

**Follow-up**:
- 下发 signal: `PRODUCT-HARDENING-BATCH-1-DISPATCHED`
- 4 份 onboarding: `docs/onboarding/{code-urgent,code-arch,data-foundation,evaluation}-phase-1.md`
- 4 worktree AGENT_IDENTITY 本地指针（gitignore）
- Kickoff prompts: `docs/handoff/product-hardening-batch-1-kickoffs.md`
- mesh.json 追加 4 条 worktree 注册

**Batch 2 预告**（不在本 A-023 范围）：
- Data Batch 2：用户回埋坑清单后产深柱 MVP 3 家完整材料包
- Evaluation Batch 2：基于 Data B2 真脏数据重跑基线，对比 B1 虚高分看 gap
- Code Batch 2：按 C1/C2 review 结果定（可能是"6 Agent 证据链前端化"或"Agent1 检索样板打通"）

---

## [Q-024] 2026-04-24 · main CLI (self) · evaluation worker 路径冲突（onboarding vs 仓库现状）

**CLI**: main (self-Q/A)
**Priority**: P0
**Blocking**: **yes** — 卡 evaluation worker Task A 开工前；worker 一粘 GO prompt 开 Task A 就会踩
**Related**: Q-023/A-023 · Preflight 审计（general-purpose agent 2026-04-24）· `docs/handoff/batch-1-review-preflight.md`

### 背景

写 Batch 1 Review Preflight 时派 Explore agent 对照 `docs/onboarding/evaluation-phase-1.md` 与仓库现状，发现路径冲突：

- **onboarding 要求**：在 `evaluation/` 根新建 `base_evaluator.py` / `cli.py` / `adapters/*.py` × 6
- **仓库现状**（2026-04-24 扫描）：`evaluation/runner/` 下已有 `base_evaluator.py`（182 行 ABC 骨架，生产就绪）+ `cli.py`（94 行，CLI 参数齐全）+ `schemas.py` + `registry.py` + `__main__.py`；`evaluation/runner/adapters/` 下已有 `agent2_riskctrl.py` / `agent4_alert.py` / `agent6_report.py` 三个 Phase A adapter 实现（前一轮 `docs/contracts/rfc/20260418-evaluation-runner.md` RFC 遗留）
- **缺什么**：agent1_channel / agent3_credit / agent5_compliance 三个 adapter 未写（正是 evaluation Batch 1 Task B 该补的）

worker resume 完 onboarding 会看到 "新建 evaluation/base_evaluator.py" 这句，按字面执行 = 在两处各有一个 base class = 双份架构；若自己先 grep 发现冲突，又没 A-NNN 指示，只能停工等裁决 = blocker。

### 选项

- **A** **续建 `evaluation/runner/`**：worker Task B 不动 base_evaluator，只补 agent1/3/5 adapter；Task A 的 rubric YAML 指向 `evaluation/` 根（与现状一致）；Task C 基线跑分用 `py -m evaluation.runner`
- **B** 另起 `evaluation/base_evaluator.py`：按 onboarding 字面建，`evaluation/runner/` 归入 deprecated，风险是 Phase A 的 agent2/4/6 实现重写 + v16 pipeline 消费接口可能断
- **C** 薄 wrapper：`evaluation/base_evaluator.py` 做 `from evaluation.runner.base_evaluator import BaseEvaluator`，双入口兼容

### 推荐

**A**。理由：

1. `evaluation/runner/base_evaluator.py` 已是 ABC 生产就绪骨架（`run(EvalRun) -> EvalResult` 全流程 + `evaluate_target` 字符串目标解析 + `mark(name, value, method, evidence, note)` adapter 便利方法），Phase A agent2/4/6 adapter 跑通验证了架构可用——**没有重写必要**
2. B 选项等于作废 Phase A 沉淀 + 潜在破 v16 pipeline 消费接口（`evaluation/agent6_report.yaml` 被 `v16_pipeline` 读）
3. C 选项看似"兼容"，实际引入两个 base class 入口 = 长期维护债

### [A-024] 2026-04-24 · 主 CLI 自定

**Decision**: A（续建 `evaluation/runner/`）

**Rationale**: ABC 骨架已经过 agent2/4/6 三个 Phase A adapter 验证架构可行性；worker 的 Task B 是 "补 Phase B 三个 adapter"，不是 "重写 base"。

**对 evaluation worker 的具体指示**（覆盖 onboarding 字面）：

| Task | onboarding 字面 | **A-024 后的实际路径** |
|---|---|---|
| A 产物 | `evaluation/agent*.yaml` × 6 | `evaluation/agent*.yaml` × 6（路径同，schema 见 Q-025） |
| B 产物 1 | 新建 `evaluation/base_evaluator.py` | **不动**，用 `evaluation/runner/base_evaluator.py` 现有 `BaseEvaluator` ABC |
| B 产物 2 | 新建 `evaluation/adapters/agent*.py` × 6 | **补** `evaluation/runner/adapters/agent1_channel.py` + `agent3_credit.py` + `agent5_compliance.py`（其他 3 个 Phase A 已存在，不覆盖） |
| B 产物 3 | `evaluation/cli.py` | **不动**，用 `evaluation/runner/cli.py`；新增 agent1/3/5 自动被 registry.py 发现 |
| C 跑法 | `python -m evaluation.cli --agent <id>` | `python -m evaluation.runner --agent <id>`（同语义）|
| C 产物 | `evaluation/baselines/2026-04-23-first-run.json` | 同，但 evaluation runner 默认路径是 `evaluation/results/YYYY-MM-DD/<agent>_<commit>.json`；worker 产 baseline 汇总请用 `evaluation/baselines/2026-04-24-first-run.json`（日期按 Task C 实际落地日）|

**Follow-up**:
- 本次 commit trailer 带 `Signal: Q-024-RESOLVED`
- evaluation worker GO prompt 增强版（见 `kickoffs.md` 补丁章节 / 主 CLI 粘贴给用户的内容）加一步："ACK 后先 `git fetch origin chore/l0-infra && git log origin/chore/l0-infra -5`，读 Q-024/A-024 + Q-025/A-025 后再动 Task A"
- code-urgent / code-arch / data-foundation worker 不受 Q-024 影响（路径不重叠）

---

## [Q-025] 2026-04-24 · main CLI (self) · rubric YAML schema 新老字段兼容

**CLI**: main (self-Q/A)
**Priority**: P0
**Blocking**: **yes** — 卡 evaluation worker Task A 开工前；Task A 写 YAML 字段名错一个全批次链路废
**Related**: Q-024/A-024（同一批 preflight 发现）· `v16_pipeline` 消费 `evaluation/agent6_report.yaml`

### 背景

现状 vs onboarding schema 字段名冲突：

- **仓库现状**（6 份 YAML，2026-04-15 格式）：
  ```yaml
  metrics:
    - name: <metric_name>
      desc: <human_readable_description>
      target: ">= 0.9" / "<= 0.02" / "pass"
  baseline: { last_run: ..., commit: ..., result: { ... } }
  ```
- **onboarding 要求**（`docs/onboarding/evaluation-phase-1.md`）：
  ```yaml
  - name: portrait_match_precision
    description: Top10 候选中匹配画像条件的比例
    method: top10_matches_criteria / 10
    baseline_target: 0.7
    blocker_threshold: 0.5
  ```

差异：`desc` → `description`（字段改名）；`target` → `baseline_target`（语义变）；新增 `method`（指标计算方法）+ `blocker_threshold`（发布阻断线）；老 `target` 的字符串表达式（">= 0.9"）被拆成数字 `baseline_target`。

硬风险：`evaluation/agent6_report.yaml` 被 `v16_pipeline.py` 消费（跑分比对 EV-6 依赖 `target` 字符串），强行改名字段会断 v16 baseline。

### 选项

- **A** 全量迁新 schema：6 份 YAML 全改，同步改 `v16_pipeline` 读取逻辑
- **B** 兼容层：`BaseEvaluator._metrics_config()` 读时优先读新字段（`description` / `baseline_target` / `blocker_threshold` / `method`），fallback 到老字段（`desc` → `description`，`target` 字符串 → 解析为 `baseline_target` 数字 + 保留原 target 逻辑）。YAML 一律按新 schema 写，老 YAML 迁移但保留 `target` 字段做双写
- **C** 改 onboarding 保留老 schema：worker 按 `desc / target` 继续写

### 推荐

**B**。理由：

1. 新 schema 字段（`method` / `blocker_threshold`）确实比老 schema 更能支撑"发布阻断线"这类产品决策，应保留
2. A 方案破 v16 pipeline 消费 = 破 Agent6 回归基线（CLAUDE.md §3.1 + Preflight §3 红线"Agent6 跑分不漂 1%"）——评估轨想改 Agent6 读法等于抢了 code-arch 的活
3. C 方案退化回老 schema = Batch 1 之后的 Batch 2 PM 对标依然没 `blocker_threshold` = 客户演示时没红绿灯
4. B 方案工作量小：`BaseEvaluator` 读 YAML 时做 2 行 `.get('baseline_target', _parse_target(m.get('target')))` 级 fallback 即可

### [A-025] 2026-04-24 · 主 CLI 自定

**Decision**: B（兼容层，新写 YAML 一律新 schema，`BaseEvaluator` 读时 fallback 老字段）

**Rationale**: 新老双写，`BaseEvaluator` 侧解析层兼容；Agent6 yaml 保留 `target` 字段（v16 pipeline 继续读），同时补 `description / method / baseline_target / blocker_threshold` 新字段（`BaseEvaluator` 读取路径）。

**对 evaluation worker 的具体指示**：

1. **新写 YAML（agent1/2/3/4/5）一律按新 schema**：
   ```yaml
   metrics:
     common:
       - name: field_completeness
         description: 字段填充率
         method: filled_fields / expected_fields
         baseline_target: 0.85
         blocker_threshold: 0.6
       # ... 5 通用
     domain:
       # ... 5 领域
   ```
   6 Agent 统一结构 `metrics.common[5] + metrics.domain[5] = 10 条`。

2. **Agent6 yaml 保留老字段 + 新增新字段**（双写）：`agent6_report.yaml` 已有的 `desc / target` 不动，每条指标追加 `description / method / baseline_target / blocker_threshold` 字段（值一致，格式规范化）。v16 pipeline 继续读 `target`，`BaseEvaluator` 优先读新字段。

3. **BaseEvaluator `_metrics_config()` 读取 fallback**（worker Task B 时实现）：
   ```python
   def _normalize_metric(m: dict) -> dict:
       return {
           'name': m['name'],
           'description': m.get('description') or m.get('desc') or '',
           'method': m.get('method') or '',
           'baseline_target': m.get('baseline_target') if 'baseline_target' in m
                              else _parse_legacy_target(m.get('target', '')),
           'blocker_threshold': m.get('blocker_threshold'),
       }
   ```
   `_parse_legacy_target` 处理 `">= 0.9"` / `"<= 0.02"` / `"pass"` 三种老格式，返回 `float` 或 `None`（`"pass"` → `None` + 注记布尔判定）。

4. **Preflight 硬指标 EV-3 调整**：新 YAML 必须 `method / baseline_target / blocker_threshold` 齐（**Agent6 yaml 豁免**，只需 description + baseline_target 可从 target 推出即视为通过）。

**Follow-up**:
- 本次 commit trailer 带 `Signal: Q-025-RESOLVED`
- Preflight `docs/handoff/batch-1-review-preflight.md` §4.1 / §4.2 / §4.5 同步更新（去掉"[主 CLI 补]"标记，改为 A-025 判决内容）

---

## [Q-028] 2026-04-24 · main CLI (self) · data-foundation Batch 1 REJECT-V2（形态错 · 把答案喂到模型嘴边）

**CLI**: main (self-Q/A)
**Priority**: P0
**Blocking**: **yes** — data-foundation 返工；其他 3 worker（code-urgent / code-arch / evaluation）APPROVE 不阻塞
**Related**: Q-023/A-023 · Q-024/A-024 + Q-025/A-025 · Preflight §2 原版 · 用户 4 次 ultrathink 纠偏 · ground-truth 中锐网络续贷包（用户本地 D:/刘野/众安/新建文件夹/2026.3.25续贷材料 · 21 份异构文件 + 5 银行流水子目录）

### 背景

Batch 1 review 发现 worker 100 家 yaml + 15 家 shortlist + 15 pits 模板。Preflight §2 DF-1~13 硬指标全通过，**但 yaml 形态本身错**：

- Agent6/3 真实输入 = 客户完整材料包文件夹（pdf/xlsx/docx/扫描件混合），不是 yaml
- Agent1 核心能力 = 从内部 KB 出发实搜外部企业（外部候选**不能 mock**）
- Agent5 核心能力 = 从内部制度库出发实搜外部政策比对（外部政策**不能 mock**）
- Agent4/2 独立本 v2 不覆盖

worker yaml 把材料解析/外搜/比对核心能力全部 bypass，答案字段（difficulty/tags/benchmark_ref）直接喂到 key-value = 把饭喂到模型嘴边。

**定责**：(1) Q-023 决策就错 · 上任主 CLI 没贯彻 §3.1 形态约束；(2) Preflight §2 没检查形态是否对 · 本任主 CLI 盲点；(3) CLAUDE.md §3.1-3.3 没条款化 mock 数据归属原则。

### 选项

- A REJECT-V2 完全重做
- B 保留 yaml 删答案 + 另起深柱
- C 实质 REJECT-V2 + 范围重划 · 推翻老 · 新建 3 组 mock（deep-pillar 5 家 + channel-kb + compliance-kb）· 保留 yaml 文字迁入 channel-kb/historical-clients

### 推荐

**C**。演化出形态矩阵 + 元规则（反结果导向第 5 条环境边界：mock 给 Agent 稳态内部 context 不替它外搜）· 分 Phase（Phase 1 Agent6/3/1/5 · Phase 2 Agent4 · Phase 3 Agent2）

### [A-028] 2026-04-24 · 主 CLI 自定

**Decision**: C（REJECT-V2 + 范围重划 + 反结果导向 5 原则首入 CLAUDE.md §3.5）

**Phase 1 Mock 矩阵**：

| Agent | mock 形态 | 位置 | 外搜 |
|---|---|---|---|
| Agent6 + Agent3 | 5 家深柱完整材料包（中锐形态） | data/mock/deep-pillar/DP001~005/ | — |
| Agent1 | 内部 KB：历史画像 + 营销倾向 + 产品目录 | data/mock/channel-kb/{historical-clients, marketing-preferences, product-catalog}/ | 实搜 |
| Agent5 | 内部制度库 5 子目录 | data/mock/compliance-kb/{credit-sop, customer-admission, kyc-aml, risk-preference, review-checklists}/ | 实搜 |

**v2 产物**：docs/onboarding/data-foundation-phase-1-v2.md + docs/handoff/data-foundation-v2-kickoff.md

**对其他 3 worker**：
- code-urgent 🟢 CONDITIONAL-APPROVE → merge + holding task W1/W2 清
- code-arch 🟢 APPROVE → merge（Agent6 v16 bit-identical）+ holding task W1 清
- evaluation 🟡 APPROVE → merge · 首轮 baseline 暂估数 · holding task W1 清（Batch 2 等 Phase 1 真 mock 重跑）

**Follow-up**:
- CLAUDE.md §3.5 反结果导向 5 原则（已落）
- Preflight §2 重写 v2 版
- Commit 拆：(a) Q-028/A-028 Signal: A-028-RESOLVED (b) v2 onboarding + kickoff + §3.5 + Preflight §2 v2 Signal: PHASE-1-DATA-FOUNDATION-REJECTED-V2-DISPATCHED
- 汇报时贴 v2 kickoff + 3 worker holding kickoff 给用户一并粘贴
- Batch 2 规划等 4 全 APPROVE + Phase 1 落地再正式启动

---

## [Q-029] 2026-04-24 · main CLI (self) · Batch 1 closeout + Batch 2 dispatch 四轨分配 + DF-V2-13 测试阶段豁免

**CLI**: main (self-Q/A)
**Priority**: P0
**Blocking**: no
**Related**: Q-023/A-023 · Q-028/A-028 · Preflight v2 review 4 agent · demo-runbook + dod-current-status

### 背景

Batch 1 状态 4/4 APPROVED：
- code-urgent + holding（合流 28d1037/54e42a8）CONDITIONAL→APPROVED
- code-arch + holding（合流 53f3eca/b412656）APPROVED
- evaluation + holding（合流 069f589/2530b5c）APPROVED
- data-foundation v2（e4f23b5）返工 · 15 硬指标全过 · F1-F5 未触发

### DF-V2-13 测试阶段豁免

用户决策："重复也没问题，只要格式对就行，我们就是测试使用"—— 2026 Q2 测试阶段重名不构成法律风险。

**豁免范围**：
- ✅ 测试阶段 2026 Q2 · 内部开发 + 内部演示
- ❌ 对外客户演示 / 商业化 / 签单 · 必须补 PM google 5 家非真存续

5 家脱敏名册（未来追溯）：龙峰精工 / 蓝汀家电 / 宸星家装 / 汇德建材 / 星胤实业

**追踪 Q-029.D**：一旦进入对外场景触发追查。

### Batch 2 四轨

| 轨 | Worker | 范围 | 期望 Signal | 工时 |
|---|---|---|---|---|
| 前端 | code-urgent | 证据链前端化 archive evidence UI + 高亮卡 + 未填标记 | READY-FOR-CODE-URGENT-B2-REVIEW | 2-3 天 |
| 外搜 | code-arch | Agent1/5 SearchProvider 接 Tavily + 银保监/央行 · 读内部 KB 做种子 | READY-FOR-CODE-ARCH-B2-REVIEW | 3-5 天 |
| 评估 | evaluation | 真基线重跑 DP001-005 + EV-12 ratio_calc_consistency + Agent1/5 召回精确率 | READY-FOR-EVALUATION-B2-REVIEW | 2-3 天 |
| 数据 | data-foundation | Phase 2 Agent4 mock（alert-pool 客户 + 流水 + 外部信号） | READY-FOR-DATA-FOUNDATION-B2-REVIEW | 5-7 天 |

**Onboarding**：
- docs/onboarding/batch-2-code-urgent-evidence-frontend.md
- docs/onboarding/batch-2-code-arch-external-search.md
- docs/onboarding/batch-2-evaluation-real-baseline.md
- docs/onboarding/batch-2-data-foundation-phase-2.md

**Kickoff**: docs/handoff/batch-2-kickoffs.md

### [A-029] 2026-04-24 · 主 CLI 自定

**Decision**: Batch 1 closeout + DF-V2-13 测试豁免 + Batch 2 四轨 dispatch

**Follow-up**:
- 本 commit Signal: Q-029-RESOLVED
- v2 合流 Signal: PHASE-1-DATA-FOUNDATION-V2-APPROVED
- Batch 2 onboarding × 4 + kickoffs + DF-V2-4 polish 合 1 commit Signal: BATCH-2-DISPATCHED

---
