import { AuditView } from "./AuditView";
import "./audit.css";

export const metadata = {
  title: "审计 · 乾策 Studio",
};

/**
 * Audit view · Phase 1 Batch 1 · Task D
 *
 * 仅合规官 + admin 可见（entry 层已过滤；页内再用 RBAC 守卫兜底 URL 直访）。
 * 消费 useEventBus.history（环形最近 200 条），前端实时协调审计；
 * 完整审计日志走后端 /api/audit（本页不直连）。
 */
export default function AuditPage() {
  return (
    <div className="v-audit">
      <AuditView />
    </div>
  );
}
