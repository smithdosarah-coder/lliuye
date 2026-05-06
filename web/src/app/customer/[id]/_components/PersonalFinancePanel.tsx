"use client";

/**
 * PersonalFinancePanel · toC 个人金融画像 (Phase C Track A · A2 前端)
 *
 * 数据源: GET /api/customer/{id}/profile (backend shared/customer_aggregator.py)
 * 显: CRM 15 字段 (subset · 金融关键) + 现持产品 + RM 互动 + consent_status
 * PIPL: consent != granted 显示警告 (不能调 AI 决策)
 */

import { useEffect, useState } from "react";

interface CrmProfile {
  customer_id: string;
  name: string;
  age: number;
  city: string;
  occupation: string;
  income_monthly: number;
  employment_status: string;
  existing_products: string[];
  credit_score: number;
  debt_ratio: number;
  risk_level: string;
  last_contact_at: string | null;
  relationship_manager_id: string;
  consent_status: string;
}

interface AggregatedProfile {
  customer: CrmProfile;
  history: unknown[];
  holdings: Array<{ product_name: string; status: string; since: string }>;
  rm_interactions: Array<{ rm_id: string; type: string; at: string | null; notes: string }>;
  metadata: {
    aggregated_at: string;
    source_count: number;
    consent_status: string;
    schema_version: string;
  };
}

const RISK_LABEL: Record<string, string> = {
  conservative: "保守",
  balanced: "平衡",
  growth: "成长",
  aggressive: "激进",
};

const EMPLOYMENT_LABEL: Record<string, string> = {
  employed: "在职",
  self_employed: "自雇",
  retired: "退休",
  student: "学生",
  unemployed: "无业",
};

const CONSENT_LABEL: Record<string, string> = {
  granted: "已授权",
  pending: "待签",
  revoked: "已撤销",
};

export function PersonalFinancePanel({ customerId }: { customerId: string }) {
  const [profile, setProfile] = useState<AggregatedProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetch(`/api/customer/${customerId}/profile`)
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        if (cancelled) return;
        setProfile(data as AggregatedProfile);
        setLoading(false);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(`${e}`);
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [customerId]);

  if (loading) {
    return (
      <section
        className="v-customer-personal-finance"
        data-testid="customer-personal-finance-loading"
        style={{ padding: 16, fontFamily: "var(--cjk)" }}
      >
        <span style={{ opacity: 0.6 }}>加载个人金融画像 · {customerId}</span>
      </section>
    );
  }

  if (error) {
    return (
      <section
        className="v-customer-personal-finance"
        data-testid="customer-personal-finance-error"
        style={{
          padding: 16,
          color: "var(--accent)",
          background: "color-mix(in srgb, var(--accent) 6%, transparent)",
          borderRadius: 12,
          margin: "12px 0",
        }}
      >
        <span>个人金融画像加载失败 · {error}</span>
      </section>
    );
  }

  if (!profile) {
    return (
      <section
        className="v-customer-personal-finance"
        data-testid="customer-personal-finance-empty"
        style={{ padding: 16, opacity: 0.6 }}
      >
        <span>该客户暂无 toC 画像 (CRM 15 字段)</span>
      </section>
    );
  }

  const c = profile.customer;
  const consentOK = c.consent_status === "granted";

  return (
    <section
      className="v-customer-personal-finance"
      data-testid="customer-personal-finance"
      data-consent={c.consent_status}
      style={{
        padding: 16,
        margin: "12px 0",
        background: "color-mix(in srgb, var(--ink-08) 50%, transparent)",
        borderRadius: 12,
        border: `1px solid ${consentOK ? "var(--ink-14)" : "color-mix(in srgb, var(--accent) 30%, transparent)"}`,
      }}
    >
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: 12,
        }}
      >
        <h3 style={{ fontFamily: "var(--cjk)", fontSize: 15, fontWeight: 600, margin: 0 }}>
          个人金融画像 · {c.name}
        </h3>
        <span
          style={{
            fontSize: 11,
            fontFamily: "var(--mono)",
            padding: "2px 8px",
            borderRadius: 8,
            background: consentOK
              ? "color-mix(in srgb, var(--accent) 14%, transparent)"
              : "color-mix(in srgb, var(--accent) 28%, transparent)",
            color: "var(--accent)",
          }}
          title="PIPL 合规 · pending/revoked 不能用客户数据做 AI 决策"
        >
          {CONSENT_LABEL[c.consent_status] ?? c.consent_status}
        </span>
      </header>

      <dl
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
          gap: "8px 24px",
          margin: 0,
          fontFamily: "var(--cjk)",
          fontSize: 13,
        }}
      >
        <KV label="基本" value={`${c.age}岁 · ${c.city} · ${c.occupation}`} />
        <KV label="就业" value={EMPLOYMENT_LABEL[c.employment_status] ?? c.employment_status} />
        <KV label="月收入" value={`${(c.income_monthly / 10000).toFixed(1)} 万`} />
        <KV
          label="风险偏好"
          value={`${RISK_LABEL[c.risk_level] ?? c.risk_level} 型`}
        />
        <KV label="征信分" value={`${c.credit_score}`} />
        <KV label="负债比" value={`${(c.debt_ratio * 100).toFixed(0)}%`} />
        <KV label="客户经理" value={c.relationship_manager_id} />
        <KV
          label="上次接触"
          value={
            c.last_contact_at
              ? new Date(c.last_contact_at).toLocaleDateString("zh-CN")
              : "未接触"
          }
        />
      </dl>

      {profile.holdings.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <span
            style={{
              fontSize: 11,
              fontFamily: "var(--mono)",
              opacity: 0.6,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
            }}
          >
            现持产品 · {profile.holdings.length}
          </span>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 4 }}>
            {profile.holdings.map((h, i) => (
              <span
                key={i}
                style={{
                  fontSize: 12,
                  fontFamily: "var(--cjk)",
                  padding: "2px 8px",
                  borderRadius: 8,
                  background: "color-mix(in srgb, var(--ink-14) 50%, transparent)",
                  color: "var(--ink-80)",
                }}
              >
                {h.product_name}
              </span>
            ))}
          </div>
        </div>
      )}

      {!consentOK && (
        <p
          style={{
            margin: "12px 0 0 0",
            fontSize: 12,
            color: "var(--accent)",
            fontFamily: "var(--cjk)",
          }}
        >
          ⚠ 客户授权状态为「{CONSENT_LABEL[c.consent_status] ?? c.consent_status}」 ·
          PIPL 不允许此客户用 AI 决策 · 请联系客户重签授权
        </p>
      )}
    </section>
  );
}

function KV({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <dt
        style={{
          fontSize: 11,
          fontFamily: "var(--mono)",
          opacity: 0.55,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
        }}
      >
        {label}
      </dt>
      <dd style={{ margin: 0, color: "var(--ink)" }}>{value}</dd>
    </div>
  );
}
