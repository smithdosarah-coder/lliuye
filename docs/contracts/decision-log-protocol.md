# Decision Log Protocol v1.0

**目的**：把"子 CLI 需要拍板 → 用户转发 paste → 主 CLI 回复 → 用户 paste 回去"的人肉消息总线，降成"文件系统消息总线 + 用户轻触发"。

**发布日期**：2026-04-18
**作者**：主 CLI
**配合文档**：`shared-change-protocol.md §八`（Commit Signal 约定）

---

## 1. 适用场景

子 CLI 遇到**需要主 CLI 拍板**的场景时使用。典型包括：

- 红/黄区改动的 RFC 审批
- 架构路径取舍（A/B/C 选项）
- 跨 Agent 接口协商
- DoD 边界调整
- 迁移 / rebase / revert 等破坏性决策

**不适用**：日常进度汇报（走 `Signal: READY-FOR-REVIEW` commit 尾巴，主 CLI 日常巡检 `git log --grep="Signal:"` 抓取）。

## 2. 文件结构

```
docs/
  contracts/
    decision-log-protocol.md    ← 本协议
  handoff/
    decisions-log.md            ← append-only 决策日志（唯一一份）
```

**为什么单一文件 + append-only**：
- 跨 Agent 一眼可查
- 历史决策永久可审计
- 不需跨目录跳转

## 3. 条目格式

### Q（Question）— 子 CLI 发起

```markdown
## [Q-NNN] YYYY-MM-DD HH:MM · <agent-tag> · <一句话标题>

**CLI**: credit | channel | report | shell | ppt | riskctrl | alert | compliance
**Priority**: P0 / P1 / P2
**Blocking**: yes / no（yes = 主 CLI 回复前我停工）
**Related**: <commit hash / RFC 路径 / 其他 Q-MMM>

### 选项
- **A** <描述>
- **B** <描述>
- **C** <描述>（可选）

### 推荐
<子 CLI 的推荐 + 理由>

### 上下文
<全量 diff / 触发样本 / 引用行号 — 越完整越好，主 CLI 不用追问>
```

### A（Answer）— 主 CLI 回复

```markdown
### [A-NNN] YYYY-MM-DD HH:MM · 主 CLI

**Decision**: A / B / C / 其他
**Rationale**: <理由，引用 CLAUDE.md 条目或协议段落>
**Follow-up**: <后续动作，如"补 RFC 路径 XXX"或"迁移 worktree"或无>
```

**紧邻 Q-NNN 之下**，不另起 section。

## 4. 工作流

### 4.1 子 CLI 流程

1. 写 `## [Q-NNN] ...` 到 `docs/handoff/decisions-log.md` 末尾
2. `git add docs/handoff/decisions-log.md`
3. `git commit -m "... 

   Signal: NEED-DECISION Q-NNN"`
4. 如果 `Blocking: yes` → 子 CLI 停工等主 CLI
5. 如果 `Blocking: no` → 子 CLI 继续做其他不冲突的任务

### 4.2 主 CLI 流程

用户切到主 CLI 说 `inbox` 或 `处理 Q-NNN`：

1. 主 CLI `git log --grep="NEED-DECISION" --since="48h ago"` 列未处理项
2. 逐个 `Read` Q 条目 → 做决策 → `Edit` 文件 append A-NNN
3. `git add` + commit：`"decision: Q-NNN → A | reason ..."`
4. 子 CLI 下次任意 commit 前 `git pull + Read decisions-log.md` 自取答案

### 4.3 人工触发词（最小化用户介入）

- `inbox` —— 列出所有未回复 Q 并逐个处理
- `处理 Q-NNN` —— 定向处理单个
- `inbox urgent` —— 只处理 P0

## 5. Q-NNN 编号规则

- 全局递增，跨 CLI 共享序列
- 由**发起 CLI** 自行分配：先 `git pull + Read decisions-log.md` 看最大 N → 自增
- 冲突检测：如果两个 Q-NNN 同时诞生（rebase 冲突），后 push 者 rename 为 Q-(N+1)

## 6. 与 Commit Signal 的关系

| 场景 | 走哪里 |
|---|---|
| 我做完一阶段要终审 | `Signal: READY-FOR-REVIEW` commit 尾巴，主 CLI 自取 |
| 我遇到真正拍板点 | `decisions-log.md` Q-NNN + `Signal: NEED-DECISION Q-NNN` commit 尾巴 |
| 我救了个火 | `Signal: RESCUE-COMMIT` commit 尾巴 + RFC 路径 |
| DoD 红线触发 | `Signal: RED-LINE-TRIGGERED` commit 尾巴（不 Q-NNN，直接停工等主 CLI 介入） |

## 7. 禁止事项

- 禁止把"进度汇报"写成 Q-NNN —— 走 Signal 尾巴
- 禁止删 / 改 / reorder 已发布的 Q 或 A —— append-only
- 禁止跨 Q 合并答案（"A-NNN: 见 A-MMM"）—— 每个 Q 独立决策

## 8. 演进

- 子 CLI 可发 Q-NNN 提议改进本协议（类型标为 `meta`）
- 如果 log 超过 200 条，主 CLI 会做一次归档（move 到 `decisions-log.archive-YYYY-MM.md`），保留最近 50 条在主文件
