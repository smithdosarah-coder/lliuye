# Phase A 真 Exit Milestone · 2026-05-01

> Phase A 验收硬线 8/8 全通 · 4 BUG 全修 · Codex re-audit verify GO · Phase B 启动 ratify

## 0. 元信息

- **里程碑日期**: 2026-05-01
- **git tag**: `phase-a-exit-bugfix-2026-05-01`
- **触发**: PM 2026-04-30 ultrathink Plan A · "先修 BUG 保证完整结构 → 修完打里程碑 → 再走优化方案 (真三方辩论 ≥ 3 轮)"
- **可退回**: 后续做优化方案 (动视觉 · 含 Customer Ribbon / 全屏渐变折中 / 登录黑洞替换 / IM 降级 等) PM 不满意 · 一句命令 (§3) 退回到这个 BUG 修过的稳定版

## 1. Phase A 8 硬线 全通 verdict

| # | 硬线 | 状态 | Evidence (commit · file:line) |
|---|---|---|---|
| #1 | 5 contracts (worker-A1) | ✅ | docs/contracts/* (agent-naming-ssot.md v1.1 + llm-prompt-contract.md + sse-envelope.md + agent-handoff-schemas.md v1.1 + workspace-state-protocol.md) |
| #2 | shared infra (worker-A2) | ✅ | shared/llm_caller/ + shared/sse_envelope.py + tests/shared 83 passed |
| #3 | Channel pilot (worker-A3 + 主 CLI BUG-B fix) | ✅ | agent_channel/api.py SSE Q-041 4 字段 + web/src/lib/api/channel.ts (commit 02daaac · 314 行) |
| #4 | 5 thin adapter (worker-A4 5 子) | ✅ | A4-credit (1d876fd merged 31e7be6) + A4-alert (bedccf9 merged 1250081) + A4-compli (183486c merged 79474f0) + A4-riskctrl (cbcc49d merged 7e40f86) + A4-report (0908a69 merged 4daedbe) · Stage 5a smoke 6 SSE PASS |
| #5 | Letterpress purge (worker-A5 + 主 CLI BUG-A fix) | ✅ | grep web/src "Letterpress\|crimson\|--color-brass\|--color-ink\|ink-brush-hr" 0 命中 (commit 1531929 清 4 处注释) |
| #6 | handoff schema (worker-A6 + 主 CLI BUG-C fix) | ✅ | agent-handoff-schemas.md v1.1 (commit 503fdad · §6 加 6 条反向链 + Agent2 触发链) |
| #7 | PRD 取证 (worker-A7) | ✅ | docs/prd/master-2026-04-29.md + 6 sub-PRD · compliance verbatim ratify |
| #8 | lint enforcement (主 CLI BUG-D fix) | ✅ | .github/workflows/lint-contracts.yml (commit fb4cead · 66 行) + lint script local 0 error 0 warn |

**Cross-Agent Integration**:
- ✅ Agent6→Agent3 handoff (CreditWorkspace.tsx:237 runDecisionWithAgent6Handoff)
- ⏳ Agent4→Agent5 handoff (schema v1.1 §6.3 已定 · 实装 Phase B-3)
- ✅ RBAC 5 user accessibleAgents 准确 (Stage 5a smoke verify)

## 2. 4 BUG 修复对照表

| BUG | 之前 (Codex audit b680pl1mo NO-GO) | Commit | 工程量 | Verify |
|---|---|---|---|---|
| BUG-A #5 | ThemeSwitch.tsx:9 残留 Letterpress/crimson | 1531929 | ~10 min | grep 0 残留 |
| BUG-B #3 | 缺 web/src/lib/api/channel.ts | 02daaac | ~30 min | tsc PASS |
| BUG-C #6 | handoff schema 仅 4 主链 (排除 Agent2 + 反向) | 503fdad | ~30 min | grep section 编号 §0-§8 全 |
| BUG-D #8 | .github/workflows/lint-contracts.yml 缺失 | fb4cead | ~30 min | local lint 0 error 0 warn |

总耗时: ~1.5h (Codex audit 估 1.5-2h · 实际在预算内)

## 3. 退回命令 (后续优化方案不满意时用)

如果 Phase B 优化方案 (动视觉 · 含 Customer Ribbon / 全屏渐变折中 / 登录黑洞替换 / IM 降级 / 6 workspace 视觉清洗 / Action Card 合并 等) ship 后 PM 不满意 · 一句命令退回到本里程碑稳定版:

```bash
cd "D:/claude code/credit_report_agent_work"
git fetch --all --tags
git reset --hard phase-a-exit-bugfix-2026-05-01
git push origin main --force-with-lease  # ⚠️ 力 push 必先跟 PM 确认
bash scripts/deploy_to_ecs.sh             # ECS 同步本里程碑版本
```

⚠️ **`git push --force-with-lease` 是 destructive 操作** (per CLAUDE.md "carefully consider risks") · PM 必须明确同意才执行。

## 4. 后续 (Phase B 启动)

按 PM 4 条顺序进入 Step 3 (里程碑后真 fire 三方辩论):

1. ⏳ Fire 真三方辩论 R2 v2:
   - Codex bg (看主 CLI R1 v2 + Gemini R1 v2 · 出 dissent)
   - Gemini sub-agent (沿用 conversation · 看主 CLI R1 v2 + Codex R1 v2 · 出 dissent)
   - 主 CLI R2 v2 doc (看 Codex+Gemini R1 v2)
2. ⏳ R3 v2 主 CLI 综合 → 完整版方案 v4 doc
3. ⏳ PM 拍板 8-9 项 → 落 Phase B charter (worker-B1 数据飞轮 + worker-B2 商业化 + worker-B3 RM workbench v4 ~21 action)

预估: 真三方辩论 ~1h · v4 综合 ~30 min · 总 ~1.5h 给 PM 完整版方案 v4

## 5. Sign-off

- Codex periodic final audit (b680pl1mo · 2026-04-30): NO-GO · 4 BLOCKER
- 主 CLI 修 4 BUG (commits 1531929 + 02daaac + 503fdad + fb4cead · ~1.5h)
- Codex re-audit (btx2sr9gq · 2026-05-01): 4/4 BUG fix PASS · Phase A GO · Phase B 启动 ratify
- 主 CLI 落 Phase A Final Audit Re doc + 本 milestone doc + git tag
- PM 隐式 ratify (per "BUG 你和 CODEX 决定就行" + Codex re-audit GO)
- ECS deploy 含 build · production live 本里程碑版本

## 6. 谁可改本 doc

- 本 doc 标记 Phase A exit 历史里程碑 · **不允许后续修改** (audit trail 留底)
- 后续 Phase B 优化方案落 `docs/research/FINAL-FRONTEND-OPTIMIZATION-PLAN-V4-2026-05-01.md` (新 doc · 与本 milestone 共存)
- 真退回到本里程碑后 · 写新 milestone doc (e.g. `PHASE-B-ROLLBACK-MILESTONE-YYYY-MM-DD.md`) · 不改本 doc
