# Worker-A6 Onboarding · 6 Agent handoff data contract (Phase A Week 2-3)

> Phase A Week 2-3 · 与 A5 + A7 并行 · 不依赖 A1/A2/A3
>
> 主 CLI dispatch commit signal: `PHASE-A-A6-DISPATCHED`

---

## 0. 复用 worktree (已建好)

- worktree: `D:\claude code\work-A6-handoff` (主 CLI 已 `git worktree add` 创建)
- 已 checkout branch: `feat/phase-a6-handoff` (派生 chore/l0-infra HEAD 84334cb)
- **resume 第一步**: cd 到 worktree · `git status` 确认 clean · 直接开干

---

## 1. 任务 (verbatim from `docs/reset/phase-a-charter.md` §3 worker-A6)

| # | 交付 | 内容要点 |
|---|---|---|
| 1 | `docs/contracts/agent-handoff-schemas.md` | 4 链 schema 定义清楚 |
| 2 | 链路 1: `Agent1.candidate_company → Agent6.upload_intent` | 字段 schema · 含 similarity vs match_score 字段名+类型对齐 (audit Cat 5) |
| 3 | 链路 2: `Agent6.report_json → Agent3.decision_input` | ReportJSON schema · A3 输入消费契约 (audit Cat 0 核心 handoff) |
| 4 | 链路 3: `Agent3.decision → Agent4.client_pool_signal` | 决策意见怎么变贷中预警客户池信号 |
| 5 | 链路 4: `Agent5.policy_event → Agent4/Agent6` | 政策事件 schema · 触发 Agent4 重扫 + Agent6 报告补充 |
| 6 | `data/mock/handoff/*.json` | 每条链路 1 个真实形态 fixture |
| 7 | export contract 共形 (Cat 13) | 6 agent docx/xlsx/pdf endpoint + button wire + fallback banner 一致性 spec |

**Phase A 验收硬线 #6** (`docs/reset/phase-a-charter.md` §1): "6 Agent handoff data contract · `docs/contracts/agent-handoff-schemas.md` 定义清楚 (不要求自动跑通 · 仅 schema 定)"

---

## 2. 不在你范围 (PM 拍板 · 别越界)

- ❌ **`/today` 重写为 RM workbench** — PM 拍板推 Phase B-3 (端到端 demo chain) · 你不动 `web/src/app/today/*`
- ❌ Workspace 4 gate 实装 — A3 (Channel pilot) + A4 (5 子 agent) 干
- ❌ shared LLM caller 接管 — A2 干

你只定 schema + sample fixture · 不真接代码。

---

## 3. 必读

- `RESET_MASTER_PLAN.md`
- `docs/reset/north-star.md` §1.4 (6 Agent 闭环路径) + §3.1 修正方向
- `docs/reset/phase-a-charter.md` §3 worker-A6 + §1 硬线 #6
- `docs/audit/conflict-register-v1.md` (你 owner: cat 0 大部分 6 entries · cat 13 5 entries · cat 5 部分 8 entries)
- `docs/audit/sub-agent-step2-round1/production-shape.md` (Cat 0 verdict + Cat 13 export 漂)
- `docs/audit/sub-agent-step2-round1/data.md` (Cat 5 三方 mock 分裂 · similarity vs match_score · grade 三命名)
- `docs/audit/prd-evidence-frozen.md` (各 agent Original Intent + Current Repo State · 帮你定 schema 真实形态)
- 任意 agent_*/api.py mock 端点 · 看现有数据形态 (e.g. `agent_credit/api.py:147` corporate 四维)
- `web/src/lib/mock/agent-*-session*.ts` (前端 mock 真形 · 你 schema 跟它对齐)

---

## 4. PM 拍板 4 件 (你必须遵守)

1. 杜绝拖死 4 机制
2. Phase A/B 严切阶段 (你严守 · 不沾 /today RM workbench)
3. active decision 必回写 root CLAUDE.md
4. 命名 SSOT 8 列 (你 schema 中 agent 命名遵 worker-A1 SSOT · 选 `compliance` 单 id · per PM 拍板)
5. legacy_gradio 全栈隔离 (worker-A7 干 · 跟你无关)

---

## 5. 协作纪律

- ❌ 不跨 worktree 改文件 (主 CLI · A1-A5 + A7 各自不动)
- ❌ commit 不带 `Signal:` trailer
- ❌ 不动 `web/` (你只 spec · 不真接代码 · 但你 mock fixture 可建 `data/mock/handoff/*.json`)
- ❌ 不动 `agent_*/api.py` (real impl 是 A4 5 子 worker 干)
- ❌ active decision 不回写
- ❌ 直接 push origin

---

## 6. ACK 协议

- 每链路 spec 完一个 commit · trailer `Signal: WORKER-A6-CHAIN-<N>-SPECCED` (N=1..4)
- export contract spec 完 commit `Signal: WORKER-A6-EXPORT-CONTRACT-SPECCED`
- 全完 + 4 fixture 落 commit `Signal: WORKER-A6-HANDOFF-CONTRACT-DONE` · trailer:
  ```
  CHAINS-SPECCED: 4 (agent1→6 / agent6→3 / agent3→4 / agent5→4+6)
  EXPORT-CONTRACT-SPECCED: yes (6 agent docx/xlsx/pdf 共形)
  FIXTURES: data/mock/handoff/{agent1-to-6, agent6-to-3, agent3-to-4, agent5-to-4-6}.json (4 文件)
  HARDLINE-6-MET: yes
  TODAY-RM-WORKBENCH: NOT-IN-SCOPE (推 Phase B-3 per PM 拍板)
  ```

---

## 7. Codex 协作

主 CLI 已 fire codex pre-dispatch draft · 你不见。落 `docs/audit/codex-drafts/A6-handoff.md`。

---

**Author**: 主 CLI · 2026-04-29
**Phase A Week 2-3 · 与 A5 + A7 并行**
