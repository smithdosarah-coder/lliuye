# Reset Master Plan · 全新出发 长周期工程

> **每个新 main CLI / compression 后必读** · 本文件是 reset 工程的唯一 umbrella 索引。
> 启于 2026-04-29 · PM 刘野 · orchestrator 主 CLI

---

## 0. 一句话定位

产品在 6 Agent POC 落地后 (2026-04-19) 进入 "走歪了" 修正期 · PM 决议把 6 单页 showroom 收敛到 1 个 RM workbench (Cursor 模式) · 同步把架构 / 命名 / mock / 设计 / LLM 工具 / 6 Agent 闭环 全部 reset。

**目标**: Phase A 完 + Phase B 完 = 产品全新出发 · 可拿出去给客户卖。

---

## 1. 北极星 = RM Workbench

**核心反思**: 当前形态是 6 个互不相干的 showroom 页 · 应该是**一个客户经理工作台 + 6 Agent 是工作台内可调用的能力矩阵** (= Cursor 模式)。

详见 `docs/reset/north-star.md`。

---

## 2. 三步执行框架

```
Step 2 · 架构审视 + 找冲突 (1-2 工作日)
   ↓ PM 拍板 conflict register
Step 1 · 清+唯一化 (Phase A · 4-6 周)
   ↓ Phase A 验收硬线全过
Step 3 · PRD + 商业化 (Phase B · 4-6 周 · 与 Step 1 后期并行)
```

每 step 内: Round 1 双 AI 独立 v1 → Round 2 互评 v2 → Round 3 (optional · 仅 dissent 项) → PM 拍板 → 执行。

---

## 3. 文档地图

| 用途 | 文档 |
|---|---|
| **产品 north star + 走歪诊断 + 修正方向** | `docs/reset/north-star.md` |
| **Phase A 7 worker 拆分 + 验收硬线** | `docs/reset/phase-a-charter.md` |
| **Phase B 2 worker 拆分** | `docs/reset/phase-b-charter.md` |
| **Codex 4 插入点 + 命令 + template** | `docs/reset/codex-mesh-protocol.md` |
| **当前状态 (已完 / 在跑 / 待启)** | `docs/reset/state-snapshot.md` |
| **anti-bias 4 硬规** | `docs/reset/anti-bias-rules.md` |
| **最新 handoff (PM 已拍板事项 + dissent)** | `docs/handoff/HANDOFF_TO_NEXT_MAIN_CLI_<latest>.md` |
| **mesh 工作机制 (worker / signal / scoreboard)** | `~/.claude/skills/multi-cli-mesh/SKILL.md` |
| **决策实时 log** | `docs/handoff/decisions-log.md` |
| **feature inventory** | `docs/features-inventory.md` |
| **6 Agent 契约** | `docs/contracts/*.md` |

---

## 4. PM 已拍板事项 (2026-04-29)

1. **杜绝拖死机制 4 条** (强制 schema / ≤ 3500 词 / 单 issue 最多 2 round 辩论 / dissent 反增即 escalate PM)
2. **Phase A/B 严切阶段** (Phase A = reset 验收硬线 · Phase B = 持续推进)
3. **active decision 必须回写 root CLAUDE.md** (谁改决策谁回写 · 不回写不算 done · CI lint enforce)
4. **命名 SSOT 词典 8 列** (agent_id / 中文 / 业务名 / UI brand / route / 色彩 token / RBAC role / eval baseline)
5. **Step 3 PRD 取证 Step 2 进行中并行启动** (激进派 · 不等 Step 2 完)

---

## 5. Reset 工程当前阶段 (随时更新)

**当前**: Step 2 conflict scan 进行中 · 4/5 sub-agent 已收 · 待整合 + Codex Round 1 + 第 5 sub-agent + PRD 取证。

**下一步**: 整合 conflict register v1 → PM 拍板 → 启 Phase A worker mesh + Codex 4 插入点工具化。

详见 `docs/reset/state-snapshot.md` (auth log)。

---

## 6. 红线 (违反即 stop the line)

- ❌ 不读本文档 + tier-1 reset docs · 直接做决策
- ❌ 任何 worker / Codex 调用未 commit signal trailer
- ❌ active decision 改了不回写 CLAUDE.md
- ❌ Phase A 验收硬线缺一项就宣称"reset 完"
- ❌ 长 LLM 输出压短输出 (anti-bias 字数硬上限)
- ❌ Codex 跨 worktree 读 / 直接 push commit (它仅产 audit doc)
- ❌ compression 后凭模糊印象做决策 (按本文 §5 恢复协议)
- ❌ **任何迭代未同步更新 `docs/reset/state-snapshot.md`** (PM 2026-04-29 硬规 · 详 CLAUDE.md §14.1)

---

**Author**: 刘野 + Claude (orchestrator) · 2026-04-29
**Compatible**: 所有 main CLI / Codex / mesh worker
