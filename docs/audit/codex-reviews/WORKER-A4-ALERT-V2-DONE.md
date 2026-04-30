verdict: AGREE

issue-1-fixed: yes  
`tier` is restored as the frontend/public alert grade field. Backend `agent_alert/api.py` emits `tier`, fixtures use `tier`, and frontend types/consumers use `tier`. Remaining `risk_level` references are compatibility/export paths only.

issue-2-fixed: yes  
`normalizeAlertSession()` now derives `scanQueueCases` and `scanSnapshotAfter.queue` from `done.hit_list.red + done.hit_list.yellow`, and live tests assert the visible hitlist changes from mock to live rows.

issue-3-fixed: yes  
`runAlertScan()` reads top-level `session_id` from canonical `done` events and preserves the legacy payload path.

issue-4-fixed: yes  
The smoke spec no longer env-skips `/api/alert/demo/run`, and spec 4 now asserts live totals, visible hitlist rows, top case row, and `data-scan-session-id`.

remaining:  
- I did not independently rerun TypeScript/Playwright because the detached review worktree had no local `node_modules`; `npx tsc --noEmit` could not resolve a local TypeScript install. Static review of `bedccf9` found no blocking residual issue against the 4 V1 findings.