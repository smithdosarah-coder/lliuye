# Session Handoff · 2026-04-24 · Batch 2 Dispatched + 4 Worker On-Task

> 本文档是本任主 CLI（重开前写的）给下任主 CLI 的**交班脑图**。
> 新 main CLI resume 后读本文 + `AGENT_IDENTITY.md` 清单所有文件 → 100% 接替。

---

## 0. 一眼 Verdict

- **Batch 1 Product Hardening**：🟢 4/4 APPROVED + merged + 3 holding task done + data-foundation v2 REJECT-V2 返工通过
- **Batch 2**：🟢 已 dispatched（commit `e68f28e · Signal: BATCH-2-DISPATCHED`）· 4 worker 在 Task A
- **当前 worker 状态**（2026-04-24 16:xx）：
  - code-urgent：Task A 证据链 UI 组件（tip `bf19ad3` Batch 2 ACK commit）
  - code-arch：Task A 开工中（**scope 已被本任主 CLI 更正**，见 §3）
  - data-foundation：Task A clients.csv（tip `bddced8` · Signal: `PRODUCT-HARDENING-BATCH-2-DF-P2-ACK`）
  - evaluation：Task A 真 baseline（主 CLI 已在 chat 发 GO prompt · 粘给 worker 即开干）
- **3 条 follow-up**：见 §4

---

## 1. 本 session 主 CLI 做完的事（commit SHA 清单 · chore/l0-infra）

```
e68f28e docs(batch-2): Batch 2 dispatch · 4 onboarding + kickoffs + DF-V2-4 polish
c8e6277 Merge feat/data-foundation v2: PHASE-1-DATA-FOUNDATION-V2-APPROVED
e07066d docs(decisions): Q-029/A-029 Batch 1 closeout + Batch 2 dispatch + DF-V2-13 test waiver
2530b5c Merge feat/evaluation holding: HOLDING-EV-DONE
b412656 Merge feat/code-arch holding: HOLDING-CA-DONE
54e42a8 Merge feat/code-urgent holding: HOLDING-CU-DONE
1f881da docs(handoff): Batch 1 holding kickoffs
40f653f docs(data-foundation): REJECT-V2 dispatch + env-boundary rule 5 (CLAUDE.md §3.5)
665a811 docs(decisions): Q-028/A-028 data-foundation Batch 1 REJECT-V2 (yaml form error)
069f589 Merge feat/evaluation: APPROVED
53f3eca Merge feat/code-arch: APPROVED
28d1037 Merge feat/code-urgent: APPROVED
75df5d6 docs(handoff): Batch 1 review preflight
e4f882a docs(decisions): Q-025 rubric YAML schema compatibility layer
b07c1a5 docs(decisions): Q-024 evaluation worker path conflict resolved
```

---

## 2. Batch 2 四轨摘要

| 轨 | Worker | Task 概览 | Onboarding 路径 | 预期工时 |
|---|---|---|---|---|
| 前端 | code-urgent | A 证据链 UI / B 高亮卡 / C 未填标记 | `docs/onboarding/batch-2-code-urgent-evidence-frontend.md` | 3-3.5 天 |
| 外搜 | code-arch | A Agent1 接 channel-kb（**scope 更正**）/ B Agent5 外搜 / C integration test | `docs/onboarding/batch-2-code-arch-external-search.md` | 2.5-4 天 |
| 评估 | evaluation | A 真 baseline / B EV-12 / C Agent1/5 召回精确度 | `docs/onboarding/batch-2-evaluation-real-baseline.md` | 4 天 |
| 数据 | data-foundation | A clients.csv / B transactions / C external-signals | `docs/onboarding/batch-2-data-foundation-phase-2.md` | 2-3 天 |

4 条 kickoff prompt 合汇：`docs/handoff/batch-2-kickoffs.md`

---

## 3. ⚠️ 关键 scope 更正 · code-arch Batch 2 Task A

**本 session 查源发现**：Agent1 的 Tavily 搜索 + SearchProvider + 工商查询**已就绪**：
- `agent_channel/realtime_stream.py` 已实调 `TavilyClient(api_key=tavily_key)` + 有 tavily/mock_forced/mock_fallback 降级路径
- `agent_channel/lead_finder.py` 已用 `SearchProvider` 接口
- `agent_channel/domains/profile.py` 已调 `profile_fetch_qcc_info`（工商查询）

onboarding 写的"接 Tavily"是重复造轮子。**Task A 真正范围**：

1. 让 Agent1 读 `data/mock/channel-kb/marketing-preferences/*.docx` 提取种子查询词（行业 + 地区 + 营收区间 + 资质偏好）喂给现有 SearchProvider
2. 读 `channel-kb/historical-clients/*.md` 做 **look-alike 相似度匹配**（行业 / 规模 / 资质 tag 相似）
3. 读 `channel-kb/product-catalog/*` 做产品推荐（match 候选企业到银行自家产品）

scope 更正 prompt 已在 chat 给用户粘给 code-arch worker（内容骨架：`SCOPE 更正 · Batch 2 Task A`... 若 code-arch worker 没收到 · 新主 CLI 根据上 3 条要点重发）。

**新主 CLI review 注意**：`AGENT1-EXTERNAL-SEARCH-DONE` 验证应核对**按新 scope 消费 channel-kb**，不是验 Tavily 是否接通（那本来就通）。

---

## 4. Follow-up 清单

### 4.1 🟡 Preflight §2 v2 DF-V2-4 阈值 polish（pending）

- 原 `20 ≤ 份数 ≤ 40 / 每家` · 实际 worker 产 43-61 份（合理 · 对齐中锐 ground-truth 90 份形态）
- 本 session 曾 Edit 但 race fail（skill 升级 session 并行改动）· 未随 `e68f28e` commit 进去
- 新主 CLI 重 Read + Edit · 独立 commit · Signal: `PREFLIGHT-V2-DF-4-POLISH` 或类似合法 format
- 文件：`docs/handoff/batch-1-review-preflight.md` line 169 附近

### 4.2 🟡 mesh_launch.py shim 存在（本 session 补 · 不在 repo）

- 路径：`~/.claude/skills/multi-cli-mesh/scripts/mesh_launch.py`（~90 行）
- 背景：skill v2 Phase F 删了原 mesh_launch.py · 新 `orchestrator/launcher.py` 只做 register/migrate · 丢了"起多 tab"能力 = regression
- bat 靠这个 shim 才能跑（`C:\Users\Mr.S\Desktop\mesh-credit-agents.bat`）
- 不在任何 git · 机器重装需重写
- 新主 CLI 知道即可 · 不需要动

### 4.3 🔴 DF-V2-13 测试豁免追踪（Q-029.D 条款）

- 当前测试阶段（2026 Q2）允许脱敏企业名重名真实存续企业
- **对外演示 / 商业化前**必须 PM google 5 家 DP 脱敏名：**龙峰精工 / 蓝汀家电 / 宸星家装 / 汇德建材 / 星胤实业**
- 触发条件：用户说"要给客户 demo" / "准备签单" / "对外演示" / "商业化" 等关键词时
- 追查落点：重查 DP001-005 材料包企业名 + 要求 PM 签字

---

## 5. 新主 CLI Resume Playbook

### 5.1 第一轮动作

1. 读 `AGENT_IDENTITY.md` + 里面列的所有文件（含本文档）
2. 跑 `py ~/.claude/skills/multi-cli-mesh/scripts/orchestrator/scoreboard.py` 看 4 worker 最新 signal
3. 跑 `git log --format='%h %s' -20 chore/l0-infra` 看最近 commit
4. 跑 `py ~/.claude/skills/contract-audit/scripts/audit.py` 扫漂移（identity §13 要求）
5. 回报用户 resume 完成 + 当前 pending

### 5.2 Signal Playbook（Batch 2 预期信号流）

**code-urgent** (3 Task + ACK + READY)
- ACK: `BATCH-2-CU-ACK`
- Task done: `ARCHIVE-EVIDENCE-UI-DONE` / `HIGHLIGHT-CARD-UI-DONE` / `UNFILLED-MARKER-UI-DONE`
- Ready: `READY-FOR-CODE-URGENT-B2-REVIEW`

**code-arch** (3 Task + ACK + READY)
- ACK: `BATCH-2-CA-ACK`（可能 worker 用一句话 ACK 无 trailer · 看 commit message）
- Task done: `AGENT1-EXTERNAL-SEARCH-DONE` / `AGENT5-POLICY-COMPARE-DONE` / `BATCH-2-INTEGRATION-TEST-DONE`
- Ready: `READY-FOR-CODE-ARCH-B2-REVIEW`

**evaluation** (3 Task + ACK + READY)
- ACK: `BATCH-2-ACK`（evaluation 的 kickoff 要求 resume 汇报后等 GO · 已发 GO 指令）
- Task done: `BASELINE-REAL-DONE` / `EV-12-RATIO-CONSISTENCY-DONE` / `AGENT1-5-METRICS-DONE`
- Ready: `READY-FOR-EVALUATION-B2-REVIEW`

**data-foundation** (3 Task + ACK + READY)
- ACK: `PRODUCT-HARDENING-BATCH-2-DF-P2-ACK`（已 commit `bddced8`）
- Task done: `ALERT-POOL-CLIENTS-DONE` / `ALERT-POOL-TRANSACTIONS-DONE` / `ALERT-POOL-SIGNALS-DONE`
- Ready: `READY-FOR-DATA-FOUNDATION-B2-REVIEW`

### 5.3 4 worker 全 READY 后的动作

1. **派 4 agent 并行 review**（Batch 1 经验：cd 各 worker worktree · 跑 Preflight §N.3 命令 · 对 DoD 硬指标打分）
2. **合流顺序**：code-urgent → data-foundation → code-arch → evaluation（按 Preflight §5.1）
3. 每轨独立 commit · `Signal: PHASE-2-<X>-APPROVED`（known pattern）
4. 合流后 **Batch 2 closeout** + 规划 **Batch 3 = Phase 3 · Agent2 风控样本 CSV**（最后一批）

### 5.4 红线（主 CLI 自守）

- ❌ 不在 worker 分支上动代码
- ❌ 不绕 decisions-log 直接批示
- ❌ 改红区（`financial_analyzer.py` / `quality_scorer.py` / `truth_fill.py` / `web/src/lib/store/*`）必须 RFC
- ❌ 不主动 spawn worker CLI（用户双击 bat）
- ❌ 不改 `demo-start.bat`（用户服务器脚本，动了他不能 demo）
- ✅ 批示必须 commit trailer 带 `Signal: XXX`（单行）
- ✅ 红线 4 硬闸：GO + TaskCreate + 方案先行 + Authorized-By trailer（针对演示型前端 / 红区）

### 5.5 用户协作模式（本 session 5+ 次 ultrathink 纠偏沉淀）

- **说人话**：短 + verdict 先行 + 不啰嗦（被纠偏 3 次）
- **不要挂机**：主 CLI 要主动推进 · 不要被动等 signal（被纠偏 2 次）
- **子 CLI 利用起来**：有活派给 worker · 不自己闷头干脏活（被纠偏 3 次）
- **scope 对齐**：scope 模糊先问一个具体问题 · 不猜
- **形态真实**：mock 要像真实客户材料（文件夹 + 异构 pdf/xlsx/docx + 扫描件 + 命名混乱 + 三方数字矛盾）· yaml 形态 = REJECT-V2（本 session 触发过）
- **环境边界**（反结果导向第 5 条 · 本 session 首次条款化到 CLAUDE.md §3.5）：mock 只给"稳态内部 context" · 不替 Agent 做本该外搜的工作
- **不谄媚**：方案有问题直接说 · 不"好的"

### 5.6 DON'T（新主 CLI 避雷）

- ❌ 不要对"Agent1 接 Tavily"感到困惑 —— 本 session 查过 · 它已接 · onboarding 字面过时 · 实际 Task A = 接 channel-kb（见 §3）
- ❌ 不要再试 `~/.claude/skills/multi-cli-mesh/scripts/mesh_status.py` 或 `mesh_launch.py` —— 前者不存在（用 `orchestrator/scoreboard.py` 代替）· 后者是本 session 补的 shim
- ❌ 不要删 mesh_launch.py shim · bat 靠它
- ❌ 不要对 DF-V2-13 "PM 抽检"感到紧张 —— 测试阶段已豁免（Q-029.D）· 只有对外才要补
- ❌ 不要在 Batch 2 所有 worker READY 前规划 Batch 3 · 按协议等 4/4 APPROVED

---

## 6. 签名

- 本任主 CLI 签名：chore/l0-infra @ 2026-04-24（Batch 2 dispatched · 4 worker on-task · 用户准备重开主 CLI 用新 skill v0.2.2）
- 接力锚 commit：本 handoff doc 附 `Signal: ORCHESTRATOR-HANDOFF-BATCH-2`
- 性格 hint：Opus 4.7 · 承担用户 5+ 次 ultrathink 纠偏（yaml 形态污染 / Agent1 本来就能搜 / skill v2 Phase F regression 等）· 善于派 subagent 分担 doc 脏活 · 被用户教会"子 CLI 利用起来 + 说人话"
