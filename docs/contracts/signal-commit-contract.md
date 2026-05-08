# Worker Signal Commit Contract v1.0 · 2026-05-08

> **状态**: outline · 基于现有 Q-054 mesh 派活 protocol (R3v2 P0 实战 validated)
> **Owner**: common worker
> **目的**: ALL IN Phase B · 5 agent worker 完成时 fire 统一格式 signal commit · 主 CLI cherry-pick 自动整合

---

## 1. Signal Commit 格式 (硬规)

**Subject** (verbatim 模板):
```
chore(mesh): signal worker <agent> ready for mesh merge ALLIN
```

`<agent>` ∈ {report, credit, alert, riskctrl, compliance}

**Body 必含 5 trailer**:
```
Worker: <agent>
Phase: B
Refs: ALLIN-2026-05-08
Signal: READY|BLOCKED|HOTFIX
Root: <Phase A common 冻结 commit hash>
```

## 2. Body 必含 7 段 (verbatim)

1. **完成摘要** (≤ 50 字 · 该 agent ALL IN 完成什么)
2. **改的文件清单** (file path + LOC delta)
3. **测试 verify** (pytest 跑结果 / Playwright spec 跑结果 / type check 结果)
4. **红线自检** (10 条 stop-the-line 逐条 ✅)
5. **依赖合同** (entity-resolution / candidate-identity / signal-commit · 用了哪些)
6. **base dashboard 行更新** (lark-base record_id + 字段更新清单)
7. **证据** (Playwright 截图 url / 真测试日志 / 性能数据)

## 3. 主 CLI cherry-pick 流程

1. 收到 worker signal commit (用 `git -C <worker_worktree> log -1` verify trailer)
2. DIFF guard: 检查 worker 没改 `shared/` (per AGENT_IDENTITY 禁改域)
3. cherry-pick worker 的所有 code commit 入 main (skip signal commit)
4. 跑总验收 (pytest 全跑 + Playwright 该 agent spec)
5. push origin main → ECS deploy (改完即部署 per CLAUDE.md §13.1)
6. 写 close-out commit `chore(mesh): WORKER-<AGENT>-CHERRY-PICK-MERGED · ALLIN`
7. 更新 lark-base dashboard 该 agent 行 `status: merged`

## 4. Risk Signal (Q-054 4 类 · 复用)

| # | 风险 | 阻断 signal |
|---|---|---|
| 1 | 改了禁改域 (e.g. shared/) | `Signal: BLOCKED` + 列违规文件 |
| 2 | 测试不通过 (pytest fail) | `Signal: BLOCKED` + 列 fail case |
| 3 | 红线触发 (任一 stop-the-line) | `Signal: BLOCKED` + 列违反条 |
| 4 | 依赖合同缺口 | `Signal: BLOCKED` + 提 RFC · 不本地绕开 |

## 5. 待 Phase A common worker 补完

- [ ] git hook (commit-msg) 验 signal commit 格式
- [ ] 主 CLI 自动 cherry-pick 脚本 (per agent)
- [ ] base dashboard 行更新自动化 (worker fire signal 后自动调 lark-base API)
- [ ] DIFF guard contract test (verify 没改 shared/)
