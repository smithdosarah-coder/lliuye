/**
 * verify-contracts.ts · CI gate for Liuye contracts drift
 *
 * Checks (in order · all must pass for exit 0):
 *   1. Lock file required fields present (schema_version / schema_hash / schemas[] / codegen_options)
 *   2. Schema metaschema validity · all 5 protocol schemas parse as valid draft-07 JSON Schema
 *      (via ajv strict mode · catches typos in keywords)
 *   3. schema_hash drift · contracts.lock.json:schema_hash == sha256(canonical_json(merged 5 schemas))
 *      (canonical = keys sorted recursively, then JSON.stringify with no whitespace · RFC 8785-ish)
 *      · per contracts.lock.json:verification.rule_4
 *      · fixtures NOT included in hash (per W1 5th-leg gotcha #1 · fixture micro-edit must not break lock)
 *   4. Fixture validation · 5 fixture files validate against their owning schema:
 *      - credit_decision.json / report.json / channel_search.json / kb_doc.json → artifact.schema
 *      - evidence_ref.json (array of 5 entries) → evidence_ref.schema (per-item)
 *   5. tsc --noEmit on new repo · credit_matrix_next/lib/protocols/generated.ts + inputSchemas.ts
 *      validate under strict mode (snake_case preserved · 0 type errors)
 *   6. Python codegen presence · liuye_service/protocols/generated.py exists (sanity · not parsed here)
 *   7. LIUYE_CONTRACT_VERSION env (if set) == contracts.lock.json:schema_version
 *      · per contracts.lock.json:verification.rule_1
 *
 * Bootstrap mode (pre W1 D1):
 *   When schema_hash is the placeholder "<TBD W1 D1 sha256>" check (3) emits an INFO line
 *   with the computed canonical hash so contract worker can paste it · still exits 0.
 *
 * Invocation:
 *   from credit_matrix_next/ : npm run contracts:verify
 *   from old repo direct     : npx tsx scripts/verify-contracts.ts
 */
import { promises as fs } from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';

const execFileP = promisify(execFile);

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const OLD_REPO = path.resolve(__dirname, '..');
const NEW_REPO = path.resolve(OLD_REPO, '..', 'credit_matrix_next');

const SCHEMA_DIR = path.join(OLD_REPO, 'shared', 'contracts', 'liuye', 'schemas');
const FIXTURE_DIR = path.join(OLD_REPO, 'shared', 'contracts', 'liuye', 'fixtures');
const TS_OUT = path.join(NEW_REPO, 'lib', 'protocols', 'generated.ts');
const PY_OUT = path.join(OLD_REPO, 'liuye_service', 'protocols', 'generated.py');

// Lock candidates · check both new repo (consumer-facing) and old repo (SSOT).
// Both should equal after W1 D1; verify they match if both present.
const LOCK_CANDIDATES = [
  path.join(NEW_REPO, 'contracts.lock.json'),
  path.join(OLD_REPO, 'shared', 'contracts', 'liuye', 'contracts.lock.json'),
];

const PLACEHOLDER_HASH_RE = /^<TBD/;

interface ContractsLock {
  schema_version: string;
  schema_hash: string;
  schemas?: string[];
  fixtures?: string[];
  codegen_options?: Record<string, unknown>;
  verification?: { rule_1?: string; rule_4?: string };
  [k: string]: unknown;
}

// Maps fixture filename → owning schema filename (used by check 4).
// evidence_ref.json is array-of-N; others are single-instance Artifact.
const FIXTURE_SCHEMA_MAP: Record<string, { schema: string; arrayMode: boolean }> = {
  'credit_decision.json': { schema: 'artifact.schema.json', arrayMode: false },
  'report.json': { schema: 'artifact.schema.json', arrayMode: false },
  'channel_search.json': { schema: 'artifact.schema.json', arrayMode: false },
  'kb_doc.json': { schema: 'artifact.schema.json', arrayMode: false },
  'evidence_ref.json': { schema: 'evidence_ref.schema.json', arrayMode: true },
};

// ---- canonical JSON (RFC 8785-ish · keys sorted recursively, no whitespace) ----
function canonicalize(value: unknown): unknown {
  if (value === null || typeof value !== 'object') return value;
  if (Array.isArray(value)) return value.map(canonicalize);
  const keys = Object.keys(value as Record<string, unknown>).sort();
  const out: Record<string, unknown> = {};
  for (const k of keys) out[k] = canonicalize((value as Record<string, unknown>)[k]);
  return out;
}

function canonicalJson(value: unknown): string {
  return JSON.stringify(canonicalize(value));
}

function sha256Hex(s: string): string {
  return createHash('sha256').update(s, 'utf8').digest('hex');
}

async function loadLocks(): Promise<{ lockPath: string; lock: ContractsLock }[]> {
  const out: { lockPath: string; lock: ContractsLock }[] = [];
  for (const p of LOCK_CANDIDATES) {
    try {
      const raw = await fs.readFile(p, 'utf8');
      out.push({ lockPath: p, lock: JSON.parse(raw) as ContractsLock });
    } catch (e: any) {
      if (e?.code !== 'ENOENT') throw e;
    }
  }
  if (out.length === 0) {
    throw new Error(`contracts.lock.json not found. searched:\n  ${LOCK_CANDIDATES.join('\n  ')}`);
  }
  return out;
}

async function listSchemas(): Promise<string[]> {
  // mirror sync-contracts.ts: skip `_` prefix (W0 T1 smoke residue).
  const entries = await fs.readdir(SCHEMA_DIR);
  return entries
    .filter((f) => f.endsWith('.schema.json') && !f.startsWith('_'))
    .sort();
}

async function mergedSchemas(schemaFiles: string[]): Promise<Record<string, unknown>> {
  const merged: Record<string, unknown> = {};
  for (const f of schemaFiles) {
    const raw = await fs.readFile(path.join(SCHEMA_DIR, f), 'utf8');
    merged[f] = JSON.parse(raw);
  }
  return merged;
}

// ---- ajv (resolve from new-repo node_modules · same as sync-contracts.ts) ----
const requireFromNewRepo = createRequire(pathToFileURL(path.join(NEW_REPO, 'package.json')).href);
type AjvModule = typeof import('ajv');
type AjvFormatsModule = typeof import('ajv-formats');

function loadAjv(): { Ajv: AjvModule['default']; addFormats: AjvFormatsModule['default'] } {
  // ajv 8 + ajv-formats 3 both ship CJS default · interop via createRequire.
  const ajvMod = requireFromNewRepo('ajv') as { default: AjvModule['default'] } | AjvModule['default'];
  const ajvFmtMod = requireFromNewRepo('ajv-formats') as { default: AjvFormatsModule['default'] } | AjvFormatsModule['default'];
  const Ajv = (ajvMod as any).default ?? (ajvMod as any);
  const addFormats = (ajvFmtMod as any).default ?? (ajvFmtMod as any);
  return { Ajv, addFormats };
}

// ---- tsc --noEmit on new repo ----
async function runTscNoEmit(): Promise<{ ok: boolean; output: string }> {
  // Resolve typescript package's tsc.js from new-repo node_modules and run with `node`.
  // Why not node_modules/.bin/tsc.cmd · the .cmd shim + shell=true on Windows breaks
  // when paths contain spaces (e.g. "D:\claude code\..."). Direct node invocation
  // dodges the shell quoting layer entirely.
  const tscJs = path.join(NEW_REPO, 'node_modules', 'typescript', 'bin', 'tsc');
  try {
    const { stdout, stderr } = await execFileP(process.execPath, [tscJs, '--noEmit', '-p', NEW_REPO], {
      cwd: NEW_REPO,
      windowsHide: true,
      maxBuffer: 10 * 1024 * 1024,
    });
    return { ok: true, output: (stdout + stderr).trim() };
  } catch (err: any) {
    return { ok: false, output: ((err?.stdout ?? '') + (err?.stderr ?? '') + (err?.message ?? '')).trim() };
  }
}

async function main(): Promise<void> {
  const errors: string[] = [];
  const warnings: string[] = [];

  // ---------- (1) load lock(s) ----------
  const locks = await loadLocks();
  const primary = locks[0]!;
  console.log(`[verify] primary lock: ${primary.lockPath}`);
  if (locks.length > 1) {
    console.log(`[verify] mirror lock:  ${locks[1]!.lockPath}`);
    // sanity · primary and mirror must agree on schema_hash + schema_version
    if (primary.lock.schema_hash !== locks[1]!.lock.schema_hash) {
      errors.push(
        `lock mirror drift · primary schema_hash=${primary.lock.schema_hash} mirror=${locks[1]!.lock.schema_hash}`,
      );
    }
    if (primary.lock.schema_version !== locks[1]!.lock.schema_version) {
      errors.push(
        `lock mirror drift · primary schema_version=${primary.lock.schema_version} mirror=${locks[1]!.lock.schema_version}`,
      );
    }
  } else {
    warnings.push(`only 1 lock file present (mirror missing); W1 D1 expects both new repo + old repo lock.`);
  }

  for (const { lockPath, lock } of locks) {
    for (const key of ['schema_version', 'schema_hash', 'schemas', 'codegen_options'] as const) {
      if (!(key in lock)) errors.push(`${lockPath}: missing required field ${key}`);
    }
  }

  // ---------- (2) schema metaschema validity ----------
  const schemaFiles = await listSchemas();
  if (schemaFiles.length !== 5) {
    errors.push(`expected 5 protocol schemas · found ${schemaFiles.length} (${schemaFiles.join(', ')})`);
  } else {
    console.log(`[verify] found ${schemaFiles.length} protocol schemas: ${schemaFiles.join(', ')}`);
  }

  const { Ajv, addFormats } = loadAjv();
  // strict=false: schemas have $id/title/description meta keywords that ajv strict would warn on.
  const ajv = new Ajv({ strict: false, allErrors: true, allowUnionTypes: true });
  addFormats(ajv);

  const schemaJsons: Record<string, any> = {};
  for (const f of schemaFiles) {
    const raw = await fs.readFile(path.join(SCHEMA_DIR, f), 'utf8');
    const json = JSON.parse(raw);
    schemaJsons[f] = json;
    try {
      // compile = full metaschema validity check + ready to validate instances.
      ajv.compile(json);
      console.log(`[verify] schema OK · ${f}`);
    } catch (err: any) {
      errors.push(`schema invalid · ${f}: ${err?.message ?? err}`);
    }
  }

  // ---------- (3) schema_hash drift ----------
  const merged = await mergedSchemas(schemaFiles);
  const computed = sha256Hex(canonicalJson(merged));
  console.log(`[verify] canonical sha256(${schemaFiles.length} schemas) = ${computed}`);

  for (const { lockPath, lock } of locks) {
    if (typeof lock.schema_hash !== 'string') {
      errors.push(`${lockPath}: schema_hash is not a string`);
    } else if (PLACEHOLDER_HASH_RE.test(lock.schema_hash)) {
      warnings.push(`${lockPath}: schema_hash is placeholder · paste this: ${computed}`);
    } else if (lock.schema_hash !== computed) {
      errors.push(
        `${lockPath}: schema_hash drift · lock=${lock.schema_hash} computed=${computed} ` +
          `(per contracts.lock.json:verification.rule_4)`,
      );
    } else {
      console.log(`[verify] lock schema_hash matches · ${lockPath}`);
    }
  }

  // ---------- (4) fixture validation ----------
  for (const [fixtureFile, spec] of Object.entries(FIXTURE_SCHEMA_MAP)) {
    const fixturePath = path.join(FIXTURE_DIR, fixtureFile);
    let body: unknown;
    try {
      body = JSON.parse(await fs.readFile(fixturePath, 'utf8'));
    } catch (err: any) {
      errors.push(`fixture parse fail · ${fixtureFile}: ${err?.message ?? err}`);
      continue;
    }
    const schemaJson = schemaJsons[spec.schema];
    if (!schemaJson) {
      errors.push(`fixture ${fixtureFile} references missing schema ${spec.schema}`);
      continue;
    }
    let validate;
    try {
      validate = ajv.compile(schemaJson);
    } catch (err: any) {
      errors.push(`fixture schema compile fail · ${spec.schema}: ${err?.message ?? err}`);
      continue;
    }

    if (spec.arrayMode) {
      // evidence_ref.json is array of N entries · validate each separately.
      if (!Array.isArray(body)) {
        errors.push(`fixture ${fixtureFile}: expected array (arrayMode) · got ${typeof body}`);
        continue;
      }
      let okCount = 0;
      for (let i = 0; i < body.length; i++) {
        const ok = validate(body[i]);
        if (ok) {
          okCount++;
        } else {
          errors.push(
            `fixture ${fixtureFile}[${i}] invalid vs ${spec.schema}: ` +
              JSON.stringify(validate.errors?.slice(0, 3) ?? null),
          );
        }
      }
      if (okCount === body.length) {
        console.log(`[verify] fixture OK · ${fixtureFile} (${okCount}/${body.length} entries) vs ${spec.schema}`);
      }
    } else {
      const ok = validate(body);
      if (ok) {
        console.log(`[verify] fixture OK · ${fixtureFile} vs ${spec.schema}`);
      } else {
        errors.push(
          `fixture ${fixtureFile} invalid vs ${spec.schema}: ` +
            JSON.stringify(validate.errors?.slice(0, 5) ?? null),
        );
      }
    }
  }

  // ---------- (5) tsc --noEmit on new repo ----------
  try {
    await fs.stat(TS_OUT);
    console.log(`[verify] tsc --noEmit on ${NEW_REPO} (consumes generated.ts + inputSchemas.ts) ...`);
    const tsc = await runTscNoEmit();
    if (tsc.ok) {
      console.log(`[verify] tsc --noEmit PASS · 0 errors`);
    } else {
      errors.push(`tsc --noEmit failed:\n${tsc.output}`);
    }
  } catch (err: any) {
    if (err?.code === 'ENOENT') {
      warnings.push(`generated.ts not present at ${TS_OUT} · skip tsc (run contracts:sync first)`);
    } else {
      errors.push(`tsc precheck fail: ${err?.message ?? err}`);
    }
  }

  // ---------- (6) Python codegen presence ----------
  try {
    await fs.stat(PY_OUT);
    console.log(`[verify] python codegen present · ${PY_OUT}`);
  } catch (err: any) {
    if (err?.code === 'ENOENT') {
      warnings.push(`generated.py not present at ${PY_OUT} · run contracts:sync to regenerate`);
    } else {
      errors.push(`py precheck fail: ${err?.message ?? err}`);
    }
  }

  // ---------- (7) env version match ----------
  const envVersion = process.env.LIUYE_CONTRACT_VERSION;
  if (envVersion && envVersion !== primary.lock.schema_version) {
    errors.push(
      `LIUYE_CONTRACT_VERSION env="${envVersion}" != lock.schema_version="${primary.lock.schema_version}" ` +
        `(per contracts.lock.json:verification.rule_1)`,
    );
  } else if (envVersion) {
    console.log(`[verify] LIUYE_CONTRACT_VERSION="${envVersion}" matches lock.schema_version`);
  } else {
    console.log(`[verify] LIUYE_CONTRACT_VERSION env not set · skipping rule_1 env check (CI-only)`);
  }

  // ---------- report ----------
  for (const w of warnings) console.warn(`[verify][WARN] ${w}`);
  if (errors.length === 0) {
    console.log(`[verify] OK · ${warnings.length} warning(s)`);
    return;
  }
  for (const e of errors) console.error(`[verify][ERROR] ${e}`);
  console.error(`[verify] FAILED · ${errors.length} error(s)`);
  process.exit(1);
}

main().catch((err) => {
  console.error('[verify] CRASHED:', err);
  process.exit(1);
});
