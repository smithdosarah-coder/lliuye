# Phase 3-Final · 轨 3 · agent1 cherry-pick Onboarding

**状态**：Phase 3-Final GO（待 user dispatch）
**发布日期**：2026-04-25
**Signal 入口（ACK）**：`PHASE-3-FINAL-T3-ACK`
**前置**：commit `4f2132e`（Phase 3-Final handoff + Q-032）+ Q-032（Phase 3-Final 总规划）
**参照决策**：`docs/handoff/decisions-log.md` Q-030（Batch 2 closeout）/ Q-031（Mesh 大清理 · agent1 frozen）/ Q-032（**Phase 3-Final 推翻 Q-031 冻结 · 激活 agent1**）+ `docs/handoff/session-2026-04-25-phase-3-final-handoff.md`（§2.3 + §4.3 + §7.1）+ `docs/scorecard/dod-current-status-2026-04-24.md`
**worker 建议**：主 CLI 代理或新建 worktree `code-agent1-cherry`（fork **chore/l0-infra**，**不** fork agent1 branch · 在 main 基础上叠 cherry-pick）
**Final Signal**：`READY-FOR-AGENT1-CHERRY-PICK-REVIEW`

---

## 1. 背景与目标

`feat/agent1-productize` branch 累积 30 commit 未合，handoff §2.3 全量归类后定性：**只有 1 条高价值 + 4 条中价值值得带回 main**，其余 15+ 条是 Option 2 rebase 时代的 marker / 已被 Batch 2 code-arch 替代 / 过期 baseline——**整体 rebase 是负 ROI**。

**本轨策略**：放弃 rebase，**只 cherry-pick** 3 条必带 + 2 条选择性，独立 commit 叠在 chore/l0-infra HEAD 上。冲突面极小，工期 0.5-1 天。

**解 DoD 条目**（参照 handoff §1.3 + §4.3）：
- **L3-8** Agent1 反馈飞轮 E2E loop
- **L1-4** Agent1 xlsx 导出
- **L1-11** Agent1→Agent3 跨 Agent handoff（与 agent3 branch `8f1a35c` 互补）

**硬边界**：本轨 **只动** `agent_channel/` + `web/src/app/archive/channel/` + `tests/agent_channel/`（cherry-pick 对应文件）+ `docs/`（onboarding/decision 记录）。**不动** 红区 / 其他 5 Agent / `evaluation/runner/` / `shared/sources/`。

---

## 2. Task 清单

### Task A · 必 cherry-pick `c408b3a` 数据飞轮 E2E loop

**目标**：Agent1 Phase 1 Task D — D2 data-flywheel E2E loop。补 L3-8 Agent1 缺位（agent6 branch `ee936fe` 提供 Agent6 飞轮 · Agent1 这条独立）。

**操作**：
```bash
git cherry-pick c408b3a
# 冲突处理：若 evaluation 相关文件冲突，**保 main 现状**（Batch 2 evaluation 已重写）
```

**完成信号**：commit message 末尾 trailer
```
Signal: AGENT1-CHERRY-PICK-START
```

---

### Task B · 必 cherry-pick `dc4c148` /api/channel/export_xlsx

**目标**：Agent1 候选企业 xlsx 导出端点 · 解 **L1-4 Agent1 xlsx 导出**。

**操作**：
```bash
git cherry-pick dc4c148
```

**冲突预测**：低（独立 endpoint · `agent_channel/api.py` 加新路由）。

**完成信号**：commit 自带 SHA · 无需额外 trailer（中间 commit 不挂 signal · 只有 START 和 final READY 挂）。

---

### Task C · 必 cherry-pick `0b6eca4` Agent1→Agent3 handoff button + UI

**目标**：Agent1 候选企业页加 "推送给 Agent3 决策" 按钮 + UI · 解 **L1-11**（与 agent3 branch `8f1a35c` Agent6→Agent3 button 形成 6→3 + 1→3 双入口）。

**操作**：
```bash
git cherry-pick 0b6eca4
```

**冲突预测**：中等（前端 `web/src/app/archive/channel/_components/*` 可能与 Batch 2 code-urgent EvidenceTrail 挂载冲突）。**冲突解法**：保留 Batch 2 EvidenceTrail 挂载 + 吸收 handoff button——双方共存，不二选一。

---

### Task D · 选择性 cherry-pick · 先读 diff 再决策

#### D-1 · `f3bd9b5` 信号多样性 ≥ 2 enforcement + eval config

**判断流程**：
```bash
git show --stat f3bd9b5
git diff main..f3bd9b5 -- agent_channel/ shared/sources/
```

- **若** 信号多样性逻辑已被 Batch 2 code-arch Agent1 外搜（`shared/sources/impls/enterprise_info.py` + Tavily provider 升级）覆盖 → **SKIP**，在 final commit body 写明 SKIP 理由
- **若** main 上不存在等价逻辑 → cherry-pick

#### D-2 · `f430e7f` data classification for channel lookalike v1.0

**判断流程**：
```bash
ls docs/data-classification.md docs/compliance/  # 看 main 上是否已有等价文件
git show --stat f430e7f
```

- **若** agent6 branch `e12805c` 的 `docs/compliance/partners-register.md` + `data-classification.md` 已经覆盖 Agent1 维度 → **SKIP**（轨 1 agent6 解冻会带过来）
- **若** 是 Agent1-specific 内容，agent6 那份不覆盖 → cherry-pick

**决策记录**：D-1/D-2 不论 pick 还是 SKIP，**都必须**在 final commit body 写明决策 + 理由（1 句即可）。

---

### Task E · pytest 全绿 + final READY signal

**操作**：
```bash
pytest tests/agent_channel/ -v
cd web && npx tsc --noEmit && cd ..   # 若 Task C 改了前端
```

**Final commit**（独立空 commit 或 docs commit · 挂 final signal）：

commit body 模板：
```
轨 3 · agent1 cherry-pick 完成

必 pick（3）：
- c408b3a feat(feedback): Agent1 数据飞轮 E2E loop · 解 L3-8
- dc4c148 feat(channel): /api/channel/export_xlsx · 解 L1-4
- 0b6eca4 feat(channel): Agent1→Agent3 handoff button + UI · 解 L1-11

选择性 pick（决策）：
- f3bd9b5 信号多样性 · [PICK / SKIP] · 理由：<1 句>
- f430e7f data classification · [PICK / SKIP] · 理由：<1 句>

显式 SKIP 清单（15+ 条 · Option 2 rebase 时代 / 已被替代 / marker 类）：
6379ae7 / c4af59d Merge remote chore/l0-infra（rebase history · no content）
ecfe05a / d17fb8b / d53603c ask Q-008/Q-009/Q-013（已解决）
d41eb49 ack onboarding marker
85bcf40 / 0292b94 window-close + ready markers
f8a4c43 eval baseline 20260419（过期）
65dd432 fix channel Option 2 rebase（已替代）
f500389 ack Option 2 rebase marker
55b7265 mesh CLI window close marker
a7d3134 Phase 2 Batch-1 complete marker
697f963 feat(eval): Option 2 code-side Agent1 runner adapter（Batch 2 evaluation 已重写）
ad0b219 eval baseline 20260418 fix（过期）
798f34c chore(l0): install dev deps + bootstrap（L0 已完成）

测试：pytest tests/agent_channel/ -v 全绿
解 DoD 条目：L3-8 / L1-4 / L1-11

Signal: READY-FOR-AGENT1-CHERRY-PICK-REVIEW
```

**注**：`1e58487 test(channel): Option 4 handoff contract E2E smoke` 和 `2898c96 docs(proposal): Agent1 Phase 2 scope draft` 在 handoff §2.3 标"可能可复用 / 可能有参考价值"——若 cherry-pick 时顺手发现有用可附加（独立判断），否则归 SKIP。

---

## 3. 验收硬指标（P3F-T3-1 ~ P3F-T3-8 · 8 项）

| # | 指标 | 阈值 | 判定方法 |
|---|---|---|---|
| P3F-T3-1 | 3 条必 cherry-pick 全部完成 | git log 出现 c408b3a / dc4c148 / 0b6eca4 三个原 SHA 的 cherry-pick commit | `git log --oneline -20 \| grep -E "c408b3a\|dc4c148\|0b6eca4"` 或对应 message |
| P3F-T3-2 | 选择性 cherry-pick 决策有理 | f3bd9b5 + f430e7f 各自 PICK/SKIP 决策记录在 final commit body · 各 1 句理由 | 看 final commit body |
| P3F-T3-3 | 15+ 条放弃 commit 显式 SKIP 列表 | final commit body 列出 §2 Task E 的 13 条 SKIP（1e58487 + 2898c96 视判断附加 · 至少 13 条） | 看 final commit body |
| P3F-T3-4 | pytest 全绿 | `pytest tests/agent_channel/ -v` exit 0 | exit code |
| P3F-T3-5 | 红区 0 漂移 | diff 不含 `financial_analyzer.py` / `quality_scorer.py` / `truth_fill.py` / `web/src/lib/store/*` | `git diff chore/l0-infra...HEAD --name-only \| grep -E "financial_analyzer\|quality_scorer\|truth_fill\|web/src/lib/store"` 为空 |
| P3F-T3-6 | Signal trailer 齐 | START + READY 两个 signal commit 都在 git log | `git log --grep="AGENT1-CHERRY-PICK-START\|READY-FOR-AGENT1-CHERRY-PICK-REVIEW" --oneline` 见 ≥ 2 条 |
| P3F-T3-7 | 解 DoD 条目 3 项齐 | final commit body 显式声明解 L3-8 + L1-4 + L1-11 | 看 final commit body |
| P3F-T3-8 | diff 白名单 | 改动只在 `agent_channel/` / `web/src/app/archive/channel/` / `tests/agent_channel/` / `docs/` 范围 | `git diff chore/l0-infra...HEAD --name-only \| grep -vE "^(agent_channel/\|web/src/app/archive/channel/\|tests/agent_channel/\|docs/)"` 为空 |

---

## 4. 红线

- ❌ **不整体 rebase agent1 branch**（30 commit 大部分过期 · 只 cherry-pick 3-5 条）
- ❌ **不动红区**（`financial_analyzer.py` / `quality_scorer.py` / `truth_fill.py` / `web/src/lib/store/*`）
- ❌ **不 git push**（跨设备同步等用户明示）
- ❌ **不动其他 5 Agent 代码**（Agent2/3/4/5/6 各有专轨 · 本轨只 Agent1）
- ❌ 不删 / 不 amend `f950b40` 或 `4f2132e` 既有 commit
- ✅ **Final commit body 必须附**：必 pick SHA（3）+ 选择性 pick SHA + 决策（2）+ 显式 SKIP 列表（≥ 13 条）+ 解 DoD 条目（3）
- ✅ 每个 cherry-pick 保留原 commit message（git cherry-pick 默认行为）+ 加 `(cherry picked from commit <sha>)` trailer（默认 `-x` 选项 · 建议加）
- ✅ 中间 cherry-pick commit 不挂 Signal · 只 START 和 final READY 挂

---

## 5. 工期

- Task A 必 pick · ~1h
- Task B 必 pick · ~1h
- Task C 必 pick + 前端冲突解决 · ~2h
- Task D 选择性判断（读 diff + 决策） · ~1h
- Task E pytest + final commit body · ~1h
- 合计 **~0.5-1 天**（cherry-pick 独立 commit · 冲突面低 · 主要工作在 Task C 前端冲突 + Task D 决策判断）
