# Onboarding Spec Self-Check Checklist

**适用场景**：主 CLI 写完 worker onboarding（`docs/onboarding/<name>.md`）准备 commit 之前
**强制等级**：必跑 · pass 才能 commit + dispatch
**触发缘起**：Q-035（agent6 v16 漂移 < 1% 红线在当前 baseline 上不可达 · 阻塞 worker 60min+ 才发现）

---

## 5 项 self-check（按 fail 频率降序）

### 1. 🔴 红线可达性（reachability）

**Rule**：每条 numeric 红线（"score 漂移 < X%" / "P95 < Y s" / "覆盖率 ≥ Z%" / "diff < N 文件"）必须在 worker 拿到状态时**物理可达**。

**Quick math**：
- 红线公式 = baseline × threshold
- 验 baseline 在 worker fork 时还有意义（not changed by 自身 commits）
- 验 threshold 在数据 noise 之上（不是 noise 内）

**Fail 例**（Q-035 真实触发）：
```
T1-4: v16 跑分漂移 < 1% vs baseline 68.6
```
baseline 68.6 是 chore/l0-infra commit `21180bf` 跑出 · agent6 branch 20 commits（含 0f436fc QC 强化 + 38901c6 模板扩展）就是设计上要降低 score · post-rebase HEAD 必然 -3% drop · 红线**不可达**。

**Fix**：写"漂移 < X% 相对 baseline Y" 时同句标 "（确认 baseline Y 在 worker 拿到数据时仍有意义 · 不被 worker 自身 commits 抵消）"。

---

### 2. 🔴 Baseline 时效性（baseline staleness）

**Rule**：onboarding 引用的 baseline / 历史数据 / 评估跑分必须 verify 仍 reflect worker 即将处理的状态。

**Quick math**：
- onboarding ref 的 baseline 时间戳 vs worker fork 时间
- 期间 main / 自身 branch 是否有 commit 影响该 baseline
- baseline 是否被新 schema / pivot 已经过期

**Fail 例**：
- onboarding 写 "vs evaluation/baselines/2026-04-26-real-run.md"· 但本任 worker rebase 含 commits 改变了 evaluation adapter · baseline 应在合后重跑

**Fix**：onboarding 头部加"baseline 时效性声明"——"本任引用 baseline X · worker fork 后 X 是否仍 valid · 不 valid 则 worker 跑前重生成"。

---

### 3. 🟡 Spec gap（5W1H 覆盖）

**Rule**：onboarding 应覆盖 worker 可能遇到的 5 类边界场景：

| Who | 谁碰到（worker / main CLI / user） |
| What | 碰到什么（conflict / drift / missing dep） |
| When | 在 Task A/B/C/D 哪步 |
| Where | 走哪条 escalation 路径（Q-NNN-RAISED commit / RFC commit / chat 禁用）|
| Why | 触发理由（红线触线 / spec ambiguous / 数据不足）|
| How | 具体 commit message + signal trailer 模板 |

**Fail 例**：
- onboarding 写"冲突 > 4 文件立即停手 askout" · 但没写"askout 怎么 askout"——worker 可能在 chat 输出（违反 protocol · 见 Q-035 lesson）

**Fix**：每条 askout / abort / blocker 触发条件后追加"具体动作 = commit `Signal: Q-NNN-RAISED` + body 含 X/Y/Z 字段"。

---

### 4. 🟡 对内一致性（internal consistency）

**Rule**：onboarding 内部 sections 之间无矛盾。重点检验对：

| 对 | 检验 |
|---|---|
| 验收硬指标 vs 红线 | 红线禁动的内容 · 验收指标不应要求改 |
| Task 描述 vs Final commit body 模板 | Task 步骤产出 · body 模板应该全 cover |
| diff 白名单 vs Task scope | Task 实际触的路径都在白名单 |
| 工期估算 vs Task 数 + 验收复杂度 | 不要 0.5d 工期写 12 项验收 |

**Fail 例**：
- T1-8 diff 白名单严格 enumeration · 但 Task A rebase 20 commit 实际触额外 4-5 路径（agent6 ACK 时 surface flag · 主 CLI illustrative 解读裁决）

**Fix**：白名单写 "限于 X / Y / Z（illustrative · 红线是不动 financial_analyzer 等 · 不是 enumeration 完整）"。

---

### 5. 🟢 DoD 条目存在性（DoD entry presence）

**Rule**：onboarding 声称解的 DoD 条目（L1-X / L2-Y / L3-Z）在 `docs/scorecard/definition-of-done.md` + `docs/scorecard/dod-current-status-XXX.md` 必须真实存在 + 未 done。

**Quick check**：
- `grep "L2-7" docs/scorecard/*.md` · 至少 1 命中
- 验 status 不是 "done" · 否则 onboarding 是 redundant
- 验编号一致（L2-7 vs L2-07 vs L2.7 不混用）

**Fail 例**：
- onboarding 写"解 L1-3 Agent3 RiskRadar" · 实际 L1-3 在 dod-current-status 里写 "🟡 RiskRadar 待加 · 后端 thin wrapper" · onboarding 应明示 "L1-3 是前端 + 后端两段 · 本任只解后端"

**Fix**：DoD 条目引用必含完整 status quote · 不是裸 ID。

---

## 流程

主 CLI 写完 onboarding · 进 commit 前：

```
1. 读自己写的 onboarding 全文
2. 跑上述 5 项 check
3. 任意 fail → 立即 fix · 不 commit
4. 全 pass → commit · trailer Signal: <ONBOARDING-X-LANDED>
```

可以辅以 subagent dry-run（subagent 模拟 worker 视角读 onboarding · report 5 项 check 各项 fail/pass）· 节省主 CLI context。

---

## 适用范围

- ✅ P3F / Phase 4+ 所有 worker onboarding
- ✅ 主 CLI 直接写的 docs（kickoffs / decisions-log Q/A · 数 baseline 引用部分）
- ❌ 旧 batch 已落盘 onboarding 不回填（spec gap 已暴露 = lesson 不需 retro）

---

## 持续维护

每次新 spec gap 触发（如 Q-035 这类）· 评估是否要在本 checklist 加新 check 项。lesson learned 加到 commit message · 不要让本 checklist 无限膨胀（minimum viable process）。
