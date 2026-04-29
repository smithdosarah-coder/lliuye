# Worker A3 (FIX 第 2 批) · ComplianceWorkspace 删 force_mock hardcode · Onboarding

> Worker CLI 在 `D:/claude code/work-A3-prd` (branch `feat/prd-summaries-A3`) ·
> 复用。上批 W-FIX-A3 (`bb8ced2` Riskctrl/Alert fallback) 已 cherry-pick MERGED ·
> 本批 fix Codex 找的 bug #5。

## Goal

修 Codex 找的 P0 bug #5:

**根因**: `web/src/app/archive/compliance/_components/ComplianceWorkspace.tsx:113`
primary CTA 路径 hardcode `force_mock: true` · 但 demo banner 只在 tertiary 路径 (line 271) 渲染 ·
**用户点 primary "开始政策比对" 实际跑 mock policy corpus · UI 标 "live" · 静默欺骗**。

**正解**: 删 hardcode `force_mock: true` · primary 跑真 endpoint · 失败 → live-fallback
banner (per spec)。mock 仍只在 tertiary "示例" dropdown · 跟 spec align。

## Acceptance

- [ ] `ComplianceWorkspace.tsx:113` (primary CTA) 删 `force_mock: true` · body 加
      `force_mock: false`:
  ```ts
  fetch("/api/compliance/policy_scan", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      policy_doc: uploadedPolicyText,
      business_docs: uploadedBusinessDocs,
      policy_meta: { title: session.objective, fetched_at: session.updated },
      force_mock: false,
    }),
  });
  ```
- [ ] **live failed → banner** (per `docs/contracts/live-fallback-banner-spec.md` v1.0):
  primary path SSE error / 4xx / 5xx → 顶部 banner "⚠️ 后端 policy_scan 调用失败
  (<code>) · 当前显 fallback 演示 · [重试]"
- [ ] **mock dropdown 路径** (tertiary) 保留 · 触发显 banner "示例数据 (training)" (现已实装 · 验)
- [ ] tsc 0 error · 加 case to `web/tests/regression/compli-empty-state.spec.ts`:
  - mock fetch · primary CTA · 验 request body `force_mock:false`
  - mock fetch fail · 验 banner `data-testid="compli-live-fail-banner"` 显
  - mock dropdown tertiary · 验 banner `data-testid="compli-demo-banner"` 显
- [ ] features-inventory.md update F-054 (Compli) entry · 加 force_mock fix note
- [ ] commit trailer:
  ```
  Signal: WORKER-A3-FIX2-COMPLIANCE-FORCE-MOCK-DONE
  RECOVER-FROM: bb8ced2
  PRESERVES: F-001~F-062
  RESPECTS: docs/contracts/live-fallback-banner-spec.md
  NEW-DOM: data-testid="compli-live-fail-banner"
  ```

## Boundary

- 改: `web/src/app/archive/compliance/_components/ComplianceWorkspace.tsx` · 加 case to spec
- 不动: backend agent_compliance/api.py (现 endpoint OK · 接 force_mock=false 已支持) · 其他 Workspace · CLAUDE.md · RFC

## Estim

1-2 hr (单 file 改 · 加 banner state + 3 spec case)
