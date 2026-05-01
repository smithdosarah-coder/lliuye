# 数据飞轮 · 第 4 环 Runbook（PM 操作手册）

**第 4 环 = 从 feedback 提取 few-shot 示例，注入 prompts.py**

对应 CLAUDE.md §6：静态知识 → 模型评估 → **动态经验(feedback)** → **提示词优化(few-shot)**。本轮关注后半段自动化链路。

**责任人**：AI 产品经理（刘野 / 代理人）
**节奏**：每周一固定时段；或 `/api/feedback/stats` 某 agent 累计 ≥ 20 条时临时触发

> **2026-05-01 update (Phase B BE10 worker-B1)**: 加了 3 件 ——
> (1) /api/feedback 同步写 audit log (银保监合规留痕 · §Step 0)
> (2) `evaluation.runner --gate` blocker_threshold 真接 publish 闸门 (§Step 6)
> (3) PoC 范围 = `agent_credit` 闭环 · 其余 5 agent 下一迭代接入 (§PoC scope)
> 详 `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` BE10 + Codex R2 §1.6 (缩 scope · 不重 A/B 平台 · 真 production Phase C)。

---

## Step 0. Audit modify 流水（自动 · 无需 PM 操作）

每次 `POST /api/feedback`（审贷员前端点"修改并保存"按钮）端点除写 `data/feedback/YYYY-MM-DD.jsonl` 外，**同步**写 `audit_service` 的 `llm_calls` 表 ——

| audit 字段 | 来源 |
|---|---|
| `endpoint` | `/api/feedback` |
| `model` | `user-feedback` |
| `user_id` | feedback payload 的 `user_id` |
| `agent_id` | feedback payload 的 `agent` |
| `prompt` | original_output JSON (LLM 原输出) |
| `response` | user_correction JSON (审贷员改后) |
| `error` | correction_reason (改的原因 · 可空) |

**用途**：银保监合规留痕 + 倒推某客户的人工干预历史。admin 查询：

```bash
curl -H "Authorization: Bearer <admin-token>" \
  "https://demo.liuye.me/api/audit/llm_calls?endpoint=/api/feedback&agent_id=credit&limit=100"
```

**故障容忍**：audit 写盘失败时主流程仍 200，jsonl 不丢（审贷员反馈是飞轮源头，不能因 audit 故障而丢）。日志会打 `[api_server] audit modify record failed: ...`。

**回归测试**：`tests/test_feedback_audit_modify.py` 三 case（happy / 400 / audit 故障 silent）。

---

## 数据流

```
审贷员修改 Agent 输出
    ↓ /api/feedback (api_server.py)
data/feedback/YYYY-MM-DD.jsonl              （第 3 环产出）
    ↓ scripts/feedback_to_fewshot.py
data/fewshot/<agent>-candidates.json         （聚类后的候选）
    ↓ PM 人工 review（必有）
data/fewshot/<agent>-candidates.json         （review 后版本）
    ↓ scripts/inject_fewshot_to_prompts.py
agent_<name>/prompts.py  :: FEW_SHOT_EXAMPLES （注入后的版本）
    ↓ Agent LLM 调用自动消费
```

---

## 周一 SOP（约 20 分钟）

### Step 1. 聚合候选（机器）

```bash
py scripts/feedback_to_fewshot.py --since 2026-04-01 --min-count 2 --top-n 5
```

- `--since`：只看本周的 feedback（避免老反馈抢位）
- `--min-count 2`：至少 2 条相似才入选，剔除偶发个例
- `--top-n 5`：每 agent 最多 5 个 few-shot，太多会污染上下文

产物：`data/fewshot/{channel,credit,alert,compliance,report,riskctrl}-candidates.json`

### Step 2. Review 候选（人）

逐个 agent 打开 candidates JSON，检查 6 条：

- [ ] `reason` 是否写明白了"审贷员为什么改"；模糊的（如"不好"）→ **删**
- [ ] `preferred_output` 的金额/日期/公司名有没有 PII；有 → **脱敏**或删
- [ ] `sample_input` 与 `preferred_output` 的字段 key 对齐（同一字段在改什么）；不对齐 → **删**
- [ ] 这条反馈是"个性化偏好"还是"共性错误"；个性化 → **删**，共性才留
- [ ] 同一 agent 下是否有重复聚类键；合并 `count`
- [ ] 最终每 agent 留 **2-4 条**高信号 example（多于 4 条会撑 prompt token）

### Step 3. 注入（机器）

先 dry-run 看要改哪些 prompts.py：

```bash
py scripts/inject_fewshot_to_prompts.py --dry-run
```

确认无误：

```bash
py scripts/inject_fewshot_to_prompts.py
```

注入点在每个 `agent_<name>/prompts.py` **末尾**，由以下 marker 包围，幂等可重跑：

```python
# >>> FEW_SHOT_EXAMPLES · auto-injected · do not edit inside >>>
# generated_at: 2026-04-24T...
# agent: credit
# count: 3
FEW_SHOT_EXAMPLES = [ ... ]
# <<< FEW_SHOT_EXAMPLES · auto-injected · do not edit inside <<<
```

### Step 4. 验证（机器）

Agent 侧读 `FEW_SHOT_EXAMPLES` 并拼进 system prompt：跑一次对应 Agent 的 demo，肉眼看输出风格是否向反馈方向收敛。

如果发现注入错了 / 拉垮了输出 → **立即回滚**：

```bash
py scripts/inject_fewshot_to_prompts.py --revert
```

（marker 块会被原子抹除，prompts.py 回到注入前状态）

### Step 5. 归档

把当周的 `data/fewshot/*-candidates.json` 复制到 `data/fewshot/archive/YYYY-WW/` 做留痕。**原位置**应保持为最新版，供下次 inject 复用（仍可跑 --revert 再重跑 --inject）。

---

## Step 6. blocker_threshold gate（CI 阻断发布 · BE10）

注入 few-shot 后 / 任何 prompt 改动后必须跑：

```bash
py -m evaluation.runner --all --gate
echo $?    # 0 = 全 PASS · 1 = 至少 1 PARTIAL/FAIL · 3 = blocker_threshold 触发(阻断发布)
```

**退出码 + 发布闸门语义**（per BE10 + Codex V2 + Sprint 2 决策 3 · 2026-05-01 4-state 升级）：

| 码 | 含义 | per-metric 状态 | 动作 |
|---|---|---|---|
| 0 | 全 metric `PASS` (≥ 0.95 × baseline_target) 或 `SKIP` | 🟢 PASS / ⚪ SKIP | **安全发布**（唯一允许自动放行） |
| 1 | 任一 metric `PARTIAL` (0.80-0.95 × bt) 或 `FAIL` (< 0.80) | 🟡 PARTIAL / 🟠 FAIL | **默认阻断**，需 PM 评审豁免才能放行 |
| 2 | adapter 未实现 / 异常 | — | **必修代码**后重跑 |
| 3 | 任一 metric 跨 `blocker_threshold`（仅 `--gate` 触发） | 🔴 BLOCKER | **不可豁免阻断**，回滚 prompt 改动 |

**Per-metric 4-state 阈值**（决策 3）：

```
越大越好 (target ">= X"):
  PASS    : value ≥ 0.95 × baseline_target   🟢
  PARTIAL : value ≥ 0.80 × baseline_target   🟡
  FAIL    : value < 0.80 × baseline_target   🟠
  SKIP    : value=None or no baseline_target ⚪

越小越好 (target "<= X"):
  PASS    : value ≤ 1.05 × baseline_target   🟢
  PARTIAL : value ≤ 1.20 × baseline_target   🟡
  FAIL    : value > 1.20 × baseline_target   🟠
  SKIP    : 同上 ⚪
```

stdout 标记：`OK` (PASS) / `~~` (PARTIAL) / `X ` (FAIL) / `??` (SKIP) / 后缀 `[BLOCKER]`。

> 红线：只有退出码 0 才视作"自动放行"。1/2/3 都属于阻断，强度递增（1 可 PM 评审豁免 / 2 必修 / 3 不可豁免）。
> 早期版本运行手册曾把 1 写成"可发布"——已修正为"默认阻断需豁免"，避免审贷员/合规官误解。

每条 metric 在 `evaluation/agent*.yaml` 的 `blocker_threshold` 字段定义阻断线。方向自动从 `target` 操作符推导（`>= X` → 越大越好 · `<= X` → 越小越好），name hint 仅作 fallback（修自 2026-05-01 baseline run 误判 case）。

**Phase B 启动时的 known blocker（不阻 worker-B1）**：

| Agent | metric | value | threshold | owner |
|---|---|---|---|---|
| alert | signal_diversity | 0.0 | ≥ 0.60 | worker-B4-alert BE5 |
| compliance | policy_coverage | 0.5 | ≥ 0.90 | worker-B4-compliance BE4 |
| compliance | conflict_recall | 0.5 | ≥ 0.90 | worker-B4-compliance BE4 |
| report | task_completion_rate | 0.0 | ≥ 0.98 | worker-B4-report BE3 |

每个 worker-B4-* 自验：自家 agent 这条 blocker 清掉后才能 phase-b-sprint{N}-end tag。

**回归测试**：`evaluation/runner/tests/test_blocker_gate.py` 7 case。

---

## Step 7. Phase B-2 baseline regen（Sprint 2 末 · 决策 4）

**触发条件**：`worker-B4-credit BE2 + worker-B4-report BE3 + worker-B4-compliance BE4` 全部 cherry-pick 到 main 后，主 CLI 给 worker-B1 commit signal `SPRINT-2-BASELINE-REGEN-GO`。worker-B1 收到信号即跑：

```bash
py -m evaluation.runner --all --out evaluation/baselines/2026-05-15-phase-b-sprint2-end.json
# 然后产出 evaluation/baselines/2026-05-15-phase-b-sprint2-end.md
```

**新指标（Sprint 2 收口含进 baseline 的）**：

| Agent | 新维度 | 来自 | 期望基线 |
|---|---|---|---|
| credit | `decision_graph_evidence_complete_rate` | worker-B4-credit BE2 (decision graph + peer_gap) | ≥ 0.85 |
| report | `task_completion_rate` | worker-B4-report BE3 (现 0.0 → 完后 ≥ 0.85) | ≥ 0.85 |
| report | `cross_section_coherence` | worker-B4-report BE3 (跨章节 sanity) | ≥ 0.90 |
| compliance | `conflict_recall` | worker-B4-compliance BE4 (现 0.5 → 完后 ≥ 0.85) | ≥ 0.85 |

**Sprint 2 末 (2026-05-15) 验收**：
- 4 项 known blocker 是否清掉（`alert/signal_diversity` 仍由 worker-B4-alert 单独 sprint 推后）
- baseline JSON commit hash 与 main HEAD 一致（per V2 codex review baseline-regen 红线）
- 加 `phase-b-sprint2-end-2026-05-15` git tag
- 写 `evaluation/baselines/2026-05-15-phase-b-sprint2-end.md` 含 verdict + delta vs `2026-05-01-phase-b-start`

**当前 sprint 不做实际 regen**：BE2/BE3/BE4 还在并行 worker 推进，现在 regen 数据无变化（参 commit `1d1af95`）。等 main CLI 收齐 cherry-pick 再发 `SPRINT-2-BASELINE-REGEN-GO`。

---

## PoC scope（only `agent_credit` consumes FEW_SHOT_EXAMPLES · 2026-05-01）

**Production safety**（per Codex V2 review）：

- **Feature flag**：`LIUYE_FEWSHOT_POC_ENABLED` 默认 **off**。`build_system_prompt(base)` 在 flag 关时直接返 `base`，完全 no-op。要让 PoC 真生效需在 `.env` / 启动脚本里 `export LIUYE_FEWSHOT_POC_ENABLED=1`。
- **PII redaction**：`_format_fewshot_block` 在喂 LLM 前对 `sample_input` / `preferred_output` / `reason` / `diff_summary` 走 `_redact_pii`，mask 手机 / 身份证 (15 + 18) / 银行卡 (16-19 位) / 邮箱。回归见 `tests/test_fewshot_poc_e2e.py::test_pii_redaction_masks_phone_idcard_bankcard_email`。

**当前**：只 `agent_credit/prompts.py` 实现 `build_system_prompt(base)` + `_format_fewshot_block`，并在 `agent_credit/advisor_formatter.py` 的对公/零售决策路径调用。

**其他 5 agent**（channel / alert / compliance / report / riskctrl）下一迭代接入 —— 当前 `inject_fewshot_to_prompts.py` 仍会把 `FEW_SHOT_EXAMPLES = [...]` 写入它们的 `prompts.py`，但还无消费者，常量是死的。这是有意的 PoC 缩 scope ——

- 防一次接 6 处出问题难定位
- 6 agent prompt token 同时爆有成本
- 先让 PM 验 agent_credit 端到端效果，确认 few-shot 收敛风格真有用，再展开

**展开做法**（每 agent 5 分钟）：

1. 在 `agent_<name>/prompts.py` 末尾 append（marker 之前）：
   ```python
   FEW_SHOT_EXAMPLES: list[dict] = []

   def _format_fewshot_block(examples: list[dict]) -> str: ...  # 抄 agent_credit
   def build_system_prompt(base: str) -> str: ...               # 抄 agent_credit
   ```
2. 在主消费点（找 `llm_chat(SYSTEM_*, ...)`）替换为 `llm_chat(build_system_prompt(SYSTEM_*), ...)`
3. 跑 `tests/test_fewshot_poc_e2e.py` 同款 e2e 验证
4. 后续考虑抽到 `shared/prompts/fewshot.py` 单源（现版本 PoC 优先，不抽抽象）

---

## 红线

- 🔴 **绝不自动 inject**：Step 2 的人工 review 不能省；脚本层已刻意拆成两步。
- 🔴 **Prompts 改动走 PR**：`inject_fewshot_to_prompts.py` 写盘后 **必须** commit 才算完。commit message 形如 `chore(prompts): inject fewshot 2026-W17 · credit=3, alert=2`。
- 🔴 **任何脱敏失误看到即回滚**：审贷员反馈里可能带客户真实名字/金额，review 阶段必须全部脱敏或删条，不要留在 prompts.py 里。
- 🟡 **max-shots**：单 agent ≤ 4 条，超了就 `--top-n 3`；上下文 token 是成本。
- 🟡 **滚动窗口**：默认 `--since` 取最近 4 周；超过 4 周前的 feedback 大多过期（业务/政策变了）。

---

## 故障排查

| 症状 | 可能原因 | 处置 |
|---|---|---|
| `candidates not found` 警告 | 先没跑 feedback_to_fewshot | 先跑 Step 1 |
| Step 1 跑完 `candidates` 为空 | `--min-count` 过严 / feedback 目录空 | 放宽到 `--min-count 1` 看看，仍空则 /api/feedback 没在收 |
| inject 后 LLM 输出变差 | few-shot 质量不行 / 示例偏差 | `--revert` 回滚，回 Step 2 重新 review |
| 注入 marker 重复出现 | 手改过 prompts.py 破坏了 marker | 人工删掉所有 marker 块后重跑 inject |

---

## 相关文件

- `scripts/feedback_to_fewshot.py` — Step 1 聚合
- `scripts/inject_fewshot_to_prompts.py` — Step 3 注入
- `api_server.py` `/api/feedback` 端点（含 audit modify · Step 0）
- `audit_service/recorder.py` — audit log sqlite 后端
- `audit_service/api.py` — admin GET `/api/audit/llm_calls`
- `evaluation/runner/cli.py` — `--gate` flag · Step 6
- `evaluation/runner/base_evaluator.py` — `_mark_blockers` + `_direction_lower_is_better`
- `agent_credit/prompts.py` — `build_system_prompt` + `FEW_SHOT_EXAMPLES`（PoC scope · 唯一接入点）
- `agent_credit/advisor_formatter.py` — 对公 + 零售决策路径调 `build_system_prompt`
- `data/feedback/` JSONL 沉淀目录（**gitignored**，含真实审贷员反馈可能含 PII）
- `data/fewshot/` 候选 + archive 目录（**gitignored**）
- `tests/fixtures/feedback/2026-04-23.jsonl` 10 条合成样本（冒烟测试用，不入生产目录）
- `tests/test_feedback_audit_modify.py` — Step 0 audit-modify 回归
- `tests/test_fewshot_poc_e2e.py` — PoC 端到端冒烟
- `evaluation/runner/tests/test_blocker_gate.py` — Step 6 blocker gate 7 case

首次部署本脚本时想跑个 demo：

```bash
cp tests/fixtures/feedback/2026-04-23.jsonl data/feedback/
py scripts/feedback_to_fewshot.py --min-count 2
```
