# Codex × Mesh 协作协议

> 让 Codex (gpt-5.5-codex) 作为 cross-AI peer 介入 mesh worker 流程。任何主 CLI 都按本协议触发 Codex · 不允许偏离。

---

## 1. Codex 在 mesh 中的角色

- **不是 worker** (没 worktree · 没 AGENT_IDENTITY)
- **是 cross-AI peer** (横向评审 / 独立草案 / 仲裁)
- 输出**仅 audit doc** (commit 在 main repo audit 目录 · 由主 CLI commit · Codex 不直接 push)
- 触发**完全由主 CLI 决定** · Codex 不轮询不主动

---

## 2. 4 个插入点

| # | 名 | 触发时机 | 主 CLI 动作 |
|---|---|---|---|
| 1 | **pre-dispatch independent draft** | 任何 worker 启动时 | 主 CLI 同时 fire codex 写独立草案 (不让 codex 看 onboarding 的"建议"段 · 防 anchor) |
| 2 | **post-DONE peer review** | worker DONE signal 后 | 主 CLI fire codex 评审 worker diff · 输出 verdict |
| 3 | **dissent arbitration** | Round 1/2 出现双方分歧 | 主 CLI fire codex 中立仲裁 |
| 4 | **periodic audit** | Phase A 中段 + Phase A 末 + Phase B 末 | 主 CLI fire codex 全仓 contract-audit + drift 扫 |

---

## 3. Codex CLI 命令 (verbatim · 主 CLI 直接复用)

### 通用模板

```bash
cd "/d/claude code/credit_report_agent_work" && \
codex exec --skip-git-repo-check --full-auto \
  -o "C:/Users/Mr.S/AppData/Local/Temp/codex_<stage>_<task>_final.md" \
  -C "D:\claude code\credit_report_agent_work" \
  < "C:/Users/Mr.S/AppData/Local/Temp/codex_<stage>_<task>_prompt.md"
```

**flag 说明**:
- `--skip-git-repo-check` · 不报 untracked file 警告
- `--full-auto` · 自动 approve sandboxed tool 执行 (避免 rejected by policy)
- `-o <file>` · 把 codex 最终 message 写入文件 (区别于 stdout 全 transcript)
- `-C <dir>` · cd to 工作目录
- `< <prompt>` · stdin 喂 prompt (避免 argv 解析问题 · 上次有踩坑)

### Background 模式 (long task · run_in_background=true)

主 CLI 用 `Bash` 工具 + `run_in_background=true` 起 codex · 拿到 task id 后等 task notification。

---

## 4. 4 类 Prompt Template (verbatim · 主 CLI 复用)

每类 template 主 CLI 用时 fill 占位符 (`<...>`) 后写到 `/tmp/codex_<stage>_<task>_prompt.md` · stdin 给 codex。

### 4.1 Template · pre-dispatch independent draft (插入点 1)

```markdown
# Codex Pre-Dispatch Independent Draft · <TASK NAME>

You are an independent staff engineer asked to draft a solution for a banking AI 6-agent product reset task. **Claude (orchestrator) is dispatching the same task to a worker IN PARALLEL with you.** You will be shown both your draft and the worker's draft in Round 2 for cross-critique.

## Anti-bias rules

- Draft INDEPENDENTLY · do NOT see worker's onboarding "建议" section
- Use schema: `改 / 坚持 / 对方弱点 / 吸收对方 / v2 final` per Q
- ≤ 3500 words total
- Concrete file paths + line numbers · NO abstractions
- Dissent appendix 必须保留

## Repo

- `D:\claude code\credit_report_agent_work` · branch `chore/l0-infra`

## Required reading

- `RESET_MASTER_PLAN.md` (project root)
- `docs/reset/north-star.md`
- `docs/reset/phase-a-charter.md` (your task is in `worker-<X>` section)
- 任务相关 contracts in `docs/contracts/`

## Task

<TASK DESCRIPTION · 主 CLI fill · 仅 task 名 + 高层目标 · 不写 "建议方案">

## Output

Markdown · 按 Phase A charter 该 worker 的"交付"清单写独立 v1 · ≤ 3500 词。

Begin.
```

主 CLI commit signal: `CODEX-DRAFT-<TASK>-DONE` · trailer `CODEX-DRAFT-PATH: docs/audit/codex-drafts/<task>.md`

### 4.2 Template · post-DONE peer review (插入点 2)

```markdown
# Codex Post-DONE Peer Review · <WORKER SIGNAL>

You are a cross-AI peer reviewer. A worker just signaled DONE. Review their diff against the onboarding spec and your own pre-dispatch draft.

## Anti-bias

- Verdict required: **AGREE / DISAGREE / NEED-MORE-INFO**
- DISAGREE 必须 cite concrete file:line + 替代方案
- ≤ 2500 words

## Inputs

### Worker DONE signal

- Worker: <WORKER NAME>
- Signal: <SIGNAL>
- Commit hash: <SHA>
- Diff stats: `git diff <SHA>~..<SHA> --stat`

### Worker diff (verbatim · attached as <stdin> block)

(主 CLI 通过 stdin 把 git diff 内容附在 prompt 末)

### Onboarding spec

(主 CLI inline `docs/onboarding/<task>.md` 内容)

### Your pre-dispatch draft (Round 1)

(主 CLI inline `docs/audit/codex-drafts/<task>.md`)

## Review Schema

Output verbatim:

```
verdict: AGREE | DISAGREE | NEED-MORE-INFO
reasoning: <1-3 sentences>
specific issues: <list · 每条 file:line + 替代>
strengths: <list · worker did well>
suggested follow-up: <if NEED-MORE-INFO · what 你需要看>
```

Begin.
```

主 CLI commit signal: `CODEX-REVIEW-<WORKER-SIGNAL>-VERDICT` · trailer:
- `CODEX-VERDICT: AGREE | DISAGREE | NEED-MORE-INFO`
- `WORKER-SIGNAL: <reviewed signal>`

### 4.3 Template · dissent arbitration (插入点 3)

```markdown
# Codex Dissent Arbitration · D-<NNN>

Two parties (Claude orchestrator + Worker) disagree on a design point. You are asked to provide a NEUTRAL arbitration verdict — NOT take a side because one is louder. Cite evidence.

## Inputs

### Dispute

- **Topic**: <e.g. workspace state 模型 4 gate 还是 5 gate>
- **Party A (Claude)**: <verbatim claim + reasoning>
- **Party B (Worker)**: <verbatim claim + reasoning>
- **Original spec source**: <docs/contracts/... · or RESET_MASTER_PLAN.md>

## Required reading

- `RESET_MASTER_PLAN.md`
- `docs/reset/north-star.md`
- 相关 contracts

## Arbitration schema

```
verdict: A | B | NEITHER (need new option) | NEED-MORE-INFO
reasoning: <evidence path · cite contracts / north-star / decisions-log>
if NEITHER: <suggest C>
PM 拍板建议: <if PM intervention needed · what info to give PM>
```

≤ 1500 words. Begin.
```

主 CLI commit signal: `CODEX-ARBITRATION-D-<NNN>-DONE` · trailer `DISSENT-ID: D-<NNN>`

### 4.4 Template · periodic audit (插入点 4)

```markdown
# Codex Periodic Audit · <PHASE> · <DATE>

Run a full-repo drift audit. Compare current state vs. acceptance hardlines.

## Required reading

- `RESET_MASTER_PLAN.md`
- `docs/reset/north-star.md`
- `docs/reset/phase-a-charter.md` (Phase A 8 验收硬线)
- `docs/reset/phase-b-charter.md` (Phase B 3 验收硬线)
- `docs/reset/state-snapshot.md` (现状)
- `docs/handoff/decisions-log.md` (since last audit)

## Audit categories (17 类)

(完整列表见 docs/reset/codex-mesh-protocol.md §6 · same as Step 2 conflict scan checklist)

## Output schema

```
| Cat | file:line | Drift evidence | Severity (P0-P4) | 建议 |
```

Plus end with: 
- **Phase A 完成度**: 8 项硬线 each (yes/partial/no + evidence)
- **新发现 drift** (since last audit · 5-10 个)
- **风险预警** (即将走歪的趋势)

≤ 4000 words. Begin.
```

主 CLI commit signal: `CODEX-PERIODIC-AUDIT-<DATE>-DONE` · trailer `AUDIT-SCOPE: full-repo` + `AUDIT-DATE: <YYYY-MM-DD>`

---

## 5. 4 类 audit 输出 dir

```
docs/audit/
├── codex-drafts/<TASK>.md          # 插入点 1
├── codex-reviews/<SIGNAL>.md       # 插入点 2
├── codex-arbitration/D-<NNN>.md    # 插入点 3
└── codex-periodic/<DATE>.md        # 插入点 4
```

每次 codex 完成 · 主 CLI 把 `/tmp/codex_*_final.md` 移到对应 dir · 加 frontmatter (date + task + signal)。

---

## 6. Codex Verdict 处理流程

```
worker DONE → 主 CLI fire codex review (插入点 2) → codex 输出 verdict
   ├── AGREE → 主 CLI cherry-pick worker diff to chore/l0-infra → MERGED
   ├── DISAGREE → 主 CLI:
   │     1. 读 codex 的 specific issues
   │     2. 自己 review 一遍 worker diff
   │     3. 如果同意 codex → 派 worker 改 → 重 review
   │     4. 如果不同意 codex → fire 插入点 3 (arbitration) → PM 拍板
   └── NEED-MORE-INFO → 主 CLI 提供 codex 要的 context · 重 fire 插入点 2
```

---

## 7. 红线

- ❌ Codex 不读 worktree 内容 · 仅读 main repo (worktree 隔离 · 防交叉污染)
- ❌ Codex 不直接 push commit · 输出仅 audit doc · 由主 CLI commit
- ❌ 插入点 1 中 Codex 不能见 onboarding 的"建议方案"段 · 仅见任务描述 (anti-anchor)
- ❌ 插入点 2 中 Codex 必须见 git diff · 不是仅 commit message (避免 review 表面)
- ❌ Codex DISAGREE 时主 CLI **必须 escalate PM** · 不能自决 MERGED
- ❌ 任何 codex output 不带 audit doc · invalid · 必须重 fire

---

## 8. Phase A worker 完整 Codex 流程示例 (worker-A1 contracts)

```
Day 1
[09:00] 主 CLI 写 docs/onboarding/A1-contracts.md
[09:01] 主 CLI commit "PHASE-A1-CONTRACTS-DISPATCHED"
[09:02] 主 CLI fire 插入点 1 (pre-dispatch draft):
        codex exec ... -o /tmp/codex_predispatch_A1_final.md
        ... < /tmp/codex_predispatch_A1_prompt.md
[09:03] worker-A1 resume worktree · 看 onboarding · 开干

Day 1-3 (worker 干活)
[worker push WORKER-A1-CONTRACTS-V1-DRAFT signal]
[codex draft 完成 · 主 CLI 写到 docs/audit/codex-drafts/A1-contracts.md]

Day 3 evening
[20:00] 主 CLI 看 worker draft + codex draft → synthesize → docs/audit/synthesis-A1-v1.md
[20:30] 主 CLI commit "SYNTHESIS-A1-V1-PREPARED" + push
[20:31] 提示 PM verify

Day 4
[09:00] PM verify · GO / 调整
[09:30] worker integrate synthesis · push WORKER-A1-CONTRACTS-V2-DONE
[09:31] 主 CLI fire 插入点 2 (post-DONE review):
        codex exec ... -o /tmp/codex_postdone_A1_review_final.md
[09:50] codex 输出 CODEX-VERDICT: AGREE
[09:51] 主 CLI cherry-pick → MERGED · push origin/chore/l0-infra + main
```

---

## 9. 主 CLI 责任清单 (per worker dispatch)

每派 1 worker · 主 CLI 必做 8 件:

1. ✅ 写 `docs/onboarding/<task>.md`
2. ✅ commit `PHASE-A-<X>-DISPATCHED` signal
3. ✅ fire codex 插入点 1 (pre-dispatch draft)
4. ✅ 等 worker push DONE signal
5. ✅ fire codex 插入点 2 (post-DONE review)
6. ✅ 看 verdict · 处理 (per §6)
7. ✅ commit codex audit doc + worker cherry-pick
8. ✅ 更新 `docs/reset/state-snapshot.md` (worker 状态变更)

8 件全做 · 才算"该 worker 工作流走完"。

---

## 10. 工程化升级 (Phase A 中段做)

当前 codex 是手工命令 + 手工 prompt fill。可升级为脚本:

- `scripts/orchestrator/codex-peer.py draft <task> --onboarding ...` (插入点 1 自动化)
- `scripts/orchestrator/codex-peer.py review <signal>` (插入点 2 自动化)
- `scripts/orchestrator/codex-peer.py arbitrate <dissent>` (插入点 3 自动化)
- `scripts/orchestrator/codex-peer.py periodic --since <date>` (插入点 4 自动化)
- mesh.json schema v3 加 `ai_peers.codex` 节
- commit-signal-registry.yaml 加 4 类新 signal regex

工程化升级 不阻 Phase A 启动 · 边走边补。worker-A2 (shared infra) 完工后顺手做。
