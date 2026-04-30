"use client";

/**
 * TicketDrawer —— 右侧滑入的 ticket 详情抽屉 + 全量操作链。
 *
 * Task B 完整功能：
 * - Accept: status → accepted + customer.advanceStage(toAgent 对应 stage) + publish handoff.accepted
 * - Reject: 必填 reason（≤140 字），status → rejected，ticket 从 kanban 消失（保留在 store）
 * - Reassign: 选 DEMO_USERS，update assignedTo + publish comment.added
 * - Archive: 从 store 移除（硬删）
 *
 * 状态 machine（简化）：
 *   requested → accepted（Accept）
 *   requested → rejected（Reject）
 *   accepted  → in_progress（手动拖拽或未来 UI 追加）
 *   in_progress → completed（手动拖拽）
 */
import { useEffect, useMemo, useState } from "react";

import {
  DEMO_USERS,
  byUserId,
  findRecipeById,
  useAuthStore,
  useCustomerStore,
  useEventBus,
  type AgentId,
  type CustomerStage,
} from "@/lib/store";
import { useTicketStore } from "../_store/ticket-store";

const AGENT_CN: Record<string, string> = {
  report: "报告助手",
  credit: "授信决策",
  channel: "获客雷达",
  alert: "贷中预警",
  compli: "合规巡查",
  riskctrl: "风控策略",
};

const TO_AGENT_STAGE: Record<AgentId, CustomerStage> = {
  channel: "lead",
  report: "report",
  credit: "credit",
  alert: "alert",
  compliance: "monitoring",
  riskctrl: "monitoring",
};

const REJECT_MAX = 140;

function findSourceEvent(eventId: string | undefined) {
  if (!eventId) return undefined;
  return useEventBus.getState().history.find((e) => e.id === eventId);
}

type Mode = "view" | "reject" | "reassign";

export function TicketDrawer({
  ticketId,
  onClose,
}: {
  ticketId: string | null;
  onClose: () => void;
}) {
  const ticket = useTicketStore((s) => (ticketId ? s.byId(ticketId) : undefined));
  const customer = useCustomerStore((s) =>
    ticket ? s.byId(ticket.customerId) : undefined,
  );
  const advanceStage = useCustomerStore((s) => s.advanceStage);
  const updateStatus = useTicketStore((s) => s.updateStatus);
  const reassign = useTicketStore((s) => s.reassign);
  const archive = useTicketStore((s) => s.archive);
  const currentUser = useAuthStore((s) => s.currentUser);

  const [mode, setMode] = useState<Mode>("view");
  const [rejectReason, setRejectReason] = useState("");
  const [pickUserId, setPickUserId] = useState<string>("");

  // Reset form state when ticket changes / drawer closes
  useEffect(() => {
    setMode("view");
    setRejectReason("");
    setPickUserId(ticket?.assignedTo ?? "");
  }, [ticketId, ticket?.assignedTo]);

  // Esc 关闭
  useEffect(() => {
    if (!ticketId) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (mode !== "view") setMode("view");
        else onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [ticketId, mode, onClose]);

  const open = Boolean(ticket);

  const recipe = useMemo(() => {
    if (!ticket) return undefined;
    // ticket 没存 recipeId，用 fromAgent+toAgent+reason 找最贴近的 recipe（description 取 reason match）
    const direct = findRecipeById(ticket.triggerEventId ?? "");
    if (direct) return direct;
    return undefined;
  }, [ticket]);

  if (!ticket) {
    return (
      <aside
        className={`tkt-drawer${open ? " tkt-drawer--open" : ""}`}
        aria-hidden={!open}
      />
    );
  }

  const sourceEvent = findSourceEvent(ticket.triggerEventId);
  const requestedBy = byUserId(ticket.requestedBy);
  const assignedTo = ticket.assignedTo ? byUserId(ticket.assignedTo) : undefined;
  const isTerminal = ticket.status === "completed" || ticket.status === "rejected";

  const handleAccept = () => {
    updateStatus(ticket.id, "accepted", {
      actor: currentUser?.id,
      reason: ticket.reason,
    });
    const nextStage = TO_AGENT_STAGE[ticket.toAgent];
    if (nextStage && customer && customer.stage !== nextStage) {
      advanceStage(ticket.customerId, nextStage);
    }
    onClose();
  };

  const handleRejectSubmit = () => {
    const reason = rejectReason.trim();
    if (!reason) return;
    updateStatus(ticket.id, "rejected", {
      actor: currentUser?.id,
      reason,
      publish: false,
    });
    onClose();
  };

  const handleReassignSubmit = () => {
    if (!pickUserId || pickUserId === ticket.assignedTo) {
      setMode("view");
      return;
    }
    reassign(ticket.id, pickUserId, currentUser?.id);
    setMode("view");
  };

  return (
    <>
      <div className="tkt-drawer-scrim" onClick={onClose} />
      <aside
        className="tkt-drawer tkt-drawer--open"
        role="dialog"
        aria-label="Ticket 详情"
      >
        <header className="tkt-dr-hd">
          <div className="tkt-dr-hd-meta">
            <span className="tkt-dr-chip">
              {AGENT_CN[ticket.fromAgent]} → {AGENT_CN[ticket.toAgent]}
            </span>
            <span className="tkt-dr-status" data-s={ticket.status}>
              {statusLabel(ticket.status)}
            </span>
          </div>
          <button className="tkt-dr-close" onClick={onClose} aria-label="关闭">
            ×
          </button>
        </header>

        <section className="tkt-dr-sec">
          <h3 className="tkt-dr-h3">客户</h3>
          <div className="tkt-dr-cust">
            <div className="tkt-dr-cust-name">
              {customer?.name ?? ticket.customerId}
            </div>
            <div className="tkt-dr-cust-meta">
              {customer?.industry ?? "行业 —"} · {customer?.region ?? "区域 —"}
              {customer?.amount ? ` · 授信 ${customer.amount} 万` : ""}
            </div>
            {customer?.tags?.length ? (
              <div className="tkt-dr-tags">
                {customer.tags.map((t) => (
                  <span key={t} className="tkt-dr-tag">
                    {t}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        </section>

        <section className="tkt-dr-sec">
          <h3 className="tkt-dr-h3">交接说明</h3>
          <p className="tkt-dr-reason">{ticket.reason}</p>
          {recipe?.description ? (
            <p className="tkt-dr-desc">{recipe.description}</p>
          ) : null}
        </section>

        <section className="tkt-dr-sec">
          <h3 className="tkt-dr-h3">Payload</h3>
          <pre className="tkt-dr-json">
            {JSON.stringify(ticket.payload ?? {}, null, 2)}
          </pre>
        </section>

        <section className="tkt-dr-sec">
          <h3 className="tkt-dr-h3">参与人</h3>
          <ul className="tkt-dr-roster">
            <li>
              <span className="tkt-dr-role">发起</span>
              <span>
                {requestedBy?.name ?? ticket.requestedBy} ·{" "}
                {requestedBy?.team ?? "—"}
              </span>
            </li>
            <li>
              <span className="tkt-dr-role">处理</span>
              <span>
                {assignedTo?.name ?? "待指派"}
                {assignedTo ? ` · ${assignedTo.team}` : ""}
              </span>
            </li>
          </ul>
        </section>

        {sourceEvent ? (
          <section className="tkt-dr-sec">
            <h3 className="tkt-dr-h3">来源事件</h3>
            <div className="tkt-dr-evt">
              <code>{sourceEvent.type}</code>
              <span className="tkt-dr-evt-time">
                {formatTime(sourceEvent.createdAt)}
              </span>
            </div>
          </section>
        ) : null}

        {mode === "reject" ? (
          <section className="tkt-dr-sec tkt-dr-form">
            <h3 className="tkt-dr-h3">拒绝原因（≤ {REJECT_MAX} 字）</h3>
            <textarea
              className="tkt-dr-textarea"
              maxLength={REJECT_MAX}
              rows={3}
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="说明退回原因，方便上游改材料 / 重填"
              autoFocus
            />
            <div className="tkt-dr-char-count">
              {rejectReason.length} / {REJECT_MAX}
            </div>
          </section>
        ) : null}

        {mode === "reassign" ? (
          <section className="tkt-dr-sec tkt-dr-form">
            <h3 className="tkt-dr-h3">重新指派</h3>
            <select
              className="tkt-dr-select"
              value={pickUserId}
              onChange={(e) => setPickUserId(e.target.value)}
              autoFocus
            >
              <option value="">— 选择处理人 —</option>
              {DEMO_USERS.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name} · {u.role} · {u.team}
                </option>
              ))}
            </select>
          </section>
        ) : null}

        <footer className="tkt-dr-ft">
          {mode === "view" ? (
            <>
              <div className="tkt-dr-ft-actions">
                {isTerminal ? (
                  <button
                    className="tkt-dr-btn tkt-dr-btn--ghost"
                    onClick={() => {
                      archive(ticket.id);
                      onClose();
                    }}
                  >
                    归档
                  </button>
                ) : (
                  <>
                    {ticket.status === "requested" ? (
                      <button
                        className="tkt-dr-btn tkt-dr-btn--primary"
                        onClick={handleAccept}
                      >
                        接受
                      </button>
                    ) : null}
                    {ticket.status === "requested" ? (
                      <button
                        className="tkt-dr-btn tkt-dr-btn--danger"
                        onClick={() => setMode("reject")}
                      >
                        拒绝
                      </button>
                    ) : null}
                    <button
                      className="tkt-dr-btn"
                      onClick={() => setMode("reassign")}
                    >
                      改派
                    </button>
                    <button
                      className="tkt-dr-btn tkt-dr-btn--ghost"
                      onClick={() => {
                        archive(ticket.id);
                        onClose();
                      }}
                    >
                      归档
                    </button>
                  </>
                )}
              </div>
              {!currentUser ? (
                <span className="tkt-dr-ft-hint">
                  未登录 · 操作仅影响本地 store，不记录 actor
                </span>
              ) : null}
            </>
          ) : null}

          {mode === "reject" ? (
            <>
              <button
                className="tkt-dr-btn tkt-dr-btn--ghost"
                onClick={() => setMode("view")}
              >
                取消
              </button>
              <button
                className="tkt-dr-btn tkt-dr-btn--danger"
                onClick={handleRejectSubmit}
                disabled={!rejectReason.trim()}
              >
                确认退回
              </button>
            </>
          ) : null}

          {mode === "reassign" ? (
            <>
              <button
                className="tkt-dr-btn tkt-dr-btn--ghost"
                onClick={() => setMode("view")}
              >
                取消
              </button>
              <button
                className="tkt-dr-btn tkt-dr-btn--primary"
                onClick={handleReassignSubmit}
                disabled={!pickUserId || pickUserId === ticket.assignedTo}
              >
                确认改派
              </button>
            </>
          ) : null}
        </footer>
      </aside>
    </>
  );
}

function statusLabel(s: string) {
  switch (s) {
    case "requested":
      return "待受理";
    case "accepted":
      return "已受理";
    case "in_progress":
      return "进行中";
    case "completed":
      return "已完成";
    case "rejected":
      return "已拒绝";
    default:
      return s;
  }
}

function formatTime(iso: string) {
  try {
    const d = new Date(iso);
    return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  } catch {
    return iso;
  }
}
