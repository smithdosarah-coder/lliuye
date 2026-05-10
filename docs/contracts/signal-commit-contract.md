# Worker Signal Commit Contract v1.1 · 2026-05-09

> **状态**: ✅ Phase A frozen (Phase A common worker · 2026-05-09)
> **Tier**: 1 (red zone · per `docs/arch/instruction-source-of-truth.md` v1.0)
> **Owner**: common worker · 修改走 RFC
> **依赖**:
> - `scripts/mesh/verify_signal_commit.py` (16 单测) · commit-msg hook + 主 CLI 手动 verify
> - `scripts/mesh/cherry_pick_worker.py` · 主 CLI 自动 cherry-pick + DIFF guard
> **历史**: 基于 Q-054 mesh 派活 protocol (R3v2 P0 实战 validated · 2026-04-30)

---

## 1. Signal Commit 格式 (硬规)

### 1.1 Subject (verbatim 模板)

```
chore(mesh): signal worker <agent> ready for mesh merge ALLIN
```

`<agent>` ∈ `{common, report, credit, alert, riskctrl, compliance}` (白名单内)

正则 (`verify_signal_commit._SIGNAL_SUBJECT_RE`):
```
^chore\(mesh\): signal worker (?P<agent>[a-z]+) ready for mesh merge ALLIN$
```

### 1.2 Body 必含 5 trailer

```
Worker: <agent>
Phase: A | B | C
Refs: ALLIN-<YYYY-MM-DD>
Signal: READY | BLOCKED | HOTFIX | RESUMED
Root: <git sha 7-40 hex>
```

校验:
- `Worker` ∈ 6 agent 白名单
- `Phase` ∈ {A, B, C}
- `Refs` 必以 `ALLIN-` 开头
- `Signal` ∈ {READY, BLOCKED, HOTFIX, RESUMED}
- `Root` 必是 git sha (7-40 hex)

### 1.3 Body 必含 7 段 (verbatim · READY signal 强制 · `--strict-body` 启用)

1. **完成摘要** (≤ 50 字 · 该 agent ALL IN 完成什么)
2. **改的文件清单** (file path + LOC delta)
3. **测试 verify** (pytest 跑结果 / Playwright spec 跑结果 / type check 结果)
4. **红线自检** (10 条 stop-the-line 逐条 ✅)
5. **依赖合同** (entity-resolution / candidate-identity / signal-commit · 用了哪些)
6. **base dashboard 行更新** (lark-base record_id + 字段更新清单)
7. **证据** (Playwright 截图 url / 真测试日志 / 性能数据)

### 1.4 Signal 类型语义

| Signal | 语义 | Phase | Body 7 段强制 |
|---|---|---|---|
| `RESUMED` | worker resume 后第一条 commit · 表态等 GO | A/B/C | 否 (轻量) |
| `READY` | 完工 · 等主 CLI cherry-pick 入 main | A/B | 是 (`--strict-body`) |
| `BLOCKED` | 撞红线 / 撞 contract 缺口 · 等 PM 仲裁 | B | 否 (但必列违反条款 + 提 RFC link) |
| `HOTFIX` | 紧急修产线 / contract 漏洞 · 短路 cherry-pick | A/B/C | 否 |

## 2. 主 CLI cherry-pick 流程

per `scripts/mesh/cherry_pick_worker.py` 5 步:

### 2.1 步骤

1. **verify signal commit 格式** (调 verify_signal_commit.py · `--strict-body` for READY)
2. **DIFF guard**: agent worker 没改 `shared/` + `docs/contracts/` + `.mesh-launcher/` (per AGENT_IDENTITY 禁改域 · common worker 例外)
3. **cherry-pick worker code commits 入 main** (skip signal commit · 按 oldest-first 顺序)
4. 主 CLI 跑总验收 (pytest 全跑 + Playwright 该 agent spec)
5. 主 CLI 写 close-out commit · 部署 + 更 lark-base

### 2.2 命令

```bash
# 主 CLI 在主 worktree 运行
py scripts/mesh/cherry_pick_worker.py \
  --worker-branch feat/allin-report \
  --signal-sha <worker fire 的 signal commit sha> \
  --base-branch main \
  --strict-body
```

可选:
- `--dry-run` · 仅打 plan · 不真 cherry-pick
- `--skip-signal-verify` · 调试用 · 慎用 (跳格式校验)

### 2.3 close-out commit (主 CLI 写 · 本脚本不写)

```
chore(mesh): WORKER-<AGENT>-CHERRY-PICK-MERGED · ALLIN

Cherry-picked <N> commits from feat/allin-<agent>:
  <commit list>

Verification:
- pytest: <result>
- Playwright (<agent> spec): <result>
- tsc: <result>

Worker: <agent>
Phase: B
Refs: ALLIN-2026-05-08
Signal: MERGED
Root: <main HEAD pre-merge>
```

### 2.4 部署 (per CLAUDE.md §13.1 改完即部署)

cherry-pick 完成后 · 主 CLI 立即:
```bash
bash scripts/deploy_to_ecs.sh
```

## 3. Risk Signal (4 类 · 复用 Q-054)

| # | 风险 | 阻断 signal | 主 CLI 行动 |
|---|---|---|---|
| 1 | 改了禁改域 (e.g. agent worker 改 shared/) | `Signal: BLOCKED` + 列违规文件 | DIFF guard 自动拦 · revert 该 commit |
| 2 | 测试不通过 (pytest fail) | `Signal: BLOCKED` + 列 fail case | 不 cherry-pick · 推回 worker |
| 3 | 红线触发 (任一 stop-the-line) | `Signal: BLOCKED` + 列违反条 | PM 介入仲裁 |
| 4 | 依赖合同缺口 | `Signal: BLOCKED` + 提 RFC | common worker 接 RFC · 改合同 |

## 4. Git hook 接入 (worker worktree 推荐)

worker worktree 启用 commit-msg hook · 防 typo:

```bash
# 在 worker worktree 内
cp scripts/mesh/verify_signal_commit.py .git/hooks/commit-msg
chmod +x .git/hooks/commit-msg
```

hook 逻辑:
- 普通 commit (非 signal) · 直接通过
- 看起来 signal 但 typo (含 "signal worker" + "mesh" 但不严格匹配) · BLOCK
- 严格 signal commit · 验 5 trailer · BLOCK 缺项

`commit-msg` hook 是 client-side · 主 CLI 不依赖 (cherry-pick 入口仍 verify).

## 5. 主 CLI 验收日志

主 CLI 在 cherry-pick 后写一个验收日志条目到 `docs/handoff/decisions-log.md`:

```markdown
## Q-NNN · ALLIN Phase B · <agent> cherry-pick 完成 · YYYY-MM-DD

### 摘要
- worker: <agent>
- signal sha: <sha>
- cherry-picked commits: N
- DIFF guard: PASS
- 总验收: pytest <result> · Playwright <result> · tsc 0 error

### 时间戳
- worker fire READY: HH:MM
- 主 CLI cherry-pick 启动: HH:MM
- cherry-pick 完成: HH:MM
- 部署 ECS 完成: HH:MM
- ROI: <计算 worker 派出到 ECS live 的 wall-clock>
```

## 6. ABI 稳定性承诺

Phase A 冻结后 · 以下 contract 不许 break (Phase B 5 worker 依赖):

- Subject 模板 verbatim
- 5 trailer 名 + 白名单
- 7 段 body keyword (中文 verbatim · 不许翻译)
- `verify_signal_commit.verify(msg, *, strict_body)` 函数签名
- `cherry_pick_worker.py` CLI 参数 (`--worker-branch` / `--signal-sha` / `--base-branch` / `--strict-body` / `--dry-run`)
- 退出码语义 (0 通过 / 1 不合格 / 2 git 错误)

## 7. 单测覆盖 (16 cases · 5 类)

per `tests/shared/test_signal_commit_verify.py`:

| 类 | 测试数 | 覆盖 |
|---|---|---|
| TestIsSignalCommit | 3 | signal vs 普通 vs typo |
| TestVerifyReady | 4 | 完整 READY · BLOCKED · 非 signal skip |
| TestSubjectViolations | 2 | typo subject + 黑名单 agent |
| TestTrailerViolations | 5 | 缺 trailer · phase / signal / refs / sha 错值 |
| TestStrictBody | 2 | strict 启用 · 7 段缺漏 |

跑通: `py -m pytest tests/shared/test_signal_commit_verify.py -v` → 16 passed.

## 8. 红线 (跨 Phase · 任一触发即 stop-the-line)

1. **worker 跳过 verify** 直 push signal commit · 主 CLI cherry-pick 时验 · 不合格立刻 reject + 推回
2. **DIFF guard 失败** (agent worker 改了 shared/) · 立刻 abort cherry-pick · revert 违规 commit · stop-the-line
3. **typo signal subject** (e.g. "signal worker report ready" 缺 ALLIN) · 启发式拦 · 不允许进 main

## 9. 待 Phase B 接入

- [ ] 5 agent worker worktree 安装 commit-msg hook (各自 resume 后)
- [ ] 主 CLI cherry-pick 流程跑通一次 (Phase B 第一个 worker fire READY 时验)
- [ ] decisions-log Q-NNN 模板按 §5 (主 CLI 自跑)
- [ ] lark-base dashboard `latest_signal` 字段自动写 (主 CLI cherry-pick 时调 lark-cli base record-update · 待 Phase A 第 4 件交付物)
