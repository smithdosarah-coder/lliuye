# Agent4 Phase 1 V2 Full Review

**Date**: 2026-04-19
**Reviewer**: main CLI subagent
**Worker HEAD**: `08f3ca7` (branch `feat/agent4-productize`, worktree `D:/claude code/demo-agent4`)
**V1 REJECT 根因**: V1 梯子 `e3acbbb` 用 rebase 重写 Phase 0 APPROVED SHA `a972e4c`（违反 A-012.D SHA 不可变）。
**V2 rewind 路径**: `git reset --hard a972e4c` → `git merge --no-ff upstream/chore/l0-infra` → cherry-pick -x × 4 → ack + READY-V2。
**Verdict**: **APPROVED**

---

## Summary

V2 梯子完全合规：reflog 实锤 Phase 0 APPROVED `a972e4c` 保留为裸 reset 目标并成为 merge 父之一（A-012.D/E 双通过），4 次 cherry-pick 均带 `(cherry picked from commit <v1>)` trailer 指向正确 V1 SHA（34f85af / e18028f / 3ef8799 / 0c06b21），committer date 严格单调递增（无 amend），V2 era reflog 只有 commit / cherry-pick / merge / reset，rebase 痕迹全部沉在 V1 era（HEAD@{14} 及更早，Step 3 GO 明示可接受）。Runner 实跑 verdict=PASS（6 deterministic 全绿，cross_hit_precision / recall_on_known_bad 走 A-013 pending_metrics 白名单 N/A 不入分母），5 条 trigger_reasons 单测全绿，100 客户全回填，3 值枚举 `{external_signal, internal_rule, cross_hit}` 封闭性实测通过（grep 枚举值 sort -u 只出 3 行）。红区零改、web/ 零改、文档三件套齐全。

---

## Gate-by-Gate

### Gate 1 — V2 四 Task cherry-pick trailer 齐全 · **PASS**

命令：`git log -1 --format=%B <sha>` × 4。证据：

| V2 SHA | trailer 最末行 | 对应 V1 SHA | 一致 |
|---|---|---|---|
| `cdc34f5` | `(cherry picked from commit 34f85afd0a95861a1af6683457c3f36c3d8ea048)` | `34f85af` | ✅ |
| `d6f82fd` | `(cherry picked from commit e18028f0d75eb2bfc1c57ffe9465fb01e3a591fb)` | `e18028f` | ✅ |
| `15afdf5` | `(cherry picked from commit 3ef87990d277b5117b57aed24bd1bbfaff4ee21d)` | `3ef8799` | ✅ |
| `69cb828` | `(cherry picked from commit 0c06b21882fc1bbf800bcf4e915247023267559c)` | `0c06b21` | ✅ |

### Gate 2 — A-012.D SHA 不可变 · **PASS**

命令 `git merge-base --is-ancestor a972e4c HEAD && echo "..."` 输出 `a972e4c reachable OK`。Phase 0 APPROVED commit 在 08f3ca7 祖先链中可达。

### Gate 3 — A-012.E merge-only · **PASS**

`git show --format='%P' -s 2fc8342` → `a972e4c854a7881ff1fd81279fd06c89090ea19c c94790679f518a79b67a92867b503c45cd246322`（两个父 SHA，左=Phase 0 APPROVED，右=upstream/chore/l0-infra 当时 HEAD）。`git show --stat 2fc8342` 首行为 `Merge: a972e4c c947906` + `Merge made by the 'ort' strategy.`——真 merge commit，非 ff / squash / rebase。

### Gate 4 — V2 era reflog 禁 rebase 痕迹 · **PASS**

`git reflog | head -20`：
- HEAD@{0}..{7}（V2 era）：commit / cherry-pick / cherry-pick / cherry-pick / cherry-pick / commit / merge / reset。**零 rebase 条目。**
- HEAD@{8}..{13}（V1 era 待清理）：V1 READY + 4 task commit + ack。
- HEAD@{14}..{19}（Phase 0 era）：含 `rebase (finish)` / `rebase (pick)` × 5。**出现在 Step 3 GO 明示可接受的 V1-及更早 era。**

### Gate 5 — V2 committer date 单调递增 · **PASS**

`git log --format='%H %cI' 478d260^..HEAD`：
```
2fc8342 2026-04-19T...（merge base，父 commit）
478d260 2026-04-19T17:13:15+08:00
cdc34f5 2026-04-19T17:25:25+08:00
d6f82fd 2026-04-19T17:36:14+08:00
15afdf5 2026-04-19T17:57:01+08:00
69cb828 2026-04-19T17:59:44+08:00
08f3ca7 2026-04-19T18:07:39+08:00
```
严格单调递增，无 amend / 回写。

### Gate 6 — Runner kernel 红区零改 · **PASS**

`git diff 478d260..HEAD -- evaluation/runner/{base_evaluator,registry,cli,__main__,schemas}.py` → 空 diff。

### Gate 7 — 后端红区零改 · **PASS**

`git diff 478d260..HEAD -- api_server.py agent_alert/api/` → 空 diff。

### Gate 8 — Web 子树零改 · **PASS**

`git diff 478d260..HEAD -- web/` → 空 diff（Task D handoff 约定被严格遵守）。

### Gate 9 — Runner 实跑 · **PASS**

命令 `py -m evaluation.runner --agent alert` 输出：
```
=== alert · PASS · 0.0s ===
    commit: 08f3ca7673ed64acfb97a926c4ce2d31e76b368a  artifacts: 0

    [Common]
      OK task_completion_rate       1.0000  (target >= 0.95)
      OK evidence_rate              1.0000  (target >= 0.95)
      OK hallucination_rate         0.0000  (target <= 0.01)
      OK tool_success_rate          1.0000  (target >= 0.90)

    [Domain]
      ? cross_hit_precision            N/A  (target >= 0.80)
      ? recall_on_known_bad            N/A  (target >= 0.90)
      OK grade_distribution_sanity  1.0000  (target pass)
      OK scan_latency_p95           0.0000  (target <= 30)
```
Verdict = **PASS**。6 deterministic 全绿。pending_metrics (`cross_hit_precision` / `recall_on_known_bad`) 走 A-013 白名单 N/A，不入分母（yaml `baseline.pending_metrics` + adapter note `"pending: Phase 2 Batch 2 — ... yaml baseline.pending_metrics 白名单，A-013 kernel 免算"`）。

### Gate 10 — trigger_reasons 零黑名单 · **PASS**

`grep -rE "RULE_ID_TO_REASON|keyword.*reason|regex.*reason" agent_alert/` → 0 hits。对齐 CLAUDE.md §12（不写关键词/正则黑名单）。

### Gate 11 — trigger_reasons 单测实跑 · **PASS**

`py -m pytest agent_alert/tests/test_trigger_reasons.py -v` → **5 passed in 0.15s**：
- `test_external_only_returns_external_signal`
- `test_internal_only_returns_internal_rule`
- `test_both_routes_collapse_to_cross_hit`
- `test_empty_hits_returns_empty_list`
- `test_enum_values_are_frozen_strings`

### Gate 12 — trigger_reasons 封闭性 + 100 客户全回填 · **PASS**

- `grep -c trigger_reasons evaluation/manual/4_20260419.yaml` → **100**（一客户一条）。
- `entity_id` 计数 = 100，与 customers 一一对应。
- `grep -E "(external_signal|internal_rule|cross_hit)" evaluation/manual/4_20260419.yaml | sort -u` → 仅 3 行，枚举封闭性实证。
- 抽查样本：红/黄灯客户取值分布见于 `external_signal` / `internal_rule` / `cross_hit`，绿灯客户为 `[]`（空列表即"无 hit"，非第 4 类）。
- 分级分布：red=3 / yellow=7 / green=90（与 Task A commit body 一致）。

### Gate 13 — Evidence-First 文档 / handoff 完整性 · **PASS**

| 文件 | 存在 | 核心内容核查 |
|---|---|---|
| `docs/design/alert-trigger-reasons-taxonomy.md` | ✅ | 6 节（语义定义 / 推断规则伪代码 / 为什么不用黑名单 / 前端展示 hook / 变更约束 / 相关文档），含反例（❌ 3 条）+ RFC 约束 |
| `docs/design/alert-dashboard-stub.md` | ✅ | 3 卡片 ASCII wireframe（分级客户数 / 触发原因码分布 / 30 天趋势）+ 字段级数据源映射表 + 4 主题 `--g0..--g7` 色系 hook + 「不在本 stub 范围」防 scope creep |
| `docs/progress/agent4-phase-1-frontend-handoff.md` | ✅ | 依赖 SHA（Task A 34f85af / Task C 3ef8799 列出）+ 3 条绝对红线（不推断 trigger_reasons / 不文本反推 / 字段缺失标「未能自动填写」）+ Stage 3 排期建议 |

---

## V1 → V2 映射证据

| Task | V1 SHA | V2 SHA | cherry-pick trailer | 验证 |
|---|---|---|---|---|
| A · runtime dump | `34f85af` | `cdc34f5` | `(cherry picked from commit 34f85afd0a95861a1af6683457c3f36c3d8ea048)` | ✅ |
| B · pending_metrics 白名单 | `e18028f` | `d6f82fd` | `(cherry picked from commit e18028f0d75eb2bfc1c57ffe9465fb01e3a591fb)` | ✅ |
| C · trigger_reasons 枚举 | `3ef8799` | `15afdf5` | `(cherry picked from commit 3ef87990d277b5117b57aed24bd1bbfaff4ee21d)` | ✅ |
| D · dashboard stub + handoff | `0c06b21` | `69cb828` | `(cherry picked from commit 0c06b21882fc1bbf800bcf4e915247023267559c)` | ✅ |

Merge base: `2fc8342` (parents = `a972e4c` Phase 0 APPROVED + `c947906` upstream chore/l0-infra)。Ack: `478d260`。READY marker: `08f3ca7`。

---

## Follow-up

非阻塞 nit / Phase 2 接手点：

1. **Phase 2 Batch 2 · pending_metrics 算法实装**：当前 `cross_hit_precision` / `recall_on_known_bad` 走 A-013 白名单 N/A。接入（a）业务方标注的 known-bad 客户清单 + （b）真实外部源（Tavily / 工商 / 司法，非 MockSearchProvider）后才能退出 pending 态计真值。
2. **30 天趋势数据储备**：Task D 卡片 C 依赖 30 日 yaml 序列；当前只有单日 dump，需累积或补造历史样本；frontend Stage 3 可先 ship 卡片 A+B（单日静态）。
3. **红灯色系语义冲突**：stub §1 自己已记录——Canvas 主题 `--g7` 是墨绿，作「红灯」会语义冲突，建议 Stage 3 改用 `--accent` + emoji 兜底。设计稿已提示，无需本 Phase 处理。
4. **API 端点 Phase 2 Batch 2 挂**：`GET /api/agent/alert/daily?date=YYYY-MM-DD` 路径候选已在 handoff §4.3 列出，body 与 yaml 1:1 对齐，过渡期前端切换点只改 data fetcher。
5. **V1 era reflog 自然过期**：HEAD@{14}..{19} 的 rebase 痕迹会随 reflog expire（默认 90 天）消失，无需手动清理；本次 Step 3 GO 已明示可接受。

---

## Scorecard 建议

**当前**：Agent4 预警 Phase 0 APPROVED **57%**（GLOBAL.md 第 32 行）
**建议**：**72%**（+15 百分点）

**理由**：

1. Phase 1 交付实打实闭合 Phase 0 报告列出的三个最大 gap：
   - L1 evaluation 从 PARTIAL 升 PASS（Task B，pending_metrics 白名单）
   - L2 «缺原因码» gap 从 🟡 转为 ✅（Task C，3 值封闭枚举 + 5 单测 + 100 客户全回填，零黑名单）
   - L2 «缺仪表盘» gap 从 ❌ 转为 🟡（Task D，设计稿 + handoff，前端实装挂 Stage 3）
2. V1→V2 rewind 对 A-012.D/E 的严格合规展现项目契约内控能力（merge-only + SHA 不可变双通过），合规贴水。
3. 还未 ship 到演示环境（web/ 零改，前端实装在 Stage 3），因此不建议直接对齐 Agent2 的 77%。

**相对校准锚点**（Agent2 Phase 1 APPROVED 77%）：

| 维度 | Agent2 Phase 1 (77%) | Agent4 Phase 1 V2 (建议 72%) | 差值原因 |
|---|---|---|---|
| L1 evaluation | ✅ PASS + σ²=0.0002 | ✅ PASS + pending 白名单 | 同档 |
| L2 UI 入口 | 🟡 ReadOnly mock 展示 | ❌ 仅设计稿（未实装） | Agent2 领先 5 分 |
| L2 原因码/审计 | 🟡 缺审计 | ✅ 原因码枚举 + 单测 + 100 回填 | Agent4 反超 |
| L5 协议合规 | 常规路径 APPROVED | V1→V2 rewind 双通 A-012.D/E | Agent4 合规贴水 +2 |

净差 ≈ -5 分，给 72%。

**不建议直接 APPROVED 到 77%** 的关键因素：Agent2 的 Task D 有 ReadOnly mock 前端入口（"有面可看"），Agent4 Task D 只到设计稿 + ticket（"有稿可移交"）；bank delivery DoD 的 L2 交互层面 Agent2 实在领先。等 frontend Stage 3 把 stub 落成真卡片，Agent4 可在 Phase 2 Batch 1 review 里再升到 77-80%。

---

## Verdict 汇总

**13 个 Gate 全 PASS，V1→V2 rewind 完整合规 A-012.D/E 双规则，Runner 实跑 PASS，4 文档就位 + 5 单测绿 + 100 客户全回填。Verdict = APPROVED。**
