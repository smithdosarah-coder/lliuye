# Worker A2 (Stage D 第 1 批) · Auth + RBAC backend · Onboarding

> Worker CLI 在 `D:/claude code/work-A2-contracts` (branch
> `feat/contracts-bootstrap-A2`) · 复用 worktree。
> 上批 Stage CF2 Alert frontend (`597c47a`) 已 cherry-pick MERGED (`f427d41`) ·
> 本批 Stage D.1 启动。

## Goal

实装 master plan §D.1 — Auth backend (bcrypt + JWT) + RBAC enforce middleware ·
按 `docs/contracts/auth-protocol.md` v1.0 spec 落地。
**gap #10 (5 user RBAC enforce 缺) 闭环** · banking production 必修。

## Acceptance

- [ ] **必读** `docs/contracts/auth-protocol.md` v1.0 全文 (cherry-pick a660019)
- [ ] **POST `/api/auth/login`** body `{user_id, password}` → bcrypt verify + 返
      `{token, user, roles}` + Set-Cookie `zhongan_auth` (JWT HS256 · 24h ·
      httpOnly · SameSite=Lax)
- [ ] **GET `/api/auth/me`** · 解析 cookie → 返 user + roles + access matrix
- [ ] **POST `/api/auth/logout`** · 清 cookie · 返 ok
- [ ] **5 user PASSWORD_MAP** 改 backend `auth_service/users.py` bcrypt hash 存储
      (现 frontend LoginForm.tsx:35-41 硬编 · 改 backend · frontend call /login API)
- [ ] **Backend defence in depth**: FastAPI `Depends(require_agent("channel"))` 等
      decorator · 各 agent endpoint mount 时加 · 验 cookie + ACCESS matrix
- [ ] curl 测 login + me + logout 全 5 user × 各 endpoint · sample 进 commit body
- [ ] pytest `auth_service/tests/` ≥ 8 case (5 user login · invalid pwd · expired
      JWT · access matrix enforce · logout · etc.)
- [ ] commit trailer:
  ```
  Signal: WORKER-A2-STAGE-D1-AUTH-RBAC-DONE
  RECOVER-FROM: 597c47a (Stage CF2 Alert done · 本批接续)
  NEW-ENDPOINT: POST /api/auth/login, GET /api/auth/me, POST /api/auth/logout
  NEW-MIDDLEWARE: require_agent FastAPI Depends decorator
  ```

## Boundary

- **改**: `api_server.py` (mount 3 auth endpoint + apply Depends to existing agent endpoints)
- **加**: `auth_service/users.py` (bcrypt user store) · `auth_service/jwt_util.py`
  (HS256 sign/verify) · `auth_service/rbac.py` (ACCESS matrix · 镜像
  web/src/lib/store/auth-store.ts:61-67) · `auth_service/dependencies.py`
  (FastAPI Depends require_agent) · `auth_service/tests/test_*.py`
- **不动**: `web/*` (frontend Stage D.1 frontend 后续 worker · AuthGate enforce 跟
  本批 spec align) · agent_*/api.py 内部业务逻辑 · CLAUDE.md · RFC

## Dependencies

- master plan §D.1 (gap #10 · banking production 必修)
- `docs/contracts/auth-protocol.md` v1.0 (cherry-pick a660019 · spec ready)
- 现状 frontend `web/src/lib/store/auth-store.ts` ACCESS matrix · 镜像到 backend
- bcrypt + python-jose / pyjwt (requirements.txt 加)

## Method

1. Read auth-protocol.md (D.1 13-step migration path)
2. 设计 `auth_service/` module (users / jwt / rbac / dependencies / tests)
3. bcrypt hash 5 user password (生产用 `bcrypt.hashpw` · 不存明文)
4. JWT HS256 sign/verify · 24h exp · payload `{user_id, role, exp}`
5. Cookie strategy: httpOnly + SameSite=Lax + Secure (production https)
6. Depends decorator · agent_id 参数 · 验 cookie + access matrix · 401/403
7. Mount 到 api_server.py · 加 Depends to 各 agent endpoint
8. pytest 8+ case + curl 验

## Trailer protocol

```
Signal: WORKER-A2-STAGE-D1-AUTH-RBAC-DONE
RECOVER-FROM: 597c47a
NEW-ENDPOINT: POST /api/auth/login, GET /api/auth/me, POST /api/auth/logout
NEW-MIDDLEWARE: require_agent FastAPI Depends decorator
```

## On completion

1. `git add auth_service/ api_server.py` + commit + push origin
2. main CLI auto-patrol → review (curl + pytest + trailer + ACCESS matrix verify)
   → cherry-pick → push origin

## Estim

5-7 hr (5 user bcrypt + JWT + cookie + middleware + 8+ test · 谨慎: 改 api_server.py
影响所有 agent endpoint · pytest 必跑 cumulative)

## NB

- frontend AuthGate (web/src/components/auth/) 现 mock check ACCESS matrix · 本批
  backend 上线后 · frontend AuthGate 改用 GET /api/auth/me 真验 · 是 Stage D.1
  frontend 子 task (后续 worker / sub-agent 派)
- demo 期 5 user 简单密码 (wangzhe/lihua/...) 仍接受 · production 期换强密码后
  bcrypt rehash · 不影响 spec
- JWT secret 走 .env `JWT_SECRET_KEY` · 不入 git
