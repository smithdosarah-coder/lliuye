# Worker A3 (Stage C 第 2 批) · Agent5 Compliance backend complete · Onboarding

> Worker CLI 在 `D:/claude code/work-A3-prd` (branch `feat/prd-summaries-A3`) ·
> 复用 Stage A+B+C 同 worktree。
> 上批 Stage C.3 Alert KB_DEMO unlock (`5f310ae`) 已 cherry-pick MERGED
> (`32f3b7e`) · 本批 Stage C.4 启动。

## Goal

实装 master plan §C.4 — Agent5 Compliance backend 完整 production-grade:
- 政策事件驱动扫 (政策发布触发)
- 业务矩阵比对 (N×M doc × clause)
- 冲突点明细生成 + LLM 修订意见
- 修订意见 Word 导出
- **gap #6 (Compli Workspace) backend** + **gap #8 (Agent5 KB_DEMO)** + **gap #12 (Compli Word)** 闭环

## Acceptance

- [ ] `POST /api/compliance/policy_scan` SSE 流式 · body `{policy_doc, business_docs: [...]}` ·
      返冲突点明细 list · 每条 `{policy_clause, business_clause, conflict_type, severity}`
- [ ] `POST /api/compliance/matrix_check` body `{policies: [...], business_lines: [...]}` ·
      返 N×M 冲突矩阵
- [ ] `POST /api/compliance/export_docx` body `{scan_id}` · 返修订意见书 .docx (含
      改 / 补 / 强 三类 RevisionPanel 格式)
- [ ] LLM 真接 (DeepSeek) 解析政策语言 + 业务规则比对 · 不是硬编关键词
- [ ] KB_DEMO 解锁 (复用 A3 上批 Alert pattern) · Tavily 401 fallback 用 mock policy 库保 demo
- [ ] curl 测 3 endpoint · sample 进 commit body
- [ ] pytest `agent_compliance/tests/` ≥ 6 case (政策扫 · 矩阵 · 冲突点分类 · 修订生成 · KB_DEMO unlock · Tavily fallback)
- [ ] commit trailer:
  ```
  Signal: WORKER-A3-STAGE-C4-COMPLI-BACKEND-DONE
  RECOVER-FROM: 5f310ae (Stage C.3 Alert done · 本批接续)
  NEW-ENDPOINT: POST /api/compliance/{policy_scan,matrix_check,export_docx}
  ```

## Boundary

- **改**: `agent_compliance/api.py` (LLM 真接 + 矩阵 + KB_DEMO unlock) +
  `agent_compliance/scan_engine.py` (新建 if 需要 · 复用 Alert pattern) +
  `agent_compliance/word_export.py` (新)
- **加**: `agent_compliance/tests/test_policy_scan.py` · `test_matrix_check.py` ·
  `test_export_docx.py` · `test_kb_demo_unlock.py`
- **不动**: `shared/kb_scan/` (Stage D.5 才 refactor) · `web/*` · 其他 Agent · CLAUDE.md · RFC

## Dependencies

- master plan §C.4 (gap #6 + #8 + #12)
- agent-compli-spec.md (Stage A.5 cherry-pick · `bf5a7f1`)
- shared/kb_scan/ (现各 Agent 各管 · 复用 Alert pattern)
- DeepSeek + Tavily clients (Tavily 401 fallback 必须 · Q-040 提)
- python-docx (Channel A1 docx · 5e7f53a · Alert A3 backend · 32f3b7e)

## Method

1. Read `agent_compliance/api.py` + `agent-compli-spec.md` + `agent_alert/scan_engine.py` (Alert pattern 参考)
2. 设计政策扫 LLM prompt (政策条款解析 → business 规则比对)
3. 矩阵 N×M (按业务线 × 政策类别 · 复用 shared/kb_scan/ 现有底座)
4. 修订意见生成: 改 / 补 / 强 三类 LLM 真生成
5. word_export 复用 Channel/Alert docx 模式 · 修订意见书 schema
6. KB_DEMO unlock: Tavily 401 catch · fallback mock 政策库
7. pytest 6 case + curl 验

## Trailer protocol

```
Signal: WORKER-A3-STAGE-C4-COMPLI-BACKEND-DONE
RECOVER-FROM: 5f310ae
NEW-ENDPOINT: POST /api/compliance/policy_scan (SSE), /api/compliance/matrix_check, /api/compliance/export_docx
```

## On completion

1. `git add agent_compliance/` + commit + push origin
2. main CLI auto-patrol → review → cherry-pick → push

## Estim

5-7 hr (政策 prompt 调优 · 矩阵 · KB_DEMO unlock · Tavily fallback · 测试)

## NB

- 政策事件驱动是 Agent5 vs Agent4 的边界 (CLAUDE.md §4) · 不是定期巡检
- 修订意见三类 (改 / 补 / 强) 是 PRD v2 用户故事核心 · 不能合并
- 业务矩阵 N×M · M (业务条款) 来自上传业务制度库 · N (政策条款) 来自新政策
