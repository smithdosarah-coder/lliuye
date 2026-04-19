# Agent2 Phase 1 · READY-FOR-REVIEW

**日期**：2026-04-19
**worktree**：`D:\claude code\demo-agent2` (`feat/agent2-productize`)
**baseline 锚**：`5b1c135` (ack/onboarding absorbed)
**HEAD**：`f1e97b0` (Task D)

---

## 1. Phase 1 Task → SHA 对账表

| # | SHA | 改动 | Signal trailer | 关键 DoD 命中 |
|---|---|---|---|---|
| A | `3cc3edf` | scripts/run_agent2_baseline.py 新增；adapter 三级 fallback；yaml baseline → runtime；fixture 降级为回归锚 | `AGENT2-PHASE-1-TASK-A-DONE` | 3 flow 捕获落盘 · runtime FPR=0.0439（严于 fixture 0.0673）· verdict=PARTIAL（2 stubs N/A 留给 Task B） |
| B | `a9387f4` | yaml.baseline.pending_metrics 白名单 + pending_reason；adapter note 一字节同义 | `AGENT2-PHASE-1-TASK-B-DONE` | verdict 从 PARTIAL 升 PASS；A-013 kernel `base_evaluator.py` git diff 空（主 CLI 锁区未触） |
| — | `8ec4283` | merge --no-ff upstream chore/l0-infra（A-019 σ²≤0.03 下发） | merge commit | A-012.E merge-only 合规 · 无 rebase/pull-rebase/force |
| C | `b8e34ac` | backtesting 每规则 FP/TN；adapter per_rule_fpr_spread；yaml target + baseline；3 单测 | `AGENT2-PHASE-1-TASK-C-DONE` | runtime σ²=0.0002 << 0.03；仅 reject 规则参与（approve/manual_review 走 N/A 跳过） |
| D | `f1e97b0` | web/src/app/riskctrl/page.tsx +81 · RuleReadOnlyList 新 127 · mock json · progress doc | `AGENT2-PHASE-1-TASK-D-DONE` | tsc 0 errors · /riskctrl & /mock/riskctrl_ruleset.json HTTP 200 · SSR 四字符串命中 · 仅 web/ 子树 diff |

---

## 2. 红区自查（A-012.D + A-012.E + A-013 kernel）

### 2.1 kernel 全家桶（evaluation/runner/ 红区）

```
$ git diff --stat 5b1c135..HEAD -- evaluation/runner/base_evaluator.py evaluation/runner/registry.py evaluation/runner/cli.py evaluation/runner/__main__.py evaluation/runner/schemas.py
# （无输出 = 0 diff）
```

A-013 kernel `base_evaluator.py` + registry / cli / `__main__` / schemas 全部未触。Agent2 只改 `evaluation/runner/adapters/agent2_riskctrl.py`（黄区 adapter）和 `evaluation/agent2_riskctrl.yaml`（黄区配置）。

### 2.2 后端红区（api_server.py / agent_riskctrl/api/）

```
$ git diff --stat 5b1c135..HEAD -- api_server.py agent_riskctrl/api/
# （无输出 = 0 diff；agent_riskctrl/api/ 目录不存在，Phase 2 新建）
```

Phase 1 未新增 `/api/riskctrl/*` 路由 —— Task D 前端走 `/mock/riskctrl_ruleset.json` 静态文件；Phase 2 落真 API 时 `RuleReadOnlyList` state shape 不变、只换 URL。

### 2.3 A-012.D SHA-immutable 锁列表（本分支 8 枚）

五枚已 review 引用的不可变 SHA：

| SHA | 角色 |
|---|---|
| `5b1c135` | 本分支 baseline · 所有 Phase 1 diff 的起点 |
| `3cc3edf` | Task A 终态引用（runtime baseline 首落） |
| `a9387f4` | Task B 终态引用（verdict=PASS 首达） |
| `b8e34ac` | Task C 终态引用（σ²=0.0002 首达） |
| `f1e97b0` | Task D 终态引用（前端 ReadOnly 首达） |

加上 `8ec4283`（merge A-019）、`46051f2`（Q-019）、`c947906`（A-019 来自 upstream）构成 Phase 1 完整引用链。

### 2.4 reflog 合规（无 rebase / amend / force-push）

```
$ git reflog | head -20
f1e97b0 HEAD@{0}: commit: feat(web): Phase 1 Task D ...
b8e34ac HEAD@{1}: commit: feat(riskctrl,eval): Phase 1 Task C ...
8ec4283 HEAD@{2}: commit (merge): merge: chore/l0-infra → agent2 ...
a9387f4 HEAD@{3}: commit: feat(riskctrl,eval): Phase 1 Task B ...
3cc3edf HEAD@{4}: commit: feat(riskctrl,eval): Phase 1 Task A ...
...
```

全 `commit` / `commit (merge)`，无 `rebase` / `amend` / `reset --hard` / `checkout -- ` 条目。A-012.E merge-only 硬化规则全程遵守。

---

## 3. Runner 最终验证

```
$ py -m evaluation.runner --agent riskctrl
=== riskctrl · PASS · 0.0s ===
    commit: f1e97b0564f396415286f2791fa3b99d8fde2196  artifacts: 0

    [Common]
      OK task_completion_rate                    1.0000  (target >= 0.95)
      OK evidence_rate                           1.0000  (target >= 0.98)
      OK hallucination_rate                      0.0000  (target <= 0.01)
      OK tool_success_rate                       1.0000  (target >= 0.95)

    [Domain]
      OK false_positive_rate                     0.0439  (target <= 0.15)
      OK per_rule_fpr_spread                     0.0002  (target <= 0.03)
      ? ks_improvement                             N/A   (target >= 0.02)
      ? rule_interpretability                      N/A   (target >= 4.0)
```

- **verdict = PASS**
- `per_rule_fpr_spread = 0.0002 << 0.03`（A-019 σ² 阈值）
- 两 stub (`ks_improvement` / `rule_interpretability`) `?` 标记 = `baseline.pending_metrics` 白名单豁免（A-013 kernel 语义，Task B 落地）→ **不降档 PARTIAL**

---

## 4. Web 前端入口验证

```
$ cd web && pnpm tsc --noEmit
# （无输出 = 0 errors）

$ pnpm dev
# ⚠ Port 3000 is in use, using available port 3001 instead
# ✓ Ready in 513ms

$ curl --noproxy '*' -s -o /dev/null -w "%{http_code}" http://localhost:3001/riskctrl
200
$ curl --noproxy '*' -s -o /dev/null -w "%{http_code}" http://localhost:3001/mock/riskctrl_ruleset.json
200

$ curl --noproxy '*' -s http://localhost:3001/riskctrl | grep -oE '规则详情|RULESET · READ ONLY|导出 JSON|进入编辑器' | sort -u
RULESET · READ ONLY
导出 JSON
规则详情
进入编辑器
```

四字符串全命中；SSR 流程正常；「导出 JSON」Blob URL 下载链路已 Task D DoD 实测；「进入编辑器」`disabled` + `<span title>` tooltip。

---

## 5. Phase 2 follow-up 挂账

| # | 事项 | 触发 / 依赖 |
|---|---|---|
| F1 | **per_rule_fpr_spread σ² 阈值 retune**：当前 runtime 7 条 LLM 规则中只 2 条 reject，且信息重合（逾期/负债率）。σ²=0.0002 绝对绿，但统计意义有限 → Phase 2 Batch 2 扩样（≥5 条独立 reject 规则）后重新拟阈值，可能下调至 0.015 | runtime LLM 规则多样性 ≥5 条 reject 后 |
| F2 | **规则编辑器完整实装**：DSL 所见即所得 + 条件推断 + 语法校验 + 在线回测预览；接 `/api/riskctrl/ruleset` (GET/PUT)；新路由 `/archive/riskctrl/editor` 或模态组件 | Stage 3 Agent 迁入 `/archive/[agent]` |
| F3 | **LLM-judge 实装**：`ks_improvement` 依赖 baseline_ruleset 对照组；`rule_interpretability` 依赖 judge prompt + rubric；unblock 后两 stub 退出 pending_metrics 白名单、走真打分 | judge infra（主 CLI 排期） |
| F4 | **前端 API 切换**：`/mock/riskctrl_ruleset.json` → `/api/riskctrl/ruleset`，state shape 不动、组件不动、只换 fetch URL | F2 API 路由落地 |

---

## 6. Signal

本 commit trailer: `AGENT2-PHASE-1-READY-FOR-REVIEW`

commit 后 **idle 等主 CLI 起 full review + scorecard bump**。
不动 `GLOBAL.md` / scorecard 文件（review gate 由主 CLI 负责）。
