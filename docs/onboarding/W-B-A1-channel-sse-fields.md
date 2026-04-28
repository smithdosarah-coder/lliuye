# Worker A1 (Stage B 第 1 批) · Channel SSE Candidate Full Fields · Onboarding

> Worker CLI 在 `D:/claude code/work-A1-inventory` (branch
> `feat/inventory-expand-A1`)。Resume 读 `AGENT_IDENTITY.md` + 本文件 + 必读 spec。
>
> **复用 Stage A 同 worktree + branch + CLI 实例**（Stage A 任务 `1b143f8` 已
> cherry-pick MERGED 进 chore/l0-infra `4bedee2`）· 本批 commit 累在
> `feat/inventory-expand-A1` 之上。

## Goal

实装 master plan §B.5 + Q-041 follow-up — 后端 `/api/channel/run` SSE done event
扩 candidate full fields:
- 原 spec: `radar / signals / funnel / match_dimensions /
  product_recommendations / pitch_scripts`
- Q-041 fix-forward: 加 `industry / geo / scale / similarity` 4 字段
  (现 production 看到 fallback "未获取" + 0%)

## Acceptance

- [ ] `/api/channel/run` SSE done event 每 candidate 含全字段:
      `name, score, signals, industry, geo, scale, similarity,
       radar_8axis, match_dimensions, product_recommendations, pitch_scripts`
- [ ] industry/geo/scale 来自 Tavily search response · LLM extract · 优先填 ·
      fallback "未获取"
- [ ] similarity 0~1 浮点 · 基于 LLM/keyword 评分 (P0 简单 keyword overlap ·
      P3 deterministic 算法 留 TODO)
- [ ] match_dimensions array · 每条 `{dim_name, hit_evidence, score}` (PRD v2
      "为什么像")
- [ ] product_recommendations Top3 · 每条 `{product_name, fit_score, intro}`
- [ ] pitch_scripts · 每条 `{customer_name_placeholder, script_text}`
- [ ] curl 一次返真 candidate full fields · sample 进 commit body
- [ ] pytest agent_channel/tests/ 全绿
- [ ] commit trailer:
  ```
  Signal: WORKER-A1-STAGE-B-SSE-FIELDS-DONE
  RECOVER-FROM: 1b143f8 (Stage A done · 本批接续)
  Q-041-FIXED: industry/geo/scale/similarity now populated
  NEW-FIELD: match_dimensions, product_recommendations, pitch_scripts
  ```

## Boundary

- **改**: `agent_channel/` (api_server.py 内 /api/channel/run handler · 或 split
  到 agent_channel/sse_extended.py · 你定 file structure)
- **不动**: `web/src/*` (前端 SSE consumer 是 B.5b 步 · 后续派)
- **不动**: 其他 5 archive Workspace backend · docs/contracts/ · CLAUDE.md · RFC

## Dependencies

- Master plan: `docs/contracts/master-execution-plan-2026-04-27.md` § B.5 (含 4 漏 step)
- Q-041 cross-ref: `docs/handoff/decisions-log.md` § Q-041 candidate metadata gap
- channel-spec.md: `docs/contracts/agent-channel-spec.md` (cherry-pick `bf5a7f1`)

## Method

1. Read `api_server.py` 找 `/api/channel/run` handler
2. Diff 现 done event vs 期望全字段
3. 设计 candidate Pydantic model (新建 dataclass)
4. LLM prompt 调整 · 抽 industry/geo/scale (从 Tavily snippet)
5. similarity 算法 P0 keyword overlap · P3 留 TODO
6. match_dimensions / product_recommendations / pitch_scripts 复用 v1
   `channel_rules` + scoring (引 channel-spec.md 给的 mock 例子)
7. pytest + curl 验

## Trailer protocol

```
Signal: WORKER-A1-STAGE-B-SSE-FIELDS-DONE
RECOVER-FROM: 1b143f8
Q-041-FIXED: industry/geo/scale/similarity now populated
NEW-FIELD: match_dimensions, product_recommendations, pitch_scripts
```

## On completion

1. `git add agent_channel/` + commit + `git push origin feat/inventory-expand-A1`
2. main CLI auto-patrol (5min cron) 抓 DONE signal
3. main CLI review (curl test · pytest · trailer) → cherry-pick → push origin/main

## Estimated effort

3-5 hr (LLM prompt 调优 + similarity P0 + match_dimensions/products/pitch + 测试)
