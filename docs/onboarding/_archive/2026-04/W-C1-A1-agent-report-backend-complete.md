# Worker A1 (Stage C 第 2 批) · Agent6 Report backend complete · Onboarding

> Worker CLI 在 `D:/claude code/work-A1-inventory` (branch
> `feat/inventory-expand-A1`) · 复用 Stage A+B 同 worktree。
> 上批 Stage B.7 (`ae2c648` Channel docx) 已 cherry-pick MERGED (`5e7f53a`) ·
> 本批 Stage C.1 启动。

## Goal

实装 master plan §C.1 — Agent6 Report backend 完整 production-grade:
- v16 pipeline (`v16_*.py` 已就) wire 到 `agent_report/api.py` (现 wrapper 层 unreleased)
- 文件上传 + 字段抽取 + Word 导出 全套 backend endpoints
- **gap #6 (Report Workspace) backend 部分** + **gap #12 (Word 导出) Report 部分** 闭环

## Acceptance

- [ ] `POST /api/report/upload` multipart 上传材料文件 (复用 Channel A2 KB upload pattern)
- [ ] `POST /api/report/fill` SSE 流式 · 内部调用 `v16_pipeline.py` (classifier → generator → QC gate) · stream stage events
- [ ] `POST /api/report/refine` body `{report_id, section, user_edit}` LLM 重写指定段
- [ ] `GET /api/report/downloads/{report_id}` · 返 `.docx` Word 文件
- [ ] `POST /api/report/export_docx` body `{report_id}` · 同上但 POST 触发生成
- [ ] curl 测全 5 endpoint · sample 进 commit body
- [ ] pytest `agent_report/tests/` ≥ 5 case (upload / fill SSE / refine / export · mock LLM)
- [ ] commit trailer:
  ```
  Signal: WORKER-A1-STAGE-C1-REPORT-BACKEND-DONE
  RECOVER-FROM: ae2c648 (Stage B.7 done · 本批接续)
  NEW-ENDPOINT: POST /api/report/{upload,fill,refine,export_docx}, GET /api/report/downloads
  ```

## Boundary

- **改**: `agent_report/api.py` (wire v16 pipeline) + `agent_report/word_export.py` (新 if 需要)
- **加**: `agent_report/tests/test_upload.py` · `test_fill_sse.py` · `test_refine.py` · `test_export_docx.py`
- **不动**: `v16_*.py` (已就 · 直接调用) · `web/*` (frontend Stage C frontend batch) · 其他 Agent · CLAUDE.md · RFC

## Dependencies

- master plan §C.1 (gap #6 Report + #12 Word)
- agent-report-spec.md (Stage A.5 cherry-pick · `bf5a7f1`)
- v16_pipeline.py (`py v16_pipeline.py --source samples/X.docx --material samples` 已可跑)
- python-docx (复用 A1 上批 Channel docx 经验 · 5e7f53a)
- DeepSeek client + QC gate (quality_scorer.py)

## Method

1. Read `v16_pipeline.py` + `agent_report/api.py` (现 wrapper) + `agent-report-spec.md`
2. 设计 endpoint signature (FastAPI multipart + SSE streaming)
3. wire `/api/report/fill` SSE 转 `v16_pipeline` 内部 stage events
4. word_export 复用 5e7f53a Channel docx 模式
5. pytest mock LLM + 真 v16 pipeline 各 case
6. curl + Word open 真验

## Trailer protocol

```
Signal: WORKER-A1-STAGE-C1-REPORT-BACKEND-DONE
RECOVER-FROM: ae2c648
NEW-ENDPOINT: POST /api/report/upload, /api/report/fill (SSE), /api/report/refine, /api/report/export_docx, GET /api/report/downloads/{id}
```

## On completion

1. `git add agent_report/` + commit + `git push origin feat/inventory-expand-A1`
2. main CLI 5min auto-patrol 抓 DONE
3. main CLI review (curl + pytest + Word open + trailer) → cherry-pick → push origin

## Estim

5-7 hr (v16 wire + 5 endpoint + Word + 测试)

## NB

- v16 pipeline 内部已含 evidence-first 三阶段 + QC 9 维 · 复用即可 · 不重做
- Word 导出 schema 跟 Agent6 v9.0/Gradio 老版 align (用户已熟悉) · 但用 v16 数据 source
