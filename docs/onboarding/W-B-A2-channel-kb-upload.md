# Worker A2 (Stage B 第 1 批) · Channel KB Upload Endpoint · Onboarding

> Worker CLI 在 `D:/claude code/work-A2-contracts` (branch
> `feat/contracts-bootstrap-A2`)。Resume 读 `AGENT_IDENTITY.md` + 本文件 + 必读 spec。
>
> **复用 Stage A 同 worktree + branch + CLI 实例**（Stage A 任务 `4e8310b` 已
> cherry-pick MERGED 进 chore/l0-infra `a660019`）· 本批 commit 累在
> `feat/contracts-bootstrap-A2` 之上。

## Goal

实装 master plan §B.6 backend 部分 — 新 endpoint
`POST /api/channel/upload_kb` 接 3 类 KB 文件 · 解析 · 存 KB id 返。

## Acceptance

- [ ] POST `/api/channel/upload_kb` · multipart upload · field `kb_type`
      (`customer_list` | `policy` | `industry_guide`) + `file` (xlsx/pdf/docx)
- [ ] 解析: xlsx → pandas DataFrame → row dict; pdf → text extract;
      docx → text extract (复用 `material_kb.py` 解析 utils)
- [ ] KB 持久化: `data/channel_kb/{kb_id}.{json,parquet}` · `kb_id` = uuid4
- [ ] return `{kb_id, kb_type, n_rows / n_pages, summary_text}` JSON
- [ ] curl 测 3 类 file 各上传一次 · sample 进 commit body
- [ ] pytest `agent_channel/tests/test_kb_upload.py` 至少 3 case (xlsx/pdf/docx)
- [ ] 错误处理: 不支持 file format → 400 · file 太大 (>50MB) → 413
- [ ] commit trailer:
  ```
  Signal: WORKER-A2-STAGE-B-KB-UPLOAD-DONE
  RECOVER-FROM: 4e8310b (Stage A done · 本批接续)
  NEW-ENDPOINT: POST /api/channel/upload_kb
  ```

## Boundary

- **改**: `agent_channel/kb_upload.py` (新建) + `api_server.py` (mount endpoint)
- **加**: `data/channel_kb/.gitkeep` + `agent_channel/tests/test_kb_upload.py`
- **不动**: `web/src/*` (前端 upload UI 是后续派) · 其他 Agent backend ·
  CLAUDE.md · RFC

## Dependencies

- Master plan §B.6: file 上传 KB · 3 类 (客户名录 / 政策 / 行业指引)
- channel-spec.md: `docs/contracts/agent-channel-spec.md` § endpoints (B.6 shape)
- material_kb.py: 解析 utils 可复用 (xlsx/pdf/docx)

## Method

1. Read `material_kb.py` 学解析模式
2. 设计 endpoint signature (FastAPI multipart · UploadFile)
3. 写解析 dispatch (xlsx/pdf/docx 各 handler)
4. KB 持久化 (json + parquet 备选 · uuid4 文件名)
5. 单元测试 3 case
6. curl 验 + log

## Trailer protocol

```
Signal: WORKER-A2-STAGE-B-KB-UPLOAD-DONE
RECOVER-FROM: 4e8310b
NEW-ENDPOINT: POST /api/channel/upload_kb
```

## On completion

1. `git add agent_channel/ data/channel_kb/.gitkeep` + commit + push origin
2. main CLI auto-patrol 抓 DONE
3. main CLI review (curl test · pytest · trailer) → cherry-pick → push origin/main

## Estimated effort

2-3 hr (file parsing utils 已有 · endpoint 简单 · 测试主要工作)
