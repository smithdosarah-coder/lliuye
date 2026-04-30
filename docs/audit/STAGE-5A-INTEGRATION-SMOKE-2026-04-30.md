# Stage 5a Integration Cross-Agent Smoke · 2026-04-30 (PRELIM)

> Phase A 真 exit 验证之一 (per phase-a-charter §174)
> 主 CLI manual smoke (curl + ECS production https://liuye.me)
> Status: **PRELIM** — backend smoke + RBAC 全 PASS · 待 Codex periodic final audit + Playwright e2e

## 0. 元信息

- 触发: PM 2026-04-30 ultrathink "Plan A · Stage 5a + 三方辩论 v2 并行"
- 验证目标: ECS production https://liuye.me (Cloudflare tunnel · 实 ECS 139.196.30.69)
- 工具: curl + JWT cookie + JSON + SSE
- 跑方式: 主 CLI 直跑 (alidns 不 resolve liuye.me · 用 `--resolve liuye.me:443:104.21.24.104` 强制)

## 1. Backend Smoke 全 PASS

### 1.1 HTML pages (12/12 · 200 OK)

| view | URL | HTTP |
|---|---|---|
| login | /login | 200 |
| today | /today | 200 |
| archive (Agent tile) | /archive | 200 |
| archive/report | /archive/report | 200 |
| archive/credit | /archive/credit | 200 |
| archive/channel | /archive/channel | 200 |
| archive/alert | /archive/alert | 200 |
| archive/compliance | /archive/compliance | 200 |
| archive/riskctrl | /archive/riskctrl | 200 |
| dispatch | /dispatch | 200 |
| warroom | /warroom | 200 |
| auth/me | /api/auth/me | 200 |

### 1.2 RBAC 5 user accessibleAgents 全 PASS

| user | role | accessibleAgents (verbatim) | verdict |
|---|---|---|---|
| u_wangzhe | rm | `[channel, report, credit, alert, compliance, riskctrl]` | ✅ 6 全 |
| u_lihua | credit_officer | `[credit, report, alert]` | ✅ 准确 |
| u_zhoumin | compliance_officer | `[compliance, report, alert]` | ✅ 准确 + 含 compliance |
| u_chenkai | risk_manager | `[riskctrl, alert, credit]` | ✅ 准确 |
| u_liuye | admin | `[channel, report, credit, alert, compliance, riskctrl]` | ✅ 6 全 |

**关键**: `compliance` 字面在 RBAC accessibleAgents 内 — **Stage 4 compli→compliance 全栈替换 production live OK ✅** (验证 76a5c08 commit + ECS deploy bl25t16wa 真生效)

### 1.3 6 Backend API SSE 真流 (6/6 PASS)

| Agent | endpoint | scenario | SSE 启动 OK | sample event |
|---|---|---|---|---|
| Agent1 channel | POST /api/channel/run | mock | ✅ | `parse done · tags=[区域:上海, 行业:制造, 关键词:look-alike]` + `signal_scan running 5 路` |
| Agent3 credit | POST /api/credit/demo/run | corp_simple | ✅ | `profile_loaded · corp_dingsheng_001 鼎盛商贸 批发零售` |
| Agent4 alert | POST /api/alert/demo/run | baseline_100 | ✅ | `kb_load done · external_scan done` |
| Agent5 compliance | POST /api/compliance/demo/run | aml | ✅ | `rule_extract running · 解析 2 份政策原文 → 68 条规则` |
| Agent6 report | POST /api/report/demo/run | easy | ✅ | `ingest 0.2 · 4 份文件 1 份扫描件 OCR 置信度偏低 · v16 pipeline` |
| Agent2 riskctrl | POST /api/riskctrl/dsl_gen | mock | ✅ | `parse_intent done` |

### 1.4 Auth 流程

- POST /api/auth/login → JWT token + cookie + user info ✅
- GET /api/auth/me (with cookie) → user + roles + accessibleAgents ✅
- 所有 12 HTML page (with cookie) → 200 ✅

## 2. Phase A 8 硬线验证状态

| # | 硬线 | 状态 | 证据 |
|---|---|---|---|
| 1 | 5 contracts (worker-A1) | ✅ | docs/contracts/* + ratify commits |
| 2 | shared infra (worker-A2) | ✅ | shared/llm_caller/ + shared/sse_envelope.py |
| 3 | Channel pilot (worker-A3) | ✅ | Agent1 SSE 真流 (1.3) |
| 4 | 5 thin adapter (worker-A4) | ✅ | 5/5 V2 merged main + 6 backend SSE 真流 (1.3) |
| 5 | Letterpress purge (worker-A5) | ✅ | 24 baseline + Playwright purge spec PASS |
| 6 | handoff schema (worker-A6) | ✅ | docs/contracts/agent-handoff-schemas.md |
| 7 | PRD 取证 (worker-A7) | ✅ | docs/prd/master + 6 sub-PRD |
| 8 | lint enforcement | ⚠️ 90% | Stage 4 ratify 完 lint 跑通 · 但 strict mode 没开 (WARN-only) |

**7/8 ✅ + 1 ⚠️** — Phase A 验收硬线基本完成 · #8 lint strict mode 是治理优化非阻塞。

## 3. 待跑 (PRELIM 完成 → FINAL)

- ⏳ Codex periodic final audit (high reasoning · 真扫 docs/reset/phase-a-charter.md 8 硬线 + verify production · sequential 等 R1 v2 完后 fire) — ~30-60 min
- ⏳ Playwright e2e 全 spec (50+ spec · ~1-2h · 后台跑 · optional · 已有 baseline)
- ⏳ Stage 5b 4 周 weekly checkpoint (Phase A 真 exit 后 · 4 周 codex audit 无 BLOCKER)

## 4. PRELIM verdict

**Phase A 真 exit basically PASS** (backend + RBAC + production live + Stage 4 ratify 验证)。

Codex periodic final audit + Playwright e2e 完后转 FINAL · 通过 → Phase A complete · Phase B 启动。

## 5. 真问题 (smoke 中发现)

无 backend bug · 无 RBAC bug · 无 production down。

唯一注意点: alidns 不 resolve liuye.me (Cloudflare 国内 DNS 阻塞) — 这是 PM 端运维问题 · 不影响真实用户 (浏览器走系统 DNS · 国内用户用 8.8.8.8/114.114.114.114 都 OK)。

## 6. Sign-off

- 主 CLI Stage 5a smoke (本 doc · PRELIM)
- Codex periodic final audit (待 R1 v2 完 · sequential fire)
- Playwright e2e (optional)
- Stage 5b 4 周 checkpoint (Phase A exit 后)
