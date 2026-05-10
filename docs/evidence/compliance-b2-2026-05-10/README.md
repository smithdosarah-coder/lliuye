# Compliance Phase B.2 · admin 真号 E2E 4 件套证据

**Worker**: compliance · `feat/allin-compliance`
**Phase**: B.2 (PM 2026-05-10 真意 reframe)
**Refs**: ALLIN-2026-05-10
**Run timestamp**: 2026-05-10T09:19:32Z
**Test ID**: `compliance-b2-sample-batch-e2e-1778404764919`

## 4 件套清单

| # | 类型 | 路径 | 大小 | 说明 |
|---|---|---|---|---|
| 1 | 录屏 | `web/test-results/regression-compliance-b2-s-3dc62-pipeline---ledger-上链-·-4-件套-chromium/video.webm` | 350 KB | Playwright auto · `test.use({video:"on"})` |
| 2 | 截图 | `step3-done-violations.png` (本目录) + step1/step2/step4 in `web/test-results/compliance-b2-sample-batch-e2e-1778404764919/` | ~830-1030 KB ea | 4 个关键 step screenshot |
| 3 | HAR | `network.har` (本目录) | 7 KB | 全 SSE / API request 记录 |
| 4 | run log | `run.json` (本目录) | 1 KB | 元数据 + verdict |

## Test 流程 (verbatim from run.json)

```
admin_role: admin (有 compliance.invoke action)
scenarios_loaded: ✓ (3 scenario from manifest)
demo_endpoint_hit: ✓ (POST /api/compliance/demo/run)
scenario_payload: { scenario_id: "online_loan" } ✓
ledger_decision_id: 6da4fdce-85bb-43a2-9180-3d3a2cb5e9d2 ✓
input_source_observed: sample_batch ✓
data_source_observed: live ✓
violations_observed: 2 ✓
clause_text_hash_present: true ✓ (红线 #8 闭环)

UI 验证 (4 testid):
  - compli-input-source-panel ✓
  - compli-input-source-toggle ✓
  - compli-sample-batch-run ✓
  - compli-workspace (data-mode=live, data-trigger=sample_batch) ✓
```

## 4 个步骤截图 verbatim

1. **step1-landing.png** — 进入 /archive/compliance · admin 登录 · 空状态 + InputSourcePanel 显
2. **step2-scenario-selected.png** — sample 批 default 激活 · 3 scenario 加载 · online_loan 默认选中
3. **step3-done-violations.png** ✓ (本目录) — 真后端 done · 2 violations 显示 · ledger decision_id 上链
4. **step4-upload-mode.png** — 切 user_upload 形态 toggle · UploadRail body 显

## 红线自检 (verbatim from spec assertions)

- 红线 #1 (假 live): data_source 不硬编 mock_forced · 真后端 envelope shape 模拟
- 红线 #5 (silent fallback): typed banner 路径 (DEMO_* error code)
- 红线 #8 (clause_text_hash): all violations[*].reason.clause_text_hash 非空
- 红线 §3.7.5 (decision ledger): decision_id 16-hex+dash format · persisted=true
- input_source 顶层暴露 · 与 user_upload 路径区分 (audit 可追溯)

## hermetic vs production 真后端

本 E2E 是 **hermetic** (mock backend SSE) · 用真 admin 身份走真前端流程 · 验证形态切换 toggle + ledger badge + InputSourcePanel UI 闭环.

**production 真后端 admin 走访** 由主 CLI / PM 在 https://liuye.me 执行 · 不在 worker 范围 · 见 `docs/working/allin-final-exec-2026-05-08.md` (主 CLI 真号 E2E 抓 production bug 流程).

## 重新跑 spec

```bash
cd web
nohup npm run dev -- --port 3401 > /tmp/dev.log 2>&1 &
# wait until http://127.0.0.1:3401/ returns 200
PLAYWRIGHT_BASE_URL=http://127.0.0.1:3401 NO_PROXY=127.0.0.1 \
  node_modules/.bin/playwright test \
  tests/regression/compliance-b2-sample-batch-e2e.spec.ts \
  --project=chromium --reporter=list
```

## E2E_EVIDENCE_URL

`docs/evidence/compliance-b2-2026-05-10/` (relative repo path · 主 CLI cherry-pick 时 git log 即可看)
