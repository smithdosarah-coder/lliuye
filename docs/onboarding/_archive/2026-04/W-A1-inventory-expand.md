# Worker A1 · features-inventory Expand · Onboarding

> Task spec for worker CLI in worktree `work-A1-inventory` (branch
> `feat/inventory-expand-A1`). Read this + `AGENT_IDENTITY.md` on resume,
> then start work.

## Goal

Expand `docs/features-inventory.md` from F-001~F-008 (Channel only) to
F-001~F-040 covering all 6 archive Workspaces + IM + Auth + Layout
shared features. Each entry must include: id / name / location /
selector / interaction / introduce commit / smoke_test path.

## Acceptance

- F-009~F-040 added (≈32 new entries)
- Categories covered:
  - F-009~F-014: Report Workspace (Agent6) — upload UI, KB hits, fields, draft, materials, export
  - F-015~F-019: Credit Workspace (Agent3) — score radar, red lines, stage tabs, decision letter, evidence
  - F-020~F-023: Alert Workspace (Agent4) — 红/黄/绿 hitlist, scan trigger, signal map, drill detail
  - F-024~F-027: Compli Workspace (Agent5) — policy diff, matrix scan, conflict points, draft revision
  - F-028~F-031: Forge Workspace (Agent2) — DSL editor, KS/AUC chart, sample distribution, run trigger
  - F-032~F-035: dispatch IM — composer slash menu, message bubble (wechat style), thread switch, drag-to-canvas
  - F-036~F-038: Auth — login form, persona switcher, logout button (already F-001 · cross-link)
  - F-039~F-040: Layout shell — Masthead 4 tabs, Desk drawer, theme switch (already F-002/F-003 · cross-link)
- Each entry has placeholder selector + smoke_test path (TODO comments OK if not yet shipped)
- Format follows existing F-001~F-008 template (don't change template)
- Commit on `feat/inventory-expand-A1` branch
- Trailer:
  ```
  Signal: WORKER-A1-INVENTORY-EXPAND-DONE
  INVENTORY-ADDED: F-009, F-010, F-011, ..., F-040
  ```

## Boundary

- Edit ONLY: `docs/features-inventory.md`
- Read-only: any code in `web/src/app/archive/*` and `agent_*/` (to grep selectors / introduce commits)
- DO NOT modify: existing F-001~F-008 entries (preserve them as-is)
- DO NOT touch: code · CSS · CLAUDE.md · other docs

## Dependencies

- Master plan: `docs/contracts/master-execution-plan-2026-04-27.md` § Stage A.3
- Existing inventory header (template) in `docs/features-inventory.md` line 1-30
- Anti-regression contract: `~/.claude/skills/multi-cli-mesh/protocols/anti-regression.md`

## Method

For each new feature:
1. `grep -rn '<selector or class>' web/src/app/archive/<workspace>/` to find DOM
2. `git log --all --oneline -p -- <file>` to find introduce / regress commits
3. Note placeholder smoke_test path (test file may not exist yet — that's fine)
4. Append entry under proper category section in inventory.md
5. Cross-link to F-001/F-002/F-003 etc when overlap (e.g. F-038 logout cross-links F-001)

## Trailer protocol

Required on completion commit (anti-regression skill enforces):
```
Signal: WORKER-A1-INVENTORY-EXPAND-DONE
INVENTORY-ADDED: F-009, F-010, F-011, ..., F-040
```

## On completion

1. `git add -A && git commit -m "..." ` with trailers above
2. `git push origin feat/inventory-expand-A1`
3. Main CLI scoreboard sees `WORKER-A1-INVENTORY-EXPAND-DONE` signal
4. Main CLI reviews diff (count of new entries · category coverage · format compliance)
5. Main CLI cherry-pick / merge to `chore/l0-infra`

## Estimated effort

1.5-2 hr — mostly read code + grep selectors + write inventory entries.
