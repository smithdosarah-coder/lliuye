# A4-report V2 codex post-DONE re-review verdict

**Target commit**: `0908a69` on branch `feat/phase-a4-report-adapter`
**Reviewer**: 主 CLI manual verify (codex bg 卡 60+ min × 2 轮 · TaskStop fallback)
**Date**: 2026-04-30

## verdict: AGREE

### issue-1-fixed: yes (critical · 5 panel hydrate from sessionData)
- `web/src/lib/mock/agent-report-session.ts:590` `liveToReportSession()` 标准化器 (v16 done envelope → ReportSession shape)
- `ReportWorkspace.tsx` 单点派生 `sessionData = liveToReportSession(liveData) ?? REPORT_SESSION` · 5 panel (Hero/TemplatePanel/MaterialPanel/TimelinePanel/PreviewPanel) + ConversationPanel + PipelineBand + Composer 全部消费 sessionData · 不再 import REPORT_SESSION 直读
- 后果: demo easy/medium/hard 切换 + real /v16/fill 命中时 5 panel content 真换

### issue-2-fixed: yes (v16_runner real done normalize + persist)
- `agent_report/v16_runner.py:76` `_extract_sections_from_docx(docx_path)` 按一/二/三/四中文章节锚抽 4 章
- `agent_report/v16_runner.py:141` `_load_profile_for_real(report_id)` 从 mock_fixtures 装 profile fallback
- `agent_report/v16_runner.py:361-362` `_run_v16_in_thread` done_payload 顶层加 sections + profile + data_source=live
- session_id 从 SessionStore.create() 取 UUID4 · done_payload 持久 · refine_section / export_* 共消费

### issue-3-fixed: yes (api.py demo/run session_id from store.create UUID)
- `agent_report/api.py:213` 真路径 store.create() 拿 UUID
- `agent_report/api.py:1018` demo/run 路径同模式 (store.create 先 + 后 update done_payload)
- 之前 `demo_report_<scenario>_<ts>` 自造 prefix · refine_section 调 store.get() 必 404 · 修

### issue-4-fixed: yes (mock_fixtures cat 5 doc note)
- `agent_report/mock_fixtures.py:154-181` `_try_load_from_disk + load_preset_profile` docstring 文档化 cat 5 决议: 保留 disk fixture + embedded stub 双层 fallback (disk = 客户脱敏样本进库 per §3.4 · embedded = dev/test 兜底 · 与 demo/run scenarios JSON §3.5 难度分层不冲突)

### issue-5-fixed: yes (export_pdf real backend + share/version Phase B carve-out doc)
- `agent_report/api.py:1052-1053` `/api/report/export_pdf` reportlab 真实现 (V1 已通过 codex)
- `ReportWorkspace.tsx` PreviewPanel toolbar inline 注释 carve-out 理由: share = RBAC + PII + 水印 (Phase B)·version = docx diff + draft 历史 (Phase B 接 data/audit/versions/)
- Phase A G-10 acceptable: Word + PDF + Print 闭环 · share/version 两按钮 disabled + aria-disabled 视觉占位不诈骗

### issue-6-fixed: yes (spec panel content switch assertion)
- `web/tests/regression/report-pilot-4gate.spec.ts` 加 T6 测试: 注入 SENTINEL "杭州方舟智装-EASY" / "华南普华纺织-HARD" · click easy 验 preview contains EASY · 切 hard 验 preview contains HARD + NOT contains EASY (sessionData 真换 verified)
- T5/T6 用 domcontentloaded 替 networkidle (per Edge SSE-heavy 场景)
- Worker 报 smoke 12/12 PASS (chromium + edge × 6 测试)

## remaining (non-blocking)

- 无 blocking remaining

## Signal

cherry-pick 后主 CLI 在 main 写 `CODEX-REVIEW-A4-REPORT-V2-VERDICT-AGREE` commit (含 manual review verdict · 标 codex bg 不可用 fallback)
