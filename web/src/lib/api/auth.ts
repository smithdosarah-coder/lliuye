/**
 * Auth backend client · 3 endpoint helper · Stage D.1 frontend (W-D1F-A2).
 *
 * 后端契约 (W-D1-A2 backend `bd143b5` 已 deliver · auth_service/):
 *   POST /api/auth/login   body {user_id, password}
 *                          → {token, user, roles, accessibleAgents}
 *                          + Set-Cookie zhongan_auth (httpOnly, SameSite=lax, 24h)
 *   GET  /api/auth/me      cookie 自动带 (httpOnly · 浏览器接管)
 *                          → {user, roles, accessibleAgents}
 *                          401 if no cookie / expired / tampered
 *   POST /api/auth/logout  → {ok, had_cookie}
 *                          清 cookie · 幂等 · 无 cookie 也 200
 *
 * 设计:
 *   - credentials: "include" · 让浏览器随请求自动带 httpOnly cookie
 *   - 走相对 path · prod 透 nginx · dev 用 NEXT_PUBLIC_API_BASE
 *   - 错误标准化为 AuthApiError · UI 拿 message 直接显
 *   - empty-state-design-protocol § frontend 不存 password (httpOnly cookie 是 source of truth)
 *
 * PB#5 (2026-05-06): zod runtime schema 校验 · 失败抛 AuthApiError code=AUTH_SCHEMA_INVALID
 *   防 backend payload 格式漂移导致 frontend 静默崩 (e.g. role enum 多值 / accessibleAgents 类型变)
 */
import { z } from "zod";

const API_BASE =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_BASE) || "";

export type AuthRole =
  | "rm"
  | "credit_officer"
  | "compliance_officer"
  | "risk_manager"
  | "admin";

export type AuthAgentId =
  | "channel"
  | "report"
  | "credit"
  | "alert"
  | "compliance"
  | "riskctrl";

export interface AuthUser {
  id: string;
  name: string;
  role: AuthRole;
  team: string;
  avatar?: string;
}

export interface AuthMeResponse {
  user: AuthUser;
  roles: AuthRole[];
  accessibleAgents: AuthAgentId[];
}

export interface AuthLoginResponse extends AuthMeResponse {
  token: string;
}

export class AuthApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "AuthApiError";
  }
}

// PB#5 zod schema · runtime 校验 backend payload (镜像 backend auth_service/users.py + rbac.py)
const AuthRoleSchema = z.enum([
  "rm",
  "credit_officer",
  "compliance_officer",
  "risk_manager",
  "admin",
]);
const AuthAgentIdSchema = z.enum([
  "channel",
  "report",
  "credit",
  "alert",
  "compliance",
  "riskctrl",
]);
const AuthUserSchema = z.object({
  id: z.string(),
  name: z.string(),
  role: AuthRoleSchema,
  team: z.string(),
  avatar: z.string().optional(),
});
const AuthMeResponseSchema = z.object({
  user: AuthUserSchema,
  roles: z.array(AuthRoleSchema),
  accessibleAgents: z.array(AuthAgentIdSchema),
});
const AuthLoginResponseSchema = AuthMeResponseSchema.extend({
  token: z.string(),
});
const AuthLogoutResponseSchema = z.object({
  ok: z.boolean(),
  had_cookie: z.boolean(),
});

function parseOrThrow<T>(schema: z.ZodType<T>, raw: unknown, status: number): T {
  const result = schema.safeParse(raw);
  if (!result.success) {
    const issues = result.error.issues.slice(0, 3).map((i) => `${i.path.join(".")}: ${i.message}`).join("; ");
    throw new AuthApiError(status, "AUTH_SCHEMA_INVALID", `后端响应格式异常: ${issues}`);
  }
  return result.data;
}

async function readErrorMessage(res: Response): Promise<{ code: string; message: string }> {
  try {
    const j = (await res.json()) as { detail?: { error?: { code?: string; message?: string } } };
    const err = j?.detail?.error;
    if (err) {
      return {
        code: String(err.code ?? "AUTH_UNKNOWN"),
        message: String(err.message ?? `HTTP ${res.status}`),
      };
    }
  } catch {
    /* fallthrough */
  }
  return { code: "AUTH_HTTP", message: `HTTP ${res.status}` };
}

/**
 * POST /api/auth/login
 *
 * 浏览器自动接收 Set-Cookie · 后续 fetch 自动带 cookie (credentials: include).
 * 失败抛 AuthApiError · UI 用 .message 直接显错误条 (e.g. "账号或密码错误").
 */
export async function loginApi(
  user_id: string,
  password: string,
): Promise<AuthLoginResponse> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id, password }),
  });
  if (!res.ok) {
    const { code, message } = await readErrorMessage(res);
    throw new AuthApiError(res.status, code, message);
  }
  return parseOrThrow(AuthLoginResponseSchema, await res.json(), res.status);
}

/**
 * GET /api/auth/me
 *
 * 401 抛 AuthApiError · AuthGate catch 后 redirect /login.
 * 200 返 user + roles + accessibleAgents (后端 ACCESS matrix · single source of truth).
 */
export async function fetchMe(): Promise<AuthMeResponse> {
  const res = await fetch(`${API_BASE}/api/auth/me`, {
    method: "GET",
    credentials: "include",
  });
  if (!res.ok) {
    const { code, message } = await readErrorMessage(res);
    throw new AuthApiError(res.status, code, message);
  }
  return parseOrThrow(AuthMeResponseSchema, await res.json(), res.status);
}

/**
 * POST /api/auth/logout
 *
 * 幂等 · 即使无 cookie 也 200 · UI 不需 try/catch (除非 network error).
 */
export async function logoutApi(): Promise<{ ok: boolean; had_cookie: boolean }> {
  const res = await fetch(`${API_BASE}/api/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) {
    const { code, message } = await readErrorMessage(res);
    throw new AuthApiError(res.status, code, message);
  }
  return parseOrThrow(AuthLogoutResponseSchema, await res.json(), res.status);
}
