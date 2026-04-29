# Worker-A7 Onboarding · PRD 取证 + draft + legacy_gradio 全栈隔离 (Phase A Week 2-3)

> Phase A Week 2-3 · 与 A5 + A6 并行 · 不依赖 A1/A2/A3
>
> 主 CLI dispatch commit signal: `PHASE-A-A7-DISPATCHED`

---

## 0. 复用 worktree (work-A3-prd · 旧 branch · resume 时切新)

- worktree 物理路径: `D:\claude code\work-A3-prd` (Stage A 旧用 · 复用)
- 当前 HEAD branch: `feat/prd-summaries-A3` (Stage A.5 旧任务)
- **resume 第一步**:
  ```bash
  cd "D:\claude code\work-A3-prd"
  git checkout chore/l0-infra
  git checkout -b feat/phase-a7-prd
  ```
- 不需要 git fetch / pull origin (本地最新)

---

## 1. 任务 (verbatim from `docs/reset/phase-a-charter.md` §3 worker-A7 + PM 4 拍板加项)

### 1.1 PRD 取证 + master + 6 sub-PRD draft (charter §3 worker-A7)

| # | 交付 | 备注 |
|---|---|---|
| 1 | PRD 取证 inventory | **已完成 70%**: `docs/audit/prd-evidence-frozen.md` (主 CLI Step 2 阶段并行启 · 飞书 7 doc found + 10 G-XX gap 列出)。你接手 · 不重复抓 · 在它基础上扩展 |
| 2 | drift table 5 列 | Original Intent / Current Repo State / Keep-Revert-Rewrite / Evidence / Owner+Deadline+Acceptance · 6 agent each |
| 3 | PM 逐条裁决 cycle | per gap (G-01..G-10 + 你新发现的 · 双写飞书) |
| 4 | master PRD v1 | `docs/prd/master-2026-04-29.md` |
| 5 | 6 sub-PRD v1 | `docs/prd/{agent1-channel, agent2-riskctrl, agent3-credit, agent4-alert, agent5-compliance, agent6-report}-prd-v1.md` |
| 6 | 双写飞书 | 用 lark-doc skill 同步 PRD 到飞书 wiki |

### 1.2 legacy_gradio 全栈隔离 (PM 4 拍板第 4 件)

PM 决: legacy_gradio **物理保留** + **全栈隔离** (备用 · 不影响产品)。具体做这 5 件:

1. **Import guard**: `legacy_gradio/__init__.py` 第一行加:
   ```python
   import os
   if os.environ.get("ALLOW_LEGACY_GRADIO") != "1":
       raise ImportError(
           "legacy_gradio archived (2026-04-29) · v16 主管线已替代 form_filler / narrative_pipeline · "
           "Set ALLOW_LEGACY_GRADIO=1 only for emergency demo fallback (see CLAUDE.md §15)."
       )
   ```
2. **工具排除**: 在 `pyproject.toml` 加:
   ```toml
   [tool.pytest.ini_options]
   norecursedirs = ["legacy_gradio", ...其他]

   [tool.ruff]
   extend-exclude = ["legacy_gradio"]

   [tool.coverage.run]
   omit = ["legacy_gradio/*"]

   [tool.mypy]
   exclude = ["legacy_gradio/"]
   ```
3. **CLAUDE.md 加 §15 单独章节** (在 §14 后):
   ```
   ## 15. Archived: legacy_gradio (备用 · 全栈隔离)

   v15 form_filler / narrative_pipeline / Gradio v7.5+v9 单机版 · 2026-04-29 移到 legacy_gradio/。
   v16 主管线 (v16_pipeline.py) 已替代 · 已用真实材料跑通。

   ### 隔离方式
   - import guard: legacy_gradio/__init__.py 默认 ImportError
   - pytest / ruff / coverage / mypy 全排除 legacy_gradio/
   - 任何主线代码不允许 import legacy_gradio

   ### Emergency demo 解锁
   ALLOW_LEGACY_GRADIO=1 py legacy_gradio/app.py
   demo 完关掉 · commit 演示日期到 docs/handoff/decisions-log.md 留底

   ### 真删条件
   PM 拍板"v16 真稳了" → 任何 worker 写 PR + PM Authorize-By trailer → git rm -rf legacy_gradio/
   ```
4. **CLAUDE.md §2 改**: 把"已归档至 legacy_gradio/ · 如需 fallback 演示从 archive 恢复" 改成 "已归档至 legacy_gradio/ · 全栈隔离 · 详 §15"
5. **Worker onboarding template 加默认提示** (`templates/onboarding-phase-N.md.tpl` 或 `docs/onboarding/_template.md` 如有 · 没有就加在 RESET_MASTER_PLAN.md 红线区): "不读 legacy_gradio/ 除非显式 ALLOW_LEGACY_GRADIO=1"

### 1.3 register Cat 12 / 16 / 部分 1 (active rule 回写)

来自 `docs/audit/conflict-register-v1.md`:
- Cat 12 evaluation drift (8 entries · 你重定义指标 · per agent 评估 yaml 跟 api 版本对齐)
- Cat 16 角色 drift (5 entries · 含"策略经理→风险经理"全栈搜替 · CLAUDE.md §1/§4 + types.ts 审贷官→审贷员 + api_server.py:376 IM prompt 改)
- Cat 1 部分 (Q-040 MAX_ROWS / Q-041 candidate metadata 4 字段 / PIPL fallback chain · 这 3 条 active rule 你回写到 CLAUDE.md 对应章节 + 加 decisions-log Q-NNN entry)

---

## 2. 不在你范围

- ❌ 5 契约 — A1 干
- ❌ shared infra (llm_caller / sse_envelope / prompts) — A2 干
- ❌ Channel pilot 4 gate — A3 干 (A1+A2 完后启)
- ❌ 5 子 thin adapter — A4 干 (A3 完后启)
- ❌ Letterpress 12 consumer — A5 干
- ❌ handoff data schema (4 链 + export contract) — A6 干

---

## 3. 必读

- `RESET_MASTER_PLAN.md`
- `docs/reset/north-star.md`
- `docs/reset/phase-a-charter.md` §3 worker-A7 + §1 硬线 #7
- `docs/audit/conflict-register-v1.md` (你 owner: cat 12 / cat 16 / 部分 cat 11 / 部分 cat 1)
- `docs/audit/prd-evidence-frozen.md` (你接手 · 不重复抓飞书)
- `docs/audit/sub-agent-step2-round1/production-shape.md` (Cat 11 legacy_gradio + Cat 14)
- `docs/audit/sub-agent-step2-round1/instruction.md` (Cat 1 4 处 active rule 未回写)
- `docs/audit/sub-agent-step2-round1/naming-route.md` (Cat 16 角色 drift 5 entries)
- `CLAUDE.md` §1 / §4 / §11 (角色 + 6 Agent 边界 + 当前版本)
- 飞书 7 PRD doc (URLs 在 prd-evidence-frozen.md Section 1)
- `docs/PRD_*.md` 本地旧版 (12+ 份 · 选 v3.0/v3.1/v2.0 最新版 · 跟飞书对照)

---

## 4. PM 拍板 5 件 (你必须遵守)

1. 杜绝拖死 4 机制
2. Phase A/B 严切阶段
3. active decision 必回写 root CLAUDE.md (Cat 1 你 owner 这 3 条 · 必回写)
4. 命名 SSOT 8 列 (worker-A1 干 · 你 PRD 命名遵 SSOT)
5. legacy_gradio 全栈隔离 (你干这件 · per §1.2 上面 5 件)

---

## 5. 协作纪律

- ❌ 不跨 worktree 改文件
- ❌ commit 不带 `Signal:` trailer
- ❌ 改 `web/` 不带 PRESERVES (你 PRD task 不动 web/)
- ❌ 改 CLAUDE.md / pyproject.toml 算 root 配置改动 · 必同 commit 含 active rule 回写说明
- ❌ 直接 push origin
- ❌ 自己拍板 G-01..G-10 PRD gap (那是 PM 决 · 你提建议给 PM 看)

---

## 6. ACK 协议

- legacy_gradio 全栈隔离完 · commit `Signal: WORKER-A7-LEGACY-GRADIO-ISOLATED` · trailer `IMPORT-GUARD: yes / TOOL-EXCLUDE: pytest+ruff+coverage+mypy / CLAUDE-MD: §15 added + §2 updated`
- master PRD + 6 sub-PRD draft 完 · commit `Signal: WORKER-A7-PRD-MASTER-DONE` · trailer:
  ```
  PRD-MASTER: docs/prd/master-2026-04-29.md
  PRD-SUBS: 6 (各 agent 一份)
  FEISHU-DUAL-WRITE: yes (sync 飞书 7 PRD doc · 同步 commit hash)
  GAP-DECIDED: <N> (G-01..G-10 + 你新发现的 · PM 裁决了几条)
  ACTIVE-RULE-BACK-WRITTEN: 3 (Q-040 MAX_ROWS · Q-041 candidate metadata · PIPL fallback)
  HARDLINE-7-MET: yes
  ```

---

## 7. Codex 协作

主 CLI 已 fire codex pre-dispatch draft · 你不见。落 `docs/audit/codex-drafts/A7-prd.md`。

---

**Author**: 主 CLI · 2026-04-29
**Phase A Week 2-3 · 与 A5 + A6 并行**
