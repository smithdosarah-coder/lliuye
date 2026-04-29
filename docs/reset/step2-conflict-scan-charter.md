# Step 2 · Conflict Scan Charter

> 新 main CLI 启动 Step 2 conflict scan 前必读 · 本文 self-contained · 答 fresh CLI 一切疑问。

---

## 1. Step 2 目标

扫全仓 17 类漂移点 → 输出 `docs/audit/conflict-register-v1.md` → PM 逐条拍板 → 进 Step 1 cleanup (Phase A)。

---

## 2. 17 类 Conflict Checklist (verbatim · SSOT)

本表是 Step 2 + Codex periodic audit + 任何后续 drift 扫的 **唯一 SSOT**。其他 doc 引用本表 (`docs/reset/step2-conflict-scan-charter.md §2`) 而非自己重写。

| Cat | 名 | 重点扫文件 |
|---|---|---|
| **0** | **产品形态 (workbench vs 6 showroom · 走歪本质)** | `web/src/app/today/*` · `web/src/app/archive/[agent]/*` · 跨 agent handoff data flow |
| 1 | 文档规范冲突 | `CLAUDE.md` vs `docs/contracts/*` vs `docs/handoff/decisions-log.md` 互相矛盾 / dangling reference |
| 2 | workspace state 模型不统一 (4 gate `started/selectedSession/liveData/selectedCandidate`) | `web/src/app/archive/{agent}/_components/*Workspace.tsx` 6 个 |
| 3 | frontend SSE 客户端不统一 | `web/src/lib/api/_live.ts streamSse` vs 各 workspace 内 EventSource / fetch reader |
| 4 | backend SSE schema 不统一 (event 名 + done payload) | `agent_*/api.py` 6 个 |
| 5 | mock source 冲突 (3 处) | `data/mock/*` + `web/src/lib/mock/*` + workspace inline `MOCK_*` const |
| 6 | prompt source 冲突 | root `prompts.py` + `agent_*/prompts.py` |
| 7 | LLM caller 冲突 | `llm.py` + `shared/llm/` + `agent_report._build_llm_caller` + `agent_*/llm*.py` |
| 8 | Agent naming 不一致 (8 列) | 代码 ID / 中文 / 业务名 / UI brand / route / 色彩 token / RBAC role / eval baseline |
| 9 | route resurrection | `web/src/app/` 顶层目录 vs `CLAUDE.md §7` canon |
| 10 | auth / RBAC 漂移 | `auth_service/users.py` + `rbac.py` vs `web/src/lib/store/auth-store.ts` |
| 11 | demo / live 边界冲突 | `force_mock: true` hardcode / silent fallback / dropdown auto-fire mock / banner 缺 |
| 12 | evaluation drift | `evaluation/*.yaml` 6 yaml vs `CLAUDE.md §11` vs `agent_*/api.py` 实际能力 |
| 13 | export contract 冲突 | 6 agent docx/xlsx/pdf endpoint + button wire + fallback banner 一致性 |
| 14 | design tokens 残留 (Letterpress) | `--color-brass` / `--color-ink` (作 color value) / `.letterpress-*` / `ink-brush-hr` |
| 15 | production sync 漂 | `main` vs ECS git tree vs `chore/l0-infra` 状态一致 |
| 16 | persona / role drift | `CLAUDE.md §1` 角色 vs `auth_service/users.py` 5 user vs PRD 用户故事 |

---

## 3. Step 2 内部 flow (主 CLI 严格按此跑)

```
[新 main CLI 启动 Step 2]
   ↓
[一次性 fire 6 路并行]
├ sub-agent 架构层    → 扫 Cat 1 / 2 / 3 / 4 / 11
├ sub-agent 数据层    → 扫 Cat 5 / 12
├ sub-agent 指令层    → 扫 Cat 1 / 6 / 7
├ sub-agent 命名路由层 → 扫 Cat 8 / 9 / 10 / 16
├ sub-agent 生产+产品形态 → 扫 Cat 0 / 13 / 14 / 15
└ Codex Round 1 (background)  → 独立扫全 17 类 (anti-bias rule 1 · 不见 sub-agent 输出)
   ↓
[每 sub-agent 输出落 doc]
docs/audit/sub-agent-step2-round1/{architecture,data,instruction,naming-route,production-shape}.md
docs/audit/codex-step2-round1.md
   ↓
[主 CLI 合成 Round 2]
读上述 6 份 → synthesize · 含 dissent appendix
   ↓
docs/audit/conflict-register-v1.md  (主 CLI commit · Signal: STEP-2-CONFLICT-REGISTER-V1-PREPARED)
   ↓
[PM 逐条拍板]
   ↓
docs/audit/conflict-register-v1.md  (PM 标决策 · 主 CLI commit · Signal: STEP-2-PM-RULED)
   ↓
[进 Step 1 Phase A]
按 register 启 Phase A worker (per phase-a-charter.md)
```

---

## 4. 5 Sub-agent prompt 模板 (verbatim · 复用)

每个 sub-agent prompt 必含:
1. cwd `D:\claude code\credit_report_agent_work` · DO NOT cd / DO NOT touch worktrees · read-only
2. 该 sub-agent 负责的 Cat 列表 (per §3 flow)
3. 强制输出 schema (3 列 markdown table):
   ```
   | Cat | file:line | 证据片段 (≤80 char) | Keep / Revert / Rewrite 建议 |
   ```
4. 字数硬上限 ≤ 700 词
5. 仅填表 · 禁散文
6. **生产+产品形态 sub-agent 额外要求**: 末尾加 1 段 `Cat 0 · 产品形态 verdict` (≤200 词 · 当前是 6 showroom 还是 1 workbench · 走歪表征 3-5 处 · Cursor 修正方向)

5 sub-agent 各自的 cat 分配:
- 架构层: 1 / 2 / 3 / 4 / 11
- 数据层: 5 / 12
- 指令层: 1 (子集) / 6 / 7
- 命名路由层: 8 / 9 / 10 / 16
- 生产+产品形态: 0 / 13 / 14 / 15

---

## 5. Codex Round 1 prompt (Step 2 专用 · 不复用 §4.4 periodic)

新增 codex-mesh-protocol.md §4.5 "Step 2 Conflict Scan Round 1" template (与 step2-conflict-scan-charter §4 sub-agent template 同形 · 但要求 codex 独立扫**全 17 类** · 一次输出 1 张大表 · 不分层)。

Codex anti-bias:
- **不见任何 sub-agent 输出** (rule 1)
- 必含 dissent appendix
- ≤ 3500 词
- 只读 main repo · 不读 worktree

---

## 6. Anti-bias rule 1 与"前任 4 sub-agent 已收"

**前任 main CLI 4 sub-agent 输出未 commit (compression 后未 verbatim 还原) · 当作不存在**。

新 main CLI 启动 Step 2 时:
- 弃用前任所有 sub-agent 高层总结 (它们在 chat history · 不可信)
- 重派 5 sub-agent + Codex Round 1 (干净 fresh)
- 新跑出来的 6 份输出 commit 到 `docs/audit/sub-agent-step2-round1/` + `docs/audit/codex-step2-round1.md`
- 这次合成的 conflict-register-v1.md 是真 ground truth

---

## 7. 飞书 PRD 取证 (Step 3 范围 · 与 Step 2 并行启动)

per PM 拍板 5 (Step 3 取证 Step 2 中并行启动):
- 主 CLI 同时启 1 个 PRD 取证 sub-agent · 与 Step 2 5 sub-agent 并行
- PRD 取证 sub-agent 任务:
  - 飞书旧 PRD 抓取: PM 发链接(主路径)/ lark-cli wiki search (备路径) → 截图 + extract intent
  - repo current state inventory (基于 features-inventory.md + CLAUDE.md §7 + contracts)
  - 写 `docs/audit/prd-evidence-frozen.md` (Original Intent / Current Repo State 两段 · 不做 Keep/Revert/Rewrite 决策 · 那是 Phase A worker-A7 的活)
- **不与 Step 2 cat scan 混** · 是 Step 3 worker-A7 启动前的"证据冻结"准备

---

## 8. conflict-register-v1 schema (verbatim)

```markdown
| Cat | file:line | 证据 (≤80 char) | Owner / Phase A worker | Keep / Revert / Rewrite |
|---|---|---|---|---|
| 0 | web/src/app/today/MorningBrief.tsx:120 | 显 dashboard · 非 RM workbench | A3 + A6 | Rewrite |
| 2 | ChannelWorkspace.tsx:115 | currentSession=MOCK · 缺 liveData gate | A3 | Rewrite |
| 7 | agent_report/api.py:264-301 | 第 4 套 caller · 硬编 OpenAI · 跳 shared/llm | A2 | Rewrite |
... (主 CLI 合成时填)
```

注: "Owner / Phase A worker" 列把 conflict 直接挂到 Phase A 7 worker 之一 · 让 Step 1 启动时知道每条交给谁。

---

## 9. 4 路 fire 调度 (一次性并行)

新 CLI 答完本 charter 后**一次 fire 6 个并行**:
- 5 sub-agent (一个 message 多个 Agent tool call)
- Codex Round 1 (Bash run_in_background)
- 同时启 PRD 取证 sub-agent (第 7 个并行)

不串行 · 17 类定义已 hard-frozen 本文 §2 · 不返工。

---

## 10. 退出标准

- `docs/audit/sub-agent-step2-round1/` 5 份 sub-agent 输出 + `docs/audit/codex-step2-round1.md` + `docs/audit/prd-evidence-frozen.md` 全 commit
- `docs/audit/conflict-register-v1.md` 合成 commit (Signal: `STEP-2-CONFLICT-REGISTER-V1-PREPARED`)
- PM 逐条拍板 commit (Signal: `STEP-2-PM-RULED`)
- 同步更新 `docs/reset/state-snapshot.md` (per §14.1 硬规)

→ 进 Step 1 Phase A worker mesh 启动
