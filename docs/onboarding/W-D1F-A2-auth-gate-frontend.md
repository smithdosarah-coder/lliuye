# Worker A2 (Stage D.1 frontend) · AuthGate enforce + LoginForm 真接 backend · Onboarding

> Worker CLI 在 `D:/claude code/work-A2-contracts` (branch
> `feat/contracts-bootstrap-A2`) · 复用 worktree。
> 上批 Stage D.1 backend (`05e790f`) 已 cherry-pick MERGED (`bd143b5`) ·
> 本批 Stage D.1 frontend 启动 · 跟你上批 backend 配对收尾 gap #10 全 stack。

## Goal

实装 master plan §D.1 frontend — AuthGate 真接 backend `/api/auth/me` ·
LoginForm 真接 `/api/auth/login` · ACCESS matrix enforce · 5 user 切换 redirect。
**gap #10 (5 user RBAC enforce 缺) frontend 闭环 · 全 stack production-grade**。

## Acceptance

- [ ] **必读** `docs/contracts/auth-protocol.md` v1.0 + 自己上批 backend
      `auth_service/` (cherry-pick bd143b5)
- [ ] **LoginForm 改 call backend**: POST `/api/auth/login` body `{user_id, password}` ·
      Set-Cookie 自动 (httpOnly · 浏览器接管) · 成功 → redirect `/today` · 失败 → 显错误
- [ ] **AuthGate component**:
  - GET `/api/auth/me` 验 cookie · 200 → 拿 user + roles · 401 → redirect `/login`
  - 用户访问 `/archive/<agent>` · ACCESS matrix 验 user.role 是否 include agent ·
    不 include → redirect `/403`
- [ ] **403 page** 新建 · 显 "权限不足" + "返回 today" link
- [ ] **Logout button** 改 call POST `/api/auth/logout` · 清 cookie · redirect `/login`
- [ ] **auth-store.ts 改造**: 移除 frontend mock LOGIC (PASSWORD_MAP 不再 frontend) ·
      改用 `user` (来自 /api/auth/me) · `logout()` 调 backend
- [ ] tsc 0 error · `cd web && npx playwright test web/tests/regression/auth-gate.spec.ts` 跑通
  - default 进 `/archive/credit` 未登录 → redirect `/login`
  - 登录 `u_lihua` (credit_officer) · 进 `/archive/credit` OK
  - 登录 `u_lihua` 进 `/archive/channel` (无权) → redirect `/403`
  - 登录 `u_liuye` (admin) · 进任 archive OK
  - logout → cookie 清 · 重进 redirect /login
- [ ] features-inventory.md 加 F-057 (AuthGate enforce real backend)
- [ ] commit trailer:
  ```
  Signal: WORKER-A2-STAGE-D1F-AUTH-GATE-FRONTEND-DONE
  RECOVER-FROM: 05e790f (D.1 backend done · 本批接续)
  PRESERVES: F-001~F-056 (列全)
  RESPECTS: docs/contracts/auth-protocol.md + empty-state-design-protocol.md
  NEW-DOM: data-testid="login-error-banner", data-testid="auth-403-page", data-testid="auth-403-back-today"
  SMOKE-PASS: web/tests/regression/auth-gate.spec.ts
  INVENTORY-ADDED: F-057
  ```

## Boundary

- **改**: `web/src/app/login/_components/LoginForm.tsx` (移除前端 PASSWORD_MAP) ·
  `web/src/lib/store/auth-store.ts` (改用 backend 验) ·
  `web/src/components/auth/AuthGate.tsx` (现有 mock check 改 call /api/auth/me)
- **加**: `web/src/lib/api/auth.ts` (login/me/logout client) ·
  `web/src/app/403/page.tsx` (403 page) ·
  `web/tests/regression/auth-gate.spec.ts` ·
  `docs/features-inventory.md` F-057
- **不动**: backend `auth_service/` (上批 bd143b5 已 deliver) · agent_*/api.py ·
  其他 Workspace · CLAUDE.md · RFC

## Dependencies

- master plan §D.1 frontend (gap #10 frontend)
- 自己上批 backend `auth_service/` (bd143b5 · POST /api/auth/login + GET /me + POST /logout · ACCESS matrix mirror)
- `web/AGENTS.md` (Next 16 警告 · cookie + middleware 模式)

## Method

1. Read 上批 `auth_service/dependencies.py` + `auth_service/users.py` (验 ACCESS matrix shape)
2. 改 LoginForm 移除 frontend PASSWORD_MAP · call backend
3. AuthGate 改 useEffect call /api/auth/me · 不通过 redirect /login
4. ACCESS matrix enforce: AuthGate 之上加 RouteGuard checking agent_id (current path)
5. 403 page 新建
6. logout 改 call backend
7. tsc + playwright smoke 5 case
8. inventory F-057 + trailer

## Trailer protocol

```
Signal: WORKER-A2-STAGE-D1F-AUTH-GATE-FRONTEND-DONE
RECOVER-FROM: 05e790f
PRESERVES: F-001, F-002, ..., F-056 (列全 56 id)
RESPECTS: docs/contracts/auth-protocol.md + empty-state-design-protocol.md
NEW-DOM: ...
SMOKE-PASS: web/tests/regression/auth-gate.spec.ts
INVENTORY-ADDED: F-057
```

## On completion

1. `git add web/` + commit + push origin
2. main CLI auto-patrol → review (tsc + playwright + 验 cookie httpOnly + RBAC matrix
   enforce) → cherry-pick → push origin

## Estim

3-5 hr (frontend wire 上批 backend · 5 case smoke · 改 4 file frontend · 加 1 page)

## NB

- backend cookie 是 httpOnly · frontend JS 不可读 (符合安全) · 但 fetch 自动带
- middleware (Next.js) 路径: SSR-aware · 不要在 client component 内 redirect (用
  Next.js redirect from server component or middleware)
- ACCESS matrix 镜像 `auth_service/rbac.py` (backend) + `auth-store.ts` (frontend ·
  本批改 single source of truth = backend · frontend cache from /me)
