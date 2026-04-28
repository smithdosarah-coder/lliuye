# Worker A3 (Stage C 第 1 批) · Agent4 Alert backend KB_DEMO 解锁 · Onboarding

> Worker CLI 在 `D:/claude code/work-A3-prd` (branch `feat/prd-summaries-A3`) ·
> 复用 Stage A+B 同 worktree。
> Stage A (`4d45e30` PRD specs) + Stage B.6b (`fd354d7` IdealProfile) 已
> MERGED 进 chore/l0-infra (`bf5a7f1` + `4be12f2`) · 本批 Stage C 启动。

## Goal

实装 master plan §C.3 — Agent4 Alert backend KB_DEMO 解锁 + 红黄绿榜单 SSE
真接。**gap #8 (Agent4 KB_DEMO mock 锁) 闭环**。

## Acceptance

- [ ] `agent_alert/api.py` `/api/alert/scan` SSE 真返红/黄/绿分级客户榜
- [ ] KB_DEMO 解锁: Tavily 401 fallback (Q-040 提) · 用 mock 数据保 demo
- [ ] `GET /api/alert/hitlist` → 返当前红/黄/绿榜单 (持久化 sqlite or jsonl)
- [ ] `GET /api/alert/drill/{client_id}` → 返单客户 drill detail (信号
      timeline + 处置建议 LLM 生成)
- [ ] curl 测 scan + hitlist + drill · sample 进 commit body
- [ ] pytest `agent_alert/tests/` 全绿 (mock Tavily · mock 在贷客户池)
- [ ] commit trailer:
  ```
  Signal: WORKER-A3-STAGE-C-ALERT-LIVE-DONE
  RECOVER-FROM: fd354d7 (Stage B done · 本批接续)
  NEW-LIVE-ENDPOINT: /api/alert/scan, /api/alert/hitlist, /api/alert/drill
  ```

## Boundary

- **改**: `agent_alert/api.py` (KB_DEMO 解锁) + `agent_alert/scan_engine.py`
  (Tavily fallback)
- **加**: `agent_alert/tests/test_scan_live.py` · `test_hitlist.py` ·
  `test_drill.py`
- **不动**: `web/*` · `shared/kb_scan/` (Stage D.5 才 refactor 共享底座) ·
  其他 Agent · CLAUDE.md · RFC

## Dependencies

- master plan §C.3 (gap #8 Agent4 KB_DEMO)
- `agent-alert-spec.md` (Stage A.5 cherry-pick · `bf5a7f1`)
- `shared/kb_scan/` 现各 Agent 各管 · 暂不 refactor (Stage D.5 后续)
- DeepSeek + Tavily clients (Tavily 401 fallback 必须 · Q-040 提)

## Method

1. Read `agent_alert/api.py` + `agent-alert-spec.md`
2. 设计在贷客户池 mock + 红/黄/绿规则 (规则库)
3. SSE event progression (规则扫 → 命中 → 分级)
4. drill detail 含信号 timeline + 处置建议 LLM 生成
5. Tavily 401 catch · fallback to mock 数据 (保 demo 可演)
6. pytest + curl 验

## Trailer protocol

```
Signal: WORKER-A3-STAGE-C-ALERT-LIVE-DONE
RECOVER-FROM: fd354d7
NEW-LIVE-ENDPOINT: /api/alert/scan, /api/alert/hitlist, /api/alert/drill
```

## On completion

1. `git add agent_alert/` + commit + push origin
2. main CLI auto-patrol → review (pytest + curl + trailer) → cherry-pick

## Estim

4-5 hr (规则库 + Tavily fallback 逻辑 + 测试)
