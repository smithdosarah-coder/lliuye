/**
 * Dispatch view · mock fixture (Stage 2 stub)
 * Stage 4 切到 in-memory store + WebSocket
 */

export type Channel = {
  id: string;
  kind: "person" | "topic";
  name: string;
  preview: string;
  unread: number;
  ts: string;
};

export const DISPATCH_CHANNELS: Channel[] = [
  { id: "c1", kind: "person", name: "@林楠 · 审贷员",       preview: "下周一前给出额度建议",  unread: 2, ts: "2h"    },
  { id: "c2", kind: "topic",  name: "#华东线晨会",           preview: "5 位参会 · 09:30",      unread: 0, ts: "07:50" },
  { id: "c3", kind: "topic",  name: "#NMPA-§214",            preview: "@王哲 复核 4 户命中",   unread: 1, ts: "04/15" },
  { id: "c4", kind: "person", name: "@周博 · 风控主管",      preview: "小微 DSL 草稿已发",     unread: 0, ts: "昨日"  },
];

export type Message = {
  id: string;
  who: string;
  body: string;
  ts: string;
};

export const DISPATCH_MESSAGES: Record<string, Message[]> = {
  c1: [
    { id: "m1", who: "@林楠", body: "宁海汇通这单麻烦今天给个初步授信额度区间。",                ts: "08:41" },
    { id: "m2", who: "@王哲", body: "好的，AI 助手报告 78% 出来后我先在群里说一下。",            ts: "08:43" },
  ],
};
