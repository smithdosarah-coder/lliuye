# worker-B4-compliance · Sprint 2 (BE4)

## 你是谁

worker-B4-compliance · Phase B Sprint 2 · branch `feat/phase-b4-compliance` · worktree `D:\claude code\work-B4-compliance`

## 你的任务

按 `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` BE4 实施 Agent5 policy registry + version diff + reason schema。

### BE4 4 件交付 (2-2.5 周)

Agent5 compliance 当前 `policy_coverage=0.5` + `conflict_recall=0.5` 都是 known blocker (per phase-b-charter v2 line 23)。修法:

1. **Policy registry** — `shared/policy_registry/` 集中政策 SOT · 含 policy_id + title + 颁布日期 + 原文 URL + version + 适用业务线
   - 落 SQLite at `data/policy_registry/policies.sqlite`
   - 加载器 `agent_compliance/policy_loader.py` · 启动时全量加载

2. **Version diff** — 政策升版时算 diff (新增条款 / 删除条款 / 修改条款)
   - `agent_compliance/policy_diff.py` · 用 difflib + 段落级 diff
   - SSE 流 emit `policy_diff` event · 通知前端 highlight 改动

3. **Violation reason schema** — 每条 violation 必带 `reason_schema`:
   ```json
   {
     "violation_id": "...",
     "policy_id": "...",
     "policy_section": "...",  // 第几条第几款
     "trigger_field": "...",   // 业务文档哪个字段触发
     "original_text": "...",   // policy 原文 verbatim
     "violation_text": "...",  // 业务文档实际文本
     "confidence": 0.0-1.0,
     "review_reason": "..."    // 人工复核记录 (可空)
   }
   ```
   `agent_compliance/violation_schema.py`

4. **Conflict recall ≥ 0.85** — 现 conflict_recall=0.5 必修到 ≥ 0.85
   - 加测试 fixture 含已知 conflict (per 反 5 原则 §3.5 · fixture 不预埋 violation_id · 让 Agent 自己识别)
   - evaluation runner 跑通 baseline

## 红线 (硬 · 违 = REJECT V2)

- 不破现有 `agent_compliance/` scan_engine 4 步 pipeline
- 不写黑名单兜底幻觉 (per CLAUDE.md §3.1 反模式)
- policy diff 必基于 difflib 确定性 · 不让 LLM 现场比 diff
- 不破 §3.7.1 MAX_ROWS=50000 + §3.7.2 Q-041 4 字段
- LLM 调用走 `shared/llm_caller/`
- evaluation runner baseline `policy_coverage ≥ 0.85` + `conflict_recall ≥ 0.85`

## ⚠️ 关键警告 · handoff schema v1.1 placeholder (双 AI 辩论 R2 · Q-048 · 2026-05-04)

`docs/contracts/agent-handoff-schemas.md:17` 自述: **"v1.1 仅 placeholder · v1.2 实装"**

你触及 **Agent5 → Agent3 / Agent6 / Agent4 反向链** (§6.1) · 该段 fixture 在 v1.1 是 placeholder · v1.2 待实装。

处理:
1. 触到反向链时**自写 fixture** in `data/mock/handoff/agent5-to-3-*.json` (or to-6 / to-4) · 不等 Sprint 3 v1.2 实装
2. 在 commit body 列你写的 fixture file:line · trailer 加 `HANDOFF-FIXTURE: data/mock/handoff/<file>.json`
3. 不动 contract 文档本身 (那是 worker-A6 / Sprint 3 工作 · 你只产 fixture)

## DONE signal

`WORKER-B4-COMPLIANCE-POLICY-REGISTRY-DONE` · trailer 必含:
- `REVIEW-MODE: codex` (codex resumed 2026-05-04 · 主 CLI fire post-DONE review bg per Q-043 protocol v2)
- `REASONING-EFFORT: medium`
- `ELAPSED: <min>`
- `HANDOFF-FIXTURE: <file>.json` (若触及反向链 · 自写 fixture)

## 工程量

**2-2.5 周**

## 必读文件

1. `docs/onboarding/B4-compliance.md` (本文)
2. `docs/research/BACKEND-DEEP-WORK-V2-1-FINAL-2026-05-01.md` 找 BE4 章节
3. `docs/reset/phase-b-charter.md` line 70-75 worker-B4-compliance 段
4. `docs/contracts/agent-handoff-schemas.md` v1.1 (含 Agent5→Agent3 §6.1)
5. `agent_compliance/scan_engine.py` 现有代码
6. `shared/llm_caller/`
7. CLAUDE.md §3.1 + §3.5 + §3.7

## 起手第一步

```bash
cd "D:/claude code/work-B4-compliance"
# read 上面 7 文件
git commit --allow-empty -m "chore(resume): WORKER-B4-COMPLIANCE-RESUMED · 我理解 Sprint 2 BE4 task

任务: BE4 policy registry + version diff + reason schema · 修 policy_coverage + conflict_recall 从 0.5 → ≥ 0.85
工程量: 2-2.5 周
DONE signal: WORKER-B4-COMPLIANCE-POLICY-REGISTRY-DONE
红线: 不破 scan_engine pipeline · 不写黑名单 · diff 用 difflib 确定性 · LLM 走 shared/llm_caller

Signal: WORKER-B4-COMPLIANCE-RESUMED"
```
