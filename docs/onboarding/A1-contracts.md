# Worker-A1 Onboarding · 5 契约 (Phase A Week 1)

> Phase A Week 1 · 与 worker-A2 并行 · 与 Step 2 conflict register PM 拍板并行 (per PM 2026-04-29 override Step 2→Phase A sequential gate)
>
> 主 CLI dispatch commit signal: `PHASE-A-A1-DISPATCHED`

---

## 0. 复用 worktree + branch checkout (第一步必做)

- worktree 物理路径: `D:\claude code\work-A1-inventory` (Stage A 旧用 · 物理存在 · 复用)
- 当前 HEAD branch: `feat/inventory-expand-A1` (Stage A 旧任务)
- **resume 第一步** (在 worktree cmd window 内):
  ```bash
  cd "D:\claude code\work-A1-inventory"
  git fetch origin
  git checkout chore/l0-infra
  git pull origin chore/l0-infra   # 含 STEP-2-CONFLICT-REGISTER-V1-PREPARED + PHASE-A-A1-DISPATCHED 的最新 main CLI commit
  git checkout -b feat/phase-a1-contracts
  ```
- 之后所有 commit 在 `feat/phase-a1-contracts` 上
- DONE 时主 CLI 从 chore/l0-infra cherry-pick 你的 commits · 你**不直接 push origin/chore/l0-infra OR origin/main** (违 §13 ECS production sync 纪律)

---

## 1. 任务 (verbatim from `docs/reset/phase-a-charter.md` §3 worker-A1)

写 5 份契约文件 · commit 到指定路径:

| # | 文件 | 内容要点 (不给实现路径建议 · 你自由发挥) |
|---|---|---|
| 1 | `docs/contracts/workspace-state-protocol.md` | 4 gate state 模型: `started` / `selectedSession` / `liveData` / `selectedCandidate` · 含 agent session shape extension |
| 2 | `docs/contracts/agent-naming-ssot.md` | 8 列单表: `agent_id` / 中文 / 业务名 / UI brand / route / 色彩 token / RBAC role / eval baseline · 6 agent (channel/credit/alert/compliance/riskctrl/report) 全列 |
| 3 | `docs/contracts/sse-envelope.md` | event 名 + done payload 共形 spec · 6 agent 全 align (当前 6 agent backend SSE done event 形态各异 · 见 audit) |
| 4 | `docs/contracts/llm-prompt-contract.md` | 8 段 template spec: safety / evidence-first / agent-role / tool-use / output-schema / self-check / few-shot / evaluation-hook |
| 5 | `docs/arch/instruction-source-of-truth.md` | 优先级: `docs/contracts/*` > root `CLAUDE.md` > scoped child `CLAUDE.md` (e.g. `agent_*/CLAUDE.md`) > `docs/onboarding/*` > `docs/handoff/decisions-log.md` |

**Phase A 验收硬线** (`docs/reset/phase-a-charter.md` §1):
- 硬线 #1 「5 份契约存在」 = 5 文件 commit · 这 task 直接锁
- 硬线 #8 「命名 SSOT 单表落地」 = 上面 #2 + CI lint 加 (任何 `agent_*/api.py` mount 路径必须在词典 route 列里)

---

## 2. 必读 (前置上下文 · 按顺序读)

| 文件 | 用途 |
|---|---|
| `RESET_MASTER_PLAN.md` (项目根) | 一次性 umbrella · 你工作在 reset 工程 Phase A |
| `docs/reset/north-star.md` | 走歪诊断 + 修正方向 (你的 5 契约就是修正手段) |
| `docs/reset/phase-a-charter.md` | §3 worker-A1 段 + §1 验收硬线 (你硬线 #1 + #8) |
| `docs/reset/anti-bias-rules.md` | Round 1 你不见 codex draft · Round 2 主 CLI 合成时给你 |
| `docs/audit/conflict-register-v1.md` | 主 CLI 合成 87 entries · 你 owner: cat 1 (9 entries) / cat 8 (6 entries) / cat 10 (5 entries) / cat 16 (5 entries) + 部分 cat 9 |
| `docs/audit/sub-agent-step2-round1/naming-route.md` | 末尾「Cat 8 · 8 列对齐表 (附录)」6 行 partial · 你完整化 |
| `docs/audit/sub-agent-step2-round1/architecture.md` | Cat 1 部分 (5 entries · CLAUDE.md / north-star / contract dangling reference) |
| `docs/audit/sub-agent-step2-round1/instruction.md` | Cat 1 子集 (4 entries · Q-040/Q-041/PIPL active rule 未回写) |
| `CLAUDE.md` (项目根) | §1 (4 角色) + §4 (6 Agent 边界 · 注意 §1 vs §4 5th 策略经理漂) + §7 (前端 canon · route 拓扑) |
| `docs/contracts/` 现有文件 | spot-check 哪些 stale (e.g. workspace-state-protocol.md 行号 stale 已被 audit 标) |

---

## 3. PM 拍板 5 件 (你必须遵守 · 不再争辩)

1. 杜绝拖死 4 机制 (强制输出 schema / ≤ 3500 词 / 单 issue 最多 2 round 辩论 / dissent 反增即 escalate PM)
2. Phase A/B 严切阶段 (你在 Phase A · 不沾 Phase B)
3. active decision 必回写 root `CLAUDE.md` (你改 contract · 必同 commit 回写 CLAUDE.md 对应章节)
4. 命名 SSOT 8 列 (你建 `docs/contracts/agent-naming-ssot.md` · **PM 待拍板 compliance OR compli 单一 id** · 你建 SSOT 留占位说明 + 给 PM 两个备选 + tradeoff · 不替 PM 决)
5. Step 3 PRD 取证 Step 2 中并行 (跟你无关 · 你专注 5 契约)

---

## 4. 协作纪律 (red lines · 违反任意一条 = REJECT V2)

- ❌ 不跨 worktree 改文件 (主 CLI · A2 · A3-A7 各自 worktree 你不动)
- ❌ commit 不带 `Signal:` trailer (validator 拒 commit)
- ❌ 改 `web/` 不带 `PRESERVES:` + `NEW-DOM:` + `SMOKE-PASS:` trailer (你 task 不动 web/ · 万一动了红线)
- ❌ active decision 改了不回写 CLAUDE.md
- ❌ 凭模糊印象做决策 (compression 后必走恢复协议 · 见 root `CLAUDE.md` §14 + §14.1 state-snapshot 实时更新)
- ❌ 直接 push `origin/chore/l0-infra` 或 `origin/main` (主 CLI 唯一可)

---

## 5. ACK 协议

- 每 contract 完一份 commit 一次 · trailer `Signal: WORKER-A1-CONTRACT-<N>-COMMITTED` (N=1..5)
- 5 份全完 · 最后 commit `Signal: WORKER-A1-CONTRACTS-DONE` · trailer 含:
  ```
  CONTRACTS: docs/contracts/workspace-state-protocol.md, docs/contracts/agent-naming-ssot.md, docs/contracts/sse-envelope.md, docs/contracts/llm-prompt-contract.md, docs/arch/instruction-source-of-truth.md
  SPEC-LINES: <total spec line count · approx>
  UNRESOLVED-QUESTIONS: <list · 留 PM 看 · e.g. "PM 拍板 compliance OR compli 单 id">
  ```
- ACK 走 commit trailer · **不在 chat** 报"已完成" (主 CLI 只看 git log)

---

## 6. Codex 协作 (anti-bias)

- 主 CLI 已 fire codex pre-dispatch draft (插入点 1) **并行你的工作** · 你**不见 codex 草案**
- Codex 输出落 `docs/audit/codex-drafts/A1-contracts.md` · 你 DONE 之前**不读**
- DONE 后主 CLI fire codex post-DONE peer review (插入点 2)
- Codex DISAGREE 时主 CLI 处理 (escalate PM 必走 · 你不直接和 codex 辩论)

---

## 7. DONE signal 详细 trailer

```
Signal: WORKER-A1-CONTRACTS-DONE
CONTRACTS: <5 paths>
SPEC-LINES: <approx total>
HARDLINE-1-MET: yes (5 contracts exist · file path verified)
HARDLINE-8-MET: <yes / partial / no · partial 时说明>
8-COLUMN-FILLED: <X/6 agents fully filled · Y/6 partial · 留占位说明>
DANGLING-REFERENCES-FIXED: <count · audit 标的 9 处 dangling 对应修了几处>
ACTIVE-DECISIONS-BACK-WRITTEN: <count · audit 标的 4 处 active rule 回写了几处>
UNRESOLVED-QUESTIONS: <list>
```

---

## 8. 主 CLI 后续动作 (你不用做 · 仅 awareness)

DONE signal 收到后:
1. 主 CLI fire codex 插入点 2 (post-DONE peer review)
2. Codex 输出 verdict AGREE / DISAGREE / NEED-MORE-INFO
3. 主 CLI 按 verdict 处理 (codex-mesh §6 流程)
4. AGREE → cherry-pick 到 chore/l0-infra · push origin · ECS sync
5. DISAGREE → 主 CLI escalate PM · 你可能要 V2 修

---

**Author**: 主 CLI · 2026-04-29
**Phase A Week 1 · 与 worker-A2 并行**
