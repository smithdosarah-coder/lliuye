# Worker A1 (Stage B 第 2 批) · Channel Word 导出 backend · Onboarding

> Worker CLI 在 `D:/claude code/work-A1-inventory` (branch `feat/inventory-expand-A1`) ·
> 复用 Stage A+B 第 1 批同 worktree · branch · CLI 实例。
> Stage B 第 1 批 (`259b47f` B.5 SSE fields) 已 cherry-pick MERGED 进
> chore/l0-infra (`2e27705`) · 本批 Stage B.7 接续。

## Goal

实装 master plan §B.7 — 后端 `POST /api/channel/export_docx` Word 导出。
**gap #12 (Channel Word 导出) 闭环**。

## Acceptance

- [ ] POST `/api/channel/export_docx` body `{session_id}` 或
      `{ideal_profile, candidates}` (兼容 mock + live)
- [ ] 返 `.docx` file (StreamingResponse + `content-disposition: attachment`)
- [ ] 内容含: 客户经理姓名 + 日期 / IdealProfile 12 维卡 / Top10 候选 (name +
      score + industry/geo/scale/similarity) / 每候选 detail (radar 8 维表 +
      信号 timeline + 匹配明细 chip + Top3 产品卡 + 切入话术段)
- [ ] python-docx 库 (复用 `agent_report/word_export.py` 模式)
- [ ] curl 测一次 · 返 .docx · Word 打开 verify (sample 进 commit body)
- [ ] pytest `agent_channel/tests/test_export_docx.py` ≥ 2 case (mock session +
      live session 两路)
- [ ] commit trailer:
  ```
  Signal: WORKER-A1-STAGE-B7-EXPORT-DOCX-DONE
  RECOVER-FROM: 259b47f (B.5 · 同 branch 接续)
  NEW-ENDPOINT: POST /api/channel/export_docx
  ```

## Boundary

- **改**: `agent_channel/export_docx.py` (新建) + `agent_channel/api.py` (mount endpoint)
- **加**: `agent_channel/tests/test_export_docx.py`
- **不动**: `web/*` · 其他 Agent backend · CLAUDE.md · RFC

## Dependencies

- master plan §B.7 (gap #12 Channel Word 导出)
- channel-spec.md endpoint shape
- python-docx (复用 agent_report/ 已用过)
- 现 sse_extras.py + ideal_profile.py 数据结构 (B.5 + B.6b 字段)

## Method

1. Read `agent_report/word_export.py` (或 word docx 类) 学模板模式
2. 设计 docx 结构 (heading / paragraph / table / list)
3. 写 endpoint + handler (StreamingResponse · BytesIO)
4. pytest mock session 验 (生成 .docx · open + assert content)
5. curl + Word open 真验

## Trailer protocol

```
Signal: WORKER-A1-STAGE-B7-EXPORT-DOCX-DONE
RECOVER-FROM: 259b47f
NEW-ENDPOINT: POST /api/channel/export_docx
```

## On completion

1. `git add agent_channel/` + commit + `git push origin feat/inventory-expand-A1`
2. main CLI 5min auto-patrol 抓 DONE
3. main CLI review (pytest + curl + Word open + trailer) → cherry-pick → push origin

## Estim

3-4 hr (docx 模板 + 测试主要工作)
