/**
 * W1-mock-test · 第 5 棒 · 2026-05-12
 * archive-storage.spec.ts · 老 sessionStorage 迁移 spec (brief §3 + §4.5 · v3 §6.2 verbatim)
 *
 * 验 `migrateArchiveStorage(liuyeSessionId)` 行为 (v3 §6.2):
 *   - 3 OLD_KEYS 全迁:
 *     * `credit-workspace-storage`
 *     * `report-workspace-storage`
 *     * `channel-workspace-storage`
 *   - idempotent · `archive_migrated_v1` 标记 · 第二次跑不动
 *   - 不丢字段: pinnedArtifactId / scrollAnchor / drafts / favorites
 *
 * 决策 (per brief): W1 frontend worker 不实做 `migrateArchiveStorage` ·
 * 但本 spec 不走 `.skip` · 改 **inline mock implementation** · 验逻辑本身.
 * 待 W2 frontend 实做后 · 替换 import 路径即跑真实 helper · 测试不动.
 *
 * Stack: jsdom 25 (`new JSDOM()` 拿 localStorage + sessionStorage · Node.js unit 跑 · 不需 Playwright)
 *
 * Run:
 *   cd tests && npx tsx migration/archive-storage.spec.ts
 *
 * Exit:
 *   0 = 全 PASS · 1 = 任一 case 失败
 */

import { JSDOM } from 'jsdom';

// ============================================================================
// migrateArchiveStorage · v3 §6.2 verbatim (W1 inline mock · W2 frontend 实做后 import 替换)
// ============================================================================

type NextUi = {
  pinnedArtifactId?: string;
  scrollAnchor?: string;
  drafts?: Record<string, string>;
  favorites?: string[];
};

const OLD_KEYS = [
  'credit-workspace-storage',
  'report-workspace-storage',
  'channel-workspace-storage',
] as const;

/**
 * v3 §6.2 verbatim (line 564-582):
 *
 * - 优先 localStorage · 兜底 sessionStorage (老 archive 双写)
 * - JSON.parse `.state` 子对象 (Zustand persist 结构 `{ state: {...}, version: N }`)
 * - 合并 pinnedArtifactId / scrollAnchor / drafts / favorites · 4 字段
 * - 写 `liuye:${sid}:ui` · 标 `liuye:${sid}:archive_migrated_v1=1`
 * - 二次跑 doneKey 已设 → return · 不动 next 数据
 */
function migrateArchiveStorage(liuyeSessionId: string): void {
  const doneKey = `liuye:${liuyeSessionId}:archive_migrated_v1`;
  if (sessionStorage.getItem(doneKey)) return;

  const next: NextUi = { drafts: {}, favorites: [] };

  for (const key of OLD_KEYS) {
    const raw = localStorage.getItem(key) ?? sessionStorage.getItem(key);
    if (!raw) continue;
    let state: Record<string, unknown> = {};
    try {
      const parsed = JSON.parse(raw) as { state?: Record<string, unknown> };
      state = parsed?.state ?? {};
    } catch {
      continue; // 坏 JSON · 跳过该 key (defensive · spec verbatim 没 try/catch · 但生产代码必有)
    }
    next.pinnedArtifactId ??= (state.pinnedArtifactId as string | undefined) ??
      ((state.pin as { artifactId?: string } | undefined)?.artifactId);
    next.scrollAnchor ??= state.scrollAnchor as string | undefined;
    Object.assign(next.drafts!, (state.drafts as Record<string, string> | undefined) ?? {});
    next.favorites!.push(...((state.favorites as string[] | undefined) ?? []));
  }

  sessionStorage.setItem(`liuye:${liuyeSessionId}:ui`, JSON.stringify(next));
  sessionStorage.setItem(doneKey, '1');
}

// ============================================================================
// jsdom · 模拟浏览器 storage (Node.js 无 localStorage/sessionStorage)
// ============================================================================

/**
 * 起一个 fresh JSDOM · 把 storage 装到 globalThis · 跑 helper · 复位
 * 每个 case 都跑一遍 · 防互相污染
 */
function withFreshDom(fn: () => void): void {
  const dom = new JSDOM('', { url: 'http://localhost:3210' });
  const win = dom.window;
  // Node.js global 装到 window 上面的 storage
  // jsdom 25 实现 localStorage / sessionStorage · 直接用即可
  // 注: TS 类型上 globalThis 不含 localStorage · 用 (globalThis as any) cast
  const g = globalThis as unknown as {
    localStorage: Storage;
    sessionStorage: Storage;
    window: typeof win;
  };
  const savedLocal = g.localStorage;
  const savedSession = g.sessionStorage;
  const savedWindow = g.window;
  g.localStorage = win.localStorage;
  g.sessionStorage = win.sessionStorage;
  g.window = win;
  try {
    fn();
  } finally {
    // 还原 (虽然 spec 跑完即退 · 防多 case 跨 dom 污染)
    g.localStorage = savedLocal;
    g.sessionStorage = savedSession;
    g.window = savedWindow;
    dom.window.close();
  }
}

// ============================================================================
// 老 archive Zustand persist payload 形态 (per W1-frontend 老仓 Grep · whiteboard-store
// / customer-store / panel-layout-store 都走 `{ state: {...}, version: N }` shape)
// ============================================================================

function makePersistedPayload(state: Record<string, unknown>, version = 0): string {
  return JSON.stringify({ state, version });
}

// ============================================================================
// Test runner (simple assertion harness · 不引 vitest/jest)
// ============================================================================

type CheckResult = { case: string; ok: boolean; detail?: string };
const results: CheckResult[] = [];

function check(name: string, ok: boolean, detail?: string): void {
  results.push({ case: name, ok, detail });
  const tag = ok ? 'PASS' : 'FAIL';
  // eslint-disable-next-line no-console
  console.log(`  [${tag}] ${name}${detail ? ` · ${detail}` : ''}`);
}

function assertEq<T>(name: string, actual: T, expected: T, detailFn?: () => string): void {
  const ok = JSON.stringify(actual) === JSON.stringify(expected);
  check(name, ok, ok ? undefined : `expected ${JSON.stringify(expected)} · actual ${JSON.stringify(actual)}${detailFn ? ` · ${detailFn()}` : ''}`);
}

function assertNull(name: string, value: unknown): void {
  const ok = value === null || value === undefined;
  check(name, ok, ok ? undefined : `expected null/undefined · actual ${JSON.stringify(value)}`);
}

function assertNotNull(name: string, value: unknown): void {
  const ok = value !== null && value !== undefined;
  check(name, ok, ok ? undefined : `expected non-null · actual ${JSON.stringify(value)}`);
}

// ============================================================================
// Test Cases
// ============================================================================

const SID = 'liuye_sess_w1_mock_test_5';

function caseSingleKeyMigrationCredit(): void {
  withFreshDom(() => {
    // 准备: 老 credit-workspace-storage 单 key + state 含 4 字段
    localStorage.setItem(
      'credit-workspace-storage',
      makePersistedPayload({
        pinnedArtifactId: 'art_credit_panorama_001',
        scrollAnchor: 'section-financial-ratios',
        drafts: { 'draft_decision_1': '建议批 PASS · 看待数据时效' },
        favorites: ['cust_A001', 'cust_A002'],
      })
    );

    migrateArchiveStorage(SID);

    // 验: liuye:<sid>:ui 写入 · doneKey 标记
    const uiRaw = sessionStorage.getItem(`liuye:${SID}:ui`);
    assertNotNull('case-1 · uiRaw written', uiRaw);
    const ui = JSON.parse(uiRaw!) as NextUi;
    assertEq('case-1 · pinnedArtifactId merged', ui.pinnedArtifactId, 'art_credit_panorama_001');
    assertEq('case-1 · scrollAnchor merged', ui.scrollAnchor, 'section-financial-ratios');
    assertEq('case-1 · drafts merged', ui.drafts, { 'draft_decision_1': '建议批 PASS · 看待数据时效' });
    assertEq('case-1 · favorites merged', ui.favorites, ['cust_A001', 'cust_A002']);
    assertEq('case-1 · doneKey set', sessionStorage.getItem(`liuye:${SID}:archive_migrated_v1`), '1');
  });
}

function caseAllThreeKeysMerged(): void {
  withFreshDom(() => {
    // 3 OLD_KEYS 全在 · 各贡献不同字段 · 测合并优先级 (first non-null wins for pinned/scrollAnchor · concat for drafts/favorites)
    localStorage.setItem(
      'credit-workspace-storage',
      makePersistedPayload({
        pinnedArtifactId: 'art_credit_001',
        drafts: { 'k_credit': 'credit draft' },
        favorites: ['fav_credit_1'],
      })
    );
    localStorage.setItem(
      'report-workspace-storage',
      makePersistedPayload({
        scrollAnchor: 'section-narrative',
        drafts: { 'k_report': 'report draft' },
        favorites: ['fav_report_1', 'fav_report_2'],
      })
    );
    localStorage.setItem(
      'channel-workspace-storage',
      makePersistedPayload({
        drafts: { 'k_channel': 'channel draft' },
        favorites: ['fav_channel_1'],
      })
    );

    migrateArchiveStorage(SID);

    const ui = JSON.parse(sessionStorage.getItem(`liuye:${SID}:ui`)!) as NextUi;
    // pinnedArtifactId: 仅 credit 有 · 取 credit (??= first non-null)
    assertEq('case-2 · pinnedArtifactId from credit', ui.pinnedArtifactId, 'art_credit_001');
    // scrollAnchor: 仅 report 有
    assertEq('case-2 · scrollAnchor from report', ui.scrollAnchor, 'section-narrative');
    // drafts: 3 来源全合并 · Object.assign 累加 (后写覆盖前写 · 但 key 不同故全保留)
    assertEq('case-2 · drafts merged 3 sources', ui.drafts, {
      'k_credit': 'credit draft',
      'k_report': 'report draft',
      'k_channel': 'channel draft',
    });
    // favorites: push 累加 · 顺序按 OLD_KEYS (credit → report → channel)
    assertEq('case-2 · favorites concat 3 sources', ui.favorites, [
      'fav_credit_1',
      'fav_report_1',
      'fav_report_2',
      'fav_channel_1',
    ]);
  });
}

function caseLegacyPinShape(): void {
  withFreshDom(() => {
    // 老仓有的 case: state.pin.artifactId (nested) · 而非 state.pinnedArtifactId (flat)
    // v3 §6.2 verbatim 支持双形态: `state.pinnedArtifactId ?? state.pin?.artifactId`
    localStorage.setItem(
      'channel-workspace-storage',
      makePersistedPayload({
        pin: { artifactId: 'art_legacy_pin_xyz' },
        favorites: [],
      })
    );
    migrateArchiveStorage(SID);
    const ui = JSON.parse(sessionStorage.getItem(`liuye:${SID}:ui`)!) as NextUi;
    assertEq('case-3 · legacy state.pin.artifactId fallback', ui.pinnedArtifactId, 'art_legacy_pin_xyz');
  });
}

function caseIdempotentSecondRun(): void {
  withFreshDom(() => {
    // 第一次跑 · 写入完
    localStorage.setItem(
      'report-workspace-storage',
      makePersistedPayload({
        pinnedArtifactId: 'art_first_run',
        drafts: { 'd1': 'first run draft' },
        favorites: ['f1'],
      })
    );
    migrateArchiveStorage(SID);
    const uiFirst = sessionStorage.getItem(`liuye:${SID}:ui`);
    assertNotNull('case-4 · first run written', uiFirst);

    // 改 source data · 期望第二次跑不动 (doneKey 守卫)
    localStorage.setItem(
      'report-workspace-storage',
      makePersistedPayload({
        pinnedArtifactId: 'art_should_NOT_appear',
        drafts: { 'd2': 'should NOT appear' },
        favorites: ['should_NOT_appear'],
      })
    );
    migrateArchiveStorage(SID);
    const uiSecond = sessionStorage.getItem(`liuye:${SID}:ui`);

    // 验: 第二次跑后 ui 字符串完全不变 (idempotent)
    assertEq('case-4 · second run no-op (idempotent · doneKey 守卫)', uiSecond, uiFirst);
    // 验: doneKey 仍是 1 (没被重写为别的值)
    assertEq(
      'case-4 · doneKey unchanged',
      sessionStorage.getItem(`liuye:${SID}:archive_migrated_v1`),
      '1'
    );
  });
}

function caseSessionStorageFallback(): void {
  withFreshDom(() => {
    // v3 §6.2 verbatim: `localStorage.getItem(key) ?? sessionStorage.getItem(key)` · localStorage 缺时 sessionStorage 兜底
    sessionStorage.setItem(
      'credit-workspace-storage',
      makePersistedPayload({
        pinnedArtifactId: 'art_sessionStorage_fallback',
        favorites: ['fb_1'],
      })
    );
    migrateArchiveStorage(SID);
    const ui = JSON.parse(sessionStorage.getItem(`liuye:${SID}:ui`)!) as NextUi;
    assertEq('case-5 · sessionStorage fallback', ui.pinnedArtifactId, 'art_sessionStorage_fallback');
    assertEq('case-5 · favorites from sessionStorage', ui.favorites, ['fb_1']);
  });
}

function caseEmptyOldKeysNoCrash(): void {
  withFreshDom(() => {
    // 3 OLD_KEYS 都不存在 · migrate 应不抛 · 仍写 ui (空 next) + doneKey
    migrateArchiveStorage(SID);
    const ui = JSON.parse(sessionStorage.getItem(`liuye:${SID}:ui`)!) as NextUi;
    assertEq('case-6 · empty source · next.drafts={}', ui.drafts, {});
    assertEq('case-6 · empty source · next.favorites=[]', ui.favorites, []);
    assertNull('case-6 · empty source · next.pinnedArtifactId undefined', ui.pinnedArtifactId);
    assertNull('case-6 · empty source · next.scrollAnchor undefined', ui.scrollAnchor);
    assertEq(
      'case-6 · doneKey still set after empty migrate',
      sessionStorage.getItem(`liuye:${SID}:archive_migrated_v1`),
      '1'
    );
  });
}

function caseFirstNonNullWinsForPinned(): void {
  withFreshDom(() => {
    // v3 §6.2 verbatim: `next.pinnedArtifactId ??= ...` · 第一个非空 wins · 后续不覆盖
    // OLD_KEYS 顺序: credit → report → channel · credit 先填 wins
    localStorage.setItem(
      'credit-workspace-storage',
      makePersistedPayload({ pinnedArtifactId: 'art_credit_pinned_first' })
    );
    localStorage.setItem(
      'report-workspace-storage',
      makePersistedPayload({ pinnedArtifactId: 'art_report_pinned_should_NOT_win' })
    );
    migrateArchiveStorage(SID);
    const ui = JSON.parse(sessionStorage.getItem(`liuye:${SID}:ui`)!) as NextUi;
    assertEq(
      'case-7 · first non-null wins (credit before report per OLD_KEYS order)',
      ui.pinnedArtifactId,
      'art_credit_pinned_first'
    );
  });
}

function caseSidNamespaceIsolated(): void {
  withFreshDom(() => {
    // 两个不同 liuyeSessionId · 互不影响 · ns key 隔离
    const SID_A = 'liuye_sess_A';
    const SID_B = 'liuye_sess_B';
    localStorage.setItem(
      'credit-workspace-storage',
      makePersistedPayload({ pinnedArtifactId: 'art_shared' })
    );

    migrateArchiveStorage(SID_A);
    migrateArchiveStorage(SID_B);

    const uiA = JSON.parse(sessionStorage.getItem(`liuye:${SID_A}:ui`)!) as NextUi;
    const uiB = JSON.parse(sessionStorage.getItem(`liuye:${SID_B}:ui`)!) as NextUi;
    assertEq('case-8 · sid A pinned merged', uiA.pinnedArtifactId, 'art_shared');
    assertEq('case-8 · sid B pinned merged', uiB.pinnedArtifactId, 'art_shared');
    assertEq(
      'case-8 · sid A doneKey isolated',
      sessionStorage.getItem(`liuye:${SID_A}:archive_migrated_v1`),
      '1'
    );
    assertEq(
      'case-8 · sid B doneKey isolated',
      sessionStorage.getItem(`liuye:${SID_B}:archive_migrated_v1`),
      '1'
    );
  });
}

// ============================================================================
// Main
// ============================================================================

function main(): number {
  // eslint-disable-next-line no-console
  console.log('[archive-storage-migration] start · 8 case · jsdom unit');
  // eslint-disable-next-line no-console
  console.log('  spec source: v3 §6.2 verbatim · migrateArchiveStorage(liuyeSessionId)');
  // eslint-disable-next-line no-console
  console.log('  note: W1 frontend 未实做 migrateArchiveStorage · 本 spec 用 inline mock 验逻辑 · W2 实做后替 import');

  caseSingleKeyMigrationCredit();
  caseAllThreeKeysMerged();
  caseLegacyPinShape();
  caseIdempotentSecondRun();
  caseSessionStorageFallback();
  caseEmptyOldKeysNoCrash();
  caseFirstNonNullWinsForPinned();
  caseSidNamespaceIsolated();

  const total = results.length;
  const pass = results.filter((r) => r.ok).length;
  const fail = total - pass;

  // eslint-disable-next-line no-console
  console.log(`\n[archive-storage-migration] total=${total} pass=${pass} fail=${fail}`);

  if (fail > 0) {
    // eslint-disable-next-line no-console
    console.log('FAIL cases:');
    for (const r of results) {
      if (!r.ok) {
        // eslint-disable-next-line no-console
        console.log(`  · ${r.case}${r.detail ? ` :: ${r.detail}` : ''}`);
      }
    }
    return 1;
  }
  // eslint-disable-next-line no-console
  console.log(
    '[archive-storage-migration] OK · 3 OLD_KEYS + idempotent + 不丢字段 + sid 隔离 + legacy pin shape · all 8 case pass'
  );
  return 0;
}

const exitCode = main();
process.exit(exitCode);
