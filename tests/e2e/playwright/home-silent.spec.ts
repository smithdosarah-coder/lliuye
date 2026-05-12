/**
 * W1-mock-test · 第 5 棒 · 2026-05-12
 * home-silent.spec.ts · ground truth 静默首页 1:1 验证 (brief §3 + §4.4)
 *
 * Coverage (per brief):
 *   1. composer 尺寸: 840 × 72 (.composer-shell__inner getBoundingClientRect · CSS var --c-composer-w/h)
 *   2. composer radius 36 · pill 32h · icon 36 · send 42 (CSS variable + DOM measurement)
 *   3. 字体栈含 4 family (Funnel Display / Instrument Sans / Noto SC / JetBrains Mono · getComputedStyle.fontFamily)
 *   4. 4 Agent chip 可见 + 中文文案 (data-testid=agent-chip-{channel,credit,report,alert})
 *   5. IME guard · 中文 composition 中 Enter 不发 (page.keyboard.type 模拟 + insertCompositionText event)
 *   6. selector EMPTY sentinel 不漂 (检查 lib/empty.ts 导出 frozen sentinel · 通过 window.__lib_empty__ probe 间接验)
 *   7. 7 data-testid 全在: hero-static / composer-textarea / composer-submit / agent-chip-{4}
 *
 * 不准 (per brief):
 *   - 不自启 frontend dev (跨棒 dev :3210 已在跑 · webServer disabled in config)
 *   - 不接 backend / SSE (本 spec 仅前端静默 hero 静态渲染 · W1 skeleton)
 *   - 不实做 selector sentinel runtime probe (W1 frontend page.tsx 未暴露 window probe · 仅断言 DOM 不抛错 · 验 store 初始 readonly)
 */
import { test, expect, type Page } from '@playwright/test';

// ============================================================================
// Constants · v3 附录 D.5 verbatim (与 credit_matrix_next/app/globals.css 同源)
// ============================================================================
const TOKENS = {
  composerW: 840,
  composerH: 72,
  radius: 36,
  send: 42,
  pillH: 32,
  iconBox: 36,
} as const;

// ground truth 字体栈 4 family · per W1-frontend layout.tsx + globals.css --c-font-* tokens.
// 注: next/font/google 注入的 var(--font-*) 是 hashed wrapper · 实际 fontFamily 含 fallback chain.
// 验证策略: getComputedStyle(body).fontFamily 必含以下 4 family substring (至少 1 个匹配)
const REQUIRED_FONT_FAMILIES = [
  'Funnel Display',
  'Instrument Sans',
  'Noto Sans SC',
  'JetBrains Mono', // 数字/代码字体 · 验首页全局栈 (body var(--c-font-body) 内含)
] as const;

const AGENT_CHIPS: ReadonlyArray<{ readonly id: string; readonly label: string }> = [
  { id: 'channel', label: '客户经理助理' },
  { id: 'credit', label: '授信助理' },
  { id: 'report', label: '报告助理' },
  { id: 'alert', label: '预警助理' },
] as const;

const REQUIRED_TESTIDS = [
  'hero-static',
  'composer-textarea',
  'composer-submit',
  'agent-chip-channel',
  'agent-chip-credit',
  'agent-chip-report',
  'agent-chip-alert',
] as const;

// ============================================================================
// Helpers
// ============================================================================

/**
 * 读 CSS variable 解析后的 px 数字 · 用 getComputedStyle on :root.
 * e.g. getCssVarPx(page, '--c-composer-w') => 840
 */
async function getCssVarPx(page: Page, varName: string): Promise<number> {
  const raw = await page.evaluate((name) => {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }, varName);
  // raw 形如 "840px" · parseFloat 拿数字
  const num = parseFloat(raw);
  if (!Number.isFinite(num)) {
    throw new Error(`CSS var ${varName} = "${raw}" 不是有效 px 值`);
  }
  return num;
}

/**
 * 拿 element 的 getBoundingClientRect width/height (实际渲染尺寸 · 比 offsetWidth 精确)
 */
async function getElementBox(page: Page, selector: string): Promise<{ width: number; height: number }> {
  return await page.evaluate((sel) => {
    const el = document.querySelector(sel);
    if (!el) throw new Error(`selector ${sel} not found`);
    const rect = el.getBoundingClientRect();
    return { width: rect.width, height: rect.height };
  }, selector);
}

// ============================================================================
// Tests
// ============================================================================

test.describe('home-silent (ground truth 1:1 · v3 §10 + 附录 D.5)', () => {
  test.beforeEach(async ({ page }) => {
    // page.goto 失败 → throw · Playwright auto-fail test (而非 hang)
    await page.goto('/', { waitUntil: 'domcontentloaded' });
    // 等首页关键 DOM 节点出现 (避免静态渲染未完即 query · v3 §10 锁 SSR static · 不需 hydrate)
    await page.waitForSelector('[data-testid="hero-static"]', { state: 'visible', timeout: 5000 });
  });

  test('7 data-testid 全在 DOM (hero / composer / 4 chip)', async ({ page }) => {
    for (const tid of REQUIRED_TESTIDS) {
      const locator = page.getByTestId(tid);
      await expect(locator, `testid="${tid}" 缺失`).toBeVisible();
    }
  });

  test('composer 尺寸 840 × 72 (.composer-shell__inner · v3 附录 D.5 锁)', async ({ page }) => {
    // 取 inner box · 因为 composer-shell wrap 是 flex container (max-width: composer-w)
    // 实际 840×72 box 在 .composer-shell__inner 上
    const box = await getElementBox(page, '.composer-shell__inner');
    expect(box.width, `composer width 期望 ${TOKENS.composerW} · 实际 ${box.width}`).toBe(TOKENS.composerW);
    expect(box.height, `composer height 期望 ${TOKENS.composerH} · 实际 ${box.height}`).toBe(TOKENS.composerH);
  });

  test('token 锁: radius 36 · pill 32h · icon 36 · send 42 (CSS var)', async ({ page }) => {
    const composerW = await getCssVarPx(page, '--c-composer-w');
    const composerH = await getCssVarPx(page, '--c-composer-h');
    const radius = await getCssVarPx(page, '--c-radius');
    const send = await getCssVarPx(page, '--c-send');
    const pillH = await getCssVarPx(page, '--c-pill-h');
    const iconBox = await getCssVarPx(page, '--c-icon');

    expect(composerW, '--c-composer-w').toBe(TOKENS.composerW);
    expect(composerH, '--c-composer-h').toBe(TOKENS.composerH);
    expect(radius, '--c-radius').toBe(TOKENS.radius);
    expect(send, '--c-send').toBe(TOKENS.send);
    expect(pillH, '--c-pill-h').toBe(TOKENS.pillH);
    expect(iconBox, '--c-icon').toBe(TOKENS.iconBox);
  });

  test('send button 实测 42 × 42 (.composer-shell__submit)', async ({ page }) => {
    const box = await getElementBox(page, '.composer-shell__submit');
    expect(box.width, `send 宽 ${TOKENS.send}`).toBe(TOKENS.send);
    expect(box.height, `send 高 ${TOKENS.send}`).toBe(TOKENS.send);
  });

  test('字体栈含 Funnel Display / Instrument Sans / Noto SC / JetBrains Mono', async ({ page }) => {
    // next/font/google 用 hashed CSS module 注入 --font-* variable · 真 CSS var 名是
    // `--font-display` / `--font-body` / `--font-zh` / `--font-mono` 等 (layout.tsx 显式设)
    // body className 含 6 个 hashed module class · 每个 class 内 declare 一个 --font-* var.
    //
    // 验证策略 (3 路兜底):
    //   1. body className 含 family slug (funnel_display / instrument_sans / noto_sans_sc / jetbrains_mono)
    //   2. body 实测 fontFamily 含至少一个 stack 内 family fallback (Funnel Display / Instrument Sans / Noto SC / JetBrains Mono)
    //   3. globals.css :root 锚 var(--c-font-*) 含全部 4 family 字面值 (CSS module class:where 注入 hashed CSS var · 解析后 raw string)
    const probe = await page.evaluate(() => {
      const bodyClass = document.body.className;
      const bodyComputed = getComputedStyle(document.body).fontFamily;
      // 从 stylesheet 里 dump --c-font-* 解析串 (从 :root 上 getComputedStyle 拿出 cascaded CSS var)
      const root = document.documentElement;
      const cs = getComputedStyle(root);
      const csBody = getComputedStyle(document.body);
      // 拿 :root + body 上的 var 解析串 (CSS module class 加在 body 上 · 故 --font-* var 走 body scope)
      const tokens = {
        rootFontDisplay: cs.getPropertyValue('--c-font-display'),
        rootFontBody: cs.getPropertyValue('--c-font-body'),
        rootFontZh: cs.getPropertyValue('--c-font-zh'),
        rootFontMono: cs.getPropertyValue('--c-font-mono'),
        bodyFontDisplay: csBody.getPropertyValue('--c-font-display'),
        bodyFontBody: csBody.getPropertyValue('--c-font-body'),
        bodyFontZh: csBody.getPropertyValue('--c-font-zh'),
        bodyFontMono: csBody.getPropertyValue('--c-font-mono'),
        bodyComputed,
        bodyClass,
      };
      return tokens;
    });

    const allTokens = Object.values(probe).join(' | ').toLowerCase();

    // 4 family 验证 (substring match: 接受任一形式)
    //   "Funnel Display" 或 "funnel_display" (next-font module slug 形式)
    //   "Instrument Sans" 或 "instrument_sans"
    //   "Noto Sans SC" 或 "noto_sans_sc"
    //   "JetBrains Mono" 或 "jetbrains_mono"
    const familyForms: ReadonlyArray<{ readonly label: string; readonly alternates: ReadonlyArray<string> }> = [
      { label: 'Funnel Display', alternates: ['funnel display', 'funnel_display'] },
      { label: 'Instrument Sans', alternates: ['instrument sans', 'instrument_sans'] },
      { label: 'Noto Sans SC', alternates: ['noto sans sc', 'noto_sans_sc'] },
      { label: 'JetBrains Mono', alternates: ['jetbrains mono', 'jetbrains_mono'] },
    ] as const;

    for (const f of familyForms) {
      const matched = f.alternates.some((alt) => allTokens.includes(alt));
      expect(
        matched,
        `字体栈缺 "${f.label}" · 验证 forms ${JSON.stringify(f.alternates)} · 实测 tokens (前 600 字): ${allTokens.slice(0, 600)}`
      ).toBe(true);
    }
  });

  test('4 Agent chip 可见 + 中文文案对 + height ≤ 32px (pill h)', async ({ page }) => {
    for (const chip of AGENT_CHIPS) {
      const locator = page.getByTestId(`agent-chip-${chip.id}`);
      await expect(locator, `chip ${chip.id} 不可见`).toBeVisible();
      await expect(locator, `chip ${chip.id} 文案`).toHaveText(chip.label);

      // chip height 必 ≤ 32 (pillH · v3 §4 chip 28-32h)
      const box = await locator.boundingBox();
      if (!box) throw new Error(`chip ${chip.id} boundingBox null`);
      expect(box.height, `chip ${chip.id} 高度 ${box.height} 超 32px 上限`).toBeLessThanOrEqual(TOKENS.pillH);
      expect(box.height, `chip ${chip.id} 高度 ${box.height} 低于 28px 下限`).toBeGreaterThanOrEqual(28);
    }
  });

  test('IME guard · 中文 composition 中 Enter 不发送 (textarea 保留 composition 文本)', async ({ page }) => {
    const textarea = page.getByTestId('composer-textarea');
    await textarea.click();
    await textarea.focus();

    // 模拟中文 IME composition: dispatch compositionstart + input (with isComposing) + compositionupdate
    // 浏览器 IME 是 platform-level event · Playwright 不能真模拟拼音 OS 输入 ·
    // 我们走 DOM API 直接派 compositionstart event · 然后 type "zhongwen" 作为 composition data · 再 press Enter.
    //
    // 期望: composition 中 useImeGuard.isComposing.current=true · onKeyDown 跳过 preventDefault + submit ·
    // textarea.value 保留 "zhongwen" (form 没 submit · 没 reset)
    //
    // 注: 当前 W1 Composer 没有 form submit 路径 (仅 console.log + setText('')) · 故验 textarea.value 仍含输入文本

    // Step 1: 派 compositionstart (React 走 onCompositionStart → guard.isComposing.current = true)
    await textarea.evaluate((el: HTMLTextAreaElement) => {
      el.focus();
      // React composition event 需要走 nativeEvent · 派一个 native compositionstart
      const startEvt = new CompositionEvent('compositionstart', { bubbles: true, data: '' });
      el.dispatchEvent(startEvt);
    });

    // Step 2: type 拼音 (delay 50 模拟真人速度)
    await page.keyboard.type('zhongwen', { delay: 50 });

    // Step 3: press Enter (在 composition 中 · 期望 guard 跳过 submit · textarea 不清空)
    // 模拟 IME composition 中按 Enter · 派 KeyboardEvent with isComposing flag
    await textarea.evaluate((el: HTMLTextAreaElement) => {
      const evt = new KeyboardEvent('keydown', {
        key: 'Enter',
        code: 'Enter',
        bubbles: true,
        cancelable: true,
        isComposing: true, // 浏览器 IME compose 中 isComposing=true · guard.onKeyDown 兜底
      });
      el.dispatchEvent(evt);
    });

    // Step 4: 派 compositionend (拿 final text)
    await textarea.evaluate((el: HTMLTextAreaElement) => {
      const endEvt = new CompositionEvent('compositionend', { bubbles: true, data: 'zhongwen' });
      el.dispatchEvent(endEvt);
    });

    // Verify: textarea 仍含 "zhongwen" 文字 · 没被 Enter 清空
    const value = await textarea.inputValue();
    expect(value, `composition 中 Enter 后 textarea 应保留输入 · 实际 "${value}"`).toContain('zhongwen');
  });

  test('IME guard · 非 composition 状态 Enter 触发 submit (textarea 清空 · 控制组对照)', async ({ page }) => {
    // 控制组: 不派 compositionstart · 直接 type + Enter · 期望 Composer.handleSubmit setText('') 清空
    const textarea = page.getByTestId('composer-textarea');
    await textarea.click();
    await textarea.fill('hello world');

    // Enter without composition · onKeyDown 走 preventDefault + submit · Composer setText('')
    await textarea.press('Enter');

    // 等一拍 (React state 更新 + DOM patch)
    await page.waitForTimeout(100);

    const value = await textarea.inputValue();
    // 非 composition Enter 应触发 submit · Composer 内部 handleSubmit 清空 setText('')
    expect(value, `非 composition Enter 后 textarea 应清空 · 实际 "${value}"`).toBe('');
  });

  test('selector EMPTY sentinel · 初始 messages/artifacts/tool_calls 不触发 inline ?? [] (回归守卫)', async ({ page }) => {
    // W1 frontend page.tsx 不消费 useLiuyeStore (W2-W4 接 messages-shell) · 故无法直接 inspect runtime state.
    // 退而求其次: 验静默 hero 渲染稳定 · 无 console error (selector inline ?? [] 引发 infinite render loop 时
    // React 会抛 "Maximum update depth exceeded" warning · captured in browser console)
    const consoleErrors: string[] = [];
    const consoleWarnings: string[] = [];
    page.on('console', (msg) => {
      const text = msg.text();
      if (msg.type() === 'error') consoleErrors.push(text);
      if (msg.type() === 'warning') consoleWarnings.push(text);
    });

    // 等 1s 让任何潜在 infinite loop 在此期内崩 (React 18+ 会 throw after ~50 同步 set state)
    await page.waitForTimeout(1000);

    // 过滤: next/font preload warning · React DevTools 提示 · service worker · 这些不算 selector regression
    const benign = (s: string) =>
      s.includes('Download the React DevTools') ||
      s.includes('preload') ||
      s.includes('Hot Module Replacement') ||
      s.includes('[next-router]');
    const realErrors = consoleErrors.filter((s) => !benign(s));
    const loopWarnings = consoleWarnings.filter(
      (s) => s.includes('Maximum update depth') || s.includes('infinite loop')
    );

    expect(realErrors, `selector 守卫 · console error: ${realErrors.join(' | ')}`).toHaveLength(0);
    expect(loopWarnings, `selector 守卫 · infinite loop warn: ${loopWarnings.join(' | ')}`).toHaveLength(0);
  });

  test('页面 lang=zh-CN · data-theme=light (默认主题锁)', async ({ page }) => {
    const lang = await page.evaluate(() => document.documentElement.lang);
    const theme = await page.evaluate(() => document.documentElement.getAttribute('data-theme'));
    expect(lang, 'html lang').toBe('zh-CN');
    expect(theme, 'html data-theme · light 默认').toBe('light');
  });
});
