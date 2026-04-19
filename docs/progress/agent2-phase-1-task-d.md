# Agent2 Phase 1 · Task D · 规则编辑器 ReadOnly 入口

**日期**：2026-04-19
**worktree**：`D:\claude code\demo-agent2` (`feat/agent2-productize`)
**onboarding 锚点**：`docs/onboarding/agent2-phase-1.md` §3 Task D（D-frontend 方案）

---

## 目标与闭环

Phase 0 页面 `web/src/app/riskctrl/page.tsx` 已有回测场景骨架（基线 / 候选 / 样本池 / DSL diff / 命中率）—— 缺"当前 ruleset 结构化只读视图"。Task D 插入 ReadOnly 子区：

- 规则表格列 rule_id / 名称 / 条件（AND 合并） / 动作（中文） / 优先级
- 规则描述 markdown 可折叠
- 「导出 JSON」按钮 → 下载合法 ruleset JSON
- 「进入编辑器」按钮 disabled + tooltip `Phase 2 交付`
- 数据来自 `/mock/riskctrl_ruleset.json`，schema 对齐后端 rules.json（Phase 2 切真 API）

---

## 交付物

### 1. 新建文件

| 文件 | 作用 |
|---|---|
| `web/public/mock/riskctrl_ruleset.json` | 5 规则示例 ruleset（schema 对齐 baseline_v1/rules.json + Phase 1 Task C 的 `{FP, TN, FP_rate}`） |
| `web/src/components/riskctrl/RuleReadOnlyList.tsx` | ReadOnly 表格 + 可折叠描述；Canvas 主题 / `--r-md: 18px` / JetBrains Mono |
| `docs/progress/agent2-phase-1-task-d.md` | 本文件 |

### 2. 修改文件

| 文件 | 变更 |
|---|---|
| `web/src/app/riskctrl/page.tsx` | 追加「规则详情」Card 子区（header 右挂 `导出 JSON` + disabled `进入编辑器`）；`useEffect` 拉 mock；`exportRuleset` 用 Blob URL 触发下载 |

### 3. 红区 clean

- `api_server.py` 未改（0 line diff）
- `agent_riskctrl/` 后端代码未改（本次仅 web/ 子树）
- 其他 5 个 agent 路由（`/credit` `/channel` `/alert` `/compliance` `/report`）文件未触
- 未新增 `/api/riskctrl/*` 路由（Phase 2 接真 API 时落）

---

## 样式纪律对齐

| 纪律项 | 落地 |
|---|---|
| `data-theme=Canvas`（默认主题） | 组件全部用 `var(--color-*)` token，主题切换自动跟随 |
| `border-radius: var(--r-md)` (18px) | 表头容器 + 动作标签 `style={{borderRadius:"var(--r-md)"}}` 显式统一 |
| 数字字段用 JetBrains Mono | rule_id / 优先级 / 条件表达式 / source line 使用 `font-tabular`（tokens 里映射到 JetBrains Mono） |
| 不自造新主题 / 新圆角 | 零新增 CSS token / 新类名 |

---

## DoD 逐条对账（commit 前实测）

- [x] `cd web && pnpm tsc --noEmit` → exit 0（零错误）
- [x] `pnpm dev` 起成 → `curl --noproxy '*' http://localhost:3001/riskctrl` HTTP 200（本地 3000 被占，dev 自动切到 3001）
- [x] `curl http://localhost:3001/mock/riskctrl_ruleset.json` HTTP 200 + 5 rules 校验
- [x] SSR 输出含新字符串：`规则详情` / `RULESET · READ ONLY` / `导出 JSON` / `进入编辑器`
- [x] 「导出 JSON」onClick → Blob URL + `<a download>`，下载 JSON schema 对齐 rules.json（description / version / ruleset.description / ruleset.rules[*].{rule_id, name, description, conditions, action, priority, backtest}）
- [x] 「进入编辑器」 `<Button disabled>` + 外层 `<span title="Phase 2 交付：…">` tooltip
- [x] `git diff api_server.py` 空；`agent_riskctrl/api/` 目录不存在（后端未加 API 路由）
- [x] `git diff` 仅 `web/` 子树（`page.tsx` 改 + `components/riskctrl/` + `public/mock/` 新增）
- [x] 未引入 shadcn / Radix（platform-shell-v1 §5.4 红区）
- [x] A-012.D / A-012.E 对齐（仅新增 / 黄区改，无 rebase / amend / force）

---

## 实装要点

### 1. Fetch mock + 状态容器

```tsx
const [readOnlyDoc, setReadOnlyDoc] = useState<...>(null);
useEffect(() => {
  fetch("/mock/riskctrl_ruleset.json")
    .then(r => r.ok ? r.json() : null)
    .then(setReadOnlyDoc);
}, []);
```

Phase 2 切真 API 时只换 URL（`/api/riskctrl/ruleset`），state shape / 下游组件不动。

### 2. Export JSON（Blob URL）

```tsx
const blob = new Blob([JSON.stringify(readOnlyDoc, null, 2)], {type:"application/json"});
const url = URL.createObjectURL(blob);
// <a href={url} download={filename}.click()
URL.revokeObjectURL(url);
```

文件名带日期戳：`riskctrl_ruleset_2026-04-19.json`。

### 3. disabled "进入编辑器"

外层 `<span title="...">` 提供 tooltip（因为 disabled Button 不触发 hover 事件）：

```tsx
<span title="Phase 2 交付：DSL 可视化编辑 + 条件推断 + 实时校验">
  <Button variant="ghost" size="sm" disabled>
    <Lock size={12} /> 进入编辑器
  </Button>
</span>
```

### 4. ReadOnly 组件 action tone 映射

```ts
const ACTION_LABEL  = { approve: "通过", reject: "拒绝", manual_review: "人工复核" };
const ACTION_TONE   = { approve: "text-sage border-sage",  reject: "text-ember border-ember", manual_review: "text-brass border-brass" };
```

直接复用 Canvas 主题已有 `--color-sage` / `--color-ember` / `--color-brass`，零新 token。

---

## Phase 2 交接点

- `/mock/riskctrl_ruleset.json` → 真 `/api/riskctrl/ruleset` GET 端点（Stage 3 Agent 迁入 `/archive/[agent]` 时一起迁）
- `进入编辑器` → 新路由 `/archive/riskctrl/editor` 或模态化编辑器组件；改 `disabled={false}` + 加 router 跳转
- `RuleReadOnlyList` 扩 `onConditionEdit` / `onActionChange` → 演化为 ReadWrite
- export JSON 格式保持不变（downstream 审计 / 审批流会消费同 schema）

---

## Signal

本 commit trailer `Signal: AGENT2-PHASE-1-TASK-D-DONE`。Task D 是 Phase 1 最后一个 Task —— commit 后 **idle 等主 CLI GO READY-FOR-REVIEW**，不自动发 READY。
