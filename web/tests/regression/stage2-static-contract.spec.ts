import { expect, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

function source(relative: string): string {
  return fs.readFileSync(path.resolve(process.cwd(), relative), "utf8");
}

test("B3 · Masthead labels contain no counters or fake navigation numbers", () => {
  const text = source("src/components/shell/Masthead.tsx");
  expect(text).not.toMatch(/\b(?:0?1|0?2|0?3|0?4)[·./-]\d+\b/);
  expect(text).not.toMatch(/>\s*\d+\s*</);
});

test("B9 · report mock body contains no mock prefix or template placeholders", () => {
  const text = source("src/lib/mock/agent-report-session.ts");
  expect(text).not.toMatch(/\(mock\)|\{T\d+\}|\{\{[^}]+\}\}/);
});
