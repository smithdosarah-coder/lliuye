import { expect, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { normalizeCreditDone, resolveAmountState, safePercent, safeRangePercent } from "../../src/app/archive/credit/_components/_normalize";
import { CREDIT_SESSION } from "../../src/lib/mock/agent-credit-session";

test("B-null · helper truth table", () => {
  expect(resolveAmountState(false, 0)).toEqual({ amountProvided: false, amount: null });
  expect(resolveAmountState(true, 0)).toEqual({ amountProvided: true, amount: 0 });
  expect(resolveAmountState(undefined, 0)).toEqual({ amountProvided: true, amount: 0 });
  expect(resolveAmountState(undefined, null)).toEqual({ amountProvided: false, amount: null });
  expect(resolveAmountState(true, Number.NaN)).toEqual({ amountProvided: false, amount: null });
  expect(resolveAmountState(undefined, Number.POSITIVE_INFINITY)).toEqual({ amountProvided: false, amount: null });
  expect(safePercent(0, 0)).toBe(0);
  expect(safePercent(5, 0)).toBe(0);
  expect(safePercent(5, 10)).toBe(50);
  expect(safeRangePercent(1, 1, 1)).toBe(0);
  expect(safeRangePercent(15, 10, 20)).toBe(50);
});

test("B-null · summary null never falls back to mock amount", () => {
  const normalized = normalizeCreditDone({
    event: "done",
    stage_tab: "corporate",
    source: "mock",
    advice: { decision: "拒绝", approved_amount: null },
    decision_graph: {
      decision_summary: { amount_provided: false, approved_amount: null },
    },
  }, CREDIT_SESSION);
  expect(normalized.limit).toMatchObject({ amountProvided: false, suggested: null });
});

test("B-null · advice and graph merge uses any explicit missing signal", () => {
  const normalized = normalizeCreditDone({
    event: "done",
    stage_tab: "corporate",
    source: "mock",
    advice: { decision: "拒绝", amount_provided: true, approved_amount: 0 },
    decision_graph: {
      decision_summary: { amount_provided: false, approved_amount: null },
    },
  }, CREDIT_SESSION);
  expect(normalized.limit).toMatchObject({ amountProvided: false, suggested: null });
});

test("B-null · summary alone hydrates provided zero and cases never render non-finite amounts", () => {
  const normalized = normalizeCreditDone({
    event: "done",
    stage_tab: "corporate",
    source: "mock",
    decision_graph: {
      decision_summary: { amount_provided: true, approved_amount: 0 },
    },
    case_matches: [
      { case_id: "missing", amount_provided: false, approved_amount: 0 },
      { case_id: "nan", amount_provided: true, approved_amount: Number.NaN },
    ],
  }, CREDIT_SESSION);
  expect(normalized.limit).toMatchObject({ amountProvided: true, suggested: 0 });
  expect(normalized.cases.map((item) => item.amount)).toEqual([
    "额度未提供 · 仅风险评估",
    "额度未提供 · 仅风险评估",
  ]);
  expect(JSON.stringify(normalized)).not.toMatch(/NaN|Infinity/);
});

test("B-null · six fixtures keep decision mirrors and expected amount distribution", () => {
  const dir = path.resolve(process.cwd(), "../data/mock/workspace/credit/scenarios");
  const files = fs.readdirSync(dir).filter((name) => name.endsWith(".json")).sort();
  expect(files).toEqual([
    "corp-dingsheng-001.json",
    "corp-ruiheng-002.json",
    "corp-zhongrui-003.json",
    "retail-lisi-002.json",
    "retail-wangwu-003.json",
    "retail-zhangsan-001.json",
  ]);
  let trueZero = 0;
  let truePositive = 0;
  for (const file of files) {
    const graph = JSON.parse(fs.readFileSync(path.join(dir, file), "utf8")).decision_graph;
    expect(graph.schema_version).toBe("1.1.0");
    const node = graph.nodes.find((item: { id: string }) => item.id === "decision::final");
    expect(node.amount_provided).toBe(graph.decision_summary.amount_provided);
    expect(node.approved_amount).toBe(graph.decision_summary.approved_amount);
    for (const mirror of [graph.decision_summary, node]) {
      expect(typeof mirror.amount_provided).toBe("boolean");
      expect(Object.hasOwn(mirror, "approved_amount")).toBe(true);
      expect(resolveAmountState(mirror.amount_provided, mirror.approved_amount)).toEqual({
        amountProvided: mirror.amount_provided,
        amount: mirror.approved_amount,
      });
    }
    if (graph.decision_summary.amount_provided && graph.decision_summary.approved_amount === 0) trueZero += 1;
    if (graph.decision_summary.amount_provided && graph.decision_summary.approved_amount > 0) truePositive += 1;
  }
  expect(trueZero).toBe(2);
  expect(truePositive).toBe(4);
});
