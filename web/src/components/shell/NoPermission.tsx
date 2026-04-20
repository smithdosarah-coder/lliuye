"use client";

import Link from "next/link";
import { AGENTS, type AgentKey } from "@/lib/agents";
import { useAuthStore } from "@/lib/store";
import type { Role } from "@/lib/store/types";

const ROLE_LABEL: Record<Role, string> = {
  rm: "客户经理",
  credit_officer: "审贷官",
  compliance_officer: "合规官",
  risk_manager: "风险经理",
  admin: "平台管理员",
};

/**
 * NoPermission — 温和解释型"无权访问"，不是 403 报错。
 * 参考 Stripe：告诉用户"你的角色不包含这个模块"，指引下一步（返回 / 协作）。
 */
export function NoPermission({ agent }: { agent?: AgentKey }) {
  const user = useAuthStore((s) => s.currentUser);
  const def = agent ? AGENTS.find((a) => a.key === agent) : null;
  const roleLabel = user ? ROLE_LABEL[user.role] : "当前角色";

  return (
    <div className="no-permission">
      <div className="eyebrow">
        <span>ACCESS · 未授权</span>
        <span className="sep" />
        <em>scope limited.</em>
      </div>
      <h1 className="no-permission-h1">
        <span className="cn">你的角色暂无此模块权限</span>{" "}
        <span className="en">
          <em>out of scope.</em>
        </span>
      </h1>
      <p className="lede">
        {def ? (
          <>
            「<strong>{def.title}</strong>」不在 <strong>{roleLabel}</strong> 的默认职责范围内。
          </>
        ) : (
          <>当前入口不对 <strong>{roleLabel}</strong> 开放。</>
        )}
        {" "}如确需查看本模块产出，请在「对话」里跨岗发起协作，或联系平台管理员调整角色。
      </p>
      <div className="no-permission-actions">
        <Link href="/today" className="no-permission-btn primary">
          返回今日
        </Link>
        <Link href="/dispatch" className="no-permission-btn">
          去对话协作 <em>↘</em>
        </Link>
        <Link href="/archive" className="no-permission-btn">
          助手目录
        </Link>
      </div>
    </div>
  );
}
