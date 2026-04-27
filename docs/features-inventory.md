# Features Inventory · 已交付前端 feature 清单

> **目的**：防回档。worker 派活前必读·改动后必须在 commit trailer 列 `PRESERVES: F-XXX` 声明保留。
> **约束**：本清单是 worker 改 `web/` 的 contract——任何改动都不能破坏已列 feature·破坏视作 regression。
> **生成于**：2026-04-27·基于 6 个回档 bug 反推首批 entries。后续每修一个 bug / 上线一个新 feature 必须 enrich。

## 模板

```yaml
F-XXX · <短标题>
location: <主文件路径> + 引用点
selector: <DOM data-testid 或类名>
interaction: <一句话描述用户操作 → 系统响应>
introduce: <commit_hash>  <YYYY-MM-DD>  <commit subject 摘要>
lost_at: <commit_hash 或 N/A>
restored: <commit_hash 或 pending>
smoke_test: <web/tests/regression/*.spec.ts 路径·没写就标 pending>
```

---

## F-001 · 退出登录按钮

- **location**: `web/src/components/shell/LogoutButton.tsx` + 引用于 `Masthead.tsx` / `PersonaSwitcher.tsx`
- **selector**: `[data-testid="logout-button"]`（待 cherry-pick 后确认）
- **interaction**: click → `store.logout()` → redirect `/login`
- **introduce**: `05fafcd` 2026-04-23「退出登录 pill · 画布/主题双 pill 对齐」
- **lost_at**: `63107fb` 2026-04-26「Stage 1 · file-snapshot 8 文件」LogoutButton.tsx 文件被删
- **restored**: pending（Phase C.1 cherry-pick `05fafcd`）
- **smoke_test**: `web/tests/regression/logout.spec.ts` pending

## F-002 · 画布开关 pill（CanvasModeToggle）

- **location**: `web/src/components/shell/CanvasModeToggle.tsx`·引用于 `AppShell.tsx`
- **selector**: `[data-testid="canvas-mode-toggle"]`
- **interaction**: click → 切换 `panel-canvas` ↔ `free-drag` mode
- **introduce**: `63107fb` 2026-04-26（毛玻璃）+ `05fafcd` 2026-04-23（双 pill 对齐）
- **lost_at**: `315de1e` 2026-04-22 revert 把 motion tokens 删了·样式降级
- **restored**: pending（Phase C.2）
- **smoke_test**: `web/tests/regression/canvas-toggle.spec.ts` pending

## F-003 · 主题切换 pill（ThemeSwitch · 4 主题）

- **location**: `web/src/components/shell/ThemeSwitch.tsx`
- **selector**: `[data-testid="theme-switch-{canvas|matcha|dusk|ink}"]` × 4
- **interaction**: click theme → set `data-theme` on `<html>` → 切换 4 主题渐变（**不含已下架的 Letterpress / Nebula**）
- **introduce**: 同 F-002（双 pill 升级）
- **lost_at**: 同 F-002（token 降级）
- **restored**: pending（Phase C.2）
- **smoke_test**: `web/tests/regression/theme-switch.spec.ts` pending

## F-004 · Forge（Agent2 风控）Workspace · ScanCTA 触发按钮

- **location**: `web/src/components/shared/ScanCTA.tsx` + `web/src/app/archive/riskctrl/_components/RiskctrlWorkspace.tsx`
- **selector**: ScanCTA 内的 `<button>` 触发回测
- **interaction**: click → POST `/api/run/riskctrl`（multiplexer endpoint）→ SSE 流式更新进度
- **introduce**: `ffc60ca` 2026-04-23「5 agent workspace 共享 ScanCTA · 补齐过程感演示」
- **lost_at**: `95437b6` 2026-04-26「Stage 3 微信气泡 + dispatch group/dm split」改了 ScanCTA `onDone` callback
- **restored**: pending（Phase C.3 对比版本 + 小修）
- **smoke_test**: `web/tests/regression/forge-trigger.spec.ts` pending

## F-005 · Scout（Agent1 获客）· 自由搜索标签

- **status**: 🔴 NEVER CORRECTLY DELIVERED·产品定位错·待重做
- **location**: `web/src/app/archive/channel/_components/ChannelWorkspace.tsx` QueryBar 区 + `web/src/lib/mock/agent-channel-session.ts` query 部分
- **interaction (期望)**: 客户经理输入 / 组合 tag → 自由搜索企业·候选基于 tag 命中·**不是** look-alike 找相似
- **introduce (错版)**: `19b6d72` 2026-04-24 实现成 look-alike KB matcher（worker 误解产品定位）
- **regress**: `95437b6` 2026-04-26 placeholder 改为「标杆客户名 / 描述画像」·**仍是错的方向**
- **fix_path**: 重写 QueryBar + ScoutQuery 类型·spec 由 PM 提供后 implement·**不能 cherry-pick · 必须新做**
- **smoke_test**: `web/tests/regression/scout-tag-search.spec.ts`（重写后写）

## F-006 · ScoreRadar 8 维评分雷达图 · 毛玻璃样式

- **location**: `web/src/components/viz/ScoreRadar.tsx` + 各 Workspace 内引用（Scout / Forge / Credit）
- **interaction**: render 8 维 radar（该企业 vs 行业 P50）
- **introduce**: `3a20bdf` v14-v5 baseline 毛玻璃风格首次落地
- **lost_at**: 全局 token 降级（`315de1e` revert）间接波及·CSS 看起来是默认样式
- **restored**: pending（Phase C.5 手动 CSS 恢复）
- **smoke_test**: visual snapshot regression（pending）

## F-007 · Today 页 · 空白状态（不含 worker hallucinate 的 4 块）

- **location**: `web/src/app/today/page.tsx` + `web/src/components/today/Hero.tsx`
- **MUST NOT contain**:
  - PriorityQueue（今日队列 · Priority 5 客户清单）
  - EventTimeline（事件流 · Timeline）
  - 4 KPI 大数字（本月已放款 / 待签卷宗 / 观察名单 / 本周新政）
- **MUST contain**: 空白 hero + 「开始演示」CTA（PM 愿景·worker 自由发挥多了 4 块）
- **introduce (错版)**: `bc70e65` + `a82efe5` 2026-04-20 worker 加 PriorityQueue + EventTimeline
- **fixed_at**: `f1acf66` 2026-04-21 删除 import 和渲染（但 user 截图显示当前 production 还有这些 block·**ECS 跑的可能不是 chore/l0-infra**·待 verify）
- **fix_path**: verify `f1acf66` 是否在 ECS production·不在则 cherry-pick（Phase C.6）
- **smoke_test**: `web/tests/regression/today-empty.spec.ts` 验 DOM **不含** `[data-testid="today-priority-queue"]` / `today-event-timeline` / `today-kpi-belt`

## F-008 · 气泡拖拽到画布 → 缩略图卡片

- **location**: `web/src/components/dispatch/MessageBubble.tsx` + `web/src/components/shell/MessagePinHandle.tsx` + `web/src/app/dispatch/_store/dispatch-store.ts`
- **selector**: `[data-pin-handle="message"]` drag source · drop target Whiteboard
- **interaction**: dispatch 消息气泡 drag handle → 拖到 Whiteboard 区域 → 缩略图卡片渲染（thumbnail·**不是** url 链接）
- **MIME**: `PANEL_PIN_MIME` 双 MIME 拖柄（缩略图 logic 依赖此 MIME）
- **introduce**: `a5572b9` 2026-04-22「任务2 · MessagePinHandle · 双 MIME 拖柄」
- **lost_at**: `95437b6` 2026-04-26 dispatch-store.updateMessage 改·`refs` 字段移除·拖柄 onDragStart 逻辑改
- **restored**: pending（Phase C.7 cherry-pick `a5572b9` + verify dispatch-store 兼容）
- **smoke_test**: `web/tests/regression/bubble-drag-thumbnail.spec.ts` pending

---

## 待补（用户暗示"还有很多其他的"）

F-009 ~ pending · 等用户继续指出 → enrich 此清单

---

## 维护规则

1. **新 feature 落地必须加 entry**·worker 在 commit message 内 trailer `INVENTORY-ADDED: F-XXX`
2. **修复回档必须更新 entry**·trailer `RESTORED: F-XXX <commit_hash>`
3. **改 web/ 不动 inventory feature**·trailer `PRESERVES: F-001, F-005, ...` 列保留 id
4. **smoke test 写完后**·把 `pending` 替换为实际路径
5. **每周巡检**：grep `web/` 找未列入 inventory 的 critical interaction（按钮 / 拖拽 / 跳转）补 entry
