/**
 * Auth store · backend-driven (Stage D.1 frontend · W-D1F-A2).
 *
 * 改造 (vs Stage A 前端硬编版):
 *   - currentUser 不再 persist · 由 /api/auth/me 真验
 *   - login(userId, password) async · 调 backend POST /api/auth/login (httpOnly cookie 浏览器接管)
 *   - logout() async · 调 backend POST /api/auth/logout (清 cookie)
 *   - bootstrap() (新) · 启动时 GET /me 同步 currentUser (cookie 有则恢复 · 无则 null)
 *   - PASSWORD_MAP **彻底移除** · password 仅 backend bcrypt hash 存 (auth_service/users.py)
 *
 * ACCESS matrix 保留前端 mirror (与 backend auth_service/rbac.py 镜像):
 *   - 用作 instant client-side guard (减一次 round-trip)
 *   - 真 enforce 在 backend Depends(require_agent("X")) (auth_service/dependencies.py)
 *   - 改一定同步两边 (auth-protocol.md 红区契约)
 */
import { create } from "zustand";

import { fetchMe, loginApi, logoutApi, AuthApiError } from "@/lib/api/auth";
import type { AgentId, PermissionAction, Role, User } from "./types";

// 5 user metadata · 镜像 backend auth_service/users.py · 仅供 LoginForm dropdown 显
// password 不在前端 (httpOnly cookie 是 source of truth)
export const DEMO_USERS: User[] = [
  { id: "u_wangzhe", name: "王哲", role: "rm",                 team: "华东·上海第一支行", avatar: "哲" },
  { id: "u_lihua",   name: "李华", role: "credit_officer",     team: "华东·授信审查部",   avatar: "华" },
  { id: "u_zhoumin", name: "周敏", role: "compliance_officer", team: "总部·合规管理部",   avatar: "敏" },
  { id: "u_chenkai", name: "陈凯", role: "risk_manager",       team: "总部·风险管理部",   avatar: "凯" },
  { id: "u_liuye",   name: "刘野", role: "admin",              team: "AI 中台",          avatar: "野" },
];

/**
 * RBAC matrix · 镜像 backend auth_service/rbac.py:ACCESS · auth-protocol.md 红区契约.
 * 改一定同步两边走 RFC.
 */
const ACCESS: Record<Role, readonly AgentId[]> = {
  rm:                 ["channel", "report", "credit", "alert", "compliance", "riskctrl"],
  credit_officer:     ["credit", "report", "alert"],
  compliance_officer: ["compliance", "report", "alert"],
  risk_manager:       ["riskctrl", "alert", "credit"],
  admin:              ["channel", "report", "credit", "alert", "compliance", "riskctrl"],
};

const HANDOFFS: Record<Role, { from: AgentId; to: AgentId }[]> = {
  rm: [
    { from: "channel", to: "report" },
    { from: "report",  to: "credit" },
    { from: "alert",   to: "compliance" },
  ],
  credit_officer:     [{ from: "credit",  to: "report" }],
  compliance_officer: [{ from: "compliance",  to: "report" }],
  risk_manager: [
    { from: "alert", to: "compliance" },
    { from: "alert", to: "credit" },
  ],
  admin: [
    { from: "channel", to: "report" },
    { from: "report",  to: "credit" },
    { from: "alert",   to: "compliance" },
    { from: "alert",   to: "credit" },
    { from: "credit",  to: "report" },
    { from: "compliance",  to: "report" },
  ],
};

interface AuthState {
  currentUser: User | null;
  /** /me 解析后 backend 给的 accessibleAgents · 与本地 ACCESS 应一致 (single source of truth = backend) */
  accessibleAgents: readonly AgentId[];
  /** bootstrap 是否已尝试一次 (避免初始 hydrate 时 UI 闪) */
  bootstrapped: boolean;
  /** in-flight login/logout · UI 防重复点击 */
  authBusy: boolean;
  /** 上次 login/me 错误 · UI 显错误条 */
  lastError: string | null;
  users: User[];

  bootstrap: () => Promise<void>;
  login: (userId: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  /** 判定权限；无登录一律 false */
  can: (action: PermissionAction) => boolean;
}

export const useAuthStore = create<AuthState>()((set, get) => ({
  currentUser: null,
  accessibleAgents: [],
  bootstrapped: false,
  authBusy: false,
  lastError: null,
  users: DEMO_USERS,

  bootstrap: async () => {
    if (get().bootstrapped) return;
    try {
      const me = await fetchMe();
      set({
        currentUser: me.user as User,
        accessibleAgents: me.accessibleAgents as readonly AgentId[],
        bootstrapped: true,
        lastError: null,
      });
    } catch (err) {
      // 401 / network error · 视作未登录 · 不 redirect (上层 AuthGate 决定)
      if (!(err instanceof AuthApiError) && err) {
        console.warn("[auth] bootstrap network error:", err);
      }
      set({
        currentUser: null,
        accessibleAgents: [],
        bootstrapped: true,
        lastError: null,
      });
    }
  },

  login: async (userId, password) => {
    if (get().authBusy) return false;
    set({ authBusy: true, lastError: null });
    try {
      const res = await loginApi(userId, password);
      set({
        currentUser: res.user as User,
        accessibleAgents: res.accessibleAgents as readonly AgentId[],
        authBusy: false,
        lastError: null,
        bootstrapped: true,
      });
      return true;
    } catch (err) {
      const msg = err instanceof AuthApiError ? err.message : "登录失败 · 网络异常";
      set({ authBusy: false, lastError: msg });
      return false;
    }
  },

  logout: async () => {
    if (get().authBusy) return;
    set({ authBusy: true });
    try {
      await logoutApi();
    } catch (err) {
      // 即使 backend 出错也清前端状态 (cookie 由 backend 控 · 浏览器可能仍残留 · 但 /me 401 后续会兜底)
      console.warn("[auth] logout backend error:", err);
    }
    set({
      currentUser: null,
      accessibleAgents: [],
      authBusy: false,
      lastError: null,
    });
  },

  can: (action) => {
    const u = get().currentUser;
    if (!u) return false;
    switch (action.kind) {
      case "agent.access":
        return ACCESS[u.role].includes(action.agent);
      case "handoff.create":
        return HANDOFFS[u.role].some(
          (h) => h.from === action.from && h.to === action.to,
        );
      case "handoff.accept":
        return ACCESS[u.role].includes(action.agent);
      case "customer.assign":
        return u.role === "rm" || u.role === "admin";
      case "audit.view":
        return u.role === "compliance_officer" || u.role === "admin";
      default:
        return false;
    }
  },
}));

export const byUserId = (id: string) => DEMO_USERS.find((u) => u.id === id);

// 仅类型 / 静态查询用 · 不通过 useAuthStore 也能用
export { ACCESS, HANDOFFS };
