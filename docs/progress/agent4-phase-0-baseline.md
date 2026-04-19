# Agent4 预警 · Phase 0 baseline 首跑报告

**Worker**: agent4 · `feat/agent4-productize`
**Baseline commit**: `9dfcaf2`（`feat(eval): Agent4 Phase 0 baseline first run`）
**Adapter commit**: `52d3f90`
**日期**: 2026-04-19
**Verdict**: PARTIAL（6 deterministic PASS + 2 Phase C stubs N/A）

---

## 1. 结果摘要

| 类别 | 指标 | 值 | 目标 | 判定 | 方法 |
|---|---|---|---|---|---|
| common | task_completion_rate | 1.0000 | ≥ 0.95 | PASS | deterministic |
| common | evidence_rate | 1.0000 | ≥ 0.95 | PASS | deterministic |
| common | hallucination_rate | 0.0000 | ≤ 0.01 | PASS | deterministic |
| common | tool_success_rate | 0.9667 | ≥ 0.90 | PASS | deterministic |
| domain | grade_distribution_sanity | 1.0000 | pass | PASS | deterministic |
| domain | scan_latency_p95 | 0.0139 min | ≤ 30 | PASS | deterministic |
| domain | cross_hit_precision | N/A | ≥ 0.80 | — | **Phase C stub (manual)** |
| domain | recall_on_known_bad | N/A | ≥ 0.90 | — | **Phase C stub (manual)** |

**红线闸门（CLAUDE.md §5.1 + §5.2）**：hallucination / evidence / task_completion 三条全绿 → `baseline_failed: false`。

### Fixture 画像（`agent_alert/tests/fixtures/phase0_scan_sample.json`）

- 在贷客户 100 家（whitelist `E0001..E0100`，零越白名单）
- 分级 3 red / 22 yellow / 75 green（红 3% < 5%，绿 75% > 70%，分布合理）
- 证据：25 家红/黄客户全部附 ≥1 条 evidence（external + internal 双路）
- 工具调用：435/450 success（96.67%）
- 扫描耗时：P95 = 832.5ms（≈ 0.014 min，远低于 30 min 目标）

---

## 2. Top-3 Gap（Phase 0 → Phase 1 必须收的债）

### Gap 1 · Phase C 指标没有真值可算
`cross_hit_precision` 和 `recall_on_known_bad` 本阶段按 onboarding 指示返回 `value=None, method="manual"`，不假装能跑。根因：
- **Precision 差一个标注库**：需要给每条"红灯"打"真阳/假阳"标签才能算交叉命中精确率
- **Recall 差一个已知问题客户集**：需要业务侧给出"真问题客户清单"作为 ground truth
影响：Phase 0 只能证"扫描流程跑通 + 格式合规"，**不能证"识别的准不准、漏不漏"**。这是 Agent4 核心价值的量化锚——Phase 1 必须接上。

### Gap 2 · Fixture 是合成数据，不是真实在贷客户池
当前 100 家客户是按"合理分布"人工生成：
- 分级比例 3/22/75 是经验值拍的，生产环境红灯比例、行业分布可能大幅漂移
- 证据字段的 signal 取自固定枚举（5 red_signals × 5 yellow_signals），覆盖面窄
- 扫描耗时是 180-2200ms 均匀随机，不反映真实外部源（tavily / 工商 / 司法）延迟拖尾
影响：基线指标虽全绿，**不代表生产环境能过同样的闸门**。Phase 1 接真 ledger + 真外部源后基线可能塌一档。

### Gap 3 · 无回归保护：adapter 和 fixture 裸奔
- `agent_alert/tests/` 目录下没有 pytest 文件（`py -m pytest agent_alert/ -q` 收集到 0 个 test）
- adapter 的指标计算逻辑（`_p95`、grade_distribution_sanity 的 red<5% / green>70% 阈值、evidence 非空判定）没有单元测试
- fixture 被误改（某个 customer 的 grade 或 scan_time_ms 被手抖改掉）基线指标会静默漂移，没人报警
影响：后续迭代任何人改 adapter 或 fixture，**基线的"真金白银"会被稀释成"假通过"**。

---

## 3. Phase 1（productize）锚点

Phase 1 从 Phase 0 的 PARTIAL → PASS 必须同时收 Gap 1/2/3。建议 Phase 1 DoD 里写入：

### 锚点 A · 业务闭环
- **后端**：接入真 ledger（在贷客户表）+ 真外部扫描源（tavily + 工商 + 司法，走 `shared/kb_scan/search_provider.py` Provider 抽象），产出真 artifact 替换合成 fixture
- **前端**：按 `docs/design/platform-shell-v1.md` 4-view 模型，在「AI 助手」view 下挂 Agent4 tile → 红/黄/绿客户榜单 + 原因码下钻 + 证据链跳转

### 锚点 B · 评估补完（Phase C 指标）
- 发 RFC 定义标注库协议：每条红灯客户带 `{ground_truth_grade, known_bad: bool}` 字段
- 补 adapter 两个 Phase C 指标：从 `method="manual"` 升到 `method="deterministic"`（cross_hit_precision / recall_on_known_bad）
- **收口 DoD**：`py -m evaluation.runner --agent alert` verdict = **PASS**（不再 PARTIAL）

### 锚点 C · 回归护栏
- `agent_alert/tests/test_adapter.py`：单测 adapter 每个指标的 happy path + 1 个边界（空 fixture / 全绿分布 / 幻觉 > 阈值）
- `agent_alert/tests/test_fixture_shape.py`：schema-check fixture（whitelist 不重、grade 枚举、evidence 结构）
- CI 挂 `py -m pytest agent_alert/ && py -m evaluation.runner --agent alert` 做门禁

### 锚点 D · 前端落位不越界
Phase 1 前端改动由 frontend CLI 执行（按 `docs/onboarding/frontend-shell-phase-1.md`），Agent4 worker 只提供 API + artifact，**不碰 `web/`**。API endpoint 形态（SSE 流式 tick / REST 快照）在 Phase 1 onboarding 里定。

---

## 4. 红区 / 红线复盘

- **红区**：本次未碰 `shared/` / `docs/contracts/` / `web/` / runner framework / `CLAUDE.md` / `docs/design/*`。仅改黄区（`evaluation/runner/adapters/agent4_alert.py` 新增、`evaluation/agent4_alert.yaml` baseline 区块更新、`agent_alert/tests/fixtures/` 新增）。
- **Productize 禁令**：Phase 0 无任何 UI / API endpoint / Pipeline 节点改动。
- **信号规范**：单 commit 单 signal 已遵守（ACK / ADAPTER-READY / BASELINE-FIRST-RUN / READY-FOR-REVIEW 各独立 commit）。

---

## 5. Handoff 到主 CLI

- **本文件**：`docs/progress/agent4-phase-0-baseline.md`（本次新增）
- **基线 yaml**：`evaluation/results/4_20260419.yaml`（gitignored，本地可查）
- **JSON 原始产出**：`evaluation/results/2026-04-19/alert_9dfcaf2f.json`（框架自动持久化）
- **等待**：主 CLI review → `docs/scorecard/GLOBAL.md` Agent4 抬到 ~60% → 下发 `docs/onboarding/agent4-phase-1.md`
