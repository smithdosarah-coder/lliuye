# 5 Demo 产品化 · 全局看板 (GLOBAL)

**更新日期**：2026-04-19（Phase 2 Batch 1 review 后）
**维护人**：主 CLI（唯一可写，子 CLI 只读）
**DoD 引用**：`docs/scorecard/definition-of-done.md` v1.0
**Mesh 状态看板**：`py C:/Users/Mr.S/.claude/skills/multi-cli-mesh/scripts/mesh_status.py`

---

## 一、战略目标

把 Agent1/2/3/4/5 五个 demo 做到 Agent6 报告助手的完整度——**能直接拿出去卖**。

对齐 DoD v1.0 的 L1 + L2 + L3 全部通过视为"可卖"；L0 是最低起跑线；L4 按客户定制。

**对标 benchmark**（2025 国内 SOTA）：
- Agent6 自动化率 vs **金融壹账通 Smart Lender 80%**（Agent6 当前 93.5%，已超）
- Agent3 评分准确率 vs **金融壹账通 Gamma 95%**
- Agent4 误报率 vs **同盾诸葛 -45%** 优化后基线
- Agent1 召回效率 vs **百融 CybotStar 950+ 银行客户规模**

---

## 二、当前完整度矩阵（2026-04-19 快照）

| Agent | Phase | L0 | L1 | L2 | L3 | 综合 | 最后裁决 |
|---|---|---|---|---|---|---|---|
| 6 报告 | v16 maintenance | ✅ | ✅ | 🟡 缺审计日志 | ✅ Phase A adapter | **95%** | `WINDOW-CLOSED-CLEAN` |
| 3 授信 | Phase 2 Batch 1 APPROVED | ✅ | ✅ handoff+docx+雷达 | ✅ 原因码+severity | ✅ 基线 PASS + Phase B adapter | **90%** | `PHASE-2-APPROVED` |
| 1 获客 | Phase 2 Batch 1 CONDITIONAL | ✅ | ✅ handoff contract | 🟡 sampling CSV | 🟡 adapter 挂 registry 待 rebase | **78%** | `CONDITIONAL-APPROVE` |
| 2 风控 | 未启 | 🟡 | ❌ 缺规则编辑器 + 图表 | 🟡 缺审计 | ❌ 基线未跑 | **55%** | 排队 |
| 4 预警 | 未启 | 🟡 | ❌ 缺仪表盘 + 导出 | 🟡 缺原因码 | ❌ 基线未跑 | **50%** | 排队 |
| 5 合规 | 未启 | 🟡 | ❌ 前端需重做 | 🟡 缺条款溯源 UI | ❌ 基线未跑 | **40%** | 排队 |

**图例**：✅ 全通 / 🟡 部分通 / ❌ 未通

---

## 三、推进顺序（按投产价值排）

```
Phase 0 (本周)
└─ Agent6 收尾 → 审计日志 + 模型卡片 + 反馈飞轮接通

Phase 1 (下周起，2 子 CLI 并行)
├─ Agent3 授信 productize（最大价值，对标 Gamma）
└─ Agent1 获客 productize（次大价值，对标 CybotStar）

Phase 2
├─ Agent4 预警 productize
└─ Agent2 风控 productize

Phase 3
└─ Agent5 合规 productize（最单薄，需要最多时间）
```

**不并行 5 个 CLI 的理由**：
- 主 CLI review 带宽有限（每个 review 需要起服务 + 亲跑 + 对 DoD 逐条打分，约 30-60 min）
- Agent5 依赖其他 agent 的共享底座稳定，最后做
- 信创 / 私有化 / 合作机构备案等 L4 条目统一在 Phase 3 末补齐

---

## 四、worktree 布局

```bash
# 已建 worktree（一次性）
git worktree add ../demo-agent3 -b feat/agent3-productize
git worktree add ../demo-agent1 -b feat/agent1-productize
git worktree add ../demo-agent4 -b feat/agent4-productize
git worktree add ../demo-agent2 -b feat/agent2-productize
git worktree add ../demo-agent5 -b feat/agent5-productize
```

| worktree | 分支 | 负责 agent | 状态 |
|---|---|---|---|
| `../demo-agent3` | `feat/agent3-productize` | Agent3 授信 | 待启动 |
| `../demo-agent1` | `feat/agent1-productize` | Agent1 获客 | 待启动 |
| `../demo-agent4` | `feat/agent4-productize` | Agent4 预警 | 排队 |
| `../demo-agent2` | `feat/agent2-productize` | Agent2 风控 | 排队 |
| `../demo-agent5` | `feat/agent5-productize` | Agent5 合规 | 排队 |

**主 CLI** 留在 `D:\claude code\credit_report_agent_work\`（main 分支）— 不写代码，只审。

---

## 五、当前焦点（Phase 2 · 2026-04-19 起）

**已完成**：Agent6 v16 Phase 1 收尾 + Agent3 Phase 1 APPROVED + Agent3 Phase 2 Batch 1 APPROVED + Agent1 Phase 2 Batch 1 CONDITIONAL-APPROVE

**在途**：
- Agent1 Option 2 rebase 修复（等 worker 重开窗口）
- `chore/agent3-lint-cleanup` fast-forward merge 进 `chore/l0-infra`

**下一批（未下发）**：
- Agent2 / Agent4 / Agent5 Phase 1 启动评估
- Agent1 Option 1 解封等 Tavily 生产 key + 合规批文

---

## 五·旧、本周焦点（Phase 0 · 已归档 2026-04-17~04-18）

### Agent6 收尾 TODO

| 条目 | DoD 映射 | 状态 |
|---|---|---|
| 审计日志接通（session_store → `data/audit/*.jsonl`） | L2-12 | ❌ |
| 合作机构清单文档化 | L2-13 | ❌ |
| 数据分级文档 | L2-14 | ❌ |
| 模型卡片 `docs/model_cards/agent6.md` | L3-11 | ❌ |
| 演示脚本 `docs/demo_script/agent6.md` | L3-12 | ❌ |
| 反馈飞轮 `/api/feedback` E2E 验证（`data/feedback/` 当前空） | L3-8 | ❌ |

---

## 六、下周预启动 · Agent3 productize 路线

**对标**：金融壹账通 Gamma 加马平台（股份行 100% 渗透）
**核心差异点**：我们做 copilot，Gamma 做 autopilot（监管红线）

### Agent3 Phase 1 任务（待子 CLI 认领）

1. **接通 Agent6 handoff 入口**：UI 加"从报告助手加载企业画像"按钮（L1-11）
2. **四维风险雷达图**：财务 / 行业 / 经营 / 担保（L1-3）
3. **标准拒贷原因码字典**：
   - `docs/reason_codes/agent3-corporate.yaml`（对公）
   - `docs/reason_codes/agent3-retail.yaml`（对私）
   - 每个分数 / 决策输出 Top-5（L2-7 / L2-8）
4. **决策意见书 docx 导出**（L1-4 / L2-15 在本地 docx 生成，不走境外 API）
5. **评估基线首跑**：`evaluation/agent3_credit.yaml` → `evaluation/results/3_YYYYMMDD.yaml`（L3-1 / L3-2）

---

## 七、主 CLI 每日动作清单

每天早 / 中 / 晚各一次（≤ 15 分钟）：

```bash
# 1. 拉所有 worktree 最新
cd ../demo-agent3 && git fetch && git log --oneline -10
cd ../demo-agent1 && git fetch && git log --oneline -10
# ...

# 2. 读所有进度文档更新
ls docs/progress/*.md | xargs ls -lt | head -5

# 3. 触发 review 的信号：子 CLI 写了新 docs/progress/*-phase-*.md
# 看到 → 进入 review 流程（见 DoD §9）

# 4. 更新本 GLOBAL.md 的完整度矩阵
```

---

## 八、Review 排队（按 FIFO）

| 提交时间 | agent | phase | 进度文档 | 状态 |
|---|---|---|---|---|
| - | - | - | - | 无待 review |

---

## 九、历史 review 归档

路径：`docs/review/{agent}-phase-{N}-review.md`
命名规范：时间倒序，主 CLI 写完立刻在此处登记。

| 日期 | agent | phase | verdict | reviewer |
|---|---|---|---|---|
| 2026-04-19 | 3 授信 | Phase 2 Batch 1 | APPROVED | 主 CLI |
| 2026-04-19 | 1 获客 | Phase 2 Batch 1 | CONDITIONAL-APPROVE | 主 CLI |
| 2026-04-19 | 3 授信 | Phase 1 | APPROVED (A-004) | 主 CLI |
| 2026-04-18 | 6 报告 | v16 Phase 1 | APPROVED (A-001~003) | 主 CLI |

---

## 十、应急联系

- 触发红线（见 DoD §10）→ 所有子 CLI 停工 → 主 CLI 调查 → 复盘文档 → 写入 memory
- 主 CLI 如不可用 → 子 CLI 自检 DoD L0 + L1 + L2 并冻结代码 → 等待
- 监管风向变化 → 主 CLI 触发 DoD 复核 → 版本升级

---

**更新本文档的责任人**：主 CLI（仅）
**更新触发**：
1. 子 CLI 进入 / 离开 phase
2. review 完成
3. DoD 版本升级
4. 新增 red line 事件
