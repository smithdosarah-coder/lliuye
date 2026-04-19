/**
 * Warroom view · mock fixture (Stage 2 stub)
 * Stage 5 切到 GET /api/warroom/tasks + POST /api/warroom/move
 */

export type WarroomColumn = "todo" | "wip" | "review" | "done";

export type WarroomTask = {
  id: string;
  column: WarroomColumn;
  title: string;
  who: string;
  prio: "P0" | "P1" | "P2";
  due: string;
};

export const WARROOM_COLUMNS: { key: WarroomColumn; label: string; meta: string }[] = [
  { key: "todo",   label: "待办",   meta: "TODO"   },
  { key: "wip",    label: "进行中", meta: "WIP"    },
  { key: "review", label: "待审",   meta: "REVIEW" },
  { key: "done",   label: "已完",   meta: "DONE"   },
];

export const WARROOM_TASKS: WarroomTask[] = [
  { id: "w1", column: "todo",   title: "宁海汇通 · 终审会前补 3 项材料", who: "王哲",         prio: "P0", due: "今日 14:00" },
  { id: "w2", column: "todo",   title: "海创智能装备 · 预审材料 7/9",    who: "王哲",         prio: "P1", due: "本周内"     },
  { id: "w3", column: "wip",    title: "星河医药 · 黄色预警复核",        who: "王哲 / 林楠",   prio: "P1", due: "明日"       },
  { id: "w4", column: "wip",    title: "§214 政策 · 4 户合规意见草稿",   who: "AI 合规助手",   prio: "P0", due: "今日 12:00" },
  { id: "w5", column: "review", title: "宁海汇通授信报告 · v3 复核",     who: "林楠",         prio: "P0", due: "今日"       },
  { id: "w6", column: "done",   title: "瑞通新材 · 完成放款手续",        who: "王哲",         prio: "P1", due: "—"          },
];
