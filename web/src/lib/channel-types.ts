// 全渠道获客 (Agent1 Look-alike) 前端数据契约
// 与后端 agent_channel/realtime_stream.py 的 _enrich_with_llm 输出字段对齐

export interface ChannelTag {
  category: string;
  value: string;
}

export interface ChannelReasonDim {
  dim: string;
  score: number;
  verdict: string;
  evidence: string;
  source: string;
}

export interface ChannelTimelineEvent {
  date: string;
  event: string;
  source: string;
}

export interface ChannelDataSource {
  label: string;
  hint: string;
}

export interface ChannelCandidate {
  name: string;
  score: number;
  source: "external" | "internal" | "both";
  region: string;
  industry: string;
  uscc: string;
  registeredCapital: string;
  founded: string;
  legalRep: string;
  employees: number;
  mainBusiness: string;
  revenueLatest: string;
  revenueGrowth: string;
  netMargin?: string | null;
  taxRating?: string | null;
  certifications: string[];
  mainCustomers: string[];
  reasons: string[];
  signal: string;
  contact?: string | null;
  reasonDims: ChannelReasonDim[];
  events: ChannelTimelineEvent[];
  dataSources: ChannelDataSource[];
  risks: string[];
  nextAction: string;
}

export interface ChannelMetrics {
  external: number;
  internal: number;
  overlap: number;
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
      overlap?: number;
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
  { key: "parse", label: "需求解析" },
  { key: "external", label: "外网搜索" },
  { key: "internal", label: "内部库检索" },
  { key: "cross", label: "双路交叉打分" },
  { key: "rank", label: "推荐理由生成" },
] as const;
