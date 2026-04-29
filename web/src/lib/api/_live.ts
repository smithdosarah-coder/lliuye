/**
 * Shared live-mode API client base · Stage Fix W-FIX-A3 (per live-fallback-banner-spec v1.0).
 *
 * 给 Riskctrl / Alert / 各 Agent client 用 · 统一:
 * - LiveFailError class · 含 status code + endpoint + body excerpt
 * - drainSse() · drain SSE stream + 解析 data: lines · onEvent callback
 * - 4xx / 5xx / network 异常 → 抛 LiveFailError · 不 silent swap mock
 *
 * 协议 §2 规则 1 · live mode 调用失败必须显式 banner · 不允许静默 fallback。
 */
"use client";


export class LiveFailError extends Error {
  /** HTTP status (0 = network error / SSE 异常) */
  status: number;
  /** API endpoint path */
  endpoint: string;
  /** body 截断 · 用于 banner 显示具体 detail */
  bodyExcerpt: string;

  constructor(message: string, status: number, endpoint: string, bodyExcerpt = "") {
    super(message);
    this.name = "LiveFailError";
    this.status = status;
    this.endpoint = endpoint;
    this.bodyExcerpt = bodyExcerpt;
  }
}


export type SseEventCallback = (event: {
  /** outer event field 或 inner payload type */
  type: string;
  /** raw parsed JSON · 调用方按 type 解析 */
  data: Record<string, unknown>;
}) => void;


/** 统一 fetch · 4xx/5xx → 抛 LiveFailError + body excerpt */
export async function postLive<T>(
  endpoint: string,
  body: unknown,
  init?: RequestInit,
): Promise<T> {
  let resp: Response;
  try {
    resp = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      ...init,
    });
  } catch (e) {
    throw new LiveFailError(
      `network error: ${e instanceof Error ? e.message : String(e)}`,
      0,
      endpoint,
      "",
    );
  }
  if (!resp.ok) {
    const excerpt = (await resp.text().catch(() => "")).slice(0, 200);
    throw new LiveFailError(
      `HTTP ${resp.status}`,
      resp.status,
      endpoint,
      excerpt,
    );
  }
  return (await resp.json()) as T;
}


/** SSE 流 · onEvent 收每条 data: ... · network/4xx/5xx → LiveFailError */
export async function streamSse(
  endpoint: string,
  body: unknown,
  onEvent: SseEventCallback,
  init?: RequestInit,
): Promise<void> {
  let resp: Response;
  try {
    resp = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(body),
      ...init,
    });
  } catch (e) {
    throw new LiveFailError(
      `network error: ${e instanceof Error ? e.message : String(e)}`,
      0,
      endpoint,
      "",
    );
  }

  if (!resp.ok) {
    const excerpt = (await resp.text().catch(() => "")).slice(0, 200);
    throw new LiveFailError(
      `HTTP ${resp.status}`,
      resp.status,
      endpoint,
      excerpt,
    );
  }

  if (!resp.body) {
    throw new LiveFailError("empty SSE body", 0, endpoint, "");
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      const parts = buf.split("\n\n");
      buf = parts.pop() ?? "";
      for (const part of parts) {
        let outerType = "";
        let dataLine = "";
        for (const line of part.split("\n")) {
          if (line.startsWith("event: ")) {
            outerType = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            dataLine = line.slice(6);
          }
        }
        if (!dataLine) continue;
        let parsed: Record<string, unknown>;
        try {
          parsed = JSON.parse(dataLine);
        } catch {
          continue;
        }
        const innerType =
          (parsed.event as string | undefined) ??
          (parsed.type as string | undefined) ??
          ((parsed.payload as { type?: string } | undefined)?.type ?? "");
        const evt = {
          type: outerType || innerType || "",
          data: parsed,
        };
        onEvent(evt);
        // 后端 error event 也算 live failure (但流已通)
        if (
          evt.type === "error" ||
          (parsed.event === "error") ||
          ((parsed.payload as { type?: string } | undefined)?.type === "error")
        ) {
          const inner =
            (parsed.payload as { message?: string } | undefined)?.message ??
            (parsed.message as string | undefined) ??
            "SSE error event";
          throw new LiveFailError(
            `SSE error event: ${inner}`,
            0,
            endpoint,
            inner.slice(0, 200),
          );
        }
      }
    }
  } catch (e) {
    if (e instanceof LiveFailError) throw e;
    throw new LiveFailError(
      `stream error: ${e instanceof Error ? e.message : String(e)}`,
      0,
      endpoint,
      "",
    );
  }
}


/** 友好 banner 文案 · 按 spec §2 §1 规范 */
export function liveFailBannerText(err: LiveFailError, agentLabel: string): string {
  const code = err.status > 0 ? `HTTP ${err.status}` : "network/SSE";
  return `⚠️ 后端 ${agentLabel} 调用失败 (${code}) · 当前显 fallback 演示数据`;
}
