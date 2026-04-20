/**
 * Fallback helper — wraps SSE async generators with automatic fallback
 * to a local mock fixture on timeout / connection failure / backend error.
 *
 * Usage:
 *   const gen = withFallback(
 *     () => streamChannelSearch({ query }),
 *     "/mock/channel_run.json",
 *     { timeoutMs: 2000, replayEvents: (j) => [...j.run_mock_events, j.done] },
 *   );
 *   for await (const [evt, source] of gen) { ... }
 *
 * Contract: the generator yields tuples [event, source] where
 *   source ∈ "live" | "mock".  The consumer can show a "降级模式"
 *   badge when source === "mock".
 */

export type FallbackSource = "live" | "mock";

export interface FallbackOptions<TEvent> {
  /** Max ms to wait for the FIRST live event before switching to mock. */
  timeoutMs?: number;
  /**
   * Converter from mock JSON payload → array of events to replay.
   * Each event is yielded with a small delay to mimic streaming.
   */
  replayEvents: (mockJson: unknown) => TEvent[];
  /** Delay between replayed mock events (ms). Default 280. */
  replayIntervalMs?: number;
}

/**
 * Wrap a live SSE generator with mock fallback.
 *
 * Behavior:
 *  - Starts the live generator and races against a timeout.
 *  - If the first event arrives within timeoutMs, streams "live" events.
 *  - If the live generator throws, the fetch rejects, or no event arrives
 *    before timeout → aborts live, fetches mockPath, replays events as "mock".
 *  - Mid-stream failures ALSO switch to mock (events not delivered yet are replayed).
 */
export async function* withFallback<TEvent>(
  startLive: (signal: AbortSignal) => AsyncGenerator<TEvent>,
  mockPath: string,
  opts: FallbackOptions<TEvent>
): AsyncGenerator<[TEvent, FallbackSource]> {
  const { timeoutMs = 2000, replayEvents, replayIntervalMs = 280 } = opts;

  const ctrl = new AbortController();
  let livePrimed = false;

  try {
    const liveGen = startLive(ctrl.signal);
    // Race first event against timeout.
    const firstResult = await Promise.race([
      liveGen.next().then((r) => ({ kind: "live" as const, r })),
      new Promise<{ kind: "timeout" }>((resolve) =>
        setTimeout(() => resolve({ kind: "timeout" }), timeoutMs)
      ),
    ]);

    if (firstResult.kind === "timeout") {
      // timed out — abort and replay mock
      ctrl.abort();
      yield* replayMock<TEvent>(mockPath, replayEvents, replayIntervalMs);
      return;
    }

    livePrimed = true;
    const first = firstResult.r;
    if (first.done) return;
    yield [first.value, "live"];

    // Continue pumping live generator
    while (true) {
      const next = await liveGen.next();
      if (next.done) return;
      yield [next.value, "live"];
    }
  } catch (e) {
    // If we errored BEFORE the live stream began producing, go to mock.
    // If we errored MID-stream (some live events already consumed),
    // also fall forward with mock so UX stays demoable.
    if (!livePrimed) {
      ctrl.abort();
    }
    // Re-enter with mock
    try {
      yield* replayMock<TEvent>(mockPath, replayEvents, replayIntervalMs);
    } catch (err) {
      // mock fetch also failed — bubble original error
      throw e instanceof Error ? e : new Error(String(err));
    }
  }
}

async function* replayMock<TEvent>(
  mockPath: string,
  replayEvents: (j: unknown) => TEvent[],
  intervalMs: number
): AsyncGenerator<[TEvent, FallbackSource]> {
  const res = await fetch(mockPath, { cache: "no-store" });
  if (!res.ok) throw new Error(`mock fetch ${mockPath} ${res.status}`);
  const json = (await res.json()) as unknown;
  const events = replayEvents(json);
  for (const evt of events) {
    await new Promise((r) => setTimeout(r, intervalMs));
    yield [evt, "mock"];
  }
}

/**
 * Simple helper — fetch a JSON mock fixture, always "mock" source.
 * For Agent2/4/5 which have no live backend route.
 */
export async function fetchMockJson<T = unknown>(
  mockPath: string
): Promise<T> {
  const res = await fetch(mockPath, { cache: "no-store" });
  if (!res.ok) throw new Error(`mock fetch ${mockPath} ${res.status}`);
  return (await res.json()) as T;
}
