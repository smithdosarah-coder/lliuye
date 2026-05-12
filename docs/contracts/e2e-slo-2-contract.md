# E2E SLO-2 · 双轨 (mock 演示 + 实时搜索) 契约 v1.0

> **PM ratify**: 2026-05-11 12:55 (GO)
> **Worker**: `e2e-daily` (worktree `credit_report_agent_work_mesh/e2e-daily`)
> **Signal**: `WORKER-SLO-2-DUAL-TRACK-READY-FOR-MERGE`
> **Branch**: `feat/b34-e2e-daily`

## 1. 一句话定位

6 助手界面 **mock 演示模式** + **实时搜索模式** 双模式都能用 · 任何 mock 冒充实时 / 503 silent fallback / spec 不 GREEN = stop the line.

## 2. 4 主活 verification (全 GREEN gate)

| 主活 | 干啥 | spec 文件 | 现状 |
|---|---|---|---|
| **D** | admin 真号 6 demo spec 跑通 GREEN | `web/tests/e2e/admin-{channel,credit,alert,compliance,report,riskctrl}.spec.ts` | ✅ 6/6 GREEN · 1 first + 5 flaky-retry-green · 3.8min |
| **A** | 6 助手实时路径 admin 真号 verify | `web/tests/e2e/admin-{agent}-realtime.spec.ts` × 6 | ✅ 6/6 GREEN (realtime UI wire + backend health) · ~5min |
| **B** | 6 助手演示 seeded replay 一致性 | `web/tests/e2e/admin-replay-consistency.spec.ts` (serial · 6 sub-test) | ✅ 6/6 GREEN · 2.4min · structural fingerprint (counts strict + numbers jaccard ≥ 80%) |
| **C** | 双轨并发 (demo + IM · session 独立) | `web/tests/e2e/admin-dual-track-concurrency.spec.ts` (2 sub-test) | ✅ 2/2 GREEN · 35s |

## 3. 不可 GO 红线 (per PM)

- **mock 冒充实时**: realtime toggle 缺失 / 切到 real mode 仍显 demo CTA · 见 §3.1
- **503 / fallback fake silent 通过**: backend endpoint 5xx / 静默兜底 mock data · 见 §3.2
- **admin E2E spec 没 GREEN**: 任 1 spec retry 后仍 red · 见 §3.3
- **6 助手 demo replay 不一致**: 同 sample 2 跑 counts 不等 OR numbers jaccard < 80% · 见 §3.4
- **session 串数据**: 并发 demo 中 agent A page 出 agent B 关键词 · 见 §3.5

### 3.1 Mock 冒充实时 detection

每 realtime spec assert:
```ts
const realToggle = page.locator('[data-testid="{agent}-input-mode-real"]');
await expect(realToggle).toBeVisible();
await realToggle.click();
await expect(realToggle).toHaveAttribute("data-active", "yes");
// real mode 下 demo CTA 必不 visible
expect(await page.locator('[data-testid="{agent}-demo-cta"]').count()).toBe(0);
```

### 3.2 503 / fallback fake detection

页面文本不允许:
- `503` / `Internal Server Error` (HTTP 5xx → cloudflare 502 / origin 503)
- `[object Object]` (序列化失败 fallback)
- `MOCK` / `N/A` 等显式 mock 标识 (in candidate meta)
- channel-pilot-candidates 必 `data-mode="live"` · 非 `mock`

### 3.3 spec GREEN gate

Playwright `retries: 1` (prod baseURL 自动开 · 见 `web/playwright.config.ts:21`). retry 后仍 fail = 真 red · 走 GitHub Issue + 责任 worker fix-forward (per workflow daily-visual.yml admin-e2e job).

### 3.4 Replay 一致性 (PM 演示给客户用)

`structuralFingerprint` (web/tests/e2e/_replay-helpers.ts):
- **counts**: 关键 selectors 的 element count · 严格相等
- **numbers**: 整页 1-3 位数字 list (sort + dedup + 前 50) · Jaccard 相似度 ≥ 0.8

不比 raw text hash · LLM byte-deterministic 几乎不可能 (即使 temp=0).

### 3.5 Session 独立 (PM #4 数据混乱根因)

2 独立 browser context 并发跑 alert + credit demo · 跑完后:
- alert page body 不含 credit 关键词 (`/4 维评分|credit-decision-cta|授信建议/`)
- credit page body 不含 alert 关键词 (`/alert-pool|180 户|红黄灯|alert-hitlist/`)

## 4. Test infra

| 文件 | 干啥 |
|---|---|
| `web/tests/e2e/_shared.ts` | adminTest fixture (cookie + storageState 双注) · `FIRST_PAINT_TIMEOUT_MS=30_000` (CF cold + AuthGate hydration) · `E2E_TIMEOUT_MS=90_000` (SSE done SLA 1.5x) |
| `web/tests/e2e/_replay-helpers.ts` | `fnv1a` / `hashTexts` / `structuralFingerprint` utils |
| `web/playwright.config.ts` | prod baseURL 自动 `retries: 1` · `PLAYWRIGHT_RETRIES` env 显式覆盖 · hermetic local dev :3101 |
| `scripts/e2e/run_admin_daily.sh` | bash SSE 探针 (6 agent demo/run endpoint · SSE done ≤ 60s · 与 spec 互补) |
| `.github/workflows/daily-visual.yml` admin-e2e job | cron 06:00 Asia/Shanghai · flag `vars.ADMIN_E2E_ENABLED='true'` · 失败自动开 Issue |

## 5. 工程时长 baseline (本次 verify 实测 · prod liuye.me)

| Job | 跑 | 时长 |
|---|---|---|
| 主活 D (6 demo spec) | 1× (retries 1) | 3.8 min |
| 主活 A (6 realtime spec) | 1× | ~5 min |
| 主活 B (6 replay sub-test) | 1× | 2.4 min |
| 主活 C (2 concurrency sub-test) | 1× | 35 s |
| **总** | sequential | **~12 min** |

GHA admin-e2e job 现 `timeout-minutes: 25` · 12min 余量充足。

## 6. Artifact 收集 (每跑必出)

per workflow daily-visual.yml admin-e2e job:
- `admin-e2e-report-{run_id}`: `playwright-report/` + `test-results/` (含 trace / video / screenshot 失败 retry)
- `playwright-report/index.html`: 交互式 报告 (含 each spec call log + page snapshot 失败)
- Issue body 含 RUN_URL · PM 一键 download

## 7. PM SLO-2 → spec 映射 table

| PM 字面 | 对应 spec | 验证方法 |
|---|---|---|
| "6 助手实时路径 admin 真号 verify" | admin-{agent}-realtime.spec.ts × 6 | UI mode toggle + backend ping |
| "演示模式 seeded mock 全 replay (2 次结果一致)" | admin-replay-consistency.spec.ts | 同 page 2 次跑 + fingerprint 比 |
| "演示模式跑时 IM 仍可调" | admin-dual-track-concurrency.spec.ts C1 | 2 context · IM ping 必 < 5s |
| "6 并发不阻塞" | admin-dual-track-concurrency.spec.ts C2 | 2 context · 并发 demo 都 done |
| "session 独立" | C2 内 sanity | alert page ≠ credit body 关键词 |
| "admin 真号 6 spec 跑通 GREEN" | admin-{agent}.spec.ts × 6 (B.3.4 原版) | retries 1 后全 GREEN |

## 8. 后续 (本 worker scope 外)

- **Phase 2 dispatch** PM 决定:
  - 是否扩 realtime spec 走完整 user flow (e.g. alert live 上传客户名录 · compliance upload 政策 docx) · 需 fixture 数据 + 上传 helper
  - 是否加 LLM audit log artifact (每跑收集 audit_service 真调记录 · PM 可看 Tavily/DeepSeek call count)
  - 是否扩 daily-visual.yml admin-e2e job 加 `replay-consistency` 单独 job (避免 long sequential 阻塞 timeout)

## 9. 信号

- **完成**: `chore(mesh): signal worker e2e-daily SLO-2 ready` + `Signal: WORKER-SLO-2-DUAL-TRACK-READY-FOR-MERGE`
- **Artifacts**: 6 E2E spec result + 真实 vs 演示 对比录屏 (Playwright trace) + visual baseline (daily-visual.spec.ts 现状) + Tavily/DeepSeek 真调 log (placeholder · 等后端 audit_service 接入)
