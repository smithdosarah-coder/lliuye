# Worker A1 (FIX 第 2 批) · Alert export_docx backend + audit decorator refactor · Onboarding

> Worker CLI 在 `D:/claude code/work-A1-inventory` (branch `feat/inventory-expand-A1`) ·
> 复用。上批 W-FIX-A1 (`18ad5d4` Report fix) 已 cherry-pick MERGED · 本批 fix
> Codex peer review 找的 bug #6 + bug #11。

## Goal

修 Codex 找的 2 个 P0/P1 bug:
- **bug #6**: AlertWorkspace.tsx:1504 调 POST /api/alert/export_docx · 但 backend
  agent_alert/api.py 没此 route · catch 仅 console.log · button silent fail
- **bug #11**: audit_service decorator 包 FastAPI route function · SSE generator
  返 StreamingResponse 后 route 退出 · audit log 显 success/fast 实际 stream 内
  LLM call 可能 fail mid-call · 银保监合规留痕失真

## Acceptance

### bug #6 fix

- [ ] **新建** `agent_alert/word_export.py` · `export_hitlist_docx(session_id, summary, cases) -> str` (返 path) · 复用 channel/export_docx pattern
- [ ] `agent_alert/api.py` 加 `POST /api/alert/export_docx`:
  ```py
  class AlertExportDocxRequest(BaseModel):
      session_id: str = ""
      summary: str = ""
      cases: list[dict] = []

  @app.post("/api/alert/export_docx")
  async def alert_export_docx(req: AlertExportDocxRequest):
      from urllib.parse import quote
      from agent_alert.word_export import export_hitlist_docx
      path = export_hitlist_docx(...)
      filename = Path(path).name
      return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                         filename=filename, headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"})
  ```
- [ ] frontend (AlertWorkspace.tsx 1504-1522) catch 改 `setExportError(err.message)` · UI 顶部 banner 显（不静默 console-only）

### bug #11 fix

- [ ] **新建** `audit_service/stream_helpers.py`:
  ```py
  def audit_stream_event(agent_id, endpoint, model, t0, *, user_id=None, error=None, extras=None):
      _record_safe(agent_id=agent_id, endpoint=endpoint, model=model, user_id=user_id,
                   latency_ms=int((time.time()-t0)*1000), error=error, extras=extras)
  ```
- [ ] 6 SSE generator 改 `try/except/finally`:
  - `agent_channel/api.py:119` `channel_run`
  - `agent_alert/api.py:112` `alert_scan`
  - `agent_credit/api.py:477` `credit_decision_v4`
  - `agent_report/api.py:1050` `report_v16_fill`
  - `agent_compliance/api.py` `compliance_policy_scan_get`
  - `agent_riskctrl/api.py` (如有 SSE)
  finally 调 `audit_stream_event(...)` (含 t0 + error + latency)
- [ ] 移除 SSE route 上的 `@audit_llm_call` decorator (保留 JSON sync route 的)
- [ ] pytest `audit_service/tests/test_stream_helpers.py` ≥ 4 case (monkeypatch recorder · 验 stream 完成后 1 audit row · 错误验 error 字段 · latency 算到 generator 完成)

## Acceptance gate

- [ ] tsc 0 error · pytest cumulative `agent_alert/tests/ audit_service/tests/` ≥ 30 PASS · 不破现有
- [ ] curl POST /api/alert/export_docx 返 .docx (sample 进 commit body)
- [ ] commit trailer:
  ```
  Signal: WORKER-A1-FIX2-ALERT-EXPORT-AUDIT-DONE
  RECOVER-FROM: 18ad5d4
  PRESERVES: F-001~F-061
  NEW-ENDPOINT: POST /api/alert/export_docx
  REFACTORED: audit_service/decorators · 6 SSE generator try/finally
  INVENTORY-ADDED: F-062
  ```

## Boundary

- 改: `agent_alert/api.py` + frontend `AlertWorkspace.tsx` + 6 agent_*/api.py SSE generator
- 加: `agent_alert/word_export.py` + `audit_service/stream_helpers.py` + tests
- 不动: web/* 其他 · 其他 backend module · CLAUDE.md · RFC

## Estim

5-7 hr (新 endpoint 简单 · audit refactor 跨 6 file careful · 测试 cumulative)
