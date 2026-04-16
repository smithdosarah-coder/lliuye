// 全渠道获客 (Agent1 信号驱动搜索) 前端数据契约
// 与后端 agent_channel/realtime_stream.py 的输出字段对齐

export interface ChannelTag {
  category: string;
  value: string;
}

export type SignalType = "bidding" | "recognition" | "tech" | "growth" | "award";

export interface SignalItem {
  type: SignalType;
  title: string;
  detail: string;
  date: string;
  source: string;
  url: string;
}

export interface MatchTag {
  label: string;
  matched: boolean;
  detail: string;
}

export interface ChannelDataSource {
  label: string;
  hint: string;
}

export interface ChannelCandidate {
  name: string;
  signalScore: number;
  signalCount: number;
  source: "external" | "internal" | "both";
  signals: SignalItem[];
  // 基础信息（企查查补全）
  region: string;
  industry: string;
  uscc: string;
  registeredCapital: string;
  founded: string;
  legalRep: string;
  employees: number;
  mainBusiness: string;
  // 匹配+营销
  matchTags: MatchTag[];
  recommendedProducts: string[];
  pitch: string;
  // 来源（收起显示）
  dataSources: ChannelDataSource[];
}

export interface ChannelMetrics {
  signalTotal: number;
  companiesFound: number;
  final: number;
}

export type ChannelSearchEvent =
  | {
      event: "stage";
      stage: string;
      status: "running" | "done";
      message?: string;
      tags?: ChannelTag[];
      count?: number;
      total?: number;
      data_source?: string;
    }
  | {
      event: "done";
      candidates: ChannelCandidate[];
      metrics: ChannelMetrics;
      data_source: string;
    }
  | {
      event: "error";
      message: string;
      traceback?: string;
    };

export const CHANNEL_STAGES = [
  { key: "parse", label: "意图解析" },
  { key: "signal_scan", label: "信号扫描" },
  { key: "aggregate", label: "实体聚合" },
  { key: "enrich", label: "工商补全" },
  { key: "pitch", label: "话术生成" },
  { key: "rank", label: "信号排序" },
] as const;

// ========== 兼容旧类型（逐步废弃） ==========

/** @deprecated use ChannelCandidate.matchTags */
export interface ChannelReasonDim {
  dim: string;
  score: number;
  verdict: string;
  evidence: string;
  source: string;
}

/** @deprecated use ChannelCandidate.signals */
export interface ChannelTimelineEvent {
  date: string;
  event: string;
  source: string;
}
