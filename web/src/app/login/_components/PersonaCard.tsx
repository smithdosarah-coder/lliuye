"use client";

import { useAuthStore } from "@/lib/store";
import type { Role, User } from "@/lib/store/types";
import { useRouter } from "next/navigation";

const ROLE_LABEL: Record<Role, string> = {
  rm: "客户经理",
  credit_officer: "审贷官",
  compliance_officer: "合规官",
  risk_manager: "风险经理",
  admin: "平台管理员",
};

const ROLE_BLURB: Record<Role, string> = {
  rm: "获客 / 报告 / 授信 / 预警 / 合规 / 风控 — 全线可见。",
  credit_officer: "聚焦授信决策 · 读报告 · 看预警。",
  compliance_officer: "政策冲突巡检 · 审计视图 · 全局可查。",
  risk_manager: "风控规则运营 · 预警 · 授信交叉查看。",
  admin: "全部模块 + 审计 + 配置面板。",
};

export function PersonaCard({ user }: { user: User }) {
  const login = useAuthStore((s) => s.login);
  const router = useRouter();

  function handlePick() {
    if (login(user.id)) router.replace("/today");
  }

  return (
    <button
      type="button"
      className="persona-card"
      onClick={handlePick}
      data-role={user.role}
    >
      <span className="persona-avatar" aria-hidden>
        {user.avatar ?? user.name.slice(-1)}
      </span>
      <span className="persona-body">
        <span className="persona-name">
          <span className="cn">{user.name}</span>
          <span className="role">{ROLE_LABEL[user.role]}</span>
        </span>
        <span className="persona-team">{user.team}</span>
        <span className="persona-blurb">{ROLE_BLURB[user.role]}</span>
      </span>
      <span className="persona-go" aria-hidden>
        进入 <em>↘</em>
      </span>
    </button>
  );
}
