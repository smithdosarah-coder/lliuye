/**
 * sync-contracts.ts · Liuye contracts codegen runner
 *
 * Reads:  shared/contracts/liuye/schemas/*.json (old repo · this script's home)
 * Writes:
 *   - credit_matrix_next/lib/protocols/generated.ts   (TS · json-schema-to-typescript)
 *   - credit_report_agent_work/liuye_service/protocols/generated.py  (PY · datamodel-code-generator)
 *
 * codegen_options enforced (from contracts.lock.json):
 *   - ts_naming: preserve_snake_case   (created_at NOT createdAt)
 *   - ts_strict: true                   (no any, all required fields explicit)
 *   - ts_additional_properties: false   (closed objects)
 *   - py_alias_generator: to_snake      (matches Pydantic snake_case)
 *   - py populate_by_name: true         (accept both alias + field name)
 *
 * Invocation:
 *   from credit_matrix_next/ : npm run contracts:sync
 *   from old repo direct     : npx tsx scripts/sync-contracts.ts
 *
 * W0 T1 status: smoke pipeline dry-run · 5 protocol schemas left for W1 contract worker.
 */
import { promises as fs } from 'node:fs';
import path from 'node:path';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';

const execFileP = promisify(execFile);

// ---------- repo layout (resolve relative to THIS script, not cwd) ----------
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const OLD_REPO = path.resolve(__dirname, '..');                       // credit_report_agent_work/
const NEW_REPO = path.resolve(OLD_REPO, '..', 'credit_matrix_next');  // sibling

// ---------- resolve json-schema-to-typescript from new-repo node_modules ----------
// rationale: this script lives in OLD_REPO/scripts/ but the npm-installed dep is in
// NEW_REPO/node_modules/ (npm only · per contracts.lock). use createRequire scoped to
// the new repo so module resolution walks up from there.
const requireFromNewRepo = createRequire(pathToFileURL(path.join(NEW_REPO, 'package.json')).href);
const j2t = requireFromNewRepo('json-schema-to-typescript') as typeof import('json-schema-to-typescript');
const compileFromFile = j2t.compileFromFile;
type JS2TSOptions = import('json-schema-to-typescript').Options;

const SCHEMA_DIR = path.join(OLD_REPO, 'shared', 'contracts', 'liuye', 'schemas');
const TS_OUT = path.join(NEW_REPO, 'lib', 'protocols', 'generated.ts');
const PY_OUT = path.join(OLD_REPO, 'liuye_service', 'protocols', 'generated.py');

// ---------- TS codegen ----------
const TS_HEADER = `/* eslint-disable */
/**
 * AUTO-GENERATED · DO NOT EDIT BY HAND
 * source: shared/contracts/liuye/schemas/*.json
 * tool:   json-schema-to-typescript
 * regen:  npm run contracts:sync  (from credit_matrix_next/)
 *
 * Field names preserve snake_case (e.g. created_at NOT createdAt) ·
 * contract-locked per contracts.lock.json:codegen_options.ts_naming.
 */
`;

const TS_OPTIONS: Partial<JS2TSOptions> = {
  bannerComment: '',                  // we prepend our own header
  additionalProperties: false,        // closed objects · contracts.lock ts_additional_properties
  strictIndexSignatures: true,        // ts_strict
  style: { singleQuote: true, semi: true },
  unreachableDefinitions: false,
};

async function listSchemas(): Promise<string[]> {
  // Exclude files starting with `_` (e.g. _smoke.schema.json · W0 T1 dry-run residue).
  // Liuye 5-protocol members are the only `.schema.json` files that survive W1.
  const entries = await fs.readdir(SCHEMA_DIR);
  return entries
    .filter((f) => f.endsWith('.schema.json') && !f.startsWith('_'))
    .sort()
    .map((f) => path.join(SCHEMA_DIR, f));
}

async function runTsCodegen(schemas: string[]): Promise<void> {
  const chunks: string[] = [TS_HEADER];
  for (const schemaPath of schemas) {
    const rel = path.relative(OLD_REPO, schemaPath).replace(/\\/g, '/');
    chunks.push(`// ---- source: ${rel} ----\n`);
    // compileFromFile preserves the field names verbatim from JSON Schema · so snake_case stays snake_case.
    const ts = await compileFromFile(schemaPath, TS_OPTIONS);
    chunks.push(ts.trimEnd() + '\n\n');
  }
  await fs.mkdir(path.dirname(TS_OUT), { recursive: true });
  await fs.writeFile(TS_OUT, chunks.join(''), 'utf8');
  console.log(`[ts] wrote ${TS_OUT} (${schemas.length} schema${schemas.length === 1 ? '' : 's'})`);
}

// ---------- Python codegen ----------
const PY_HEADER = `# AUTO-GENERATED · DO NOT EDIT BY HAND
# source: shared/contracts/liuye/schemas/*.json
# tool:   datamodel-code-generator (Pydantic v2)
# regen:  npm run contracts:sync  (from credit_matrix_next/)
#
# Field names use snake_case (matches Pydantic style) · populate_by_name=True
# means consumers can pass either snake_case or the JSON Schema property name.
# contract-locked per contracts.lock.json:codegen_options.py_alias_generator.
from __future__ import annotations

`;

async function pyExecutable(): Promise<string> {
  // Prefer `py` launcher on Windows · fallback to `python` / `python3`.
  const candidates = process.platform === 'win32' ? ['py', 'python', 'python3'] : ['python3', 'python'];
  for (const exe of candidates) {
    try {
      await execFileP(exe, ['-c', 'import datamodel_code_generator; print("ok")']);
      return exe;
    } catch (err: any) {
      if (err?.code === 'ENOENT' || /ENOENT/.test(String(err?.message))) continue;
      // python found but datamodel_code_generator missing
      throw new Error(
        `[py] ${exe} found but datamodel_code_generator missing. Install: ${exe} -m pip install datamodel-code-generator==0.25.*`,
      );
    }
  }
  throw new Error(`[py] no python launcher on PATH (tried: ${candidates.join(', ')})`);
}

async function runPyCodegen(schemas: string[]): Promise<void> {
  await fs.mkdir(path.dirname(PY_OUT), { recursive: true });
  const exe = await pyExecutable();
  console.log(`[py] using ${exe} -m datamodel_code_generator`);

  // datamodel-code-generator's directory mode wants modular output (one .py per schema).
  // Single-file mode requires single-file input. Run once per schema · concat outputs.
  const parts: string[] = [PY_HEADER];
  for (const schemaPath of schemas) {
    const rel = path.relative(OLD_REPO, schemaPath).replace(/\\/g, '/');
    const tmpOut = path.join(path.dirname(PY_OUT), `.tmp.${path.basename(schemaPath)}.py`);
    const args: string[] = [
      '-m', 'datamodel_code_generator',
      '--input', schemaPath,
      '--input-file-type', 'jsonschema',
      '--output', tmpOut,
      '--output-model-type', 'pydantic_v2.BaseModel',
      '--target-python-version', '3.11',
      '--snake-case-field',                 // canonical snake_case
      '--allow-population-by-field-name',   // -> populate_by_name=True (Pydantic v2)
      '--use-schema-description',
      '--use-title-as-name',
      '--disable-timestamp',
    ];
    try {
      // PYTHONIOENCODING=utf-8 + PYTHONUTF8=1 force UTF-8 stdio on Windows ·
      // datamodel-code-generator print()s file body to disk and the default GBK
      // codec on zh-CN Windows refuses to encode unicode arrows / CJK in schema
      // descriptions (e.g. '↔' U+2194). without this · py codegen aborts.
      const env = { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' };
      const { stdout, stderr } = await execFileP(exe, args, { cwd: OLD_REPO, env });
      if (stdout) console.log(`[py] ${path.basename(schemaPath)}: ${stdout.trim()}`);
      if (stderr) console.error(`[py:stderr] ${path.basename(schemaPath)}: ${stderr.trim()}`);
    } catch (err: any) {
      throw new Error(
        `[py] datamodel-code-generator failed on ${rel}: ${err?.message ?? err}\n${err?.stderr ?? ''}`,
      );
    }
    let body = await fs.readFile(tmpOut, 'utf8');
    // strip the per-file `from __future__ import annotations` (we already wrote it once)
    body = body.replace(/^from __future__ import annotations\s*\n/m, '').trimEnd();
    parts.push(`# ---- source: ${rel} ----\n${body}\n\n`);
    await fs.unlink(tmpOut).catch(() => {});
  }
  await fs.writeFile(PY_OUT, parts.join(''), 'utf8');
  console.log(`[py] wrote ${PY_OUT} (${schemas.length} schema${schemas.length === 1 ? '' : 's'})`);
}

// ---------- main ----------
async function main(): Promise<void> {
  console.log(`[sync] SCHEMA_DIR = ${SCHEMA_DIR}`);
  const schemas = await listSchemas();
  if (schemas.length === 0) {
    throw new Error(`no schemas found in ${SCHEMA_DIR}`);
  }
  console.log(`[sync] found ${schemas.length} schema(s):`);
  schemas.forEach((s) => console.log(`  - ${path.basename(s)}`));

  await runTsCodegen(schemas);
  await runPyCodegen(schemas);

  console.log('[sync] OK · ts + py codegen complete.');
}

main().catch((err) => {
  console.error('[sync] FAILED:', err);
  process.exitCode = 1;
});
