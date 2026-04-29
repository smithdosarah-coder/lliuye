# Worker-A2 Onboarding · shared infra (Phase A Week 1)

> Phase A Week 1 · 与 worker-A1 并行 · 与 Step 2 conflict register PM 拍板并行 (per PM 2026-04-29 override Step 2→Phase A sequential gate)
>
> 主 CLI dispatch commit signal: `PHASE-A-A2-DISPATCHED`

---

## 0. 复用 worktree + branch checkout (第一步必做)

- worktree 物理路径: `D:\claude code\work-A2-contracts` (Stage A 旧用 · 物理存在 · 复用)
- 当前 HEAD branch: `feat/contracts-bootstrap-A2` (Stage A 旧任务)
- **resume 第一步** (在 worktree cmd window 内):
  ```bash
  cd "D:\claude code\work-A2-contracts"
  git fetch origin
  git checkout chore/l0-infra
  git pull origin chore/l0-infra
  git checkout -b feat/phase-a2-shared
  ```
- 之后所有 commit 在 `feat/phase-a2-shared`
- DONE 时主 CLI cherry-pick 回 chore/l0-infra · 你**不直接 push origin**

---

## 1. 任务 (verbatim from `docs/reset/phase-a-charter.md` §3 worker-A2)

| # | 文件 | 内容要点 |
|---|---|---|
| 1 | `shared/llm_caller/{client,prompts,audit,retry,provider}.py` (5 个 module) | 收编 root `llm.py:LLMClient` + 现有 `shared/llm/router.py` (Stage E.3 已建 · 0 production import) · 含 deepseek/qwen/moonshot provider abstraction · PIPL 境内优先 fallback chain |
| 2 | `shared/sse_envelope.py` | helper for backend SSE event 共形 (event 名 + done payload schema · 6 agent api.py 后续 imp 此 helper) |
| 3 | `shared/prompts/contract.py` | 8 段 template (per A1 worker 的 `docs/contracts/llm-prompt-contract.md` 输出 · A1 完后你 align · 但 A1 spec done 之前你可先建 module 骨架) |
| 4 | `tests/shared/test_llm_caller.py` + `tests/shared/test_sse_envelope.py` | pytest 全 PASS |

**Phase A 验收硬线** (`docs/reset/phase-a-charter.md` §1):
- 硬线 #2 「shared infra 抽出」 = `shared/llm_caller/` core 写完 · `shared/sse_envelope.py` 写完 · `shared/prompts/contract.py` 8 段 template 写完 · pytest PASS

---

## 2. 必读 (前置上下文 · 按顺序读)

| 文件 | 用途 |
|---|---|
| `RESET_MASTER_PLAN.md` (项目根) | umbrella |
| `docs/reset/north-star.md` | §2.2 架构层 (3 套 LLM caller 现状) · §3.2 修正方向 |
| `docs/reset/phase-a-charter.md` | §3 worker-A2 段 + §1 硬线 #2 |
| `docs/reset/anti-bias-rules.md` | Round 1 不见 codex |
| `docs/audit/conflict-register-v1.md` | 主 CLI 合成 87 entries · 你 owner: cat 6 (7 entries) / cat 7 (8 entries) + 部分 cat 4 (sse envelope 共形 · 6 entries) + 部分 cat 5 (mock source · 8 entries) |
| `docs/audit/sub-agent-step2-round1/instruction.md` | **关键**: Cat 7 verbatim 4+1 套 caller 全 list (root `llm.py:56` + `shared/llm/router.py:27` + `agent_riskctrl/llm_judge.py:123` + `agent_report/api.py:264` + `agent_alert/api.py:312` + `agent_compliance/scan_engine.py:84` + `agent_riskctrl/api.py:141`) |
| `docs/audit/sub-agent-step2-round1/architecture.md` | Cat 4 (backend SSE schema · 6 agent done payload 形态) |
| `docs/audit/sub-agent-step2-round1/data.md` | Cat 5 (mock source · similarity vs match_score 三方分裂 · grade 三命名) |
| `llm.py` (root · ~190 行) | Caller 1 现状 · 你迁源 |
| `shared/llm/__init__.py` + `shared/llm/router.py` | Caller 2 现状 · 你接管 + 扩展 |
| `agent_report/api.py:264-301` | Caller 4 反例 (硬编 OpenAI · 跳全栈) · 你 spec 让它无路可跳 |
| `agent_riskctrl/llm_judge.py` | Caller 3 反例 (LLMJudge 独立基类) |
| 任意 1 个 `agent_*/api.py` SSE done event handler (e.g. `agent_channel/realtime_stream.py:229`) | 看 done payload 现状 |

---

## 3. PM 拍板 5 件 (你必须遵守 · 不再争辩)

1. 杜绝拖死 4 机制 (强制 schema / ≤ 3500 词 / 单 issue ≤ 2 round 辩论 / dissent 反增即 escalate PM)
2. Phase A/B 严切阶段 (你在 Phase A · 不沾 Phase B)
3. active decision 必回写 root `CLAUDE.md` (你改 shared/* · 必同 commit 回写 CLAUDE.md §3.x 对应章节)
4. 命名 SSOT 8 列 (worker-A1 的活 · 你不重建 · 但 你 module spec 中 agent 命名遵守 SSOT)
5. Step 3 PRD 取证 Step 2 中并行 (跟你无关)

---

## 4. 协作纪律 (red lines)

- ❌ 不跨 worktree 改文件 (主 CLI · A1 · A3-A7 各自 worktree 你不动)
- ❌ commit 不带 `Signal:` trailer
- ❌ 改 `web/` 不带 `PRESERVES:` 等 trailer (你不动 web/)
- ❌ 改 `shared/*` 是 red zone · **本 task 整个目的就是建 shared/llm_caller/ + shared/sse_envelope.py** (PM 拍板授权 · charter §3 worker-A2 verbatim) · **不算 RFC 流程触发** · 但其他 shared/* 改动需要 RFC
- ❌ 跨 worktree 修改 `agent_*/api.py` (你只建 helper · agent migration 是 worker-A4 的 5 子 worker 干 · 你不动)
- ❌ active decision 改了不回写 CLAUDE.md
- ❌ 直接 push `origin/chore/l0-infra` OR `origin/main`

---

## 5. ACK 协议

- 每 module 完一个 commit 一次 · trailer `Signal: WORKER-A2-MODULE-<N>-COMMITTED`
- 全完 commit `Signal: WORKER-A2-SHARED-INFRA-DONE` · trailer:
  ```
  MODULES: shared/llm_caller/{client,prompts,audit,retry,provider}.py, shared/sse_envelope.py, shared/prompts/contract.py
  TESTS: tests/shared/test_llm_caller.py, tests/shared/test_sse_envelope.py
  PYTEST-PASS: <X passed, 0 failed>
  HARDLINE-2-MET: yes
  CALLER-1-COVERED: <yes / partial · 说明 root llm.py 哪些功能你接管 · 哪些保留兼容>
  CALLER-2-CONTINUITY: <yes · shared/llm/ 现有 1 production import 你不破坏>
  CALLER-3-4-5-DEPRECATION-PATH: <你 spec 怎么让 agent_riskctrl/llm_judge + agent_report/_build_llm_caller + agent_alert/compliance/riskctrl 直 LLMClient 这 5 处 deprecate · A4 worker 后续迁>
  UNRESOLVED-QUESTIONS: <list>
  ```
- 不在 chat 报"已完成"

---

## 6. Codex 协作 (anti-bias)

- 主 CLI 已 fire codex pre-dispatch draft 并行 · 你**不见 codex 草案** (落 `docs/audit/codex-drafts/A2-shared-infra.md`)
- DONE 后主 CLI fire codex post-DONE peer review · 你不直接辩论

---

## 7. 与 worker-A1 协作 (并行 · 同 Week 1)

- A1 写 `docs/contracts/llm-prompt-contract.md` · 你的 `shared/prompts/contract.py` impl 该 spec
- 时序: A1 + A2 并行 · 但 contract.py impl 等 A1 spec 落地。建议你先建 module 骨架 (空函数 + docstring) · A1 spec done 后 fill。
- 沟通走 `docs/handoff/decisions-log.md` Q-NNN · **不直接改 A1 worktree 的文件**

---

## 8. DONE signal 后主 CLI 后续

DONE → fire codex review → AGREE 则 cherry-pick → push → ECS sync (per CLAUDE.md §13.1 backend 改 `--skip-build`)

---

**Author**: 主 CLI · 2026-04-29
**Phase A Week 1 · 与 worker-A1 并行**
