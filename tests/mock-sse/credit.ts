/**
 * Mock SSE Server · Credit (Agent3 授信) · 端口 8002
 *
 * W1 mock-test worker 第 3 棒 · 老 v1.0 SSE 协议 (per docs/contracts/sse-envelope.md v1.0 §1.5)
 * 不发 liuye 11 event · 由 backend `adapters/sse_v1_to_liuye.py` 转译
 *
 * 7 老 event: profile_loaded / stage / stream / tool_call / tool_result / done / error
 * Heartbeat: 15s · seq 单调递增 · Last-Event-ID replay
 * Demo mode: env `LIUYE_DEMO_MODE=mock` → 返预录 fixture (tests/fixtures/credit_decision_PASS.json)
 *
 * CLI:
 *   node tests/mock-sse/credit.ts --port 8002 --fixture tests/fixtures/credit_decision_PASS.json
 */

import express, { type Request, type Response } from 'express';
import cors from 'cors';
import * as fs from 'fs';
import * as http from 'http';
import * as path from 'path';

const AGENT_ID = 'credit';
const HEARTBEAT_INTERVAL_MS = 15_000;

interface SseEvent {
  id: number;
  event: 'profile_loaded' | 'stage' | 'stream' | 'tool_call' | 'tool_result' | 'done' | 'error';
  data: Record<string, unknown>;
}

function writeEvent(res: Response, evt: SseEvent): void {
  res.write(`id: ${evt.id}\n`);
  res.write(`event: ${evt.event}\n`);
  res.write(`data: ${JSON.stringify(evt.data)}\n\n`);
}

function loadFixture(fixturePath: string): Record<string, unknown> {
  const abs = path.isAbsolute(fixturePath) ? fixturePath : path.resolve(process.cwd(), fixturePath);
  if (!fs.existsSync(abs)) {
    throw new Error(`fixture not found: ${abs}`);
  }
  return JSON.parse(fs.readFileSync(abs, 'utf-8')) as Record<string, unknown>;
}

/** 构造 credit SSE event 序列 (4 维评分 + red_lines + decision_letter · 老 v1.0) */
function buildEventSequence(fixture: Record<string, unknown>, startSeq: number): SseEvent[] {
  const events: SseEvent[] = [];
  let seq = startSeq;

  const snapshot = (fixture.snapshot as Record<string, unknown>) ?? {};
  const scoring = (snapshot.scoring as Record<string, unknown>) ?? {};
  const decision = (snapshot.decision as Record<string, unknown>) ?? {};
  const qc = (snapshot.qc as Record<string, unknown>) ?? {};

  // 1. stage: feature_extract
  events.push({
    id: seq++,
    event: 'stage',
    data: {
      stage: 'feature_extract',
      progress: 0.15,
      message: '特征抽取中',
    },
  });

  // 2. tool_call (scoring_model_corporate)
  events.push({
    id: seq++,
    event: 'tool_call',
    data: {
      tool_name: 'credit.scoring_model_corporate',
      args: { segment: 'corporate', subject_id_hash: '5f8a3c1d2e9b6047' },
    },
  });

  // 3. tool_result (4 维评分)
  events.push({
    id: seq++,
    event: 'tool_result',
    data: {
      tool_name: 'credit.scoring_model_corporate',
      ok: true,
      result: {
        composite_score: scoring.composite_score ?? 75,
        risk_grade: scoring.risk_grade ?? 'B',
      },
    },
  });

  // 4. stage: red_line_check
  events.push({
    id: seq++,
    event: 'stage',
    data: {
      stage: 'red_line_check',
      progress: 0.55,
      message: '红线检查中',
    },
  });

  // 5. stream (LLM 决策推理片段)
  events.push({
    id: seq++,
    event: 'stream',
    data: {
      text: `4 维评分汇总 · 综合分 ${scoring.composite_score ?? 75} · 风险定档 ${scoring.risk_grade ?? 'B'}`,
    },
  });

  // 6. stage: decision_compose
  events.push({
    id: seq++,
    event: 'stage',
    data: {
      stage: 'decision_compose',
      progress: 0.9,
      message: '审批意见生成中',
    },
  });

  // 7. done (per envelope §2.1 · payload = CreditPayload per sse-envelope.md §3.3)
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
      duration_ms: 3_800,
      metrics: {
        score_total: scoring.composite_score ?? 75,
        red_line_count: 0,
        evidence_count: 3,
      },
      payload: {
        score_radar: scoring,
        red_lines: [],
        decision_letter: decision,
        qc,
        evidence_trail: (fixture.evidence_refs as unknown[]) ?? [],
        decision_verdict: decision.decision ?? '通过',
        segment: 'corporate',
        data_source: 'mock',
      },
      warnings: [],
      errors: [],
      trace_id: `trace_${AGENT_ID}_${Date.now()}`,
    },
  });

  return events;
}

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

  app.get('/api/credit/decide', (req: Request, res: Response) => {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache, no-transform');
    res.setHeader('Connection', 'keep-alive');
    res.setHeader('X-Accel-Buffering', 'no');
    res.flushHeaders();

    const lastEventId = parseInt(req.header('Last-Event-ID') ?? '0', 10);
    const startSeq = isNaN(lastEventId) ? 1 : lastEventId + 1;

    const heartbeat = setInterval(() => {
      try {
        res.write(`: ping ${Date.now()}\n\n`);
      } catch {
        clearInterval(heartbeat);
      }
    }, HEARTBEAT_INTERVAL_MS);

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
    }, 250);

    req.on('close', () => {
      clearInterval(drainTimer);
      clearInterval(heartbeat);
    });
  });

  const server = app.listen(port, () => {
    console.log(`[mock-sse:${AGENT_ID}] listening on http://localhost:${port}`);
    console.log(`  fixture: ${fixturePath}`);
    console.log(`  demo_mode: ${demoMode}`);
    console.log(`  endpoints: GET /health · GET /api/credit/decide (SSE)`);
  });
  return server;
}

function _parseArgs(argv: string[]): { port: number; fixture: string } {
  const args = argv.slice(2);
  let port = 8002;
  let fixture = 'tests/fixtures/credit_decision_PASS.json';
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

if (typeof require !== 'undefined' && require.main === module) {
  const { port, fixture } = _parseArgs(process.argv);
  start(port, fixture);
}
