# Reset 工程 Phase A 综合汇报 · 2026-04-30

> 主 CLI Round 4 真最终版本 (主 CLI Round 1 v1 + Codex Round 1 v1 + Codex Round 2 review 主 CLI 融合 · 双向互检后)
>
> Round 2 verdict: DISAGREE · 主 CLI ack 6 加补

---

## TL;DR (verdict 先)

- **大阶段任务**: 让 6 Agent POC 走歪的产品形态**轻装上阵** · 才能进 Phase B 商业化 (per RESET_MASTER_PLAN verbatim)
- **当前**: Phase A technical hardlines 6/8 ✅ + 1 ⏳ (#4 真动中) + 1 ⚠️ (#8 90%)
- **真"轻装"intent: ~55%** (含 A4 5 子真完 + compliance 全栈替换 + V3/V4 minor + integration smoke + neat-freak)
- **ETA 双轨**:
  - **Technical hardlines**: Apr30 夜 / May1 EOD
  - **Phase A charter exit (含 4 周 checkpoint + audit · per §174)**: 5 月底 / 6 月初
  - **Reset 工程完毕 (Phase A 8 + Phase B 3 = 11)**: 5-7 周

---

## 1. 大阶段任务 + 目的

**Reset 工程** (启 2026-04-29 · PM 决议) · 本质是**轻装上阵**:

- 不是修 8 硬线 bug
- 是**清掉所有走歪 / 漂移 / 技术债** · 让团队后续 4-6 周进 Phase B 时不背包袱

**5 大走歪表征** (per north-star §2):
1. 6 单页 showroom · 没 RM workbench (Cursor 模式)
2. `shared/llm/` 0 用 + 4+1 套并行 caller
3. 6 workspace 0 个真 4 gate state model
4. `compliance` vs `compli` 全栈分裂
5. Letterpress 残留 + `/design` canon 未建 + 角色文案漂

**3 Step 框架** (per RESET_MASTER_PLAN §2):
- Step 2 conflict scan ✅ 完 (87 entries register · PM 拍板 4 件)
- **Step 1 Phase A cleanup ⏳ ~85% 技术 / ~55% 轻装 (当前)**
- Step 3 Phase B PRD + 商业化 ⏳ 部分启 (worker A7 PRD draft 完)

---

## 2. 当前进度 (Apr30 verify · main HEAD `edaf2e0`)

### Phase A 8 硬线 results (技术)

| # | 状态 | 证据 |
|---|---|---|
| 1 | ✅ contracts (A1) | merged main + ECS · `3752d98` + `1d04b94` · A1 V2 codex AGREE |
| 2 | ✅ shared infra (A2) | merged main + ECS · `2bfc5ad` + `8223cad` · A2 V2 codex AGREE |
| 3 | ✅ Channel pilot (A3 V3) | merged main + ECS · `8cc0b66` · A3 V3 codex AGREE |
| 4 | ⏳ 5 thin adapter | A4-report ✅ ADAPTER-DONE (codex V1 DISAGREE · V2 fix 中) · A4-alert ✅ ADAPTER-DONE (codex review 中) · A4-credit/compli/riskctrl 接近 final step signal |
| 5 | ✅ Letterpress (A5 V3) | merged main + ECS · `e0eaa70` |
| 6 | ✅ handoff schema (A6 V2) | merged main + ECS · `5cfb718` |
| 7 | ✅ PRD (A7 V3) | merged main + ECS · `36a713a` |
| 8 | ⚠️ SSOT 90% | A1 SSOT compliance 写定 · 但全栈替换 stale (3 处 · per Codex Round 2 加补) |

### 真"轻装上阵" intent: ~55%

剩余包袱 (Codex Round 2 加补):
- A4 5 子真完 (1/5 final ADAPTER-DONE met · 4/5 接近 · A4-report V2 fix 中)
- **compliance 全栈替换** (blocker · 不 optional · per Codex Round 2 加补):
  - `web/src/components/shell/AuthGate.tsx:21` regex 仍认 `/archive/.../compli`
  - `web/src/lib/auth/agent-id.ts:16` patch 映射 `compliance→compli` 仍存
  - `docs/contracts/agent-naming-ssot.md:54` 写"PM 拍板后删 patch" 但仍存
- V3/V4 minor cleanup (A3 ConversationPanel · A5 globals.css 注释 · A1 contracts minor)
- integration cross-agent smoke (硬线 #4 第二轮)
- neat-freak doc/memory drift

---

## 3. 下一阶段方案 (5 Stage · Codex Round 2 加补后修正)

### Stage 1 · A4 Freeze + Final Signals (ETA 2-4h)
- A4 4 worker (credit/alert/compli/riskctrl) 清 dirty · 发 `WORKER-A4-{X}-ADAPTER-DONE` (final · 不 step)
- A4-report V2 fix 6 issue (worker 收到 PM paste · 跑中)
- 风险: dirty WIP 丢 = 拖 4-8h

### Stage 2 · Codex Post-DONE Review × 5 (ETA 2-3h)
- 5 份 codex audit doc (含 A4-report V2)
- 只接 AGREE OR 一轮 V2 fix
- **严守**: A4 final ADAPTER-DONE ≠ 免 codex review · 必跑

### Stage 3 · Cherry-pick + Main + ECS Full Deploy (ETA 2-4h)
- 5 merge commit (feat/phase-a4-{X}-adapter × 5 → chore/l0-infra)
- main merge + push origin
- ECS full deploy (含 npm build · 5-10 min · 改 web/* 多 file)
- **严守**: conflict 必 commit `conflict-resolution-note` (前 3 次 `--theirs/--ours` 破例 · per Codex audit 加补)

### Stage 4 · Lightweight Cleanup Gate (ETA 3-5h · **blocker · 不 optional**)
- compliance 全栈锁 (5 file consumer 替换):
  - `web/src/lib/store/types.ts` AgentId 改
  - `web/src/lib/store/auth-store.ts` ACCESS map
  - `web/src/lib/auth/agent-id.ts` patch 删
  - `web/src/components/shell/AuthGate.tsx` regex 改 `/archive/compliance`
  - `auth_service/rbac.py:42` VALID_AGENTS 改
  - `docs/contracts/agent-naming-ssot.md:54` PM-TBD 删
- A3/A5/A1 V3/V4 minor cleanup
- doc/memory drift 整理 (含 11:00 state-snapshot Day 2 段)

### Stage 5 (拆 5a + 5b · per Codex Round 2 加补)

**Stage 5a · Technical Exit Audit (ETA 2-3h · Apr30/May1 可完)**:
- integration cross-agent smoke (Playwright 跨 6 agent workspace 联动测试)
- Codex periodic final audit (verify 全 8 硬线 + 17 类 conflict scan 无新 drift)
- commit `PHASE-A-TECHNICAL-COMPLETE` state-snapshot

**Stage 5b · Charter Exit Wait Condition (ETA 4 周 · 5 月底 / 6 月初)**:
- PM 周一 checkpoint 至少 4 周连续无 BLOCKER (per phase-a-charter §174)
- Codex periodic audit 通过 (重跑 17 类 audit · 验证无新 drift)
- commit `PHASE-A-CHARTER-EXIT` state-snapshot
- 进 Phase B (worker-B1 数据飞轮 + worker-B2 商业化)

---

## 4. 对外口径 (PM 参考 · Codex Round 2 严守)

❌ **不能说**: "Phase A Apr30/May1 完毕"
✅ **改说**:
- **"Phase A technical hardlines (8 项) Apr30/May1 完"**
- **"Phase A charter exit (含 4 周 weekly checkpoint + Codex periodic audit) 5 月底 / 6 月初"** (per phase-a-charter §174)
- **"Reset 工程完毕 (11 项 = Phase A 8 + Phase B 3) 5-7 周"** (per phase-b-charter §44-46)

---

## 5. Phase A → Phase B 衔接

- **B1 数据飞轮 thin MVP** (per phase-b-charter §19-29): Phase A 后期可准备 · 不抢 critical path · 交付 `/api/feedback` + baseline + few-shot 注入 + runbook
- **B2 商业化 doc** (per phase-b-charter §31-40): 可并行轻量启 · 交付 `docs/biz/{pricing, multi-tenant, trial-flow, sales-playbook}-assumptions.md`
- **Phase B exit** = 3 B 硬线 + Phase A 8 硬线 = **11 项全过** = reset 完毕

---

## 6. 主 CLI 失误 audit (诚实 · 15 件)

### Self-audit 9 件 (主 CLI 自列)
1. 9 worker 一次 dispatch 过激进 (PM 批"开都开了")
2. GitHub PAT scope 漏 anticipate (A1 V2 workflow file 触发 push 拒)
3. 第一次 ECS push fail 没 verify (silent failure · ECS 跑老代码)
4. blocker debug 凭印象 (没 git verify 就发 paste 错指令)
5. launcher 后没 verify cmd 全 active (A4-report 一直 0 commit PM 才注意)
6. mesh-prompt 含 cmd 特殊字符 (A4-credit cmd 启 fail)
7. A7 重复 Block A.0 (active rule 我已 fix-forward 但 onboarding 没移除)
8. decisions-log Q-NNN 漏 Day 1 (Q-042 第二天才补登)
9. conflict resolve `--theirs` 简单粗暴 (Q-042 audit 段被覆盖)

### Codex Round 1 加补 4 件 (codex periodic audit)
10. state-snapshot 断档 (§14.1 严守失败 · 已补 `74bb28d`)
11. A4 final signal 不一致 (step ≠ ADAPTER-DONE · onboarding §5 verbatim)
12. A4-report verify 错 (cron git log limit · 实际已 final · 错 surface "静默")
13. conflict resolve 无审计保真 (没 commit `conflict-resolution-note`)

### PM 提示 framing 偏差 ack 1 件
14. **~85% framing 偏差** (results vs intent · 真"轻装" ~55% 不是 ~85%)

### Codex Round 2 review 我融合加补 1 件
15. **Round 2 单向 anti-bias 违规** (我 read codex Round 1 但 codex 没 review 我融合 · PM 指出 · Codex Round 2 真双向后改)

### Codex Round 2 critical 加补 6 件 (融合 framing 修正)
- Phase A exit ≠ Apr30/May1 (charter §174 4 周 checkpoint + periodic audit)
- 11 项是 **reset 完毕** 不是 Phase A exit (主 CLI 概念混淆)
- A4 4/5 不是"接近 final"是"等 final signal"
- A4-report 仍需 codex review (final 不免 review)
- hardline #4 含 Playwright smoke (codex review 必核 smoke 证据)
- compliance lock 后 stale 3 处 (AuthGate.tsx + agent-id.ts + agent-naming-ssot.md)

---

## 7. 立即行动 (next 30 min)

- A4 4 worker (credit/alert/compli/riskctrl) chat 收到 PM paste final ADAPTER-DONE 提醒
- A4-alert codex review 跑中 (`byc8bwak0` · ~3 min)
- A4-report V2 fix worker 跑中 (PM 已 paste 6 issue fix)
- A4-credit/compli/riskctrl 等 final ADAPTER-DONE
- 收齐 5 final + 5 codex AGREE → cherry-pick × 5 → push → ECS full deploy → Stage 4 cleanup compliance 全栈

---

## 附录 · 评分 + 信心

**Codex Round 2 评分主 CLI 融合**:
- progress 汇报准度: 7/10
- 5 stage 合理度: 8/10
- ETA 双轨现实度: 3/10 (主 CLI 偏乐观 · Codex 改为 conservative)
- compliance blocker 判定准度: 8/10
- Phase A exit 11 项严守准度: 4/10 (主 CLI 概念混淆 · 已修正)

**Codex Round 1 periodic audit verdict**: PARTIAL · 信心 42/100

**Round 4 真最终版本依据**:
- `docs/audit/codex-periodic/MAIN-CLI-DAY-1-2-AUDIT.md` (Codex Day 1+2 audit)
- `docs/audit/codex-periodic/ROUND-1-PHASE-A-STATUS.md` (Codex Round 1 v1)
- `docs/audit/codex-periodic/ROUND-2-REVIEW-MAIN-CLI-FUSION.md` (Codex Round 2 review 我融合)
- `docs/handoff/decisions-log.md` Q-042 + Q-042.B (PM 4 拍板 + compliance ratify)
- `docs/audit/conflict-register-v1.md` (87 entries · PM 拍板 4)
- `docs/reset/state-snapshot.md` (Day 1+2 段 · 11:00 sync)
