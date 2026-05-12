/**
 * W1-mock-test · checkpoint 8/11 · 第 4 棒 · 2026-05-12
 *
 * Purpose
 *   验 5 Liuye contract schema 自身合法 (是合规的 draft-07 JSON Schema)。
 *   非 fixture 校验 (那是 payload-shape.spec.ts) · 只验 schema 文件本身。
 *
 * Checks (4 类 · 总 5 schema × N check = 20+ assertion)
 *   1. ajv.validateSchema(schema) 过 draft-07 metaschema
 *   2. `$id` / `$schema` / `title` / `description` 4 必填 meta 字段全有 + 非空
 *   3. root level `additionalProperties: false` (5 schema 全部锁死 · 不允许偷字段)
 *      · liuye_chat_event 走 oneOf 分支 · 顶层仍 additionalProperties:false 合规
 *   4. `$schema` 必须是 draft-07 metaschema URL
 *
 * Run
 *   cd tests && node_modules/.bin/tsx contract/schema-validate.spec.ts
 *
 * Exit
 *   0 = 全 PASS · 1 = 任一 schema 失败 (打印 ajv errors + 退出)
 *
 * Hidden gotcha 处理
 *   · ajv 8 strict=false 关掉非标关键字警告 (避免 description 自定义关键字误报)
 *   · ajv-formats 注册 format=date-time / uri-reference 等 · metaschema 本身不验 format · 但 compile 阶段需注册避免 unknown-format warn
 *   · ajv.validateSchema(schema) 与 ajv.compile(schema) 不同: 前者验 schema 自身合法 · 后者编译可用 · 本 spec 两步都跑
 */

import Ajv, { ErrorObject } from "ajv";
import addFormats from "ajv-formats";
import { readFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// repo-root-relative path · tests/contract → ../../
const SCHEMA_DIR = resolve(__dirname, "../../shared/contracts/liuye/schemas");

const SCHEMA_FILES = [
  "artifact.schema.json",
  "evidence_ref.schema.json",
  "kb_doc.schema.json",
  "liuye_chat_event.schema.json",
  "tool_call.schema.json",
] as const;

const REQUIRED_META_FIELDS = ["$id", "$schema", "title", "description"] as const;
const DRAFT_07_METASCHEMA = "http://json-schema.org/draft-07/schema#";

interface CheckResult {
  schema: string;
  check: string;
  ok: boolean;
  detail?: string;
}

const results: CheckResult[] = [];

function record(schema: string, check: string, ok: boolean, detail?: string): void {
  results.push({ schema, check, ok, detail });
}

function formatAjvErrors(errors: ErrorObject[] | null | undefined): string {
  if (!errors || errors.length === 0) return "(no errors)";
  return errors
    .slice(0, 5)
    .map((e) => `[${e.instancePath || "/"}] ${e.keyword}: ${e.message}`)
    .join(" | ");
}

function main(): number {
  const ajv = new Ajv({ allErrors: true, strict: false });
  addFormats(ajv);

  for (const file of SCHEMA_FILES) {
    const path = resolve(SCHEMA_DIR, file);
    let schema: Record<string, unknown>;
    try {
      schema = JSON.parse(readFileSync(path, "utf8"));
    } catch (err) {
      record(file, "read+parse", false, (err as Error).message);
      continue;
    }
    record(file, "read+parse", true);

    // Check 1: ajv.validateSchema (draft-07 metaschema compliance)
    const metaOk = ajv.validateSchema(schema);
    record(file, "metaschema (draft-07)", metaOk === true, metaOk ? undefined : formatAjvErrors(ajv.errors));

    // Check 2: required meta fields ($id / $schema / title / description)
    for (const field of REQUIRED_META_FIELDS) {
      const val = schema[field];
      const present = typeof val === "string" && val.length > 0;
      record(file, `meta-field present + non-empty: ${field}`, present, present ? undefined : `got ${JSON.stringify(val)}`);
    }

    // Check 3: $schema must point to draft-07 metaschema
    const schemaUrl = schema["$schema"];
    const draftOk = schemaUrl === DRAFT_07_METASCHEMA;
    record(file, `$schema = draft-07 URL`, draftOk, draftOk ? undefined : `got ${JSON.stringify(schemaUrl)}`);

    // Check 4: root additionalProperties === false (5 schema 全部锁死)
    const addProps = schema["additionalProperties"];
    const addPropsOk = addProps === false;
    record(file, "root additionalProperties: false", addPropsOk, addPropsOk ? undefined : `got ${JSON.stringify(addProps)}`);

    // Check 5: ajv.compile must succeed (catch invalid $ref / definitions / etc.)
    let compileOk = true;
    let compileErr: string | undefined;
    try {
      ajv.compile(schema);
    } catch (err) {
      compileOk = false;
      compileErr = (err as Error).message.slice(0, 300);
    }
    record(file, "ajv.compile (no throws)", compileOk, compileErr);
  }

  // Print report
  let passed = 0;
  let failed = 0;
  const failedRows: CheckResult[] = [];
  for (const r of results) {
    if (r.ok) {
      passed++;
    } else {
      failed++;
      failedRows.push(r);
    }
  }

  console.log(`[schema-validate] total=${results.length} pass=${passed} fail=${failed}`);
  if (failed > 0) {
    console.error("\n[schema-validate] FAILURES:");
    for (const r of failedRows) {
      console.error(`  · ${r.schema} :: ${r.check}`);
      if (r.detail) console.error(`    detail: ${r.detail}`);
    }
    return 1;
  }

  console.log(`[schema-validate] OK · 5 schema · metaschema + 4 meta-field + additionalProperties + compile · all ${passed} checks pass`);
  return 0;
}

const exitCode = main();
process.exit(exitCode);
