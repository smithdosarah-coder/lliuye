# Auth Protocol v1.0

**目的**: 定义 5 user 真实登录 + JWT httpOnly cookie + RBAC ACCESS matrix enforce + AuthGate redirect 的端到端架构 · 取代 Stage A 的前端硬编 PASSWORD_MAP。覆盖 master plan gap #10 与 D.1。

**适用范围**: `web/src/app/login/` · `web/src/lib/store/auth-store.ts` · `web/src/middleware.ts` (新建) · `api_server.py` 新加 `/api/auth/*` 段 · 后续新增 `auth_service/` 后端模块。  
**Owner**: 主 CLI · 修改本协议走红区 RFC。  
**生效**: Stage D.1 · 与 im-protocol.md 协同 (IM 取已登录 currentUser 限 thread visibility)。

---

## 1. 现状 (master plan gap #10 + D.1)

| Gap | 现状 | 文件位置 |
|---|---|---|
| Password 前端硬编 | `PASSWORD_MAP` 在 LoginForm.tsx · 任何人 view-source 看见 | `web/src/app/login/_components/LoginForm.tsx:35-41` |
| 无 JWT / cookie | login 仅 `useAuthStore.login(userId)` 写 zustand persist · 用 localStorage | `web/src/lib/store/auth-store.ts:105-147` |
| RBAC 仅前端 enforce | `useAuthStore.can()` 在 client 判 · 任意改 store 可越权 | `web/src/lib/store/auth-store.ts:117-136` |
| 无 /403 redirect | 后端无 ACCESS 校验 · 越权访问无阻断 | (无) |
| Logout 仅清前端 store | 无后端 cookie 清理 · token 重放风险 | `web/src/lib/store/auth-store.ts:116` |

本协议端到端把 auth 抽到 backend · 前端仅做 UX layer。

---

## 2. 5 Fixed Accounts (preserve current shape)

5 user 在 `web/src/lib/store/auth-store.ts:14-50` 已定义 (`DEMO_USERS`)。Stage D.1 不改 user shape · 只把 password 移到 backend bcrypt:

```python
# auth_service/users.py (Stage D.1 新建)
import bcrypt

USERS = {
    "u_wangzhe": {
        "id": "u_wangzhe", "name": "王哲", "role": "rm",
        "team": "华东·上海第一支行", "avatar": "哲",
        "password_hash": bcrypt.hashpw(b"wangzhe", bcrypt.gensalt()).decode(),
    },
    "u_lihua": {
        "id": "u_lihua", "name": "李华", "role": "credit_officer",
        "team": "华东·授信审查部", "avatar": "华",
        "password_hash": bcrypt.hashpw(b"lihua", bcrypt.gensalt()).decode(),
    },
    "u_zhoumin": {
        "id": "u_zhoumin", "name": "周敏", "role": "compliance_officer",
        "team": "总部·合规管理部", "avatar": "敏",
        "password_hash": bcrypt.hashpw(b"zhoumin", bcrypt.gensalt()).decode(),
    },
    "u_chenkai": {
        "id": "u_chenkai", "name": "陈凯", "role": "risk_manager",
        "team": "总部·风险管理部", "avatar": "凯",
        "password_hash": bcrypt.hashpw(b"chenkai", bcrypt.gensalt()).decode(),
    },
    "u_liuye": {
        "id": "u_liuye", "name": "刘野", "role": "admin",
        "team": "AI 中台", "avatar": "野",
        "password_hash": bcrypt.hashpw(b"liuye", bcrypt.gensalt()).decode(),
    },
}
```

Demo 期 password 仍取 user 名拼音 (用户 2026-04-27 决议 · 见 `LoginForm.tsx:33` 注释) · 客户走访 / 生产前替换企业 SSO。

---

## 3. Endpoints

### 3.1 POST /api/auth/login

```
Body:    { user_id: string, password: string }
Returns: 200 { token, user, roles }
         401 { error: "账号或密码错误" }
         429 { error: "登录过频" }   (rate limit · IP 5/min)

Behavior:
  1. SELECT user from USERS by user_id · not found → 401
  2. bcrypt.checkpw(password, user.password_hash) → False → 401 (constant-time)
  3. Generate JWT (HS256 · secret from env JWT_SECRET · exp=24h)
     payload: { sub: user.id, role: user.role, iat, exp }
  4. Set-Cookie: zhongan_auth=<jwt>; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=86400
     (本地 dev 去 Secure)
  5. Return JSON { token: <jwt>, user: <DEMO_USERS shape>, roles: ACCESS[user.role] }
```

JWT 不放 ACCESS matrix 全量 (避免 cookie 膨胀) · 仅放 role · 前端从 `/api/auth/me` 拿 accessibleAgents。

### 3.2 GET /api/auth/me

```
Cookie:  zhongan_auth=<jwt>
Returns: 200 { user, roles, accessibleAgents }
         401 { error: "未登录或 token 过期" }

Behavior:
  1. 从 cookie 取 JWT · 解码 · 验签 · 验 exp
  2. SELECT user from USERS by sub · 拼 ACCESS[role]
  3. Return { user, roles: [role], accessibleAgents: ACCESS[role] }
```

前端在 layout 顶层调 `/api/auth/me` 同步 `useAuthStore.currentUser`。无 Cookie 或 401 → middleware redirect `/login`。

### 3.3 POST /api/auth/logout

```
Cookie:  zhongan_auth=<jwt>
Returns: 200 { ok: true }

Behavior:
  1. Set-Cookie: zhongan_auth=; HttpOnly; Max-Age=0  (清 cookie)
  2. (可选) 写 logout audit · 不阻
  3. 前端拿到 200 后 useAuthStore.logout() + router.replace("/login")
```

### 3.4 RBAC matrix (preserve auth-store.ts:61-67)

```python
# auth_service/rbac.py (Stage D.1 新建 · 与 web/src/lib/store/auth-store.ts:61-67 镜像)
ACCESS = {
    "rm":                  ["channel", "report", "credit", "alert", "compli", "riskctrl"],
    "credit_officer":      ["credit", "report", "alert"],
    "compliance_officer":  ["compli", "report", "alert"],
    "risk_manager":        ["riskctrl", "alert", "credit"],
    "admin":               ["channel", "report", "credit", "alert", "compli", "riskctrl"],
}

HANDOFFS = {
    # 镜像 web/src/lib/store/auth-store.ts:72-92
}
```

**纪律**: 前后端两份 ACCESS 定义不能漂移。Stage D.1 后建 `docs/arch/rbac-source-of-truth.md` 锁版本号 · 任何改 ACCESS 同时改两边走 RFC。

---

## 4. JWT Configuration

```python
# auth_service/jwt_util.py
import os, jwt, datetime
from datetime import timedelta, timezone

JWT_SECRET = os.environ["JWT_SECRET"]   # 32+ char random · .env 必填
JWT_ALG = "HS256"
JWT_EXP_HOURS = 24

def issue(user_id: str, role: str) -> str:
    now = datetime.datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=JWT_EXP_HOURS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)

def verify(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
```

`.env` 加 `JWT_SECRET=<openssl rand -hex 32>`. 启动 wrapper `scripts/start_uvicorn.py` 必须校验存在 · 缺则 abort (类比当前 DEEPSEEK_API_KEY 校验)。

---

## 5. Cookie Strategy

| 选项 | 值 | 理由 |
|---|---|---|
| `Name`     | `zhongan_auth` | 单一 cookie · 不分 access/refresh (demo 级 · 24h 一次重登可接受) |
| `HttpOnly` | true | 前端 JS 不可读 · XSS 偷不到 token |
| `Secure`   | true (生产) / false (本地 dev) | 生产 https only · `https://demo.liuye.me` |
| `SameSite` | `Lax` | 防 CSRF · 同域子页面正常 cookie 携带 |
| `Path`     | `/` | 全站共享 |
| `Max-Age`  | 86400 (24h) | 与 JWT exp 对齐 |

**前端不操作 cookie** · 从 `/api/auth/me` 取 user data · 不读 `document.cookie`。`useAuthStore` `partialize` 不再 persist `currentUser` (因为 cookie 是 source of truth) · 改成每次 layout mount 调 `/api/auth/me` rehydrate。

---

## 6. AuthGate (frontend enforcement)

### 6.1 Next.js middleware (推荐 · Next 16 SSR-aware)

```ts
// web/src/middleware.ts (Stage D.1 新建)
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const PUBLIC_PATHS = ["/login", "/api/auth/login"];
const AGENT_PATHS = /^\/archive\/(channel|report|credit|alert|compli|riskctrl)/;

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  if (PUBLIC_PATHS.some((p) => pathname.startsWith(p))) return NextResponse.next();

  const cookie = req.cookies.get("zhongan_auth");
  if (!cookie) return NextResponse.redirect(new URL("/login", req.url));

  // 检 agent path 是否在 ACCESS 内 (cookie payload 解码 · 不调 backend 减 latency)
  const m = pathname.match(AGENT_PATHS);
  if (m) {
    const role = await getRoleFromJwt(cookie.value);
    const agentId = m[1];
    if (!ACCESS_LOOKUP[role]?.includes(agentId)) {
      return NextResponse.redirect(new URL("/403", req.url));
    }
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
```

> **Next 16 警告**: `web/AGENTS.md` 提示本仓库 Next 16 有 breaking changes · middleware 使用前必读 `node_modules/next/dist/docs/` 实际 API · 上述代码是模式说明 · 落地实现以 Next 16 真 API 为准。

### 6.2 Client-side 兜底

middleware 是第一道闸 · 但 archive Workspace 顶层 client component 也再校验一次:

```tsx
// web/src/app/archive/<agent>/page.tsx (Stage D.1 改)
"use client";
import { useAuthStore } from "@/lib/store";
import { redirect } from "next/navigation";

export default function ChannelArchivePage() {
  const can = useAuthStore((s) => s.can);
  if (!can({ kind: "agent.access", agent: "channel" })) {
    redirect("/403");
  }
  return <ChannelWorkspace />;
}
```

防 middleware 漏配 / cookie 解码出错时仍 enforce。`useAuthStore.can()` 已存 (`auth-store.ts:117-136`) · 不动签名。

### 6.3 /403 page (新建)

```tsx
// web/src/app/403/page.tsx (Stage D.1 新建)
export default function ForbiddenPage() {
  return (
    <main>
      <h1>无权访问</h1>
      <p>此 Agent 不在你当前角色 (admin / 客户经理 / 审贷官 / 合规官 / 风险经理) 的 ACCESS 范围内。</p>
      <a href="/today">返回 today</a>
    </main>
  );
}
```

---

## 7. Backend ACCESS Enforcement

middleware + client 两道闸已防越权 UI 渲染 · 但 backend agent endpoint 也必须校验 (defence in depth):

```python
# auth_service/dependencies.py (Stage D.1)
from fastapi import Depends, HTTPException, Cookie
from auth_service.jwt_util import verify
from auth_service.rbac import ACCESS

async def require_user(zhongan_auth: str | None = Cookie(default=None)):
    if not zhongan_auth:
        raise HTTPException(401, "未登录")
    try:
        payload = verify(zhongan_auth)
    except Exception:
        raise HTTPException(401, "token 无效或过期")
    return payload  # {sub, role, iat, exp}

def require_agent(agent_id: str):
    async def _check(user=Depends(require_user)):
        if agent_id not in ACCESS.get(user["role"], []):
            raise HTTPException(403, f"role {user['role']} 无权访问 {agent_id}")
        return user
    return _check

# 使用 (agent_channel/api.py · 类似 6 Agent 全套)
@router.post("/api/channel/run")
async def channel_run(req: ChannelRunRequest, user=Depends(require_agent("channel"))):
    # ... 已确保 user 有权
```

---

## 8. Migration path (Stage D.1)

| # | 文件 | 动作 |
|---|---|---|
| 1 | `auth_service/users.py` (新建) | 5 user + bcrypt password hash · USERS dict |
| 2 | `auth_service/jwt_util.py` (新建) | issue / verify · JWT_SECRET from env |
| 3 | `auth_service/rbac.py` (新建) | ACCESS / HANDOFFS 镜像前端 |
| 4 | `auth_service/dependencies.py` (新建) | require_user / require_agent factory |
| 5 | `api_server.py` | 加 `/api/auth/login` / `/api/auth/me` / `/api/auth/logout` 三 endpoint |
| 6 | `.env` + `scripts/start_uvicorn.py` | 加 JWT_SECRET 校验 |
| 7 | `web/src/middleware.ts` (新建) | redirect /login if no cookie · /403 if no access |
| 8 | `web/src/app/login/_components/LoginForm.tsx` | 删 PASSWORD_MAP · handleSubmit 改 fetch `/api/auth/login` |
| 9 | `web/src/lib/store/auth-store.ts` | login(userId, password) async · fetch `/api/auth/login` · 不 persist password |
| 10 | `web/src/app/layout.tsx` | mount 时 fetch `/api/auth/me` rehydrate currentUser |
| 11 | `web/src/app/403/page.tsx` (新建) | 友好 forbid 页 |
| 12 | 6 个 `agent_*/api.py` | 各 router 端点加 `Depends(require_agent("..."))` |
| 13 | docs/arch/rbac-source-of-truth.md (新建) | 锁 ACCESS 版本号 · 漂移防护 |

每步独立 commit · trailer 含 `Signal: D-AUTH-STAGE-N-DONE` (具体 step signal 由 Stage D worker onboarding 定义)。

---

## 9. Acceptance gate

Stage D.1 完成判定:
- 错密码 5 次 · 401 + rate limit 触发 (curl 验)
- 对密码登录 · `Set-Cookie: zhongan_auth=...; HttpOnly` 在响应头 · 浏览器 devtools 可见
- 用李华账号访问 `/archive/channel` (rm-only) · 跳 `/403`
- 用王哲账号访问 6 Agent 全开
- Backend agent 端点 curl 不带 cookie · 401
- Cookie 过期 → middleware redirect /login · 重登恢复
- Logout 后 cookie 立即清 · 再访问 protected 路径跳 /login
- Playwright spec `auth-rbac-enforce.spec.ts` 5 user × 6 path matrix 跑通

---

## 10. 与其他契约的关系

- `im-protocol.md §2` · IM 用户即 auth 用户 · WebSocket connect 用同一 JWT
- `workspace-state-protocol.md` · Workspace 入口 page.tsx 调 `useAuthStore.can()` · 但 store 行为不在本协议
- `shared-change-protocol.md` · ACCESS matrix 修改是红区 (跨 6 Agent 影响) · 必走 RFC
- 后端 `agent_*/api.py` 加 `Depends(require_agent("..."))` 是黄区 (各 Agent 自己 router · 但调用本协议 dependencies factory · 改 factory 走红区 RFC)
