# worker-B4-riskctrl · Sprint 3 (BE6 + BE8 · Agent2 DSL + 回测 + 业务指标双轨)

## 你是谁

worker-B4-riskctrl · Phase B Sprint 3 · branch `feat/phase-b4-riskctrl` · worktree `D:\claude code\work-B4-riskctrl`

## 你的任务

按 `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` BE6 + BE8 实施 Agent2 DSL 上线性 + 业务指标双轨 + 回测可信度。

### BE6 DSL 上线性 + 业务指标双轨 (2-2.5 周)

1. **DSL 字段字典** — 每个 DSL rule field 明确 datatype + 单位 + 允许值范围 · 写 `agent_riskctrl/dsl_field_dict.py`
2. **单位归一** — 元 / 万元 / 亿 / 百分比 / bps 自动归一 (e.g. "1.5亿" → 150000000)
3. **互斥/遮蔽** — 同 field 多 rule 命中 priority + override semantics
4. **业务指标双轨** — KS / AUC (统计口径 给数据科学家) + **通过率 / 坏账率 / 利润影响** (业务口径 给业务方) · 双 metrics output
5. **MAX_ROWS=50000 不破** (per Q-040 active rule + §3.7.1)

### BE8 回测可信度 (2 周)

6. **Champion / Challenger 对比** — 回测时双 model 对比 · 报告差异 + 推荐 winner
7. **PSI** (Population Stability Index) — 月度跑 · `data/riskctrl/psi/<month>.jsonl`
8. **分月趋势** — 回测结果按月分组 · 看时间稳定性
9. **误杀解释** — false positive 个案 · LLM 给可解释 reason (per CLAUDE.md §3.1 治本路径 · LLM 不算 KS)

## 红线 (硬 · 违 = REJECT V2)

- 不破现有 `agent_riskctrl/` DSL 生成 + 回测 + KS 计算 4 步 pipeline
- 不破 §3.7.1 **MAX_ROWS=50000** (Q-040 active rule · 真实风控样本量 5-50 万 · 不允许回退到 ≤ 500)
- 不破 §3.7.2 Q-041 4 字段
- LLM 调用走 `shared/llm_caller/` · **禁止新增 `from llm import LLMClient` OR `LLMClient(...)` 直连** (per Q-052 P2.6 grep guard 修正版 · BASELINE=30 hits / 14 file at dispatch HEAD `269aba1` · DIFF guard `git diff origin/main...HEAD` 必 0 新增 · 不 touch 已知残留 14 file)
- 不动 shell / today / auth / dispatch (B5 owns)
- 业务指标计算确定性 (Python · 不让 LLM 现场算) · 误杀解释除外 (per CLAUDE.md §3.1)
- 跨 agent handoff 走 §6.4 (Agent4→Agent2 已实装) + §6.5 + §6.6 (Agent2→Agent4/Agent3 反向)
- evaluation runner baseline 不退化 (vs `evaluation/baselines/2026-05-04-sprint2-end.md`)

## ⚠️ Sprint 3 关键警告 (per Q-052 + Codex R2 audit dispose)

1. **B5 contract first 阻 approve/export action 集成**: 你 Day 1-3 backend-only · DSL/backtest 不碰 `/today`/auth/dispatch · 等 B5 schema freeze (~5/16) 后可加 approve/export action gate
2. **handoff §6.5+§6.6 Agent2 触发链业务深度** (per Q-052 P2.5 主 CLI 已修 stale): 你触 Agent2→Agent4 (dsl_deployed) + Agent2→Agent3 (dsl_versioned) 时扩展业务深度 · 写真 `data/mock/handoff/agent2-to-4-dsl-deploy.json` + `agent2-to-3-rubric.json` 业务字段
3. **MAX_ROWS=50000 红线**: 改 `agent_riskctrl/backtesting.py:22, 67, 84` 三处常量 · 任何回退到 ≤ 500 触发 demo blocker (per Q-040 verbatim)
4. **legacy LLMClient grep guard 修正版** (per Codex Sprint 3 onboarding pre-dispatch review NEEDS-FIX): BASELINE=30 hits / 14 file at dispatch HEAD `269aba1` · 你**不 touch 已知残留 14 file** + **不增加新残留** · DIFF guard `git diff origin/main...HEAD` 必 0 新增
5. **业务指标双轨 KS / 坏账率 同 commit ship**: 不允许只 ship KS · 必双轨 (业务方 demo 必备 · per CLAUDE.md §1 风险经理给行长汇报场景)

## DONE signal

`WORKER-B4-RISKCTRL-BACKTEST-DSL-DONE` · trailer 必含:
- `REVIEW-MODE: codex`
- `REASONING-EFFORT: medium`
- `ELAPSED: <min>`
- `HANDOFF-FIXTURE: <fixture file:line>` (per Q-052 P2.5)
- `GREP-GUARD-LEGACY-LLM: BASELINE=30; NEW=0` (per Q-052 P2.6 修正版)
- `MAX-ROWS: 50000` (per Q-040 verbatim)

## 工程量

BE6 2-2.5 周 + BE8 2 周 = **4-4.5 周**

## 必读文件

1. `docs/onboarding/B4-riskctrl.md` (本文)
2. `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` 找 BE6 + BE8 章节
3. `docs/reset/phase-b-charter.md` v2.2 段
4. `docs/handoff/decisions-log.md` Q-052 + Q-040 (MAX_ROWS=50000)
5. `docs/contracts/agent-handoff-schemas.md` §6.5+§6.6 Agent2 链 (post-P2.5 stale 已修)
6. `agent_riskctrl/` 现有代码 (DSL + backtest 4 步 pipeline · 不破)
7. `shared/llm_caller/`
8. `evaluation/baselines/2026-05-04-sprint2-end.md`
9. CLAUDE.md §3.1 + §3.5 + §3.7.1 (MAX_ROWS) + §3.7.5 (decision ledger)

## 起手第一步

```bash
cd "D:/claude code/work-B4-riskctrl"
git fetch origin && git rebase origin/main  # per Q-050
# read 上面 9 文件
git commit --allow-empty -m "chore(resume): WORKER-B4-RISKCTRL-RESUMED · 我理解 Sprint 3 BE6+BE8 task

任务: BE6 DSL 上线性 + 业务指标双轨 (KS+通过率+坏账率+利润影响) + BE8 回测可信度 (champion/challenger + PSI + 分月 + 误杀解释)
工程量: 4-4.5 周
DONE signal: WORKER-B4-RISKCTRL-BACKTEST-DSL-DONE
红线: 不破 4 步 pipeline · MAX_ROWS=50000 不破 (Q-040) · LLM 走 shared/llm_caller · 不增 legacy LLMClient · 业务指标确定性算

Signal: WORKER-B4-RISKCTRL-RESUMED"
```

完了等主 CLI verify · 主 CLI GO 后开干 BE6。
