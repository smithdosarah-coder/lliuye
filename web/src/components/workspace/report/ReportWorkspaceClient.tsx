"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  Download,
  Play,
  RotateCcw,
  Trash2,
  Scale,
  Activity,
  ShieldCheck,
  ArrowRight,
  AlertTriangle,
} from "lucide-react";

import { Button } from "@/components/ui/Button";
import { FileDrop, type UploadedFile } from "@/components/ui/FileDrop";
import { Card, Stat } from "@/components/viz/Card";
import { PipelineRail } from "@/components/viz/PipelineRail";
import { QuestionnairePanel } from "@/components/ui/QuestionnairePanel";

import { getReportHealth, streamReportFill, streamReportRefine } from "@/lib/api";
import {
  INITIAL_REPORT_STATE,
  REPORT_STAGES,
  type BusinessLine,
  type ReportState,
  type ReportStage,
  type ReportSection,
} from "@/lib/credit-types";

const PRESETS: Array<{
  key: string;
  name: string;
  tagline: string;
  business_line: BusinessLine;
}> = [
  {
    key: "dingsheng_trade",
    name: "鼎盛商贸",
    tagline: "对公示例 · 建材批发 · 流贷 500 万",
    business_line: "corporate",
  },
  {
    key: "zhangsan_restaurant",
    name: "张某餐饮",
    tagline: "普惠示例 · 个体经营 · 50 万",
    business_line: "inclusive",
  },
];

// 业务线 → 预置模板文件名(客户不上传时显示为"内置默认")
const BUSINESS_LINE_TEMPLATES: Record<BusinessLine, string> = {
  corporate: "对公授信申报表-标准版.docx",
  inclusive: "普惠授信申报书-标准版.docx",
  reserved: "—",
};

const BUSINESS_LINE_OPTIONS: Array<{
  value: BusinessLine;
  label: string;
  disabled?: boolean;
  tooltip?: string;
}> = [
  { value: "corporate", label: "对公" },
  { value: "inclusive", label: "普惠" },
  { value: "reserved", label: "其他", disabled: true, tooltip: "敬请期待" },
];

type HandoffKey = "credit" | "alert" | "compliance";
const HANDOFF_CARDS: Array<{
  key: HandoffKey;
  title: string;
  subtitle: string;
  Icon: typeof Scale;
}> = [
  { key: "credit", title: "进入授信决策", subtitle: "报告 → 评分 → 额度建议", Icon: Scale },
  { key: "alert", title: "进入贷中预警", subtitle: "客户 × 风险规则矩阵", Icon: Activity },
  { key: "compliance", title: "进入合规核验", subtitle: "新政策 × 存量制度", Icon: ShieldCheck },
];

export function ReportWorkspaceClient() {
  const router = useRouter();
  const [preset, setPreset] = useState<string>("dingsheng_trade");
  const [businessLine, setBusinessLine] = useState<BusinessLine>("corporate");
  const [uploaded, setUploaded] = useState<UploadedFile[]>([]);
  const [templateUpload, setTemplateUpload] = useState<UploadedFile[]>([]);
  const [mockMode, setMockMode] = useState(true);
  const [state, setState] = useState<ReportState>(INITIAL_REPORT_STATE);
  const [llmConnected, setLlmConnected] = useState<boolean | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // 挂载时拉一次 LLM 状态(单次即可,不轮询——避免无谓流量)
  useEffect(() => {
    getReportHealth()
      .then((h) => setLlmConnected(h.llm_connected))
      .catch(() => setLlmConnected(false));
  }, []);

  const run = async (presetKey: string, lineOverride?: BusinessLine) => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    const line = lineOverride ?? businessLine;
    setPreset(presetKey);
    if (lineOverride) setBusinessLine(lineOverride);
    setState({
      ...INITIAL_REPORT_STATE,
      doneStages: new Set(),
      phase: "running",
    });

    // 真 pipeline 模式下,材料 File[] 和模板 File 需要真实传给后端
    const realFiles: File[] | undefined = mockMode
      ? undefined
      : (uploaded.map((u) => u.file).filter(Boolean) as File[]);
    const realTemplate: File | undefined = mockMode
      ? undefined
      : (templateUpload[0]?.file as File | undefined);

    // 超时守护:600s 未收到任何 stage 事件推进 → 视为卡死
    let lastEventAt = Date.now();
    const TIMEOUT_MS = 10 * 60 * 1000;
    const watchdog = setInterval(() => {
      if (Date.now() - lastEventAt > TIMEOUT_MS) {
        clearInterval(watchdog);
        abortRef.current?.abort();
        setState((s) => ({
          ...s,
          phase: "error",
          error: "生成超时(10 分钟无进度更新),请联系 IT 检查 LLM / pipeline 健康状态。",
        }));
      }
    }, 5000);

    try {
      for await (const evt of streamReportFill(
        {
          preset: presetKey,
          mock: mockMode,
          business_line: line,
          files: realFiles,
          template_file: realTemplate,
        },
        ctrl.signal
      )) {
        lastEventAt = Date.now();
        applyEvent(evt, setState);
      }
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      setState((s) => ({ ...s, phase: "error", error: String(e) }));
    } finally {
      clearInterval(watchdog);
    }
  };

  // 点击预置场景 chip:同时预填业务线 + 模板 + 触发生成
  const applyPreset = (p: (typeof PRESETS)[number]) => {
    setBusinessLine(p.business_line);
    setPreset(p.key);
    // 模板槽位清空(表示用业务线默认),材料槽位保持不变
    setTemplateUpload([]);
    // 只预填,不自动触发生成 — 用户审视后点"开始生成"
  };

  const reset = () => {
    abortRef.current?.abort();
    setState(INITIAL_REPORT_STATE);
  };

  const clearAll = () => {
    abortRef.current?.abort();
    setUploaded([]);
    setTemplateUpload([]);
    setState(INITIAL_REPORT_STATE);
  };

  const refine = async (
    answers: Array<{ id: string; answer: string; skipped?: boolean }>
  ) => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setState((s) => ({ ...s, phase: "refining", doneStages: new Set() }));

    try {
      for await (const evt of streamReportRefine(
        {
          session_id: state.sessionId,
          preset,
          profile_id: state.profile?.profile_id,
          answers: answers
            .filter((a) => !a.skipped && a.answer.trim())
            .map((a) => ({ id: a.id, value: a.answer })),
        },
        ctrl.signal
      )) {
        applyEvent(evt, setState);
      }
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      setState((s) => ({ ...s, phase: "error", error: String(e) }));
    }
  };

  const handoffTo = (key: HandoffKey) => {
    if (!state.profile) return;
    const url = state.handoff?.[key] ?? `/${key}?preset=${preset}`;
    try {
      sessionStorage.setItem(
        "enterprise_profile",
        JSON.stringify(state.profile)
      );
    } catch {
      // sessionStorage blocked — still proceed with in-app nav
    }
    router.push(url);
  };

  const running = state.phase === "running" || state.phase === "refining";
  const showRight =
    state.phase === "done" && state.pendingQuestions.length > 0;
  const showHandoff = state.phase === "done" && !!state.profile;

  // 真模式 + LLM 未连接 → 禁用"开始生成"(Mock 模式例外,允许)
  const realRunBlocked = !mockMode && llmConnected === false;
  const runDisabledTooltip = realRunBlocked
    ? "LLM 未连接,请联系 IT 配置 DEEPSEEK_API_KEY。可切 MOCK 模式继续演示。"
    : undefined;

  return (
    <div>
      {/* 顶部状态控件（原 header 右侧） */}
      <div className="flex items-center justify-end gap-4 mb-4 flex-wrap">
        <LLMStatusIndicator connected={llmConnected} />
        <MockToggle value={mockMode} onChange={setMockMode} disabled={running} />
      </div>

      {/* 顶部错误 banner — 不清空已生成内容,便于用户查看部分结果 */}
      {/* --color-ember → #c8463a (semantic danger; kept literal across themes) */}
      {state.phase === "error" && state.error && (
        <div className="mb-4 flex items-start gap-3 px-4 py-3 border-l-4 border-[#c8463a] bg-[rgba(200,60,40,0.06)]">
          <AlertTriangle size={18} className="text-[#c8463a] shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <div className="font-display text-[14px] text-[#c8463a]">
              生成遇到问题
            </div>
            <div className="mt-0.5 text-[12px] text-[var(--ink-80)] leading-relaxed break-all">
              {state.error}
            </div>
            <div className="mt-1 text-[11px] font-tabular tracking-wider text-[var(--ink-48)]">
              已生成的段落保留在下方,可选择重试或切换 MOCK 模式演示。
            </div>
          </div>
          <button
            onClick={() => setState((s) => ({ ...s, phase: "idle", error: undefined }))}
            className="text-[var(--ink-48)] hover:text-[var(--ink)] shrink-0"
            aria-label="关闭"
            title="关闭提示"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* 真模式 ETA 提示 */}
      {!mockMode && running && (
        <div className="mb-4 px-4 py-2.5 border border-[var(--accent)] bg-[rgba(167,120,47,0.05)] text-[12px] text-[var(--ink-80)] flex items-center gap-2">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--accent)] animate-pulse" />
          <span className="font-tabular tracking-wider">真实 pipeline 运行中 · 预计 5-10 分钟,请保持页面打开</span>
        </div>
      )}

      {/* 12-col grid: 左 320px / 中自适应 / 右 360px */}
      <div
        className={`grid gap-6 ${
          showRight
            ? "grid-cols-1 lg:grid-cols-[320px_minmax(0,1fr)_360px]"
            : "grid-cols-1 lg:grid-cols-[320px_minmax(0,1fr)]"
        }`}
      >
        {/* ─────────────── 左栏 ─────────────── */}
        <aside className="space-y-5">
          <Card eyebrow="BUSINESS LINE" title="业务线">
            <div className="flex flex-wrap gap-0.5">
              {BUSINESS_LINE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => !opt.disabled && !running && setBusinessLine(opt.value)}
                  disabled={opt.disabled || running}
                  title={opt.tooltip}
                  className={`flex-1 px-3 py-1.5 text-[12px] font-medium transition-all border ${
                    businessLine === opt.value
                      ? "bg-[var(--ink)] text-[var(--g0)] border-[var(--ink)]"
                      : "bg-[var(--g1)] text-[var(--ink-80)] border-[var(--ink-28)] hover:border-[var(--ink-48)]"
                  } disabled:opacity-40 disabled:cursor-not-allowed`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <div className="mt-2 text-[10px] font-tabular tracking-wider text-[var(--ink-48)]">
              {businessLine === "reserved"
                ? "敬请期待"
                : "银行按业务线匹配申报书模板与字段表。"}
            </div>
          </Card>

          <Card eyebrow="TEMPLATE" title="申报书模板">
            <FileDrop
              label="拖入 或 点击上传模板"
              hint={`不传则使用 ${BUSINESS_LINE_TEMPLATES[businessLine]}`}
              accept=".doc,.docx"
              maxFiles={1}
              onChange={setTemplateUpload}
              preset={templateUpload}
            />
            {templateUpload.length === 0 && (
              <div className="mt-2 text-[10px] font-tabular tracking-wider text-[var(--ink-48)] flex items-center gap-1.5">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-[var(--accent)]" />
                {BUSINESS_LINE_TEMPLATES[businessLine]}(内置默认)
              </div>
            )}
          </Card>

          <Card eyebrow="MATERIALS" title="客户材料">
            <FileDrop
              label="拖入 或 点击上传"
              hint="支持 PDF · Word · 财报 · 征信"
              accept=".pdf,.doc,.docx,.xlsx,.png,.jpg"
              onChange={setUploaded}
              preset={uploaded}
            />
            <div className="mt-2 text-[10px] text-[var(--ink-48)] font-tabular">
              {mockMode
                ? "Mock 模式 · 上传仅记录元信息,走后端快速路径。"
                : "真实模式 · 上传后走完整解析 pipeline。"}
            </div>
          </Card>

          <Card eyebrow="DEMO PRESETS" title="预置场景">
            <div className="space-y-2">
              {PRESETS.map((p) => (
                <button
                  key={p.key}
                  onClick={() => !running && applyPreset(p)}
                  disabled={running}
                  className={`w-full text-left px-3 py-3 border transition-all disabled:opacity-60 disabled:cursor-not-allowed ${
                    preset === p.key
                      ? "border-[var(--ink)] bg-[var(--ink-04)]"
                      : "border-[var(--ink-14)] hover:border-[var(--ink-48)]"
                  }`}
                >
                  <div className="font-display text-[14px] text-[var(--ink)]">
                    {p.name}
                  </div>
                  <div className="mt-1 text-[10px] font-tabular tracking-wider text-[var(--ink-48)]">
                    {p.tagline}
                  </div>
                </button>
              ))}
            </div>

            <div className="mt-4 flex gap-2">
              <Button
                onClick={() => run(preset)}
                disabled={running || realRunBlocked}
                className="flex-1"
                title={runDisabledTooltip}
              >
                <Play size={14} />
                {running ? "生成中…" : "开始生成"}
              </Button>
              {state.phase !== "idle" && (
                <Button variant="secondary" onClick={reset} disabled={running}>
                  <RotateCcw size={14} />
                </Button>
              )}
            </div>
          </Card>
        </aside>

        {/* ─────────────── 中栏 ─────────────── */}
        <section className="space-y-5 min-w-0">
          <Card eyebrow="PIPELINE" title="生成流水线">
            <PipelineRail
              stages={REPORT_STAGES}
              active={state.activeStage}
              done={state.doneStages}
              error={state.phase === "error"}
            />
            {/* --color-ember → #c8463a (semantic danger; kept literal across themes) */}
            {state.phase === "error" && state.error && (
              <div className="mt-4 text-[12px] text-[#c8463a] font-tabular border-l-2 border-[#c8463a] pl-3">
                {state.error}
              </div>
            )}
          </Card>

          <Card
            eyebrow="REPORT"
            title={state.profile?.company_name ?? "报告预览"}
            action={
              state.stats ? (
                <span className="text-[10px] font-tabular tracking-wider text-[var(--ink-48)]">
                  自动 {state.stats.auto_filled}/{state.stats.total_fields} · 未填 {state.stats.unfilled}
                </span>
              ) : null
            }
          >
            <ReportPreview
              sections={state.sections}
              phase={state.phase}
              activeStage={state.activeStage}
            />

            {state.phase === "done" && state.stats && (
              <div className="mt-6 pt-5 border-t border-[var(--ink-14)] grid grid-cols-3 gap-6">
                <Stat label="总字段" value={state.stats.total_fields ?? 0} />
                <Stat label="自动填写" value={state.stats.auto_filled ?? 0} />
                <Stat
                  label="未能填写"
                  value={state.stats.unfilled ?? 0}
                  hint="已标注"
                />
              </div>
            )}
          </Card>

          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              disabled={state.phase !== "done" || !state.docxUrl}
              onClick={() => {
                if (state.docxUrl && !state.docxUrl.startsWith("#")) {
                  window.location.href = state.docxUrl;
                }
              }}
            >
              <Download size={14} /> 下载 docx
            </Button>
            <Button
              variant="secondary"
              onClick={() => run(preset)}
              disabled={running}
            >
              <RotateCcw size={14} /> 重新生成
            </Button>
            <Button
              variant="ghost"
              onClick={clearAll}
              disabled={running}
            >
              <Trash2 size={14} /> 清空
            </Button>
          </div>

          {showHandoff && (
            <Card eyebrow="HANDOFF" title="继续下游流程">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {HANDOFF_CARDS.map(({ key, title, subtitle, Icon }) => (
                  <button
                    key={key}
                    onClick={() => handoffTo(key)}
                    className="group text-left p-4 border border-[var(--ink-28)] hover:border-[var(--ink)] hover:bg-[var(--ink-04)] transition-all"
                  >
                    <div className="flex items-center gap-2 text-[var(--accent)]">
                      <Icon size={16} />
                      <span className="text-[10px] font-tabular tracking-[0.25em] uppercase">
                        {key}
                      </span>
                    </div>
                    <div className="mt-2 font-display text-[15px] text-[var(--ink)]">
                      {title}
                    </div>
                    <div className="mt-1 text-[11px] text-[var(--ink-48)]">
                      {subtitle}
                    </div>
                    <div className="mt-3 flex items-center gap-1 text-[11px] font-tabular text-[var(--ink-48)] group-hover:text-[var(--ink)]">
                      带企业画像跳转
                      <ArrowRight size={11} className="transition-transform group-hover:translate-x-0.5" />
                    </div>
                  </button>
                ))}
              </div>
              <div className="mt-3 text-[10px] font-tabular tracking-wider text-[var(--ink-48)]">
                * 通过 sessionStorage 携带 EnterpriseProfile,下游 Agent 无需重复解析。
              </div>
            </Card>
          )}
        </section>

        {/* ─────────────── 右栏 ─────────────── */}
        {showRight && (
          <aside className="space-y-5 min-w-0">
            <Card eyebrow="PENDING" title="补充问卷">
              <div className="mb-3 text-[11px] text-[var(--ink-48)] leading-relaxed">
                系统识别出若干字段缺少证据支撑,请就下列问题补充,或直接跳过留待人工。
              </div>
              <QuestionnairePanel
                questions={state.pendingQuestions}
                busy={state.phase === "refining"}
                onSubmit={refine}
              />
            </Card>
          </aside>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function applyEvent(
  evt: import("@/lib/credit-types").ReportEvent,
  setState: React.Dispatch<React.SetStateAction<ReportState>>
) {
  setState((prev) => {
    const next: ReportState = {
      ...prev,
      doneStages: new Set(prev.doneStages),
      sections: [...prev.sections],
    };
    if (evt.event === "stage") {
      // mark previous active as done, flip to new
      if (prev.activeStage && prev.activeStage !== evt.stage) {
        next.doneStages.add(prev.activeStage);
      }
      next.activeStage = evt.stage;
      return next;
    }
    if (evt.event === "section") {
      const idx = next.sections.findIndex((s) => s.id === evt.section.id);
      if (idx >= 0) next.sections[idx] = evt.section;
      else next.sections.push(evt.section);
      return next;
    }
    if (evt.event === "profile") {
      next.profile = evt.profile;
      return next;
    }
    if (evt.event === "done") {
      // ensure final stage closes out
      if (prev.activeStage) next.doneStages.add(prev.activeStage);
      for (const s of REPORT_STAGES) next.doneStages.add(s.key as ReportStage);
      next.activeStage = undefined;
      next.sessionId = evt.session_id;
      next.profile = evt.payload.profile;
      next.sections = evt.payload.sections;
      next.pendingQuestions = evt.payload.pending_questions ?? [];
      next.handoff = evt.payload.downstream_handoff;
      next.stats = evt.payload.stats;
      next.docxUrl = evt.payload.docx_url;
      next.phase = "done";
      return next;
    }
    if (evt.event === "error") {
      next.phase = "error";
      next.error = evt.message;
      return next;
    }
    return next;
  });
}

function MockToggle({
  value,
  onChange,
  disabled,
}: {
  value: boolean;
  onChange: (v: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <label
      className={`inline-flex items-center gap-2 text-[11px] font-tabular tracking-wider select-none ${
        disabled ? "opacity-50" : "cursor-pointer"
      }`}
    >
      <span className="text-[var(--ink-48)]">MOCK</span>
      <button
        type="button"
        role="switch"
        aria-checked={value}
        disabled={disabled}
        onClick={() => onChange(!value)}
        className={`relative inline-flex h-5 w-10 items-center transition-colors ${
          value
            ? "bg-[var(--ink)]"
            : "bg-[var(--ink-04)] border border-[var(--ink-28)]"
        }`}
      >
        <span
          className={`inline-block h-3.5 w-3.5 bg-[var(--g0)] transition-transform ${
            value ? "translate-x-5" : "translate-x-0.5"
          }`}
        />
      </button>
      <span
        className={value ? "text-[var(--ink)]" : "text-[var(--ink-48)]"}
      >
        {value ? "ON" : "OFF"}
      </span>
    </label>
  );
}

function ReportPreview({
  sections,
  phase,
  activeStage,
}: {
  sections: ReportSection[];
  phase: ReportState["phase"];
  activeStage?: ReportStage;
}) {
  if (phase === "idle") {
    return (
      <div className="py-16 text-center">
        <div className="text-[10px] font-tabular tracking-[0.25em] text-[var(--accent)] uppercase">
          AWAITING
        </div>
        <p className="mt-3 font-display text-[20px] text-[var(--ink)]">
          待生成报告
        </p>
        <p className="mt-2 text-[12px] text-[var(--ink-48)]">
          选择预置场景 或 上传材料包后点击「开始生成」
        </p>
      </div>
    );
  }

  if (sections.length === 0) {
    const label = stageLabel(activeStage) ?? "准备中";
    return (
      <div className="py-12 text-center">
        <div className="text-[10px] font-tabular tracking-[0.25em] text-[var(--accent)] uppercase">
          WORKING
        </div>
        <p className="mt-3 font-display text-[18px] text-[var(--ink)]">
          {label}
        </p>
        <div className="mt-4 mx-auto w-24 h-0.5 bg-[var(--ink-14)] overflow-hidden">
          <motion.div
            className="h-full bg-[var(--accent)]"
            animate={{ x: ["-100%", "100%"] }}
            transition={{ duration: 1.2, repeat: Infinity, ease: "linear" }}
            style={{ width: "40%" }}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <AnimatePresence initial={false}>
        {sections.map((sec) => (
          <motion.article
            key={sec.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="pb-4 border-b border-[var(--ink-14)] last:border-0 last:pb-0"
          >
            <h4 className="font-display text-[15px] text-[var(--ink)] mb-2">
              {sec.title}
            </h4>
            <p className="text-[13px] leading-[1.8] text-[var(--ink-80)] whitespace-pre-wrap">
              {sec.content}
            </p>
          </motion.article>
        ))}
      </AnimatePresence>
      {(phase === "running" || phase === "refining") && activeStage && (
        <div className="text-[11px] font-tabular tracking-wider text-[var(--accent)]">
          · {stageLabel(activeStage)}…
        </div>
      )}
    </div>
  );
}

function stageLabel(key?: ReportStage): string | undefined {
  if (!key) return undefined;
  return REPORT_STAGES.find((s) => s.key === key)?.label;
}

/**
 * LLM 连接状态指示器 — 右上角状态灯。
 * 安全:不暴露 API key 内容,仅显示布尔。
 * null → 未知(加载中),true → 绿色已连接,false → 红色未连接。
 */
function LLMStatusIndicator({ connected }: { connected: boolean | null }) {
  const isLoading = connected === null;
  const ok = connected === true;
  const label = isLoading ? "LLM 检测中" : ok ? "LLM 已连接" : "LLM 未连接";
  // --color-ember → #c8463a (semantic danger; kept literal across themes)
  const dotClass = isLoading
    ? "bg-[var(--ink-48)]"
    : ok
    ? "bg-[var(--safe)]"
    : "bg-[#c8463a]";
  const textClass = isLoading
    ? "text-[var(--ink-48)]"
    : ok
    ? "text-[var(--ink)]"
    : "text-[#c8463a]";

  return (
    <div
      title={
        ok
          ? "LLM API 已通过环境变量配置"
          : isLoading
          ? "正在查询后端健康状态…"
          : "后端未检测到 DEEPSEEK_API_KEY,请联系运维配置环境变量"
      }
      className="inline-flex items-center gap-2 px-3 py-1.5 border border-[var(--ink-28)] font-tabular text-[11px] tracking-wider select-none"
    >
      <span
        className={`inline-block w-2 h-2 rounded-full ${dotClass} ${
          ok ? "animate-pulse" : ""
        }`}
      />
      <span className={textClass}>{label}</span>
    </div>
  );
}
