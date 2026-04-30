verdict: AGREE

issue-1-fixed: yes  
`normalizeRedLines` and `normalizeCases` now only fallback on `null`/`undefined`; explicit `[]` derives to empty UI arrays. This fixes stale mock red lines/cases for clean live done envelopes.

issue-2-fixed: yes  
`/api/credit/reports/sessions` now scans `data/handoff/report_to_credit/*.json` first, emits `source: "archive"`, uses `path.stem` as `session_id`, and `handoff_from_report` resolves that same id back to the archive file. Demo remains fallback.

issue-3-fixed: yes  
`web/next.config.ts` adds `CREDIT_BACKEND` and rewrites `/api/credit/:path*` to backend port 8000 by default.

issue-4-fixed: yes  
T5/T6 no longer silently pass when rows/buttons are absent. They hard-route the relevant APIs, require the case row/export button to be visible, and assert drawer/banner behavior.

remaining:  
- none blocking for the four V1 DISAGREE issues.
- note: current workspace `HEAD` is `72aa606`, not `1d876fd`; I reviewed the target commit via `git show 1d876fd`.