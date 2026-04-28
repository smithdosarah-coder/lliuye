# Empty-State Design Protocol v1.0

> 6 Agent Workspace 统一**空白启动规范** · production-grade trust model 必经设计。
> 适用 Channel + Report + Credit + Alert + Compli + Forge 全部 archive workspace。
> 任何 frontend 派活前必读 + 在 onboarding §Acceptance 中 cross-reference 本规范。

## 1. 为什么要空白启动（产品 reasoning · 必读）

### 1.1 信任（Banking P0）
银行用户对"假数据"零容忍。进页面看到 "5000 万营收 SaaS B 轮 · 98% 匹配" →
用户第一反应:**"这哪来的? 我没输入啊?"** 数据真实性怀疑 1 秒 · 整个产品信任崩塌。
合规上银保监不容许"误导性 UI"（看起来像真实数据但是 mock）。

### 1.2 数据归属 = 法律责任
用户主动上传 → 数据归用户（user-driven · 责任清晰）。
系统预填 → 数据来源不明（system-driven · 责任模糊）。
银行场景 · 谁的数据谁负责。AI 辅助 ≠ AI 替代。

### 1.3 反 5 原则 §3.5 environment boundary
原则字面: "mock 给 Agent 稳态内部 context · 不替它做本该外搜的工作"。
空白启动 = 让用户做"触发"这件本该用户做的事。
预填 = 越俎代庖 · 替用户决定了 query。

### 1.4 AI Trust Model · Show Its Work
AI 必须**展示工作**: 用户输入 → 看 LLM 怎么想 → 看 SSE 流式 → 看证据 → 看结论。
跳过这流程 = 看结论但不知 reasoning · 信任不起来。

### 1.5 Demo vs Production 路径必须**显式分开**
- Production: 空白 → 上传 → 真扫描 → 真结果
- Demo（内部 showcase / 走访）: dropdown "示例 session" 显式标 demo → 加载 mock
- **两条路径不能用同一 UI 入口 · 不能默认加载 mock**

## 2. 空白态视觉构成（5 件具体 · 不是 nothing）

### 2.1 场景 Hero
- 一句话 problem statement（不是 marketing fluff）
- 例: Channel: `全渠道获客助手 · 找相似企业 + 推产品 + 生话术`
- 例: Report: `信贷报告生成 · 上传客户材料 + AI 辅助起草 + 一键 Word 导出`
- 字号 20-24px · 字重 medium

### 2.2 主 CTA · 3 入口分级（primary / secondary / tertiary）
- **Primary 显著**: 用户最该走的路径（上传 KB / 上传材料 / 输入策略）
- **Secondary 次要**: 轻量启动（自由查询 / 选模板）
- **Tertiary 降级**: 历史 / 示例 / demo（字号小 · 灰色 · 标 `(示例)` tag）

### 2.3 Panel 区 · 空骨架（placeholder · **不是真数据**）
- 灰底（`--g0b` 50% 透明度）
- 1 行说明文字: `扫描完成后此处显示 X` / `候选企业出现在这里`
- **不显示任何模拟数字 / 假候选 / 假信号 / 假 radar**
- 高度 = 真实数据渲染后高度（避免 CLS layout shift）

### 2.4 状态透明 · 右下 status pill
- 服务健康: 🟢 服务正常 / 🟡 LLM 缓慢 / 🔴 后端故障
- LLM 预算: `余 500 / 1000 调用`（透明 · 让用户知 cost）
- 历史: `上次扫描: 2 天前 王哲 (可恢复)`（continuity）

### 2.5 Demo 显式标记
mock 数据出现位置必含:
- `(demo)` / `示例` 字样 · 字号小 · 灰色降级
- dropdown title: `历史会话（示例 · 仅培训演示）`
- 进入 mock session 后 banner:
  `⚠️ 您正在查看示例数据 · 切真实输入 → [按钮]`

## 3. 状态机 · `started` 默认 false

```typescript
const [started, setStarted] = useState(false);  // 默认 false · 不可改

// 只在以下 trigger 设 true:
// 1. user 上传 KB / 材料 (primary CTA · B.6 类)
// 2. user submit textbox query (secondary)
// 3. user 点 dropdown "示例 session" (tertiary · 显式标 demo)

// !started 时:
//  - 渲染 Hero + 3 CTA + Panel 空骨架 + status pill
//  - DO NOT render mock candidates / radar / signals
//  - DO NOT 自动 trigger LLM call
//  - DO NOT 自动 fetch /api/<agent>/run
```

## 4. Mock data 约束

- `mock_sessions.ts` / `mock_data.ts` **不 default load** · 仅在 user 主动选 dropdown 触发
- mock data 在 dropdown title 必含 `(示例)` tag
- mock data 显示时 panel 顶部 banner: `示例数据 (training mode)`
- production 用户**不应**默认看到 mock data
- mock 数据本身仍遵守反 5 原则（脱敏 / 难度分层 / 真实来源锚定）

## 5. Acceptance Gate（每 Workspace 必跑 · CI 阻断）

- [ ] 进入 `/archive/<agent>` default 渲染:
  - Hero + 3 CTA + Panel 空骨架 + status pill
  - **DO NOT 含模拟候选 / 数字 / radar / signals**
- [ ] 用户上传 KB / 材料 → `setStarted(true)` → panel 真数据填充
- [ ] dropdown "示例" 显式标 `(demo)` tag · 字号小 · 灰色
- [ ] 选 "示例" → banner 显示 `示例数据 (training)` · 真实路径切回 button visible
- [ ] tsc 0 error
- [ ] Playwright spec `<agent>-empty-state.spec.ts` 验:
  - default 状态无 mock data
  - dropdown demo 标记
  - 上传 trigger 改 started

## 6. 6 Agent Workspace 改造点

| Agent | route | empty-state 改造点 |
|---|---|---|
| Channel (Agent1) | `/archive/channel` | `started` default false · `MOCK_SESSIONS_MAP` 不 default load · dropdown 标 (示例) · 主 CTA = 上传 KB 3 dropzone |
| Report (Agent6) | `/archive/report` | 主 CTA = 上传材料 + 选模板 · secondary = 历史 session · v16 pipeline 用户触发后跑 |
| Credit (Agent3) | `/archive/credit` | 主 CTA = 选材料（来自 Agent6 handoff）+ 起决策 · secondary = 历史 |
| Alert (Agent4) | `/archive/alert` | 主 CTA = 启动扫描（KB 已加载即可）· panel 默认空 · 历史 secondary |
| Compli (Agent5) | `/archive/compli` | 主 CTA = 上传政策 / 启动巡检 · 业务矩阵 panel 默认空 |
| Forge (Agent2) | `/archive/riskctrl` | 主 CTA = 选样本 + 写策略 · DSL panel 默认空 · 回测 panel 默认空 |

## 7. Migration path

Stage C frontend 派活时, sub-agent / worker 必读本规范, 在 onboarding 中 cross-reference:

1. **Channel** (今天 sub-agent 部分实现) · 验 `started` default false · `mock_sessions` 改 dropdown
2. **5 Agent Workspace frontend 改造**时, onboarding §Acceptance 必含本规范 §5
3. 各 Workspace 加 `<agent>-empty-state.spec.ts` smoke

## 8. 与 anti-regression 协议关系

empty-state 设计是 user-facing feature · 必入 `docs/features-inventory.md`:
- F-046 Channel empty state（升级 F-005）
- F-047 Report empty state
- F-048 Credit empty state
- F-049 Alert empty state
- F-050 Compli empty state
- F-051 Forge empty state

trailer 必含 `PRESERVES: F-001~F-045` + `INVENTORY-ADDED: F-046~`...

## 9. 与 production grade 8 条关系

empty-state 是 8 production constraint 中的第 1+3 条具体落地:
- 第 1 条「空白启动」= 本规范 §2-§5
- 第 3 条「实功能 = 呈现」= 本规范 §3 状态机 + §4 Mock 约束

CLAUDE.md §3.5 反 5 原则 + 8 production constraint 升级时, 本规范作为
implementation reference。
