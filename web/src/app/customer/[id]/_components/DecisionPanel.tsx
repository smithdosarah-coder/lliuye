"use client";

/**
 * DecisionPanel · 走访闭环 demo (Phase C Track A · A3)
 *
 * 走访闭环 4 步:
 *   1. 选客户 (上一页 customer list)
 *   2. AI 决策建议 (调 POST /api/decision/build)
 *   3. RM review (accept/modify/reject · 调 POST /api/decision/{id}/review)
 *   4. 导出 word/pdf (调 POST /api/decision/{id}/export)
 */

import { useState } from "react";
import { useAuthStore } from "@/lib/store";

interface DecisionResult {
  decision_id: string | null;
  customer_id: string;
  intent: string;
  reasons: Array<{
    text: string;
    source_tier: string;
    source_url: string;
    evidence_date: string;
    freshness_days: number;
    claim_type: string;
    reason_confidence: number;
    staleness_policy_passed: boolean;
  }>;
  core_reasons_count: number;
  background_reasons_count: number;
  decision_summary: string;
  confidence: number;
  block: boolean;
  block_reason: string | null;
  tier_distribution: Record<string, number>;
  metadata?: {
    model: string;
    model_status: string;
    is_llm_grounded: boolean;
    generated_at: string;
  };
}

const TIER_LABEL: Record<string, string> = {
  internal_authoritative: "内部权威",
  government: "政府监管",
  industry: "行业",
  public_web: "公开 web",
  unknown: "未识别",
};

export function DecisionPanel({ customerId }: { customerId: string }) {
  const currentUser = useAuthStore((s) => s.currentUser);
  const reviewerId = currentUser ? `RM-${currentUser.name}` : "RM-未登录";

  const [decision, setDecision] = useState<DecisionResult | null>(null);
  const [building, setBuilding] = useState(false);
  const [reviewStatus, setReviewStatus] = useState<string | null>(null);
  const [exportStatus, setExportStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleBuild() {
    setBuilding(true);
    setError(null);
    setReviewStatus(null);
    setExportStatus(null);
    try {
      const r = await fetch("/api/decision/build", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ customer_id: customerId, intent: "ai_advice_proactive" }),
      });
      if (!r.ok) {
        const text = await r.text();
        throw new Error(`HTTP ${r.status}: ${text.slice(0, 200)}`);
      }
      const data = (await r.json()) as DecisionResult;
      setDecision(data);
    } catch (e) {
      setError(`${e}`);
    } finally {
      setBuilding(false);
    }
  }

  async function handleReview(action: "accept" | "modify" | "reject") {
    if (!decision?.decision_id) return;
    let reason = "";
    if (action !== "accept") {
      reason = window.prompt(`${action === "modify" ? "修改" : "驳回"}原因 (≥ 5 字):`) || "";
      if (reason.trim().length < 5) {
        setError(`${action} 必带 reason ≥ 5 字 · 已取消`);
        return;
      }
    }
    setReviewStatus(`提交中 (${action})...`);
    setError(null);
    try {
      const r = await fetch(`/api/decision/${decision.decision_id}/review`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          decision_id: decision.decision_id,
          reviewer: reviewerId,
          action,
          reason,
        }),
      });
      if (!r.ok) {
        const text = await r.text();
        throw new Error(`HTTP ${r.status}: ${text.slice(0, 200)}`);
      }
      const data = await r.json();
      setReviewStatus(`✓ ${action} 成功 · review_id=${data.review_id} · ledger=${data.ledger_persisted ? "已上链" : "未上链"}`);
    } catch (e) {
      setError(`review 失败: ${e}`);
      setReviewStatus(null);
    }
  }

  async function handleExport(format: "docx" | "pdf") {
    if (!decision?.decision_id) return;
    setExportStatus(`导出 ${format.toUpperCase()} 中...`);
    setError(null);
    try {
      const r = await fetch(`/api/decision/${decision.decision_id}/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          decision_id: decision.decision_id,
          format,
        }),
      });
      if (!r.ok) {
        const text = await r.text();
        throw new Error(`HTTP ${r.status}: ${text.slice(0, 200)}`);
      }
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `walkthrough_${decision.decision_id}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setExportStatus(`✓ ${format.toUpperCase()} 已下载 (${blob.size} bytes)`);
    } catch (e) {
      setError(`导出失败: ${e}`);
      setExportStatus(null);
    }
  }

  return (
    <section
      className="v-customer-decision-panel"
      data-testid="customer-decision-panel"
      style={{
        padding: 16,
        margin: "12px 0",
        background: "var(--chalk)",
        borderRadius: 12,
        border: "1px solid var(--ink-14)",
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
          AI 决策建议 · 走访闭环
        </h3>
        {!decision && (
          <button
            type="button"
            onClick={handleBuild}
            disabled={building}
            data-testid="customer-decision-build-btn"
            style={{
              padding: "6px 16px",
              fontSize: 12,
              fontFamily: "var(--mono)",
              background: "var(--accent)",
              color: "var(--chalk)",
              border: "none",
              borderRadius: 12,
              cursor: building ? "wait" : "pointer",
              opacity: building ? 0.5 : 1,
            }}
          >
            {building ? "生成中…" : "→ 调用 AI 建议"}
          </button>
        )}
      </header>

      {error && (
        <div
          data-testid="customer-decision-error"
          role="alert"
          style={{
            padding: 12,
            marginBottom: 12,
            background: "color-mix(in srgb, var(--accent) 8%, transparent)",
            borderRadius: 8,
            color: "var(--accent)",
            fontSize: 13,
          }}
        >
          {error}
        </div>
      )}

      {decision && decision.block && (
        <div
          data-testid="customer-decision-blocked"
          role="alert"
          style={{
            padding: 12,
            background: "color-mix(in srgb, var(--accent) 16%, transparent)",
            borderRadius: 8,
            color: "var(--accent)",
            fontSize: 13,
          }}
        >
          ⚠ 决策受阻: {decision.block_reason}
        </div>
      )}

      {decision && !decision.block && (
        <div data-testid="customer-decision-result" style={{ fontFamily: "var(--cjk)" }}>
          {/* Tier 0.3 · ai_decision honest 标注 (PM 5/7 拍板) · 用户看清是 LLM 还是 fallback */}
          {decision.metadata && !decision.metadata.is_llm_grounded && (
            <div
              data-testid="customer-decision-honest-banner"
              role="note"
              style={{
                padding: "6px 12px",
                marginBottom: 10,
                background: "color-mix(in srgb, var(--ink-14) 50%, transparent)",
                borderLeft: "3px solid var(--ink-48)",
                borderRadius: 4,
                fontSize: 12,
                color: "var(--ink-65)",
              }}
            >
              ⓘ {decision.metadata.model_status} · 模型: <code>{decision.metadata.model}</code>
            </div>
          )}
          <p style={{ margin: "4px 0 12px 0", fontSize: 13 }}>{decision.decision_summary}</p>
          <div style={{ display: "flex", gap: 12, fontSize: 12, marginBottom: 12 }}>
            <span>
              核心理由 · <b>{decision.core_reasons_count}</b>
            </span>
            <span>
              背景 · <b>{decision.background_reasons_count}</b>
            </span>
            <span>
              置信度 · <b>{decision.confidence}</b>
            </span>
          </div>

          <details style={{ marginBottom: 12 }}>
            <summary style={{ cursor: "pointer", fontSize: 12, opacity: 0.7 }}>
              展开 {decision.reasons.length} 条理由 (含证据链)
            </summary>
            <ol style={{ marginTop: 8, paddingLeft: 20, fontSize: 12 }}>
              {decision.reasons.map((r, i) => (
                <li key={i} style={{ marginBottom: 8 }}>
                  <div>{r.text}</div>
                  <div style={{ fontSize: 11, opacity: 0.6, fontFamily: "var(--mono)" }}>
                    [{TIER_LABEL[r.source_tier] ?? r.source_tier}] · {r.source_url} ·{" "}
                    {r.freshness_days}d · {r.staleness_policy_passed ? "时效✓" : "过期"}
                  </div>
                </li>
              ))}
            </ol>
          </details>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button
              type="button"
              onClick={() => handleReview("accept")}
              data-testid="customer-decision-accept-btn"
              style={btnStyle("accept")}
            >
              ✓ 接受
            </button>
            <button
              type="button"
              onClick={() => handleReview("modify")}
              data-testid="customer-decision-modify-btn"
              style={btnStyle("modify")}
            >
              ✎ 修改
            </button>
            <button
              type="button"
              onClick={() => handleReview("reject")}
              data-testid="customer-decision-reject-btn"
              style={btnStyle("reject")}
            >
              ✗ 驳回
            </button>
            <span style={{ flex: 1 }} />
            <button
              type="button"
              onClick={() => handleExport("docx")}
              data-testid="customer-decision-export-docx-btn"
              style={btnStyle("export")}
            >
              ⇩ 导出 Word
            </button>
            <button
              type="button"
              onClick={() => handleExport("pdf")}
              data-testid="customer-decision-export-pdf-btn"
              style={btnStyle("export")}
            >
              ⇩ 导出 PDF
            </button>
          </div>

          {reviewStatus && (
            <div
              data-testid="customer-decision-review-status"
              style={{
                marginTop: 8,
                fontSize: 11,
                fontFamily: "var(--mono)",
                color: "var(--accent)",
              }}
            >
              {reviewStatus}
            </div>
          )}
          {exportStatus && (
            <div
              data-testid="customer-decision-export-status"
              style={{
                marginTop: 8,
                fontSize: 11,
                fontFamily: "var(--mono)",
                color: "var(--accent)",
              }}
            >
              {exportStatus}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function btnStyle(kind: "accept" | "modify" | "reject" | "export"): React.CSSProperties {
  return {
    padding: "6px 12px",
    fontSize: 12,
    fontFamily: "var(--mono)",
    background: kind === "accept"
      ? "color-mix(in srgb, var(--accent) 16%, transparent)"
      : kind === "reject"
      ? "color-mix(in srgb, var(--ink-14) 50%, transparent)"
      : "color-mix(in srgb, var(--ink-08) 80%, transparent)",
    color: kind === "accept" ? "var(--accent)" : "var(--ink)",
    border: `1px solid ${kind === "accept" ? "var(--accent)" : "var(--ink-14)"}`,
    borderRadius: 12,
    cursor: "pointer",
  };
}
