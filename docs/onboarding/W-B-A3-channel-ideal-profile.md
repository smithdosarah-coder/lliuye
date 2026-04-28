# Worker A3 (Stage B 第 1 批) · Channel IdealProfile LLM Extract · Onboarding

> Worker CLI 在 `D:/claude code/work-A3-prd` (branch
> `feat/prd-summaries-A3`)。Resume 读 `AGENT_IDENTITY.md` + 本文件 + 必读 spec。
>
> **复用 Stage A 同 worktree + branch + CLI 实例**（Stage A 任务 `4d45e30` 已
> cherry-pick MERGED 进 chore/l0-infra `bf5a7f1`）· 本批 commit 累在
> `feat/prd-summaries-A3` 之上。

## Goal

实装 master plan §B.6b — 新 endpoint
`POST /api/channel/profile`：消费 KB id · LLM 解析 · 抽 IdealProfile 12 维特征。

## Acceptance

- [ ] POST `/api/channel/profile` · body `{kb_id, kb_type}`
- [ ] 读 KB blob (`data/channel_kb/{kb_id}.*` · A2 worker 会先写出 KB) · 解析
      row/text 给 LLM
- [ ] LLM (DeepSeek) 抽 IdealProfile 12 维:
      `industry_focus, scale_preference, geo_coverage, stage,
       capital_relation, business_size, employee_size, customer_type,
       product_keywords, value_chain_position, growth_signals, risk_signals`
- [ ] return `{ideal_profile: {dim_1: value, ...}, confidence_score, reasoning_text}` JSON
- [ ] curl 测一次完整 KB → IdealProfile (sample 进 commit body)
- [ ] pytest 至少 1 case (mock LLM + KB · 验 12 维 shape)
- [ ] 错误处理: kb_id 不存在 → 404 · LLM timeout → 504
- [ ] commit trailer:
  ```
  Signal: WORKER-A3-STAGE-B-IDEAL-PROFILE-DONE
  RECOVER-FROM: 4d45e30 (Stage A done · 本批接续)
  NEW-ENDPOINT: POST /api/channel/profile
  DEPENDS-ON: A2 (kb_id from /api/channel/upload_kb)
  ```

## Boundary

- **改**: `agent_channel/ideal_profile.py` (新建) + `api_server.py` (mount endpoint)
- **加**: `agent_channel/tests/test_ideal_profile.py`
- **不动**: `web/src/*` (前端 profile card UI 是后续派) · 其他 Agent backend ·
  CLAUDE.md · RFC

## Dependencies

- Master plan §B.6b: IdealProfile 抽画像 · 12 维特征
- channel-spec.md: B.6b endpoint shape
- DeepSeek client: `api_server.py` 已配置
- A2 (`/api/channel/upload_kb`) 写出 `data/channel_kb/{kb_id}.json` 是本 task 输入

## Method

1. Read `agent_channel/` 现 LLM call 模式 (复用)
2. 设计 IdealProfile dataclass (12 维 · Pydantic)
3. 写 LLM prompt (system: "提取理想客户画像" · user: KB blob)
4. 解析 LLM JSON output → IdealProfile (含 fallback 防 LLM 不返 valid JSON)
5. 单元测试 mock LLM
6. curl 验 (依赖 A2 先 push 完 · 或 mock kb_id 测试)

## Trailer protocol

```
Signal: WORKER-A3-STAGE-B-IDEAL-PROFILE-DONE
RECOVER-FROM: 4d45e30
NEW-ENDPOINT: POST /api/channel/profile
DEPENDS-ON: A2 kb_id pipeline
```

## On completion

1. `git add agent_channel/` + commit + push origin
2. main CLI auto-patrol 抓 DONE
3. main CLI review (curl test · pytest · trailer · 跨 A2 endpoint integration check)
   → cherry-pick → push origin/main

## Estimated effort

2-3 hr (LLM prompt 调优主要工作 + 12 维 dataclass)
