"use client";

import { byUserId } from "@/lib/store";
import type { Customer, Role, User } from "@/lib/store/types";

const ROLE_LABEL: Record<Role, string> = {
  rm: "客户经理",
  credit_officer: "审贷官",
  compliance_officer: "合规官",
  risk_manager: "风险经理",
  admin: "管理员",
};

export function CollaboratorList({ customer }: { customer: Customer }) {
  const owner = byUserId(customer.assignedTo);
  const shared = customer.sharedWith
    .map(byUserId)
    .filter((u): u is User => Boolean(u));

  return (
    <section className="v-customer-team">
      <div className="sec-head">
        <span className="sep" />
        <em>协同人员</em>
      </div>
      <div className="team-block owner">
        <div className="team-label">负责人</div>
        {owner ? (
          <div className="person">
            <span className="avatar">{owner.avatar ?? owner.name[0]}</span>
            <span className="info">
              <span className="nm">{owner.name}</span>
              <span className="sub">
                {ROLE_LABEL[owner.role]} · {owner.team}
              </span>
            </span>
          </div>
        ) : (
          <div className="person muted">未指派</div>
        )}
      </div>
      <div className="team-block">
        <div className="team-label">
          协同 <em>{shared.length}</em>
        </div>
        {shared.length === 0 ? (
          <div className="person muted">暂无协同人员</div>
        ) : (
          <ul className="team-list">
            {shared.map((u) => (
              <li key={u.id} className="person">
                <span className="avatar sm">{u.avatar ?? u.name[0]}</span>
                <span className="info">
                  <span className="nm">{u.name}</span>
                  <span className="sub">
                    {ROLE_LABEL[u.role]} · {u.team}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
