/**
 * W1-mock-test · checkpoint 8/11 · 第 4 棒 · 2026-05-12
 *
 * Purpose
 *   验 5 fixture 符合对应 schema · 含 chunked patch 三件套 cross-field check (per hidden gotcha #4)。
 *
 * Fixture → Schema mapping
 *   1. tests/fixtures/channel_5candidates.json        → artifact.schema.json (type=channel_search)
 *   2. tests/fixtures/credit_decision_PASS.json       → artifact.schema.json (type=credit_decision)
 *   3. tests/fixtures/report_v16_PARTIAL.json         → artifact.schema.json (type=report_draft)
 *   4. shared/contracts/liuye/fixtures/kb_doc.json    → artifact.schema.json (type=kb_upload_result)
 *      [contract worker 的 fixture · cross-fixture 引用 · 不归 mock-test 写]
 *   5. shared/contracts/liuye/fixtures/evidence_ref.json → evidence_ref.schema.json (array mode · 5 element)
 *      [contract worker 的 fixture · array · 逐元素验证]
 *
 * Chunked patch cross-field triple check (hidden gotcha #4)
 *   artifact.schema.json L175-189 chunk_index / chunk_total / chunk_assembly 3 字段 optional ·
 *   但语义上 chunked 必三件套同存 (v3 §2.2 hardline)。
 *   schema 没强制 cross-field · 本 spec post-check:
 *     · 任一 chunk_* 字段存在 → 三件套必同存 · 否则 fail
 *     · chunk_index ∈ [0, chunk_total) (chunk_index < chunk_total · 监单调编号)
 *     · chunk_assembly ∈ {streaming, final}
 *
 * Run
 *   cd tests && node_modules/.bin/tsx contract/payload-shape.spec.ts
 *
 * Exit
 *   0 = 全 PASS · 1 = 任一 fixture 或 chunked check 失败
 *
 * Hidden gotcha 处理
 *   · 用 post-check function 而非 ajv 自定义 keyword: keyword 改 schema 文件 · 我们契约层 schema 不动 (W1-contract SSOT) · post-check 在 spec 层加 cross-field 保险
 *   · evidence_ref.json 是 array · 不是 object · 要 isArray + forEach 逐验
 *   · kb_doc.json 用 artifact schema (type=kb_upload_result) · 不是用 kb_doc schema 验整个 fixture · kb_doc schema 验的是 KBDoc 单条 · 这里 fixture 是 Artifact + snapshot.kb_docs[]
 */

import Ajv, { ErrorObject, ValidateFunction } from "ajv";
import addFormats from "ajv-formats";
import { readFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const REPO_ROOT = resolve(__dirname, "../..");
const SCHEMA_DIR = resolve(REPO_ROOT, "shared/contracts/liuye/schemas");

interface FixtureBinding {
  label: string;
  fixturePath: string;
  schemaName: string;
  arrayMode: boolean;
  expectedType?: string; // for artifact-typed fixtures · cross-check fixture.type matches binding
}

const BINDINGS: FixtureBinding[] = [
  {
    label: "channel_5candidates → artifact (channel_search)",
    fixturePath: resolve(REPO_ROOT, "tests/fixtures/channel_5candidates.json"),
    schemaName: "artifact.schema.json",
    arrayMode: false,
    expectedType: "channel_search",
  },
  {
    label: "credit_decision_PASS → artifact (credit_decision)",
    fixturePath: resolve(REPO_ROOT, "tests/fixtures/credit_decision_PASS.json"),
    schemaName: "artifact.schema.json",
    arrayMode: false,
    expectedType: "credit_decision",
  },
  {
    label: "report_v16_PARTIAL → artifact (report_draft)",
    fixturePath: resolve(REPO_ROOT, "tests/fixtures/report_v16_PARTIAL.json"),
    schemaName: "artifact.schema.json",
    arrayMode: false,
    expectedType: "report_draft",
  },
  {
    label: "kb_doc (contract worker) → artifact (kb_upload_result)",
    fixturePath: resolve(REPO_ROOT, "shared/contracts/liuye/fixtures/kb_doc.json"),
    schemaName: "artifact.schema.json",
    arrayMode: false,
    expectedType: "kb_upload_result",
  },
  {
    label: "evidence_ref (contract worker) → evidence_ref (array)",
    fixturePath: resolve(REPO_ROOT, "shared/contracts/liuye/fixtures/evidence_ref.json"),
    schemaName: "evidence_ref.schema.json",
    arrayMode: true,
  },
];

interface CheckResult {
  binding: string;
  check: string;
  ok: boolean;
  detail?: string;
}

const results: CheckResult[] = [];

function record(binding: string, check: string, ok: boolean, detail?: string): void {
  results.push({ binding, check, ok, detail });
}

function formatAjvErrors(errors: ErrorObject[] | null | undefined): string {
  if (!errors || errors.length === 0) return "(no errors)";
  return errors
    .slice(0, 5)
    .map((e) => `[${e.instancePath || "/"}] ${e.keyword}: ${e.message}`)
    .join(" | ");
}

/**
 * Chunked patch cross-field triple check.
 * 三件套必同存: chunk_index + chunk_total + chunk_assembly.
 * 任一存在 → 必同存 · 否则 invariant violation.
 * 额外校验: chunk_index < chunk_total · chunk_assembly ∈ {streaming, final}.
 *
 * @returns 错误列表 (空数组 = OK)
 */
interface ChunkedCheckResult {
  patchId: string;
  chunkIndex?: number;
  chunkTotal?: number;
  chunkAssembly?: string;
  errors: string[];
}

function validateChunkedPatchTriple(patches: unknown): ChunkedCheckResult[] {
  if (!Array.isArray(patches)) return [];
  const out: ChunkedCheckResult[] = [];
  for (const patch of patches) {
    if (typeof patch !== "object" || patch === null) continue;
    const p = patch as Record<string, unknown>;
    const hasIdx = "chunk_index" in p;
    const hasTotal = "chunk_total" in p;
    const hasAsm = "chunk_assembly" in p;
    const anyChunked = hasIdx || hasTotal || hasAsm;
    if (!anyChunked) continue;

    const errors: string[] = [];
    const triple = [hasIdx, hasTotal, hasAsm].filter(Boolean).length;
    if (triple !== 3) {
      errors.push(
        `chunked patch triple incomplete: has chunk_index=${hasIdx}, chunk_total=${hasTotal}, chunk_assembly=${hasAsm} (must be all-or-none)`,
      );
    }
    const idx = p["chunk_index"] as number | undefined;
    const total = p["chunk_total"] as number | undefined;
    const asm = p["chunk_assembly"] as string | undefined;

    if (typeof idx === "number" && typeof total === "number") {
      if (idx < 0) errors.push(`chunk_index ${idx} < 0`);
      if (total < 1) errors.push(`chunk_total ${total} < 1`);
      if (idx >= total) errors.push(`chunk_index ${idx} >= chunk_total ${total} (out of bound)`);
    }
    if (typeof asm === "string" && asm !== "streaming" && asm !== "final") {
      errors.push(`chunk_assembly "${asm}" not in {streaming, final}`);
    }

    out.push({
      patchId: (p["id"] as string) || "(no id)",
      chunkIndex: idx,
      chunkTotal: total,
      chunkAssembly: asm,
      errors,
    });
  }
  return out;
}

/**
 * 额外校验: 同 chunk_total 下 chunk_index 序列覆盖 [0..total-1] · 末 chunk_assembly=final · 之前=streaming.
 * 不属 schema 层 hardline · 但 spec/v3 §2.2 暗示分片协议契约 · 写入 spec 防回归。
 */
function validateChunkedPatchSequence(chunkedRows: ChunkedCheckResult[]): string[] {
  const errors: string[] = [];
  if (chunkedRows.length === 0) return errors;
  // group by chunk_total
  const groups = new Map<number, ChunkedCheckResult[]>();
  for (const row of chunkedRows) {
    if (typeof row.chunkTotal !== "number") continue;
    if (!groups.has(row.chunkTotal)) groups.set(row.chunkTotal, []);
    groups.get(row.chunkTotal)!.push(row);
  }
  for (const [total, rows] of groups) {
    const indices = rows.map((r) => r.chunkIndex).filter((i) => typeof i === "number") as number[];
    indices.sort((a, b) => a - b);
    // sequence sanity
    if (rows.length === total) {
      // full sequence available · indices should be 0..total-1
      for (let i = 0; i < total; i++) {
        if (indices[i] !== i) {
          errors.push(`chunked sequence gap: total=${total} expected index ${i} got ${indices[i]}`);
        }
      }
      // last chunk (index=total-1) must be chunk_assembly=final · earlier ones streaming
      const sorted = [...rows].sort((a, b) => (a.chunkIndex ?? 0) - (b.chunkIndex ?? 0));
      for (let i = 0; i < sorted.length; i++) {
        const expected = i === sorted.length - 1 ? "final" : "streaming";
        if (sorted[i].chunkAssembly !== expected) {
          errors.push(
            `chunked assembly order wrong: chunk_index=${sorted[i].chunkIndex} expected "${expected}" got "${sorted[i].chunkAssembly}"`,
          );
        }
      }
    }
  }
  return errors;
}

function main(): number {
  const ajv = new Ajv({ allErrors: true, strict: false });
  addFormats(ajv);

  // Pre-load + compile all schemas
  const compiled = new Map<string, ValidateFunction>();
  for (const file of ["artifact.schema.json", "evidence_ref.schema.json", "kb_doc.schema.json", "liuye_chat_event.schema.json", "tool_call.schema.json"]) {
    const s = JSON.parse(readFileSync(resolve(SCHEMA_DIR, file), "utf8"));
    compiled.set(file, ajv.compile(s));
  }

  // Tally chunked patch hits across all artifact fixtures · for final report
  const chunkedHits: { binding: string; rows: ChunkedCheckResult[] }[] = [];

  for (const binding of BINDINGS) {
    let raw: unknown;
    try {
      raw = JSON.parse(readFileSync(binding.fixturePath, "utf8"));
    } catch (err) {
      record(binding.label, "read+parse fixture", false, (err as Error).message);
      continue;
    }
    record(binding.label, "read+parse fixture", true);

    const validate = compiled.get(binding.schemaName);
    if (!validate) {
      record(binding.label, "schema-loaded", false, `schema ${binding.schemaName} not compiled`);
      continue;
    }

    if (binding.arrayMode) {
      // Array fixture · validate each element
      if (!Array.isArray(raw)) {
        record(binding.label, "array shape", false, `expected array got ${typeof raw}`);
        continue;
      }
      record(binding.label, "array shape", true, `length=${raw.length}`);
      let allOk = true;
      const errs: string[] = [];
      raw.forEach((el, i) => {
        const ok = validate(el);
        if (!ok) {
          allOk = false;
          errs.push(`[${i}] ${formatAjvErrors(validate.errors)}`);
        }
      });
      record(binding.label, "ajv.validate (per element)", allOk, allOk ? undefined : errs.slice(0, 3).join(" || "));
    } else {
      // Object fixture · single ajv validate
      const ok = validate(raw);
      record(binding.label, "ajv.validate", ok === true, ok ? undefined : formatAjvErrors(validate.errors));

      // Type field cross-check (artifact fixtures only)
      if (binding.expectedType) {
        const obj = raw as Record<string, unknown>;
        const got = obj["type"];
        const typeOk = got === binding.expectedType;
        record(binding.label, `fixture.type == ${binding.expectedType}`, typeOk, typeOk ? undefined : `got ${JSON.stringify(got)}`);

        // Chunked patch cross-field check (artifact-typed fixtures · patches[] live here)
        const patches = obj["patches"];
        const chunkedRows = validateChunkedPatchTriple(patches);
        if (chunkedRows.length > 0) {
          const seqErrors = validateChunkedPatchSequence(chunkedRows);
          let allChunkOk = chunkedRows.every((r) => r.errors.length === 0) && seqErrors.length === 0;
          let detail: string | undefined;
          if (!allChunkOk) {
            const tripleErrs = chunkedRows.flatMap((r) => r.errors).slice(0, 3);
            detail = [...tripleErrs, ...seqErrors.slice(0, 3)].join(" | ");
          }
          record(
            binding.label,
            `chunked patch triple+sequence (n=${chunkedRows.length})`,
            allChunkOk,
            detail,
          );
          chunkedHits.push({ binding: binding.label, rows: chunkedRows });
        }
      }
    }
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

  console.log(`[payload-shape] total=${results.length} pass=${passed} fail=${failed}`);
  if (chunkedHits.length > 0) {
    console.log(`[payload-shape] chunked patch hits across ${chunkedHits.length} fixture:`);
    for (const h of chunkedHits) {
      console.log(`  · ${h.binding}: ${h.rows.length} chunked patch`);
      for (const row of h.rows) {
        console.log(
          `      id=${row.patchId} index=${row.chunkIndex} total=${row.chunkTotal} assembly=${row.chunkAssembly} ${row.errors.length === 0 ? "OK" : "FAIL: " + row.errors.join("; ")}`,
        );
      }
    }
  } else {
    console.log("[payload-shape] no chunked patches across fixtures · cross-field check vacuous (no regression hidden)");
  }

  if (failed > 0) {
    console.error("\n[payload-shape] FAILURES:");
    for (const r of failedRows) {
      console.error(`  · ${r.binding} :: ${r.check}`);
      if (r.detail) console.error(`    detail: ${r.detail}`);
    }
    return 1;
  }

  console.log(`[payload-shape] OK · 5 fixture · ajv + type + chunked triple+sequence · all ${passed} checks pass`);
  return 0;
}

const exitCode = main();
process.exit(exitCode);
