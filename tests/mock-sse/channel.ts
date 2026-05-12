/**
 * Mock SSE Server · Channel (Agent1 获客) · 端口 8001
 *
 * W1 mock-test worker 第 3 棒 · 老 v1.0 SSE 协议 (per docs/contracts/sse-envelope.md v1.0 §1.5)
 * 不发 liuye 11 event · 由 backend `adapters/sse_v1_to_liuye.py` 转译
 *
 * Wire form (per field-naming.md §6):
 *   event: <name>\n
 *   data: <single-line JSON>\n
 *   \n
 *
 * 7 老 event (verbatim from sse-envelope.md §1.5 table):
 *   profile_loaded / stage / stream / tool_call / tool_result / done / error
 *
 * Heartbeat: 15s · 用 SSE comment line (": ping <seq>")
 * Seq: 单调递增 (per envelope · 续传时 Last-Event-ID replay)
 * Demo mode: env `LIUYE_DEMO_MODE=mock` → 返预录 fixture (tests/fixtures/channel_5candidates.json)
 *
 * CLI:
 *   node tests/mock-sse/channel.ts --port 8001 --fixture tests/fixtures/channel_5candidates.json
 *
 * Programmatic:
 *   import { start } from './channel';
 *   const server = start(8001, 'tests/fixtures/channel_5candidates.json');
 */

import express, { type Request, type Response } from 'express';
import cors from 'cors';
import * as fs from 'fs';
import * as http from 'http';
import * as path from 'path';

const AGENT_ID = 'channel';
const HEARTBEAT_INTERVAL_MS = 15_000;

interface SseEvent {
  id: number;
  event: 'profile_loaded' | 'stage' | 'stream' | 'tool_call' | 'tool_result' | 'done' | 'error';
  data: Record<string, unknown>;
}

/** 把 SSE event 写到 response stream */
function writeEvent(res: Response, evt: SseEvent): void {
  // id: 单调递增 · 用于 Last-Event-ID replay
  res.write(`id: ${evt.id}\n`);
  res.write(`event: ${evt.event}\n`);
  // data 必须是单行 JSON (per field-naming.md §6 wire form · NDJSON style)
  res.write(`data: ${JSON.stringify(evt.data)}\n\n`);
}

/** 加载 fixture (LIUYE_DEMO_MODE=mock 时返预录 artifact) */
function loadFixture(fixturePath: string): Record<string, unknown> {
  const abs = path.isAbsolute(fixturePath) ? fixturePath : path.resolve(process.cwd(), fixturePath);
  if (!fs.existsSync(abs)) {
    throw new Error(`fixture not found: ${abs}`);
  }
  return JSON.parse(fs.readFileSync(abs, 'utf-8')) as Record<string, unknown>;
}

/** 构造 channel SSE event 序列 (老 v1.0 · 7 event 子集) */
function buildEventSequence(fixture: Record<string, unknown>, startSeq: number): SseEvent[] {
  const events: SseEvent[] = [];
  let seq = startSeq;

  const snapshot = (fixture.snapshot as Record<string, unknown>) ?? {};
  const candidates = (snapshot.candidates as unknown[]) ?? [];
  const summary = (snapshot.summary as Record<string, unknown>) ?? {};

  // 1. profile_loaded (Channel pilot · per sse-envelope.md §1.5 optional event)
  events.push({
    id: seq++,
    event: 'profile_loaded',
    data: {
      agent: AGENT_ID,
      ideal_profile: snapshot.seed ?? {},
      ts: new Date().toISOString(),
    },
  });

  // 2. stage: signal_density
  events.push({
    id: seq++,
    event: 'stage',
    data: {
      stage: 'signal_density',
      progress: 0.2,
      message: '11 信号源扫描中',
    },
  });

  // 3. tool_call (SearchProvider 调用)
  events.push({
    id: seq++,
    event: 'tool_call',
    data: {
      tool_name: 'channel.search_provider',
      args: { industry_code: 'C36', geo: '江苏-常州', scale: '规上中型' },
    },
  });

  // 4. tool_result (候选返回)
  events.push({
    id: seq++,
    event: 'tool_result',
    data: {
      tool_name: 'channel.search_provider',
      ok: true,
      result: { hits: candidates.length },
    },
  });

  // 5. stage: ranked
  events.push({
    id: seq++,
    event: 'stage',
    data: {
      stage: 'ranked',
      progress: 0.7,
      message: `${candidates.length} 候选已排序`,
    },
  });

  // 6. stream (LLM 摘要片段)
  events.push({
    id: seq++,
    event: 'stream',
    data: {
      text: `Top 候选: ${candidates.length} 家 · 难度分层 ${JSON.stringify(summary.by_difficulty ?? {})}`,
    },
  });

  // 7. done (per envelope §2.1 · ok=true · 含 payload tail + metrics + warnings + errors + trace_id)
  events.push({
    id: seq++,
    event: 'done',
    data: {
      event: 'done',
      version: '1.0',
      agent: AGENT_ID,
      session_id: `sess_${AGENT_ID}_${Date.now()}`,
      ok: true,
      ts: new Date().toISOString(),
      duration_ms: 2_400,
      metrics: {
        signal_total: 11,
        companies_found: candidates.length,
        final: candidates.length,
        kb_files_used: 3,
      },
      payload: {
        candidates,
        summary,
        data_source: 'mock',
      },
      warnings: [],
      errors: [],
      trace_id: `trace_${AGENT_ID}_${Date.now()}`,
    },
  });

  return events;
}

/** 启动 mock SSE server (programmatic API · export 供测试 import) */
export function start(port: number, fixturePath: string): http.Server {
  const app = express();
  app.use(cors());

  const demoMode = process.env.LIUYE_DEMO_MODE ?? 'mock';
  const fixture = loadFixture(fixturePath);

  app.get('/health', (_req: Request, res: Response) => {
    res.json({
      ok: true,
      agent: AGENT_ID,
      port,
      demo_mode: demoMode,
      fixture: path.basename(fixturePath),
    });
  });

  app.get('/api/channel/run', (req: Request, res: Response) => {
    // SSE headers
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache, no-transform');
    res.setHeader('Connection', 'keep-alive');
    res.setHeader('X-Accel-Buffering', 'no');
    res.flushHeaders();

    // Last-Event-ID replay (per sse-envelope.md §1.5 forward-compat)
    const lastEventId = parseInt(req.header('Last-Event-ID') ?? '0', 10);
    const startSeq = isNaN(lastEventId) ? 1 : lastEventId + 1;

    // heartbeat (15s · SSE comment line · 不算 seq)
    const heartbeat = setInterval(() => {
      try {
        res.write(`: ping ${Date.now()}\n\n`);
      } catch {
        clearInterval(heartbeat);
      }
    }, HEARTBEAT_INTERVAL_MS);

    // 推 event 序列 (demo mode = mock → 从 fixture 加载 · 否则 live 走真实 backend · 本 mock server 仅 mock)
    const events = buildEventSequence(fixture, startSeq);
    let i = 0;
    const drainTimer = setInterval(() => {
      if (i >= events.length) {
        clearInterval(drainTimer);
        clearInterval(heartbeat);
        res.end();
        return;
      }
      writeEvent(res, events[i]);
      i += 1;
    }, 200);

    req.on('close', () => {
      clearInterval(drainTimer);
      clearInterval(heartbeat);
    });
  });

  const server = app.listen(port, () => {
    console.log(`[mock-sse:${AGENT_ID}] listening on http://localhost:${port}`);
    console.log(`  fixture: ${fixturePath}`);
    console.log(`  demo_mode: ${demoMode}`);
    console.log(`  endpoints: GET /health · GET /api/channel/run (SSE)`);
  });
  return server;
}

/** CLI entry · node tests/mock-sse/channel.ts --port 8001 --fixture <path> */
function _parseArgs(argv: string[]): { port: number; fixture: string } {
  const args = argv.slice(2);
  let port = 8001;
  let fixture = 'tests/fixtures/channel_5candidates.json';
  for (let i = 0; i < args.length; i += 1) {
    if (args[i] === '--port' && i + 1 < args.length) {
      port = parseInt(args[i + 1], 10);
      i += 1;
    } else if (args[i] === '--fixture' && i + 1 < args.length) {
      fixture = args[i + 1];
      i += 1;
    }
  }
  return { port, fixture };
}

// CLI bootstrap (only when invoked directly · not on import)
if (typeof require !== 'undefined' && require.main === module) {
  const { port, fixture } = _parseArgs(process.argv);
  start(port, fixture);
}
