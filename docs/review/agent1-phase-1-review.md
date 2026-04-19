# Agent1 Phase 1 Productize Review

**日期**：2026-04-19
**reviewer**：主 CLI
**onboarding**：docs/onboarding/agent1-phase-1.md
**worktree**：D:/claude code/demo-agent1 · branch `feat/agent1-productize`
**HEAD**：28d094a
**Signal**：AGENT1-PHASE-1-READY-FOR-REVIEW
**Range**：c4af59d..28d094a（5 commits：19fe4b2 Task A / ecfe05a Q-013 / 6379ae7 merge α kernel / 9df1466 Task B / c408b3a Task D）

## Verdict

**APPROVED**

## DoD 对账（逐条）

| 条目 | 状态 | 证据 |
|---|---|---|
| Task A · 字面枚举 ≥6 红区 | OK | `docs/progress/agent1-phase-1-redzone-gap.md:32-39` 列 7 条（runner 4 __init__/base/registry/cli/__main__ + decisions-log.md 等）@ `19fe4b2` |
| Task A · worker 只许保 upstream + abort + Q | OK | 文档 §2 加强项 + §4 演练实录；反例引 `fddb1c6`/`65dd432` + `e69244f`/`0292b94` 双 SHA |
| Task A · Q trail 可检索 | OK | `git log --grep=NEED-DECISION c4af59d..28d094a` → Q-013 @ `ecfe05a`；Q-007/8/9 在历史 decisions-log 可查 |
| Task B · `py -m evaluation.runner --agent channel` verdict=PASS | OK | reviewer 本地重跑 @ HEAD `28d094a` → `=== channel · PASS · 26.9s ===` common 5/5 + domain 4/5 OK + 1 pending |
| Task B · grep legacy metric key = 0 | PARTIAL | 活配置 `evaluation/agent1_channel.yaml` 已清；`evaluation/results/1_2026041{8,9}.yaml` 历史产物仍含 4 处（commit 自白 "非产物外 0 命中"，属回溯基线 dump，非回归） |
| Task B · yaml 仅剩 meta/scenarios/metrics/baseline | OK | yaml L10-75 仅 4 顶层段；`config_version: 1.1` |
| Task B · `scripts/eval_run.py` 删除 + 无残留引用 | PARTIAL | 脚本已删；活码引用 0；文档残留 7 处均为历史档（onboarding / decisions-log / review / 旧 progress），worker 不该改 |
| Task B · 红线闸门未回归 | OK | halluc 0.0 / evidence 1.0 / task 1.0 / diversity 2.3 / diversity_pass 1.0 — 全绿 |
| Task B · β mock-exempt 诚实语义 | OK | `evaluation/runner/adapters/agent1_channel.py` mock 分支 emit `passed=True + note="mock-exempt"` @ `9df1466` |
| Task B · pending 白名单语义落地 | OK | yaml L70-75 `baseline.pending_metrics: [candidate_relevance_at_top10]` + `pending_reason`，kernel `base_evaluator.py:96-97` 读白名单 |
| Task D · POST /api/feedback + JSONL 日分 | OK | `api_server.py` 既有端点（主 CLI 落）；reviewer 实跑 smoke `data/feedback/2026-04-19.jsonl` +1 ok |
| Task D · few-shot 抽取 → prompts.py 注入 | OK | `scripts/extract_feedback_fewshots.py` + sentinel 块 `agent_channel/prompts.py` @ `c408b3a` |
| Task D · E2E smoke 5 步 | OK | `scripts/feedback_smoke.py` 113 行 reviewer 实跑全绿：`prompts.py changed: 04fdb7e1d517 → 410303b01f9c` + marker 'LPR 减点 30bp' present |
| Task D · 红线未回归 | OK | Task D 后再跑 runner verdict=PASS 保持 |
| 全 Phase · pytest 29/29 | OK | reviewer 实跑 `py -m pytest agent_channel/ -q` → 29 passed in 7.81s |
| 全 Phase · handoff contract 8/8 | OK | reviewer 实跑 `agent_channel/tests/test_handoff_contract.py -v` → 8 passed |

## 硬规则对账

| 规则 | 状态 | 说明 |
|---|---|---|
| R-A smoke-must-test | OK | Task B commit msg 声称 `--agent channel → PASS`，reviewer 在 HEAD `28d094a` 重跑确认 PASS；Task D smoke 声称 `prompts.py changed`，reviewer 重跑 hash diff 可见 |
| R-B 一 commit 一 signal | OK | 5 个 commit trailer `Signal:` grep 各 1：`19fe4b2` TASK-A-DONE / `ecfe05a` NEED-DECISION Q-013 / `9df1466` TASK-B-DONE / `c408b3a` TASK-D-DONE / `28d094a` READY-FOR-REVIEW |
| A-012.D SHA 不可变 | OK | `git reflog feat/agent1-productize @{0..6}` 无 amend / rebase finish；Phase 1 的 5 commit 自 ACK 后均为新增，零重写 |
| Signal await semantics | OK | Task D commit msg 自陈 "idle 等主 CLI GO 再进 READY"；Task B / Task A 同纪律 |

## 红区审计（`git diff c4af59d..28d094a`）

Worker 零触碰红区。严格审计：

- `shared/**` `docs/contracts/**` `api_server.py` `agent_*/api/**` `evaluation/runner/{__init__,adapters/__init__,registry,cli,__main__}.py` — diff 命中 0
- `evaluation/runner/base_evaluator.py` — 变动仅来自 `7e6438d3`（主 CLI 亲操 A-013 α kernel patch），通过 merge `6379ae7f` 进入 worker 分支；`--first-parent` 无 worker 直触
- `docs/handoff/decisions-log.md` — 变动仅来自 `4414f525`（A-012，主 CLI 亲操）通过 merge `c4af59d` 进入；`--no-merges --first-parent` 命中 0 worker commit

## Top 3 Gap（Phase 2 锚点）

1. **`candidate_relevance_at_top10` 仍 pending** — Phase 1 按 A-012.C 授权 skip，baseline 标 `pending_reason: "Phase-2-Batch-2 human review"`。domain 4/5 实测 + 1/5 pending ≠ LLM 链路对齐业务语义。Phase 2 Batch 2 必须起人工回录（或 LLM-as-judge 半自动），domain 升 5/5。
2. **mock-exempt 覆盖了 source_url_reachable 真实 HTTP 探活** — 当前 `source_url_reachable_rate=1.0` 来自 `passed=True + note="mock-exempt"`，实际路径零覆盖。Phase 2 需补非 mock 场景（至少 1 个 Tavily 生产或 sandbox 采样）真测 HTTP 200 率，否则该指标形同虚设。
3. **Task D bootstrap sample 是 worker 自标（非审贷员）** — sentinel 块里 "LPR 减点 30bp / 专精特新切入" 是 worker 本地填的示范数据，真实反馈飞轮尚未接审贷员输入。Phase 2 需落「真实反馈 ≥ N 条阈值」+「低于阈值不抽 few-shot 回注」双保险，避免 bootstrap 污染实战 prompt。

## 亮点

- **A-013 跨 CLI 协作范式成立**：worker 在红区前主动 Q-013（`ecfe05a`）+ 主 CLI 亲操 α kernel（`7e6438d3`）+ worker 合并后落 β（`9df1466`）— 完美贯穿 A-012.D 红区归属原则，零越权。
- **β 语义修正体现治本思路**：mock 分支原 `passed=None` 借 None 语义表达豁免是历史误判；改 `passed=True + note` 后 Evidence-First 可见性与语义诚实双赢，而不是 adapter 过滤掉指标。
- **Task D 选 in-process TestClient 避端口**：`scripts/feedback_smoke.py` 不起 uvicorn / 不占端口，CI-friendly；smoke 覆盖 POST → JSONL → extract → prompts.py diff 5 步全链路。
- **pytest 29/29 + handoff 8/8 + runner PASS** 三锚点同时不倒退，productize L0~L3 层形态达标。
- Task A 演练档诚实标注 "正式协议归主 CLI" 不越权写 `shared-change-protocol.md`，纪律达标。

## Scorecard 预估

**Agent1**：82% → **86%**（目标 ≥ 85% 达成）

## Required Actions

无（APPROVED）。

**Phase 2 Batch 2 onboarding 起草时采纳**：
- Top Gap 1/2 作主线（domain 5/5 + 真 HTTP 探活）
- bootstrap 污染双保险作 Task D 延展
- Tavily production ingress（D1 原推迟项）与上述并轨

**主 CLI 落地动作**：
- 更新 `docs/scorecard/GLOBAL.md` Agent1 列 82% → 86%
- 发 `Signal: AGENT1-PHASE-1-APPROVED` 告知 worker，授权 `WINDOW-CLOSED-CLEAN`
