"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuthStore } from "@/lib/store";

interface CustomerListItem {
  customer_id: string;
  name: string;
  age: number;
  city: string;
  risk_level: string;
  credit_score: number;
  relationship_manager_id: string;
  last_contact_at: string | null;
  consent_status: string;
}

const RISK_LABEL: Record<string, string> = {
  conservative: "保守",
  balanced: "平衡",
  growth: "成长",
  aggressive: "激进",
};

const CONSENT_LABEL: Record<string, string> = {
  granted: "已授权",
  pending: "待签",
  revoked: "已撤销",
};

export function CustomerListClient() {
  const currentUser = useAuthStore((s) => s.currentUser);
  const [items, setItems] = useState<CustomerListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filterMine, setFilterMine] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const rmId = filterMine && currentUser
      ? `RM-${currentUser.name}`
      : "";
    const url = rmId
      ? `/api/customer/list?rm=${encodeURIComponent(rmId)}`
      : "/api/customer/list";

    fetch(url)
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        if (cancelled) return;
        setItems((data as { items: CustomerListItem[] }).items || []);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(`${e}`);
      });

    return () => {
      cancelled = true;
    };
  }, [currentUser, filterMine]);

  return (
    <div className="v-customer-list" style={{ padding: 24, fontFamily: "var(--cjk)" }}>
      <header style={{ marginBottom: 24 }}>
        <h1 style={{ fontFamily: "var(--display)", fontSize: 28, margin: 0 }}>
          客户列表
        </h1>
        <p style={{ opacity: 0.7, margin: "8px 0 0 0", fontSize: 13 }}>
          {filterMine
            ? `仅显 ${currentUser?.name ?? "未登录"} 的客户`
            : "全量客户"} · 走访闭环第 1 步
        </p>
        <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
          <button
            type="button"
            onClick={() => setFilterMine(true)}
            data-testid="customer-list-filter-mine"
            style={{
              padding: "6px 14px",
              fontSize: 12,
              fontFamily: "var(--mono)",
              background: filterMine
                ? "var(--accent)"
                : "color-mix(in srgb, var(--ink-14) 50%, transparent)",
              color: filterMine ? "var(--chalk)" : "var(--ink-65)",
              border: "1px solid var(--ink-14)",
              borderRadius: 12,
              cursor: "pointer",
            }}
          >
            我的客户
          </button>
          <button
            type="button"
            onClick={() => setFilterMine(false)}
            data-testid="customer-list-filter-all"
            style={{
              padding: "6px 14px",
              fontSize: 12,
              fontFamily: "var(--mono)",
              background: !filterMine
                ? "var(--accent)"
                : "color-mix(in srgb, var(--ink-14) 50%, transparent)",
              color: !filterMine ? "var(--chalk)" : "var(--ink-65)",
              border: "1px solid var(--ink-14)",
              borderRadius: 12,
              cursor: "pointer",
            }}
          >
            全行客户
          </button>
        </div>
      </header>

      {error ? (
        <div
          data-testid="customer-list-error"
          style={{
            padding: 16,
            background: "color-mix(in srgb, var(--accent) 8%, transparent)",
            borderRadius: 12,
            color: "var(--accent)",
          }}
        >
          客户列表加载失败 · {error}
        </div>
      ) : items === null ? (
        <div data-testid="customer-list-loading" style={{ opacity: 0.6 }}>
          加载中…
        </div>
      ) : items.length === 0 ? (
        <div
          data-testid="customer-list-empty"
          style={{
            padding: 48,
            textAlign: "center",
            background: "color-mix(in srgb, var(--ink-08) 50%, transparent)",
            borderRadius: 12,
          }}
        >
          <p style={{ opacity: 0.6 }}>
            暂无客户 ·{filterMine ? " 切换 [全行客户] 看全部" : " "}
          </p>
        </div>
      ) : (
        <ul
          data-testid="customer-list"
          style={{
            listStyle: "none",
            margin: 0,
            padding: 0,
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
            gap: 12,
          }}
        >
          {items.map((c) => (
            <li
              key={c.customer_id}
              data-customer-id={c.customer_id}
              style={{
                background: "var(--chalk)",
                border: "1px solid var(--ink-14)",
                borderRadius: 14,
                padding: 16,
              }}
            >
              <Link
                href={`/customer/${c.customer_id}`}
                style={{
                  textDecoration: "none",
                  color: "inherit",
                  display: "block",
                }}
              >
                <header
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "baseline",
                    marginBottom: 8,
                  }}
                >
                  <h3 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>
                    {c.name}
                  </h3>
                  <span
                    style={{
                      fontSize: 11,
                      fontFamily: "var(--mono)",
                      opacity: 0.5,
                    }}
                  >
                    {c.customer_id}
                  </span>
                </header>
                <dl
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                    gap: 6,
                    margin: 0,
                    fontSize: 12,
                  }}
                >
                  <KV label="年龄" value={`${c.age} 岁`} />
                  <KV label="城市" value={c.city} />
                  <KV
                    label="风险偏好"
                    value={`${RISK_LABEL[c.risk_level] ?? c.risk_level}`}
                  />
                  <KV label="征信分" value={`${c.credit_score}`} />
                </dl>
                <footer
                  style={{
                    marginTop: 10,
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: 11,
                    opacity: 0.7,
                  }}
                >
                  <span>RM · {c.relationship_manager_id}</span>
                  <span
                    data-consent={c.consent_status}
                    style={{
                      fontFamily: "var(--mono)",
                      color:
                        c.consent_status === "granted"
                          ? "var(--accent)"
                          : "var(--ink-65)",
                    }}
                  >
                    {CONSENT_LABEL[c.consent_status] ?? c.consent_status}
                  </span>
                </footer>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function KV({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span
        style={{
          fontSize: 10,
          fontFamily: "var(--mono)",
          opacity: 0.55,
          textTransform: "uppercase",
          letterSpacing: "0.05em",
        }}
      >
        {label}
      </span>
      <div style={{ fontSize: 12, color: "var(--ink)" }}>{value}</div>
    </div>
  );
}
