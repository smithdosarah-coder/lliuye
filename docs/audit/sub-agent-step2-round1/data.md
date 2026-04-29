---
sub-agent: data
cat: [5, 12]
date: 2026-04-29
round: 1
---

| Cat | file:line | 证据 (≤80 char) | Keep / Revert / Rewrite |
|---|---|---|---|
| 5 | web/src/lib/mock/agent-channel-sessions.ts:129 | `Candidate.similarity: number` (0-1 float) | Rewrite |
| 5 | agent_channel/candidate_profile.py:78 | `match_score: int = 0  # 0-100` 后端用 int 0-100 | Rewrite |
| 5 | web/src/app/archive/channel/_components/ChannelWorkspace.tsx:1320 | 前端做双字段兼容 `similarity ?? match_score` 掩盖裂缝 | Revert |
| 5 | web/src/lib/mock/agent-alert-session.ts:62 | `tier: "red"\|"yellow"\|"green"` — 前端 mock 用 tier | Keep |
| 5 | agent_alert/word_export.py:22 | 后端 export 接受 `risk_level/level/tier` 三键兼容 | Rewrite |
| 5 | agent_alert/runtime_dump.py:105 | 后端 runtime 写 `"grade"` 键 — 第三种命名 | Rewrite |
| 5 | web/src/lib/mock/agent-credit-session.ts:214 | mock 写死 `"四维"` note: `财/经/合/担` 四维标签 | Keep |
| 5 | agent_credit/api.py:147 | corporate 维度: 经营财务/行业/经营管理/担保 (4 维实现) | Keep |
| 12 | evaluation/agent2_riskctrl.yaml:3 | yaml `version: v3.1` · api.py line 39 `version="4.0"` | Rewrite |
| 12 | evaluation/agent3_credit.yaml:3 | yaml `version: v3.1` · api.py line 62 `version="4.0"` | Rewrite |
| 12 | evaluation/agent4_alert.yaml:3 | yaml `version: v3.1` · api.py line 50 `version="3.2"` | Rewrite |
| 12 | evaluation/agent5_compliance.yaml:3 | yaml `version: v3.1` · api.py line 50 `version="3.2"` | Rewrite |
| 12 | evaluation/agent3_credit.yaml:18 | desc "四维评分" · api.py impl 3 stage_tab 各 4 维，但 small_biz 降权为 4 维变种 · 无跨段汇总"四维" | Rewrite |
| 12 | evaluation/agent6_report.yaml:82 | `last_run: 2026-04-03` · commit: null — 基线无 commit SHA 无法回溯 | Rewrite |
| 12 | evaluation/agent1_channel.yaml:3 | yaml `version: v4.0` · api.py `version="4.0"` — 一致 | Keep |
| 12 | evaluation/agent6_report.yaml:3 | yaml `version: v16` · CLAUDE.md §11 "Agent6 报告 v16" — 一致 | Keep |
