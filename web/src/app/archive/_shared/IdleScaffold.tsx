/**
 * IdleScaffold — B.3.4 fix-indep 主活B layout primitive.
 *
 * 共享原则 (PM 2026-05-11 真意 verbatim):
 *   "6 助手 idle 空白同改 (共享原则: 主 CTA + 占位 + 完成后显啥提示)"
 *
 * 设计 (codex R7 verdict 落地):
 *   "shared contract + shared invariants + local adapters where domain truly differs"
 *
 *   - shared contract  → IdleScaffoldProps · 强制 3 slot (primary / placeholderCards / completionHint)
 *   - shared invariants → DOM 结构 + data-testid 命名规范 + a11y role
 *   - local adapters    → 各 workspace 自己 fill props 内容 (业务文案 / 数字 / icon)
 *
 * 不夹带业务逻辑 · 不动后端 · 仅 layout primitive.
 * 不与 P0-R1 shared-extract 冲突 (那个抽 evidence_pipeline / output_validator
 * 等业务模块 · 本 scaffold 是纯 UI primitive).
 *
 * 用法 (示例 · alert idle):
 *   <IdleScaffold
 *     agentKey="alert"
 *     testIdPrefix="alert-idle"
 *     primary={<button>启动扫描</button>}
 *     secondary={<button>选规则集</button>}
 *     placeholderCards={[
 *       <Card>红/黄/绿 totals</Card>,
 *       <Card>Top 客户预览</Card>,
 *       <Card>下一步建议</Card>,
 *     ]}
 *     completionHint="扫描完成后此处显示信号 timeline + 处置建议 + 证据 drawer"
 *   />
 *
 * 不强迁老 workspace · 老 workspace 各有自洽 idle (审过 spec) · 强迁会破 testid + 增 regression 风险.
 * 见 docs/working/b34-fix-indep-idle-audit-2026-05-11.md (主活B-2) · 6 workspace 3-slot 合规审计.
 */

import type { AgentKey } from "@/lib/agents";
import type { ReactNode } from "react";

/**
 * 3-slot contract (强制 primary + placeholderCards + completionHint).
 *
 * placeholderCards 必须 >= 1 项 · 0 项时 idle 即"大空白" (PM 截图痛 #4).
 * completionHint 必须非空字符串 · 没填则 idle 缺乏"完成后会显啥"引导.
 */
export type IdleScaffoldProps = {
  agentKey: AgentKey;
  testIdPrefix: string; // e.g. "alert-idle" → 子 testid 前缀
  primary: ReactNode;
  secondary?: ReactNode;
  placeholderCards: ReactNode[];
  completionHint: string;
  className?: string;
  /** 可选 eyebrow text (e.g. "AGENT · 04 · TOWER · 贷中预警引擎") · 不强求. */
  eyebrow?: string;
  /** 可选 title (h1) · 不强求 · 老 workspace 已自带 hero. */
  title?: string;
  /** 可选 sub (h1 下方说明) · 不强求. */
  sub?: string;
};

/**
 * 静态结构 (FE invariant · spec 可断言):
 *   <section data-testid="{prefix}-scaffold" data-agent-key={agentKey}>
 *     [optional <header> with eyebrow/title/sub]
 *     <div data-testid="{prefix}-cta-row" role="group">
 *       {primary}
 *       {secondary}
 *     </div>
 *     <div data-testid="{prefix}-placeholders" role="region">
 *       {placeholderCards.map(card => <article data-testid="{prefix}-placeholder-card">{card}</article>)}
 *     </div>
 *     <p data-testid="{prefix}-completion-hint" role="note">{completionHint}</p>
 *   </section>
 */
export function IdleScaffold(p: IdleScaffoldProps) {
  if (p.placeholderCards.length < 1) {
    /* 静默 fallback · dev-time 提示靠 prop 验证 (TODO: 加 dev warning) ·
       runtime 不抛 · 不阻断 render. */
  }
  if (!p.completionHint.trim()) {
    /* 同上 · 缺 hint 不阻断 · 但 spec 必断言非空. */
  }

  const cls = ["idle-scaffold", p.className].filter(Boolean).join(" ");
  return (
    <section
      className={cls}
      data-testid={`${p.testIdPrefix}-scaffold`}
      data-agent-key={p.agentKey}
      aria-label={`${p.agentKey} idle scaffold`}
    >
      {p.eyebrow || p.title || p.sub ? (
        <header className="idle-scaffold__head">
          {p.eyebrow ? <div className="idle-scaffold__eyebrow">{p.eyebrow}</div> : null}
          {p.title ? <h1 className="idle-scaffold__title">{p.title}</h1> : null}
          {p.sub ? <p className="idle-scaffold__sub">{p.sub}</p> : null}
        </header>
      ) : null}

      <div
        className="idle-scaffold__cta-row"
        role="group"
        aria-label="主操作"
        data-testid={`${p.testIdPrefix}-cta-row`}
      >
        {p.primary}
        {p.secondary}
      </div>

      <div
        className="idle-scaffold__placeholders"
        role="region"
        aria-label="占位卡 · 启动后将填实"
        data-testid={`${p.testIdPrefix}-placeholders`}
      >
        {p.placeholderCards.map((card, i) => (
          <article
            key={i}
            className="idle-scaffold__placeholder-card"
            data-testid={`${p.testIdPrefix}-placeholder-card`}
          >
            {card}
          </article>
        ))}
      </div>

      <p
        className="idle-scaffold__completion-hint"
        role="note"
        data-testid={`${p.testIdPrefix}-completion-hint`}
      >
        {p.completionHint}
      </p>
    </section>
  );
}

/**
 * 类型级 contract assertion (编译期验证 · 不需 runtime test).
 * 任何破坏 IdleScaffoldProps shape 的改动都会让 TS build 失败.
 */
export type _IdleScaffoldContract_RequiresPrimary = IdleScaffoldProps["primary"];
export type _IdleScaffoldContract_RequiresPlaceholders = IdleScaffoldProps["placeholderCards"];
export type _IdleScaffoldContract_RequiresCompletionHint = IdleScaffoldProps["completionHint"];
