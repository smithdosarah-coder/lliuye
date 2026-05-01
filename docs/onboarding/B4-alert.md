# worker-B4-alert · Sprint 2 (BE5 + BE9)

## 你是谁

worker-B4-alert · Phase B Sprint 2 · branch `feat/phase-b4-alert` · worktree `D:\claude code\work-B4-alert`

## 你的任务

按 `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` BE5 + BE9 实施 Agent4 信号质量 + batch analytics。

### BE5 信号质量 (1 周)

Agent4 alert 当前 baseline `signal_diversity=0.0` 是 known blocker (per phase-b-charter v2 line 25)。修法:

1. **Freshness scoring** — 每条信号加 `freshness_score` (0-100 · 当天=100 · -10/day decay) · 写 `agent_alert/signal_quality.py`
2. **Source confidence** — 每条信号加 `source_confidence` (high/med/low based on source_type · gov 官网=high · 财经媒体=med · 社媒=low) · table 落 `data/mock/workspace/alert/source_confidence.json`
3. **Fallback banner** — SSE 流加 banner event · provider degrade 时显示 "搜索源 X 不可用 · fallback 到 Y" · per `docs/contracts/sse-envelope.md`
4. **Scan replay** — `/api/alert/scan/replay/{scan_id}` 端点 · 历史 scan 可重放 · per audit 需求

### BE9 跨客户 batch analytics + alert clustering (2 周)

5. **Batch scan** — `/api/alert/batch_scan` 端点 · 一次扫多客户 · 内 yield 流式进度
6. **Alert clustering** — 同类型 alert 跨客户聚合 (e.g. "10 客户都触发 industry-policy-X") · 用 `shared/similarity` jaccard 0.7 阈值聚类
7. **Per Agent4→Agent5 handoff** (per `docs/contracts/agent-handoff-schemas.md` v1.1 §6.4)

## 红线 (硬 · 违 = REJECT V2)

- 不破现有 `agent_alert/` 4 步 pipeline (signal_search → cross_match → severity → recommendation)
- 不引入 ML (alert clustering 用确定性 jaccard · 不用 embedding)
- 不破 §3.7.1 MAX_ROWS=50000 + §3.7.2 Q-041 4 字段
- evaluation runner baseline 跑通 · `signal_diversity ≥ 0.85` (从 0.0 → ≥ 0.85)
- LLM 调用走 `shared/llm_caller/` (不裸 OpenAI client)

## DONE signal

`WORKER-B4-ALERT-SIGNAL-QUALITY-DONE` · trailer 必含:
- `REVIEW-MODE: manual` (codex 用尽 until 2026-05-08 · 主 CLI 自接 review)
- `REASONING-EFFORT: medium`
- `ELAPSED: <min>`

## 工程量

- BE5 1 周 + BE9 2 周 = **3 周**

## 必读文件 (按顺序)

1. `docs/onboarding/B4-alert.md` (本文)
2. `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` 找 BE5 + BE9 章节
3. `docs/reset/phase-b-charter.md` line 63-68 worker-B4-alert 段
4. `docs/contracts/agent-handoff-schemas.md` v1.1 §6.4 Agent4→Agent5
5. `docs/contracts/sse-envelope.md` (fallback banner format)
6. `agent_alert/` 现有代码 (4 步 pipeline · 不破)
7. `shared/llm_caller/` (LLM caller 唯一入口)
8. CLAUDE.md §3.5 反 5 原则 + §3.7 active rules

## 起手第一步

```bash
cd "D:/claude code/work-B4-alert"
git status
git log --oneline -5
# read 上面 8 文件
# commit RESUMED signal:
git commit --allow-empty -m "chore(resume): WORKER-B4-ALERT-RESUMED · 我理解 Sprint 2 BE5 + BE9 task

我是 worker-B4-alert · Sprint 2 · branch feat/phase-b4-alert
任务: BE5 信号质量 (freshness + source_confidence + fallback banner + scan replay) + BE9 batch + clustering
工程量: 3 周
DONE signal: WORKER-B4-ALERT-SIGNAL-QUALITY-DONE
红线: 不破现有 pipeline · 不引入 ML · MAX_ROWS=50000 + Q-041 不破 · LLM 走 shared/llm_caller

Signal: WORKER-B4-ALERT-RESUMED"
```

完了等主 CLI verify · 主 CLI GO 后开干。
