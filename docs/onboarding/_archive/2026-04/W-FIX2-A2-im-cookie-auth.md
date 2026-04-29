# Worker A2 (FIX 第 2 批) · IM Cookie Auth Chain Fix · Onboarding

> Worker CLI 在 `D:/claude code/work-A2-contracts` (branch `feat/contracts-bootstrap-A2`) ·
> 复用。上批 W-FIX-A2 (`1e85ee1` IM send + pin_ref) 已 cherry-pick MERGED · 本批
> fix Codex 找的 bug #8 (IM dead 真根源 · cookie 名错)。

## Goal

修 Codex 找的 P0 bug #8:

**根因**: `web/src/lib/api/im.ts:34` 读 `document.cookie` 找 `auth_token` · 但 D.1
backend 真 cookie 名 `zhongan_auth` + httpOnly (JS 不可读) · 所以 IM token resolve
全 fall to demo · 真 user 用 IM 时 auth fail / permission fail · 整个 IM 链断。

**正解**: frontend 不读 cookie · 用 `credentials: "include"` 让 browser 自动带
zhongan_auth cookie · backend 各 IM endpoint 加 `Cookie()` parameter 验 (复用 D.1 auth)。
不重新设计 IM-specific token (Codex 建议过度工程)。

## Acceptance

- [ ] **frontend** `web/src/lib/api/im.ts` 全 fetch 加 `credentials: "include"` (移除
      `getImToken()` 读 cookie · 保留 fallback localStorage 作 demo · 但优先 credentials)
- [ ] **frontend** `web/src/lib/im/websocket.ts` WebSocket connect 用 cookie auth
      (Browser WebSocket 自动带 cookie if same-origin or Cookie env var)
- [ ] **backend** 各 IM endpoint 加 `zhongan_auth: str | None = Cookie(default=None)`
      parameter:
  - POST /api/im/messages
  - GET /api/im/threads
  - GET /api/im/threads/{tid}/messages
  - POST /api/im/threads/{tid}/read
  - POST /api/im/threads (create)
  - POST /api/im/send (legacy · maybe deprecate)
  - WS /ws/im (already has cookie support · verify)
- [ ] **backend** im_service/ 加 helper `_resolve_im_user(zhongan_auth) -> user_id`:
  ```py
  def _resolve_im_user(zhongan_auth: str | None) -> str:
      from auth_service.jwt_util import verify, JWTError
      if not zhongan_auth:
          raise HTTPException(401, "缺 cookie")
      try:
          return verify(zhongan_auth)["sub"]
      except JWTError:
          raise HTTPException(401, "cookie 无效")
  ```
- [ ] frontend 全 IM fetch 验 `credentials: "include"` · grep 全 im.ts
- [ ] curl 测: login 拿 cookie → /api/im/threads 仅带 cookie · 验 200 (不 send Bearer)
- [ ] pytest `im_service/tests/test_cookie_auth.py` ≥ 5 case (cookie 有效 · 缺 · 过期 · 无效 sub · 复用 D.1 auth_service jwt_util)
- [ ] commit trailer:
  ```
  Signal: WORKER-A2-FIX2-IM-COOKIE-AUTH-DONE
  RECOVER-FROM: 1e85ee1
  PRESERVES: F-001~F-062
  REFACTORED: web/src/lib/api/im.ts (credentials:include · 移除 cookie 读) ·
              im_service/ 6 endpoint 加 Cookie param
  ```

## Boundary

- 改: `web/src/lib/api/im.ts` · `web/src/lib/im/websocket.ts` · `im_service/api.py`
      (or wherever IM routes mount) · `im_service/auth.py` (新 helper)
- 加: `im_service/tests/test_cookie_auth.py`
- 不动: auth_service/ (D.1 已就 · 复用 verify) · web/* dispatch UI (已 W-FIX-A2 done) · CLAUDE.md · RFC

## Estim

3-4 hr (frontend grep + 改 6 endpoint Cookie param + 5 case test)

## NB

- 不增 /api/im/token endpoint (Codex 建议过度) · 不增 token 概念 · 复用 D.1 cookie
- 兼容: WebSocket 也用 cookie · query token 作 backup (浏览器 WS API
  自动带 cookie · server-side 也能 read)
