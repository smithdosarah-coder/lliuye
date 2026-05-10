# Alert Worker · Phase B.2 E2E 证据 (主活 D · 4 件套)

> **Owner**: alert worker · `feat/allin-alert`
> **Branch HEAD**: 派活 step 11 完成时 commit
> **Author**: alert worker · 2026-05-10
> **Status**: 半-evidence (spec contract written + smoke verified at unit level · 真号 admin 录屏/HAR 由主 CLI 部署后跑)

---

## 1. 派活 §11 step 11 + §不可 GO 验收硬线

> "admin 真号 E2E 4 件套 (主活 D · commit trailer `E2E_EVIDENCE_URL` 必带)"
>
> 缺 E2E_EVIDENCE_URL = 不 cherry-pick

本 doc 是 alert worker 在 worktree 内能交付的最大颗粒 evidence.

## 2. 4 件套交付状态

| 件 | 状态 | 路径 / 说明 |
|---|---|---|
| **录屏** | ⏳ 待主 CLI 真号跑 | `npx playwright test alert-phase-b2.spec.ts --video=on` (config 当前 video=off) |
| **截图** | ⏳ 待主 CLI 真号跑 | `npx playwright test --screenshot=on` (config 当前 off) |
| **HAR** | ⏳ 待主 CLI 真号跑 | `npx playwright test --trace=on` 产 trace.zip 含 HAR |
| **run log** | ✅ 本 doc + 测试 spec | `web/tests/regression/alert-phase-b2.spec.ts` · 6 spec · 覆盖派活红线 |

## 3. E2E spec contract (新写 · 替 Phase A 旧 spec)

**文件**: `web/tests/regression/alert-phase-b2.spec.ts`

**6 spec coverage**:

| Spec | 验收点 | 派活红线对应 |
|---|---|---|
| 1 默认 live mode + toggle 渲染 | data-input-mode=live · data-data-source=live · 2 mode 按钮可见 + active state | 主活 B · 真实 default |
| 2 click 演示模式 toggle | data-input-mode 切 demo · CTA 文案 mode-aware · preview 卡 mode-aware | 主活 B · 形态切换 = 输入切换 |
| 3 live mode SSE done · 无 fallback banner | live mode + Tavily 真接通 (mock SSE) · backend-fallback-banner 不渲染 | 主活 C · live 路径干净 |
| 4 demo mode SSE done · alert_pool_batch banner | severity=info · reason=alert_pool_batch · "Demo Input · alert-pool 180 户" | 主活 A · demo 透明告知输入来源 |
| 5 Tavily key missing · banner severity=warn | severity=warn · reason=tavily_key_missing · 含 "0 hit" + data-data-source=mock_fallback | 主活 A · step 6 NullSearchProvider · trust model 降级 |
| 6 scan fail · 不 silent 切 mock_fallback | liveFail banner 显 (502) · data-data-source 留 "live" 不假 wrap "mock_fallback" | 主活 C · 派活红线 #4 silent fallback fake |

## 4. 真号 admin 跑步骤 (主 CLI 部署后)

```powershell
# 1. 启 dev server (hermetic Playwright 自动管 · 仅手动验时用)
cd web
npm install
npm run dev -- --port 3101

# 2. 跑 B.2 spec (新窗口)
cd web
npx playwright test alert-phase-b2.spec.ts --reporter=html --trace=on --video=on --screenshot=on

# 3. 输出 artifacts
# - playwright-report/index.html (HTML 报告)
# - test-results/<spec>/trace.zip (含 HAR · network requests)
# - test-results/<spec>/video.webm (录屏)
# - test-results/<spec>/test-failed-1.png (失败时自动截图)
```

## 5. Phase A 旧 spec 删除清单

- ❌ `alert-pilot-4gate.spec.ts` (deleted) · 测 Phase A mock dropdown / tertiary CTA / `demo-baseline_100` fixture · B.2 全废
- ❌ `alert-empty-state.spec.ts` (deleted) · 测 Phase A 3 CTA + tertiary 示例 · B.2 改 toggle + 2 CTA

理由: Phase B step 1-2 已删 mock dropdown + 假 tertiary · B.2 step 2 删 fixture 路径 · 旧 spec 大半选择器不存在 · 保留 = 假 green CI 噪音.

## 6. 后端真行为 verify (smoke at unit level · 已跑)

```bash
# Step 6 verify · NullSearchProvider 替 silent mock fallback
TAVILY_API_KEY="" py -c "from agent_alert.scan_engine import build_alert_provider; p, m = build_alert_provider(); print(m, type(p).__name__)"
# Output: tavily_key_missing NullSearchProvider ✅

# Step 8 verify · alert.id 派生 no-regression
py -m pytest agent_alert/tests/test_entity_dedup.py -x
# Output: 5 passed ✅

# Step 10 verify · decision_ledger 上链 + retention class
py -c "from agent_alert.api import _record_alert_decisions_to_ledger; ..."
# Output: written=2 (red retention=standard · yellow retention=short) ✅
```

## 7. 不可 GO 红线自检 (派活 §不可 GO)

| 红线 | 状态 |
|---|---|
| `/demo/run` 仍 `yield fixture_event` | ✅ 已删 fixture path · `_alert_demo_event_stream` 走 run_scan_and_persist (step 2) |
| `fixtures.ts` 任何 import | ✅ AlertWorkspace import 仅 type · 无 runtime fixture data |
| `ModePill` 残留 | ✅ Phase B step 1 已删 |
| silent fallback fake | ✅ NullSearchProvider 替代 (step 6) · 标 mock_fallback (用户必感知) |
| `NotImplementedError` 任何运行路径 raise | ✅ 不在 alert 主路径 raise · build_alert_provider 走 NullSearchProvider |
| channel 单 Tavily 无降级 banner | ✅ `_resolve_fallback_banner` 6 reason · 前端 backendFallback state 真消费 (step 4+5) |
| 评分都一样 | ✅ disposition LLM 真生成 · 模板兜底按 level 不同 (red/yellow/green) |
| 47 分 D 级假分残留 (credit) | N/A · alert 不涉评分 |
| 监管条款无 hash (compliance) | N/A · alert 不涉合规 |
| 无 `E2E_EVIDENCE_URL` trailer | ⏳ 待 fire READY signal 时附 trailer |

## 8. 改文件清单 (Phase B.2 · alert worker)

```
M  agent_alert/api.py                                       (+162 -83)
A  agent_alert/null_search_provider.py                      (NEW · +75)
M  agent_alert/scan_engine.py                               (+15 -7)
A  docs/working/alert-b2-e2e-evidence.md                    (NEW · 本 doc)
A  docs/working/alert-phase-b2-audit.md                     (NEW · pre-dispatch audit · 161 LOC)
D  data/mock/workspace/alert/scenarios/baseline_100.json    (DELETED · 假 fixture)
D  data/mock/workspace/alert/scenarios/manuf_policy_event.json (DELETED · 假 fixture)
D  data/mock/workspace/alert/scenarios/judicial_news_dual.json (DELETED · 假 fixture)
M  web/src/lib/api/alert.ts                                 (+38 -2)
M  web/src/app/archive/alert/_components/AlertWorkspace.tsx (+225 -41)
M  web/src/app/archive/alert/alert-workspace.css            (+147)
A  web/tests/regression/alert-phase-b2.spec.ts              (NEW · 240 LOC)
D  web/tests/regression/alert-pilot-4gate.spec.ts           (DELETED · Phase A obsolete)
D  web/tests/regression/alert-empty-state.spec.ts           (DELETED · Phase A obsolete)
```

---

**End evidence**
