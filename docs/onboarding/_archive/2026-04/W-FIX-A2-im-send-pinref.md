# Worker A2 (FIX 第 1 批) · IM Send + PinRef Thumbnail · Onboarding

> Worker CLI 在 `D:/claude code/work-A2-contracts` (branch
> `feat/contracts-bootstrap-A2`) · 复用 worktree。
> 上批 Stage E.3 PIPL (`0847fdf`) 已 cherry-pick MERGED · 本批 fix user 报 bug 3。

## Goal

User 报 production bug 3:

1. dispatch IM 聊天框是摆设 · 无法发送
2. 画布拖到 composer 是 url 链接 · 不是 thumbnail (违反 F-008 + live-fallback-banner-spec §2 规则 4)

修按 `docs/contracts/live-fallback-banner-spec.md` v1.0 规范。

## Acceptance

- [ ] **必读** `docs/contracts/live-fallback-banner-spec.md` v1.0 §2 规则 4 + §3 排版
- [ ] **必读** F-008 (拖柄 + thumbnail 已交付 feature) + F-058 (D.2F frontend cherry-pick)
- [ ] **ComposerBar onSubmit 真 wire**:
  - 输入文字 + Enter (or click send button) → call `sendMessage(threadId, text)`
  - sendMessage 走 `web/src/lib/api/im.ts` POST `/api/im/messages` (cookie 必带)
  - 失败 4xx/5xx → 顶部 banner "⚠️ 发消息失败 (<code>) · [重试]"
- [ ] **MessageBubble pin_ref 严格 thumbnail**:
  - `message.kind === "pin_ref"` AND `message.refs?.thumbDataUrl` → 渲染 thumbnail card (图标 + agent_id + title)
  - 否则: error log + UI 显 "拖拽 ref 失败" + 灰色占位 · **禁止 fallback url 链接**
- [ ] **WebSocket 连不上 banner**: ws state !== "open" 持续 30s → 顶部 banner "⚠️ IM 实时连接断开 · [重连]"
- [ ] tsc 0 error · 加 smoke `web/tests/regression/im-fix.spec.ts` (3 case · send 真 POST verify / pin_ref thumbnail render / live fail banner 显)
- [ ] features-inventory.md 加 F-060 (IM send wire + pin_ref strict thumbnail + live fail banner)
- [ ] commit trailer:
  ```
  Signal: WORKER-A2-FIX-IM-SEND-PINREF-DONE
  RECOVER-FROM: 0847fdf
  PRESERVES: F-001~F-059
  RESPECTS: docs/contracts/live-fallback-banner-spec.md
  NEW-DOM: data-testid="im-send-fail-banner", data-testid="im-pin-ref-error"
  SMOKE-PASS: web/tests/regression/im-fix.spec.ts
  INVENTORY-ADDED: F-060
  ```

## Boundary

- 改: `web/src/app/dispatch/_components/ComposerBar.tsx` (onSubmit wire) ·
      `web/src/app/dispatch/_components/MessageBubble.tsx` (pin_ref thumbnail strict) ·
      `web/src/lib/api/im.ts` (sendMessage error handling) · `dispatch-store.ts`
      (banner state)
- 加: `web/tests/regression/im-fix.spec.ts` · F-060 inventory
- 不动: backend im_service/ · auth_service/ · 其他 Workspace

## Estim

3-4 hr (send wire + thumbnail strict + banner · careful 不破 D.2F)
