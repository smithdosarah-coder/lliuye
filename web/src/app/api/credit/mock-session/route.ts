/**
 * /api/credit/mock-session
 *
 * Stage 2 · P3F 轨 4 · feat/credit-mock-endpoint 等价物（前端 Next.js route 实现 ·
 * onboarding §1.3 明文允许）。frozen branch feat/credit-mock-endpoint 实现在
 * `agent_credit/mock_sessions.py` 后端 · 违 §1.3 红线 (后端禁动)。本任改写为
 * Next.js route handler · 消费 main 已落地 `CREDIT_SESSIONS` 三板块 (corp/small/retail)。
 *
 * 用法:
 *   GET /api/credit/mock-session              → corp 默认
 *   GET /api/credit/mock-session?mode=corp    → 对公 800 万 · approved-cut
 *   GET /api/credit/mock-session?mode=small   → 普惠小微 300 万 · pending
 *   GET /api/credit/mock-session?mode=retail  → 对私 50 万 · approved
 *
 * 返回 shape: CreditSession (web/src/lib/mock/agent-credit-session.ts)
 */

import { NextResponse } from "next/server";
import {
  CREDIT_SESSIONS,
  type CreditMode,
} from "@/lib/mock/agent-credit-session";

const VALID_MODES: ReadonlyArray<CreditMode> = ["corp", "small", "retail"];

function isValidMode(value: string | null): value is CreditMode {
  return value !== null && (VALID_MODES as ReadonlyArray<string>).includes(value);
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const raw = searchParams.get("mode");
  const mode: CreditMode = isValidMode(raw) ? raw : "corp";
  const session = CREDIT_SESSIONS[mode];
  return NextResponse.json(
    { mode, session },
    { headers: { "cache-control": "no-store" } },
  );
}
