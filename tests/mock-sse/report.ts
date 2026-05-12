/**
 * Mock SSE Server · Report (Agent6 报告 · v16 主管线) · 端口 8003
 *
 * W1 mock-test worker 第 3 棒 · 老 v1.0 SSE 协议 (per docs/contracts/sse-envelope.md v1.0 §1.5)
 * 不发 liuye 11 event · 由 backend `adapters/sse_v1_to_liuye.py` 转译
 *
 * 7 老 event: profile_loaded / stage / stream / tool_call / tool_result / done / error
 *
 * v16 5 stage (中文 stage_label · per fixture pipeline_progress.stage_log):
 *   ingest 材料解析 → extract 字段抽取 → infer 结构推断 → write 段落生成 → audit 质量复核
 *
 * Heartbeat: 15s · seq 单调递增 · Last-Event-ID replay
 * Demo mode: env `LIUYE_DEMO_MODE=mock` → 返预录 fixture (tests/fixtures/report_v16_PARTIAL.json)
 *
 * CLI:
 *   node tests/mock-sse/report.ts --port 8003 --fixture tests/fixtures/report_v16_PARTIAL.json
 */

import express, { type Request, type Response } from 'express';
import cors from 'cors';
import * as fs from 'fs';
import * as http from 'http';
import * as path from 'path';

const AGENT_ID = 'report';
const HEARTBEAT_INTERVAL_MS = 15_000;

interface SseEvent {
  id: number;
  event: 'profile_loaded' | 'stage' | 'stream' | 'tool_call' | 'tool_result' | 'done' | 'error';
  data: Record<string, unknown>;
}

interface StageLogEntry {
  stage_key: string;
  stage_label: string;
  started_at: string;
  ended_at: string;
  status: string;
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

/** v16 5-stage 中文 stage_label fallback (per quality_scorer.py + v16_pipeline.py CLI naming) */
const V16_STAGE_LOG_FALLBACK: StageLogEntry[] = [
  { stage_key: 'ingest', stage_label: '材料解析', started_at: '', ended_at: '', status: 'done' },
  { stage_key: 'extract', stage_label: '字段抽取', started_at: '', ended_at: '', status: 'done' },
  { stage_key: 'infer', stage_label: '结构推断', started_at: '', ended_at: '', status: 'done' },
  { stage_key: 'write', stage_label: '段落生成', started_at: '', ended_at: '', status: 'done' },
  { stage_key: 'audit', stage_label: '质量复核', started_at: '', ended_at: '', status: 'done' },
];

/** 构造 report SSE event 序列 (v16 5 stage · 中文 stage_label · 老 v1.0) */
function buildEventSequence(fixture: Record<string, unknown>, startSeq: number): SseEvent[] {
  const events: SseEvent[] = [];
  let seq = startSeq;

  const snapshot = (fixture.snapshot as Record<string, unknown>) ?? {};
  const header = (snapshot.header as Record<string, unknown>) ?? {};
  const pipelineProgress = (snapshot.pipeline_progress as Record<string, unknown>) ?? {};
  const stageLog =
    ((pipelineProgress.stage_log as StageLogEntry[]) ?? V16_STAGE_LOG_FALLBACK).slice(0, 5);
  const qcGate = (snapshot.qc_gate as Record<string, unknown>) ?? {};
  const reportJson = (snapshot.report_json as Record<string, unknown>) ?? {};

  // 1. profile_loaded (报告材料就绪)
  events.push({
    id: seq++,
    event: 'profile_loaded',
    data: {
      agent: AGENT_ID,
      uploaded_files: 6,
      template_id: header.template_id ?? 'tmpl_corp_credit_v16_2026q2',
      ts: new Date().toISOString(),
    },
  });

  // 2-6. 5 stage event (verbatim 中文 stage_label · 每 stage 1 event)
  stageLog.forEach((stage, idx) => {
    const progress = (idx + 1) / 5;
    events.push({
      id: seq++,
      event: 'stage',
      data: {
        stage: stage.stage_key,
        stage_label: stage.stage_label,
        progress: Number(progress.toFixed(2)),
        message: `${stage.stage_label} (${idx + 1}/5)`,
      },
    });
  });

  // 7. tool_call (classifier)
  events.push({
    id: seq++,
    event: 'tool_call',
    data: {
      tool_name: 'report.v16_classifier',
      args: { template_id: header.template_id ?? '', material_count: 6 },
    },
  });

  // 8. tool_result (classifier 输出)
  const classification = (snapshot.classification as Record<string, unknown>) ?? {};
  events.push({
    id: seq++,
    event: 'tool_result',
    data: {
      tool_name: 'report.v16_classifier',
      ok: true,
      result: {
        elements_total: classification.elements_total ?? 246,
        by_op: classification.by_op ?? {},
      },
    },
  });

  // 9. stream (Evidence-First section_generator 三阶段)
  events.push({
    id: seq++,
    event: 'stream',
    data: {
      text: 'Evidence-First 三阶段 (汇集→Grounded 生成→自审) · 第 1 章 streaming chunk 0/3',
    },
  });

  // 10. stream (chunk 1/3)
  events.push({
    id: seq++,
    event: 'stream',
    data: {
      text: '段落生成 · 第 1 章 chunk 1/3 · 公司隶属汽车制造业(C36)',
    },
  });

  // 11. stream (chunk 2/3 final · 含 "未能自动填写")
  events.push({
    id: seq++,
    event: 'stream',
    data: {
      text: '段落生成 · 第 1 章 chunk 2/3 final · 未能自动填写：股东个人涉诉历史明细 · 建议人工补充',
    },
  });

  // 12. tool_call (quality_scorer)
  events.push({
    id: seq++,
    event: 'tool_call',
    data: {
      tool_name: 'report.quality_scorer',
      args: { dimensions: 9 },
    },
  });

  // 13. tool_result (QC 9 维评分)
  events.push({
    id: seq++,
    event: 'tool_result',
    data: {
      tool_name: 'report.quality_scorer',
      ok: true,
      result: {
        verdict: qcGate.verdict ?? 'PARTIAL',
        dimensions_passed: qcGate.dimensions_passed ?? 7,
        dimensions_total: qcGate.dimensions_total ?? 9,
        blocked_dimensions: qcGate.blocked_dimensions ?? [],
      },
    },
  });

  // 14. done (per envelope §2.1 · payload = ReportPayload per sse-envelope.md §3.2)
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
      duration_ms: 12_000,
      metrics: {
        field_completeness: reportJson.field_completeness ?? 0.78,
        evidence_rate: reportJson.evidence_rate ?? 0.91,
        qc_score:
          ((qcGate.dimensions_passed as number) ?? 7) /
          ((qcGate.dimensions_total as number) ?? 9),
        hallucination_rate: 0.02,
      },
      payload: {
        report_json: reportJson,
        uploaded_files: 6,
        kb_hits: 12,
        extracted_fields: classification,
        draft_sections: snapshot.sections ?? [],
        qc_result: qcGate,
        unfilled_marker_count: ((reportJson.fields_pending as unknown[]) ?? []).length,
        stage_log: stageLog,
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
      stage_log_5: V16_STAGE_LOG_FALLBACK.map((s) => `${s.stage_key}(${s.stage_label})`),
    });
  });

  app.get('/api/report/v16/fill', (req: Request, res: Response) => {
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
    }, 300);

    req.on('close', () => {
      clearInterval(drainTimer);
      clearInterval(heartbeat);
    });
  });

  const server = app.listen(port, () => {
    console.log(`[mock-sse:${AGENT_ID}] listening on http://localhost:${port}`);
    console.log(`  fixture: ${fixturePath}`);
    console.log(`  demo_mode: ${demoMode}`);
    console.log(`  v16 stages: ${V16_STAGE_LOG_FALLBACK.map((s) => s.stage_label).join(' → ')}`);
    console.log(`  endpoints: GET /health · GET /api/report/v16/fill (SSE)`);
  });
  return server;
}

function _parseArgs(argv: string[]): { port: number; fixture: string } {
  const args = argv.slice(2);
  let port = 8003;
  let fixture = 'tests/fixtures/report_v16_PARTIAL.json';
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
