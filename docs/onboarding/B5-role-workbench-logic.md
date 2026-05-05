# worker-B5-role-workbench-logic · Sprint 3 (4+1 角色定位工作台 contract first + implementation)

## 你是谁

worker-B5-role-workbench-logic · Phase B Sprint 3 · branch `feat/phase-b5-role-workbench-logic` · worktree `D:\claude code\work-B5-role-workbench-logic`

## 你的任务

按 `docs/reset/phase-b-charter.md` v2.2 段 (Q-052 reframe charter v2 #3 改名 "4+1 角色定位工作台") 实装 4+1 角色 home view + ACCESS matrix + 后端 row-level/action gate + 前端工作台逻辑层 (F5/F7/F8/F9/F10/F15) + V2-issue-3 policy_diff endpoint。

### contract-first sub-PR (Day 1-3 · ~5/14-5/16)

**冻结 schema (不改用户可见行为)**:

1. **row-level Depends schema** (`auth_service/dependencies.py` 加 schema · 不改 enforcement):
   - action enum: `invoke` / `read` / `export` / `handoff` / `approve`
   - per-agent per-action ACCESS matrix 扩展 (从现 binary `agent_id` access 升级)
   - read-only flag for cross-agent visibility (RM 看 Agent3/Agent4 read-only)

2. **RM 权限契约目标定义** (`auth_service/rbac.py` 加 spec · 不改 ACCESS):
   - 目标: RM 主调 Agent1 (channel) + Agent6 (report)
   - 目标: RM 看 Agent3 (credit) + Agent4 (alert) `read_only`
   - 目标: RM **不可调** Agent2 (riskctrl) + Agent5 (compliance)

3. **V2-issue-3 policy_diff endpoint contract** (`agent_compliance/api.py` 加 spec · 不改实装):
   - `POST /api/compliance/policy_diff` route signature
   - SSE envelope (`shared.sse_envelope.encode_event` `{event:"policy_diff", payload:{diffs, summary}}`)
   - test signature `tests/agent_compliance/test_policy_diff_endpoint.py`

4. **Frontend types/mirror skeleton** (`web/src/lib/store/auth-store.ts` + `web/src/components/shell/AuthGate.tsx`):
   - 加 row-level types (skeleton · 不破现 working state)
   - test skeleton

### implementation sub-PR (Day 4-5 · ~5/17-5/18)

**atomic 跨前后端**:

1. `auth_service/rbac.py:9-14`: ACCESS RM 收窄 (Agent1+Agent6 主调 · Agent3+Agent4 read-only · 移除 Agent2+Agent5 access)
2. `web/src/lib/store/auth-store.ts:35-40`: 前端 mirror 同步
3. `web/src/components/shell/AuthGate.tsx`: 加 row-level/action gate enforcement
4. `web/src/app/today/_components/TodayContent.tsx`: 5 角色 home view differentiation (F5 客户上下文常驻 + F7 Today 单链路 + F8 handoff 任务卡 + F9 segment-aware + F10 Action Card + F15 Live evidence)
5. `agent_compliance/api.py`: 加 `POST /api/compliance/policy_diff` route + SSE envelope
6. `tests/agent_compliance/test_policy_diff_endpoint.py`: endpoint test

## 红线 (硬 · 违 = REJECT V2)

- 不破现有 4+1 ACCESS matrix 4 角色名 (rm/credit_officer/compliance_officer/risk_manager/admin)
- 不破现有 5 fixed user (王哲/李华/周敏/陈凯/刘野 per `auth_service/users.py:46-50`)
- contract sub-PR + implementation sub-PR 必都跨前后端 atomic · **禁止先改一端** (PM 5/4 verbatim)
- 不动视觉打磨 (F1-F4 / F11-F14 / F16-F17 · Q-047 视觉冻结仅冻审美装饰层)
- LLM 调用走 `shared/llm_caller/` · **禁止新增 `from llm import LLMClient` OR `LLMClient(...)` 直连** (per Q-052 P2.6 grep guard · BASELINE=30 hits / 14 file at dispatch HEAD `269aba1` · DIFF guard `git diff origin/main...HEAD --stat | grep "from llm import LLMClient\|LLMClient("` 必 0 新增 · 不 touch 已知残留 14 file 留 Sprint 4 整合改)
- 不破 §3.7.1 MAX_ROWS=50000 + §3.7.2 Q-041 4 字段
- evaluation runner baseline 不退化 (vs `evaluation/baselines/2026-05-04-sprint2-end.md`)
- 反向链 fixture 业务深度自写 (per §3.5 #5 mock 边界 · 主 CLI 已修 stale + schema-valid 最小 placeholder · 你扩展业务深度)

## ⚠️ Sprint 3 关键警告 (per Q-052 + Codex R1+R2 audit dispose)

1. **B5 contract first 阻 B4-channel/B4-riskctrl frontend integration**: B4-channel/riskctrl Day 1-3 backend-only · approve/export action 集成等 B5 schema freeze (~5/16) 才能改前端
2. **V2-issue-3 endpoint DoD 必含 API route + sse_envelope + endpoint test** (Codex R2 catch · 不只 lib · per docstring "planned in BE4 #5" 上次 V2 漏)
3. **legacy LLMClient grep guard** (per Q-052 P2.6 Sprint 4 waiver · 修正版): BASELINE=30 hits / 14 file at dispatch (含 `api_server.py` + `agent_channel/realtime_stream.py` + `ideal_profile.py` + `v16_classifier.py` + `shared/base_agent.py` + `enterprise_info.py` + `rule_extractor.py` + `legacy_gradio/agent.py` + `monitoring_service/health.py` + `shared/kb_scan/search_provider.py` + `shared/llm_caller/{client,provider}.py` 等) · 你**不 touch 已知残留** + **不增加新残留** · DIFF guard `git diff origin/main...HEAD` 必 0 新增 · 任何新增 = REJECT
4. **handoff fixture 业务深度** (per Q-052 P2.5 主 CLI 修 stale 后): B5 触 §6.1 反向链 (Agent5→Agent3 violation_blocked) 时扩展业务深度 → 写真 `data/mock/handoff/agent5-to-3-block.json` 业务字段
5. **PM "禁止先改一端"**: contract sub-PR + implementation sub-PR 都跨前后端 atomic · 单 commit chain 跨多 file · 不允许 backend-only OR frontend-only sub-PR

## DONE signal

`WORKER-B5-ROLE-WORKBENCH-LOGIC-DONE` · trailer 必含:
- `REVIEW-MODE: codex` (Q-043 v2 sequential bg medium reasoning)
- `REASONING-EFFORT: medium`
- `ELAPSED: <min>`
- `FIX-FORWARD: contract sub-PR + implementation sub-PR 都 atomic 跨前后端`
- `HANDOFF-FIXTURE: <if 触链路自写 fixture>` (per Q-052 P2.5)
- `GREP-GUARD-LEGACY-LLM: BASELINE=30; NEW=0` (per Q-052 P2.6 修正版 · BASELINE 是 dispatch HEAD `269aba1` 时点 · NEW 是 worker DONE 时 `git diff origin/main...HEAD` 新增命中数 · 必 0)

## 工程量

3 周 (Week 6 Day 1-3 contract first + Day 4-5 implementation + Week 7-8 polish)

## 必读文件

1. `docs/onboarding/B5-role-workbench-logic.md` (本文)
2. `docs/reset/phase-b-charter.md` v2.2 段 (Sprint 3 排期 + 4 worker 边界)
3. `docs/handoff/decisions-log.md` Q-052 (8 active rule + RM 权限契约目标)
4. `docs/contracts/agent-handoff-schemas.md` v1.1 (反向链 + Agent2 链 fixture status post-P2.5/P3.9)
5. `auth_service/rbac.py:9-39` ACCESS matrix 现状
6. `auth_service/users.py:46-50` 5 fixed user
7. `web/src/components/shell/AuthGate.tsx:56-64` 前端 guard 现状
8. `web/src/app/today/_components/TodayContent.tsx:21-90` `/today` 通用 dashboard 现状 (待 differentiation)
9. CLAUDE.md §1 4 角色 + §3.7 active rules + §15 SSOT 优先级
10. `evaluation/baselines/2026-05-04-sprint2-end.md` baseline (Sprint 3 改前对比锚)

## 起手第一步

```bash
cd "D:/claude code/work-B5-role-workbench-logic"
git status
git fetch origin && git rebase origin/main  # per Q-050 防 base 漂
git log --oneline -5

# read 上面 10 文件
git commit --allow-empty -m "chore(resume): WORKER-B5-ROLE-WORKBENCH-LOGIC-RESUMED · 我理解 Sprint 3 4+1 角色定位工作台 task

我是 worker-B5-role-workbench-logic · Sprint 3 · branch feat/phase-b5-role-workbench-logic
任务: contract-first sub-PR (row-level/action Depends schema + RM 权限契约 + V2-issue-3 endpoint contract) + implementation sub-PR (atomic 跨前后端 · 5 role home view + endpoint consumer)
工程量: 3 周 (Week 6 contract+implementation + Week 7-8 polish)
DONE signal: WORKER-B5-ROLE-WORKBENCH-LOGIC-DONE
红线: contract+implementation 都 atomic 跨前后端 · 不动视觉打磨 · LLM 走 shared/llm_caller · 不增 legacy LLMClient · evaluation 不退化

Signal: WORKER-B5-ROLE-WORKBENCH-LOGIC-RESUMED"
```

完了等主 CLI verify · 主 CLI GO 后开干 contract-first sub-PR。
