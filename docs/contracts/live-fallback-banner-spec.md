# Live-Fallback Banner Spec v1.0

> 6 Agent Workspace 的 **live mode 失败处理规范** · production trust model 必修。
> 用户必须知道当前看到的是真后端数据还是 fallback 演示。
> 适用 Channel/Report/Credit/Alert/Compli/Riskctrl 全部 archive workspace +
> dispatch IM。

## 1. 为什么必须 banner（trust model）

empty-state-design-protocol v1.0 §1.5 已钉死: production / demo 路径**必须显式分开**。
worker 实装时常加 "live failed → silent mock fallback" · 用户分不清真假 →
banking 信任崩塌（user 怒"左右脑互博"）。

## 2. 4 条硬规则（CI 阻断 / review 必查）

### 规则 1 · live mode 调用失败 → 显式 banner

frontend call backend (e.g., `/api/<agent>/run` SSE / `/api/<agent>/decision` /
etc.)·任何 4xx / 5xx / network error / SSE 异常断流 →
**顶部 banner**:

```
⚠️ 后端 <endpoint> 调用失败 (<status_code>) · 当前显 fallback 演示数据 · [重试]
```

不允许静默 swap mock + 假装成功。

### 规则 2 · mock dropdown 触发 → 显式 banner

empty-state-design-protocol §2.5 已规定 · 复述:
- mock dropdown title 必 `(示例)` 灰色降级
- 选 mock session → 顶部 banner `示例数据 (training mode) · 切真实输入 → [按钮]`

### 规则 3 · 摆设 button 必须 wire（zero placeholder）

任何可见 button / input / dropdown · onClick / onSubmit 必有真后端 call
（或显式 disabled with tooltip 解释 "Stage X 计划")。
**禁止 placeholder UI · 没 wire 不上线**。

### 规则 4 · F-008 pin_ref kind 严格 thumbnail

dispatch IM 拖柄到 composer · `kind="pin_ref"` 渲染**必须** thumbnail card
(图标 + agent_id + title 摘要)。**禁止 fallback url 链接**。
判断逻辑:
- `message.kind === "pin_ref"` AND `message.refs?.thumbDataUrl` → 渲染 thumbnail
- 否则: error log + UI 显 "拖拽 ref 失败" 而非 url

## 3. UI 排版硬线（review 阻断）

- mock-banner align: 跟其他 banner / hero text 同 padding / margin · 不溢出
- "主 CTA" button 不允许 width >= 50% panel · 也不允许 width < 120px
- "上传 / 选择" button 必有 file input wire · onClick 真触发选文件
- 6 Agent Workspace empty-state CTA 视觉规范统一 (见 channel-workspace.css 模板)

## 4. Acceptance Gate (per Workspace · CI 必跑)

- [ ] live failed (mock 502/503 backend) → banner 显
- [ ] mock dropdown 选 → banner "示例 (training)" 显
- [ ] 0 摆设 button (每 button 验真触发 endpoint or 显式 disabled)
- [ ] pin_ref kind smoke (拖柄 → thumbnail · 不显 url)
- [ ] css align review (banner + button width 符合 §3)

## 5. 6 Workspace + IM 改造点

| Module | 改造 |
|---|---|
| Channel | live failed banner · KB upload retry · pin_ref thumbnail (drop from drawer) |
| Report | live failed banner · "生成报告" button width fix · "上传模板" wire file input · mock-banner align fix |
| Credit | live failed banner · 红线渲染 retry · Word 导出 button wire |
| Alert | live failed banner · "启动扫描" button 真接 `/api/alert/scan` · 不直接 mock dispatch |
| Compli | live failed banner · 政策 upload retry · 修订意见 button wire |
| Riskctrl | live failed banner (含 backtest HTTP 422) · DSL editor wire · KS chart fallback banner |
| dispatch IM | composer onSubmit wire `POST /api/im/messages` · cookie 必带 · pin_ref thumbnail 严格 (F-008) |

## 6. Migration

frontend 派活时, sub-agent / worker 必读本规范, onboarding §Acceptance 必 cross-ref。
F-059 ~ F-064 inventory entry 加各 Workspace 的 live-fallback banner DOM。
