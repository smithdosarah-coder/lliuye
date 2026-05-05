# worker-B4-channel · Sprint 3 (BE1 + BE12 · Agent1 候选证据 + personal_insight)

## 你是谁

worker-B4-channel · Phase B Sprint 3 · branch `feat/phase-b4-channel` · worktree `D:\claude code\work-B4-channel`

## 你的任务

按 `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` BE1 + BE12 实施 Agent1 候选证据评分 + 内源 + conversion + personal_insight 子域。

### BE1 候选证据评分 (1.5-2 周)

1. **候选 4 字段 metadata 已实装 (Sprint 1 V2 done · per Q-041)**: industry / geo / scale / similarity 不破
2. **候选证据评分** — 每候选挂证据链 (出处 file / URL / 段落 ID) · 评分 0-100 · 写 `agent_channel/candidate_evidence_scorer.py`
3. **数据源状态** — `SearchProvider` (Tavily / 企查查 / akshare) 健康检查 · UI banner 显 "搜索源 X 可用" / "X 不可用 fallback Y"
4. **内源已成交客户库** — `data/channel_kb/` 整理 · candidate_company KB 维度对齐 (4+1 字段 + 已成交 flag)
5. **Conversion tracking** — RM 决策候选后追踪是否真成单 · 写 `data/feedback/<RM>/<candidate_id>.jsonl`

### BE12 个人画像 (Agent1 子域 · 2.5 周)

> ⚠️ **口径修正 (per Codex Sprint 3 onboarding pre-dispatch review NEEDS-FIX)**: BE12 是 **Agent1 `personal_insight` 子域** (服务客户/候选个人画像 POC) · 不是 RM 业绩画像。RM 业绩指标只能作为**经营策略维度输入** · 不是主 schema。原始锚点见 `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md:54-59` (BE12 复用 `shared/personal_profile.py` + 服务个人画像 POC + 4 维度评价: 个人画像 / 产品适配 / 合规 / 话术 / PII / latency)。

6. **personal_insight 子域** — Agent1 候选客户的个人画像 (per `shared/personal_profile.py` 已建) · POC 服务 BE13 4 维度评价
7. **payload schema** (后端 · 客户/个人画像 POC) — `{candidate_id, person_features: {age_band, occupation, income_band, ...}, product_fit: [...], compliance_check: {pep, sanction, ...}, talking_points: [...], pii_redacted: bool, latency_ms}` · 经营策略维度可附 (如 `rm_segment_match: {industries, avg_conversion}`)
8. **API endpoint** — `GET /api/channel/personal_insight/{candidate_id}` SSE stream · 用 `shared.sse_envelope`
9. **不改前端 home view layout** (B5 owns · B7 BE13 跑 4 维度评价 · 不是 RM widget)

## 红线 (硬 · 违 = REJECT V2)

- 不破现有 `agent_channel/` 4 步 pipeline (signal_search → cross_check → score → recommend)
- 不破 §3.7.2 Q-041 4 字段 metadata (industry / geo / scale / similarity)
- 不破 §3.7.1 MAX_ROWS=50000
- LLM 调用走 `shared/llm_caller/` · **禁止新增 `from llm import LLMClient` OR `LLMClient(...)` 直连** (per Q-052 P2.6 grep guard 修正版 · BASELINE=30 hits / 14 file at dispatch HEAD `269aba1` · DIFF guard `git diff origin/main...HEAD` 必 0 新增 · 不 touch 已知残留 14 file)
- 不动 shell / today / auth / dispatch (B5 owns)
- 不动 `web/src/app/today/_components/TodayContent.tsx` layout (B5 owns)
- 候选证据评分确定性 · 不让 LLM 现场算 (per CLAUDE.md §3.1)
- evaluation runner baseline 不退化 (vs `evaluation/baselines/2026-05-04-sprint2-end.md`)

## ⚠️ Sprint 3 关键警告 (per Q-052 + Codex R2 audit dispose)

1. **B5 contract first 阻 frontend 改动**: 你 Day 1-3 backend-only · 不碰 `/today`/auth/dispatch · 等 B5 schema freeze (~5/16) 后可消费 row-level Depends
2. **personal_insight payload schema 后端 only · 不改 layout**: B5 RM home view 消费本 payload · 你 owns payload schema + endpoint · B5 owns layout
3. **handoff §6.1+§6.2 反向链业务深度** (per Q-052 P2.5 主 CLI 已修 stale): 你触 Agent3→Agent6 反向 (BE2 decision graph 评分时缺材料 → Agent6 补料) 时扩展业务深度 · 写真 `data/mock/handoff/agent3-to-6-gap.json` 业务字段
4. **legacy LLMClient grep guard 修正版** (per Codex Sprint 3 onboarding pre-dispatch review NEEDS-FIX): BASELINE=30 hits / 14 file at dispatch HEAD `269aba1` (含 `agent_channel/realtime_stream.py` + `ideal_profile.py` channel 相关 + `enterprise_info.py` + 其他 11 file) · 你**不 touch 已知残留 14 file** + **不增加新残留** · DIFF guard `git diff origin/main...HEAD` 必 0 新增

## DONE signal

`WORKER-B4-CHANNEL-CANDIDATE-EVIDENCE-DONE` · trailer 必含:
- `REVIEW-MODE: codex` (Q-043 v2)
- `REASONING-EFFORT: medium`
- `ELAPSED: <min>`
- `HANDOFF-FIXTURE: <fixture file:line>` (per Q-052 P2.5 触链路自写)
- `GREP-GUARD-LEGACY-LLM: BASELINE=30; NEW=0` (per Q-052 P2.6 修正版 · 详 onboarding §⚠️ #4)

## 工程量

BE1 1.5-2 周 + BE12 2.5 周 = **4-4.5 周**

## 必读文件

1. `docs/onboarding/B4-channel.md` (本文)
2. `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` 找 BE1 + BE12 章节
3. `docs/reset/phase-b-charter.md` v2.2 段 (Sprint 3 排期 + 4 worker 边界)
4. `docs/handoff/decisions-log.md` Q-052 + Q-041 (4 字段 metadata 红线)
5. `docs/contracts/agent-handoff-schemas.md` v1.1 (反向链 fixture status post-P2.5)
6. `agent_channel/` 现有代码 (4 步 pipeline · 不破)
7. `shared/personal_profile.py` (BE12 复用)
8. `shared/llm_caller/`
9. `evaluation/baselines/2026-05-04-sprint2-end.md`
10. CLAUDE.md §3.1 + §3.5 + §3.7

## 起手第一步

```bash
cd "D:/claude code/work-B4-channel"
git fetch origin && git rebase origin/main  # per Q-050
# read 上面 10 文件
git commit --allow-empty -m "chore(resume): WORKER-B4-CHANNEL-RESUMED · 我理解 Sprint 3 BE1+BE12 task

任务: BE1 候选证据评分 (4 字段 + 数据源 + 内源 KB + conversion) + BE12 personal_insight 子域 (payload + endpoint)
工程量: 4-4.5 周
DONE signal: WORKER-B4-CHANNEL-CANDIDATE-EVIDENCE-DONE
红线: 不破 4 步 pipeline + Q-041 4 字段 + MAX_ROWS · 不动 shell/today (B5 owns) · LLM 走 shared/llm_caller · 不增 legacy LLMClient · 候选评分确定性

Signal: WORKER-B4-CHANNEL-RESUMED"
```

完了等主 CLI verify · 主 CLI GO 后开干 BE1。
