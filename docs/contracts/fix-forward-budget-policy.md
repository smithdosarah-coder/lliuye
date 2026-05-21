# Fix-Forward Budget Policy

> 2026-05-21 立 · codex R1 修正版 ROI #3 落地 · 防 5/10 §病灶 #2 fix-forward 失控复发

## 1. 为什么需要这条 policy

### 历史数据

| 日期 | 数据窗口 | fix 占比 |
|---|---|---|
| 2026-05-10 retro | 4/27 → 5/10 · 14 天 · 733 commits | **109/733 ≈ 14.9%** |
| 2026-05-21 follow-up | 5/10 → 5/21 · 11 天 · 255 commits | **173/255 ≈ 67.8%（飙升 4.5 倍）** |

### 病灶

5/10 复盘 §2.5 已分析过——没有"停下来 retro"的自动触发机制，团队进入持续救火状态时**没人喊停**。codex R1 也独立验证："fix-forward 限流必要，但若没有 CI red gate 和例外审批，只会变口号"。

### 本 policy 目标

把"何时停手"从**人工触发**（5/10 PM 手动跑复盘）改成**结构化触发**（CI 自动 gate）。

## 2. 阈值

最近 50 commits 中 fix/hotfix/revert 占比：

| 占比 | 状态 | CI 行为 | 团队行动 |
|---|---|---|---|
| ≤ 30% | 🟢 健康 | PASS 静默 | 正常推进 |
| 30% < x ≤ 50% | 🟡 警戒 | PASS + warning + PR 评论 | Monitor 趋势，**计划 retro 准备** |
| > 50% | 🔴 失控 | **FAIL + 阻断 PR merge** | **Stop the line**: 停 feature 工作 + 跑 retro + 排前 2 类根因 |

**阈值依据**：
- 30%：5/10 retro 时已经标 "实际修 bug 比例（含 feat 里 fix-forward）> 30%" 为不健康
- 50%：5/21 实测 67.8% 时项目"卡到爆"是 hindsight 共识，50% 留缓冲

## 3. 例外审批

**两个 label 可绕过 gate**（在 GitHub PR 上加 label）：

### Label A: `hotfix-emergency`

- **用途**：真 P0 生产事故，必须立即 ship
- **谁能加**：项目 maintainer（PM / tech lead）
- **后续义务**：PR merge 后 24h 内开 retro Issue，分析根因 + 防御措施

### Label B: `fix-forward-approved`

- **用途**：已经走过 freeze + retro 流程，本 PR 是 retro 输出的修复
- **谁能加**：retro 主持人（默认 PM）
- **前置条件**：retro 文档已沉淀到 `docs/handoff/retro-YYYY-MM-DD.md`

## 3.5. Auto-triggered retro（CI 自动开 Issue）

触发 > 50% 后 CI workflow 自动开 GitHub Issue with label `fix-forward-retro` + `p0-incident` + `stop-the-line`。仅在 `push` 到 `main` 时开（PR 失败由 PR comment 处理，避免重复噪音）。Issue body 含：

- 数据快照（window / fix count / ratio / CI run URL / 触发 commit SHA）
- Top 20 fix commits（自动从 main 拉最近 50 commits 过滤）
- Step 1-4 retro checklist（与 §4 freeze procedure 对齐 · checklist 格式可直接勾）
- 关闭条件（重跑 ratio 命令 · < 30% 关 Issue）
- 配套链接（policy doc / 5/10 retro wiki page）

**去重**：开 Issue 前查同 label 是否已有 open Issue，有则在原 Issue 上加评论说明新 commit 仍 fail，不重开（防止连续 push 刷一堆重复 Issue）。

**首次 trigger 后 24 小时内必须**：

1. PM ack Issue（评论或 assign）
2. 跑 retro · 沉淀 `docs/handoff/retro-YYYY-MM-DD.md`
3. apply 防御 patch（label `fix-forward-approved`）

**为什么需要这层自动化**：5/21 已经验证"CI warning + PR 评论"不足以触发停手——人会忽略 warning。开正式 Issue with checklist 把"看到 warning"转成"必须 close 的 todo"，比 PR 评论更难忽略。

## 3.6. Overdue 自动升级 (cron 闭环)

policy §3.5 自动开 Issue 后，**仍可能被忽略**。`.github/workflows/fix-forward-overdue-check.yml` 每 6h 扫 open `fix-forward-retro` Issue:

- 创建后 ≥ 24h 仍无 ack（无 assignee · 无 user 评论 · 无 `fix-forward-approved` label）→ 加 `overdue-retro` label + 评论 @ PM
- 重复升级：每 6h 跑 · 已 `overdue-retro` 不重加 label · 但持续评论 @ PM 直到 ack

**Ack 定义（任一即算）**：
- assignee 不为空
- 任意 user 评论（非 bot）
- label 含 `fix-forward-approved`

**为什么需要这层**：5/21 复盘 §病灶 #2 真因不是"没 CI gate"，是"看见 warning 不 act"。Issue + @ mention 比 CI warning 难忽略，但**人仍可能忽略**。Cron + label 升级把"忽略"转成 "label 标在 GitHub 公开可见" + 重复评论压力。

**未来升级路径**（agent12 R3 提议）：
- 中: 接飞书 webhook · open / overdue 时同步推 #liuye-mesh @ PM
- 重: 接 PagerDuty / Opsgenie 真正 on-call 升级

## 4. Freeze procedure（触发 > 50% 后必走）

### Step 1: Stop the line（< 1 day）

- 所有 worker / contributor **暂停 feature 工作**
- 主 CLI / PM 在 `#liuye-mesh` 或类似频道发 freeze announcement
- 当前 in-flight PRs 不强删，但**新 PR 暂停 merge**（除 hotfix-emergency）

### Step 2: Retro（1-2 day）

- 收集最近 N=50 commits 全列表
- 按根因分类（按 5/10 retro §2 5 个病灶为 template）
- 找 top 2 类，确定 owner + due date
- 沉淀到 `docs/handoff/retro-YYYY-MM-DD.md`

### Step 3: Apply fixes（1-3 day）

- 针对 top 2 类根因写防御 patch（可能多个 PR，每个 PR 加 `fix-forward-approved` label）
- Patch merge 后跑 `git log -50 --format=%s | grep -ciE "^(fix|hotfix|revert)" | awk ...` 看新 ratio

### Step 4: Resume

- ratio 降到 ≤ 30% 触发 unfreeze
- 沉淀经验到 `docs/contracts/` 防再坑

## 5. 集成

### CI workflow

`.github/workflows/fix-forward-budget.yml` 已就位。触发条件：
- 每个 PR 到 main
- 每个 push 到 main
- `workflow_dispatch` 手动触发（含 window size 参数）

### Branch protection

**需要 user 手动配置**（GitHub UI）：
1. Settings → Branches → main rules
2. Require status check `fix-ratio-gate` to pass before merge
3. Bypass: `hotfix-emergency` / `fix-forward-approved` label

### Pre-commit hook（建议但未强制）

可选给 contributor 自己 install:

```bash
# scripts/hooks/pre-commit (可选 install)
WINDOW=50
TOTAL=$(git log -${WINDOW} --format=%s 2>/dev/null | wc -l)
FIX=$(git log -${WINDOW} --format=%s 2>/dev/null | grep -ciE "^(fix|hotfix|revert)" || echo 0)
RATIO=$(awk "BEGIN { printf \"%.1f\", ($FIX/$TOTAL)*100 }")
if awk "BEGIN { exit !($RATIO > 50) }"; then
  echo "[fix-forward gate] ratio $RATIO% > 50% · 请走 retro 不要继续 fix-forward"
  exit 1
fi
```

## 6. FAQ

**Q: 我的 PR 是真业务功能但 commit message 里有 'fix'，会被算进去吗？**

A: Pattern 是 commit message **开头**带 `fix` / `hotfix` / `revert`（含中文"修复"）。`feat(xxx): xxx 同时修复 yyy` 这种 **不算** 因为开头是 feat。如果你的 PR 是 feat 但单个 commit 写成 fix，也只会让 fix ratio 升一点，不影响 PR 单独 merge（除非 ratio 累积过线）。

**Q: 100 commits window 不够长 / 太长怎么办？**

A: `workflow_dispatch` 可指定 window size。trend analysis 推荐对比多个 window（30/50/100）看是否真持续。

**Q: 老分支或 feature branch fix ratio 高会影响 main 的 gate 吗？**

A: 不会。CI 只看**本分支最近 N commits**，跨分支独立。

**Q: 例外 label 滥用怎么办？**

A: 加 label 是 GitHub log 公开操作。retro 时统计**例外 label 使用频率**——如果 hotfix-emergency 一个月用了 ≥ 5 次，说明 P0 频率本身有问题，是更深的根因。

## 7. 历史踩坑（防止 policy 自己变成形式主义）

| 时间 | 事件 | 学到的 |
|---|---|---|
| 2026-05-21 立此 policy | 5/21 follow-up 数据 67.8% 后才写 | policy 必须**前置防御**而非"等再失控后再写" |
| 待发生 | 第一次触发 gate | 实测阈值 50% 是否合理 / 例外 label 用了多少 |

## 8. 配套

- `.github/workflows/fix-forward-budget.yml` — CI gate
- `wiki/concepts/Agent 矩阵工程实践原则.md` (vault) — 5/10 retro 5 病灶详解
- `wiki/questions/2026-05-21-产品矩阵-status-vs-510-retro.md` (vault) — 5/21 数据
- `docs/contracts/css-naming-ssot.md` — 同类"事后反应→前置防御"治本模式
