# Main CLI Round 1 · v1 · "下一步 1-3 周 plan" · Independent

> 作者: 主 CLI Claude Opus 4.7 (1M context) · 2026-05-04 · 独立 v1 · 不见 Codex v1 (anti-bias rule 1)
> Round 1 fire 时 Codex bg 在并行跑 · 双方 R1 完成后进 R2 互评

## 1. Scope 界定

"下一步 1-3 周" = 2026-05-04 (今天 · post-Q-047 reset session day 1) 起 · 至 ~2026-05-25 · Phase B Sprint 2 启动 + 第一/第二 worker 进展期。

含: Sprint 2 三 worker 派单 prep + worker DONE 序列处理 + Phase A 8 硬线现状梳理 + critical path 风险暴露 + Sprint 3 charter prep (BE7 提前调整)。

不含: 视觉路线 (Q-047 冻结 · PM 显式 unfreeze 才动) · Sprint 3 三 worker 实际派单 (~5/25 后) · Sprint 4 整合 · Sprint 5 demo。

## 2. TL;DR

1-3 周做 5 件 · 第一周内 4 件并行 + 后续 2 周 worker DONE 序列被动跟。**核心判断**: Sprint 2 三 worker 照原计划启 (charter v2 真主线 · Q-046 验证) · 但启之前必做 critical path 风险暴露 (Phase A 8 硬线现状 doc · 尤其 #6 handoff schema · 这是 demo 闭环前提) · 启之后用 codex post-DONE peer review 双闸 (插入点 2 · codex 已恢复)。

## 3. Concrete deliverable

| # | item | owner | 时间 | DoD (file:line / signal) |
|---|---|---|---|---|
| 1 | 三 onboarding trailer update | 主 CLI | 30 min · today | `docs/onboarding/B{4-alert,4-compliance,2-biz}.md` `REVIEW-MODE: manual` → `codex` (codex 已恢复) · commit signal `ONBOARDING-TRAILER-UPDATE-CODEX-RESUMED` |
| 2 | Phase A 8 硬线现状 doc | 主 CLI | 1-2 hr · today | `docs/audit/phase-a-status-2026-05-04.md` · 8 项逐条 yes/partial/no + evidence (file:line / commit sha) · 暴露 #5 Letterpress Q-047 后 / #6 handoff schema / #7 PRD master 真状态 |
| 3 | Phase B pre-Sprint-2 audit (Codex periodic 插入点 4 提前) | 主 CLI fire codex bg | 60 min wall · today | `docs/audit/codex-periodic/2026-05-04-phase-b-pre-sprint2.md` + commit signal `CODEX-PERIODIC-AUDIT-2026-05-04-DONE` · 4 questions 答 (Q1 Sprint 1 BE drift / Q2 Sprint 2 onboarding 清晰度 / Q3 Sprint 3 BE7 提前调整 / Q4 Phase A 8 硬线完成度) |
| 4 | cron 5 min 巡逻启 | 主 CLI ScheduleWakeup | 5 min · today | cron alive · git log -50 --since=10min · 扫 3 worker branch (`feat/phase-b4-alert` + `feat/phase-b4-compliance` + `feat/phase-b2-biz` · 4 旧 worker branch 已 release 不扫) |
| 5 | PM 双击 launch.bat 启 3 后端 worker | PM | 5 min · today (audit 后) | 3 cmd window 启 (B4-alert + B4-compliance + B2 · 不含 B3) |
| 6 | 等 B2 BE11 DONE | worker-B2 | ~1 week (~5/11) | `WORKER-B2-BIZ-DONE` signal commit |
| 7 | B2 post-DONE codex review (插入点 2) | 主 CLI fire codex bg | 60 min wall | `docs/audit/codex-reviews/WORKER-B2-BIZ-DONE.md` + commit signal `CODEX-REVIEW-WORKER-B2-BIZ-DONE-VERDICT` · trailer `CODEX-VERDICT: AGREE/DISAGREE/NEED-MORE-INFO` |
| 8 | B2 cherry-pick + push (codex AGREE 后) | 主 CLI | 15 min | main 含 B2 · ECS deploy 不需 (doc only) |
| 9 | Sprint 3 charter v2.2 prep | 主 CLI | 2-3 hr · 5/14 起 | `docs/reset/phase-b-charter.md` v2.2 段 (BE7 提前 + worker-B7 减半 1-1.5w → 0.75-1w + 减半时间分配建议) · PM verify |
| 10 | 等 B4-compliance DONE | worker | ~2-2.5 weeks (~5/18-5/21) | `WORKER-B4-COMPLIANCE-POLICY-REGISTRY-DONE` |
| 11 | B4-compliance review + ECS deploy --skip-build | 主 CLI | ~1 hr | codex review verdict + cherry-pick + ECS pull + restart compliance service |
| 12 | 等 B4-alert DONE (~3w · 5/25 周) | worker | week 3 末 | `WORKER-B4-ALERT-SIGNAL-QUALITY-DONE` |
| 13 | B4-alert review + ECS deploy --skip-build | 主 CLI | ~1 hr | 同 #11 |
| 14 | Sprint 3 派单 prep (3 onboarding 写) | 主 CLI | week 3 末 (5/22-5/25) | `docs/onboarding/B4-{channel,riskctrl}.md` + `B7-final.md` 草稿 · 等 PM verify |

## 4. 风险

| # | 风险 | 触发条件 | 缓解 | 缓解 owner |
|---|---|---|---|---|
| 1 | worker 派偏 charter (Q-046 5 跑偏) | onboarding 模糊 / worker 自跳 sprint | 三 onboarding 已严格写 + #3 audit Q2 加固 + 启后 codex post-DONE review 双闸 | 主 CLI |
| 2 | Phase A 8 硬线 #6 handoff schema partial → Sprint 2/3 stuck | #2 现状 doc 暴露后才知 | #2 现状 doc today 必出 · 若 partial 则 Sprint 3 减半的 1-1.5 周补 · 不留到 Sprint 4 | 主 CLI |
| 3 | Codex 第二次用尽 (token / quota) | 频繁 fire bg / 高 reasoning | medium reasoning default · sequential 1 bg at a time · 90 min monitor fallback manual (Q-043 v2) | 主 CLI |
| 4 | ECS 部署失败 (build / restart / healthcheck) | code 改 break / config 漂 | `scripts/deploy_to_ecs.sh` 含 healthcheck · 失败 abort · `--skip-build` for backend-only | 主 CLI |
| 5 | 数据飞轮 BE10 + decision ledger BE7 没 monitoring → silent regression | Sprint 2 worker 改后端无 baseline 比对 | #3 audit 包含 evaluation runner baseline check · Sprint 2 worker onboarding 已要求跑 baseline (B4-alert `signal_diversity ≥ 0.85`) | 主 CLI + worker |

## 5. DoD (整体 3 周后)

3 周后 PM 看到:
- Sprint 2 三 worker (B4-alert + B4-compliance + B2) 全 DONE · cherry-pick 进 main · ECS 部署 (--skip-build for backend / B2 不需)
- Phase A 8 硬线现状 doc + Codex periodic audit doc 留底 (`docs/audit/`)
- Sprint 3 charter v2.2 (含 BE7 提前调整 + worker-B7 减半时间分配 + 三 worker onboarding 草稿)
- decisions-log Q-048..Q-051 (本期决策追加)
- state-snapshot Day 3..Day 21 完整段 (CLAUDE.md §14.1 硬规守住)
- cron scoreboard 显 "Sprint 2 done · Sprint 3 ready"
- 5 跑偏 root cause 硬规 0 violation (任何派单前 grep charter / PM idle 先读 charter / Sprint 边界 mental switch / P0 写死优先级 / PM 高频提醒 STOP 5s)

## 6. 不做的事 (反 Q-046 5 跑偏)

- ❌ 不派 Sprint 3 worker (charter 真主线说 Sprint 3 是 ~5/25 后启 · 不提前)
- ❌ 不接 BE7 提前的 worker-B7 (Sprint 3 worker · 不主动加 worker)
- ❌ 不动视觉 (Q-047 PM ratify 冻结 · 任何视觉变更 PM 显式 unfreeze 才启)
- ❌ 不 codex 并发 (Q-043 v2 sequential 1 bg at a time · 哪怕 R1 R2 也是各自一次)
- ❌ 不省 onboarding update (codex 恢复后 trailer 改 codex · 0 cost · 防 worker 误以为 manual review)
- ❌ 不省 audit / 现状 doc (Q-046 5 跑偏硬规 · 启动前必 verify · 不允许"看着像 OK"就启)
- ❌ 不在 PM 高频提醒时立即响应 (STOP 5s · 想 charter 真主线 vs 印象)
- ❌ 不对 B3 视觉撤回的 worker 做 post-DONE review (Q-047 后 B3 release · 视觉成果已撤 · review 无意义)

## 7. 替代方案 evaluated rejected

- A. **不 audit · 直接派 Sprint 2** — 拒. Q-046 5 跑偏硬规 #1 要求 charter verify · audit 是显式 verify · 省 60 min audit 换 3 周 worker 派偏风险不值得
- B. **Phase A 8 硬线全补完再启 Sprint 2** — 拒. Phase A 已 declared exit (commit fb4cead + Codex re-audit GO) · 补 Phase A 走 Sprint 3 worker-B7 减半的 1-1.5 周更合理 · 不阻 Sprint 2 启动
- C. **完全 reset Phase B charter v2** — 拒. v2 已 PM ratify (Q-045) + Q-046 接受 Sprint 2 真主线既成事实 · 不再翻 · 避免决策 thrashing
- D. **Sprint 2 + Sprint 3 合并启 (6 worker 同时跑)** — 拒. 反 Q-046 跑偏硬规 #3 (Sprint 边界 mental switch) · 6 worker 主 CLI cron 巡逻 + post-DONE review 容量超载 · cost / 风险 / collision 都不划算
- E. **post-DONE review 4 worker (B1+B4-credit+B4-report+B3) 各 fire 1 次 codex** — 拒. 4 次 fire bg cost 高 · 集成进 1 次 periodic audit (item #3 Q1) 更高 ROI · B3 视觉撤了不需 review

## 8. Critical path 反推 (Sprint 5 demo 4 维 → 现在 1-3 周)

Phase B 验收硬线 #5 (charter line 28): "RM 工作台 1 客户全流程跑通 + 1 个完整 video 录 + 个人画像 POC 跑通 4 维度评价 + 银行客户演示 ready"

Critical path:
1. **RM 工作台 1 客户全流程** = 6 Agent handoff 真串 (Agent6→Agent3→Agent4→Agent5) · **依赖 Phase A 8 硬线 #6 handoff schema** (worker-A6) — 这是 1-3 周必暴露的关键风险
2. **个人画像 POC** = BE12 (Agent1 personal_insight 子域) + BE13 (B7 final POC) · **Sprint 3 才做 · 1-3 周不在 critical path**
3. **video 录 + 银行客户演示** = Sprint 5 主 CLI 自己 + PM · **5 周后 · 不在 1-3 周 critical path**

1-3 周 critical path verdict:
- Sprint 2 B4-alert BE5+BE9 = Agent4 信号质量 + batch — **YES** (RM 工作台需要 Agent4)
- Sprint 2 B4-compliance BE4 = Agent5 policy registry — **YES** (RM 工作台需要 Agent5)
- Sprint 2 B2 BE11 商业化 doc only — **NO 直接 critical path** · 但 Phase B 验收硬线 #2 要求 (`pricing/multi-tenant/trial-flow`-assumptions doc + tenant_id 数据模型 spec)
- **Phase A 8 硬线 #6 handoff schema 真状态** — **真 critical path · 必须 today 暴露**

结论: 1-3 周 plan 在 critical path 上的 ~70% (Sprint 2 三 worker 中 2 个 + #2 现状 doc 暴露 #6 handoff schema 状态) · ~30% 是 enabler 工作 (商业化 doc / audit / cron / onboarding update) · 这个比例合理。

## 9. Dissent appendix

预期 Codex R1 v1 可能推荐 + 我不同意:

1. **Codex 可能推荐 Sprint 2 启动前先做 6 Agent handoff schema (worker-A6 补)** — 我**部分反对**: 启动前应该 *暴露* (item #2 现状 doc) 但 *不补* · 补留 Sprint 3 减半时间。理由: handoff schema 不阻 Sprint 2 三 worker (alert / compliance / biz doc 三个不依赖 handoff schema 完整)。但若 audit verdict 显示 schema 完全空白 (而非 partial) · 可能改主意。
2. **Codex 可能推荐 4 worker (B1+B4-credit+B4-report+B3) 各 fire post-DONE review** — 我反对: cost 4x · 集成 1 次 periodic audit 更高 ROI (item #3)
3. **Codex 可能推荐 monitoring/observability gate 加 Sprint 2** — 我**赞同必要性 · 反对 timing**: 留 Sprint 4 整合时做更合理 · Sprint 2 worker onboarding 已要求 evaluation baseline 跑 (够 first-line)
4. **Codex 可能推荐 Sprint 2 + Sprint 3 合并启 (BE7 提前后腾出 worker capacity)** — 我反对: 反 Q-046 跑偏硬规 #3 · cron + review capacity 超载 · 不值
5. **Codex 可能推荐 R3 codex 仲裁 (插入点 3) 替代 PM 拍** — 我反对: PM 才是 final 拍板 · codex 只产 audit doc 不仲裁产品决策 (codex-mesh-protocol §7 红线)
6. **Codex 可能推荐三 onboarding trailer 不只是 codex 改 manual · 还要加更多 contract reference** — 我可能赞同 · 看 Codex 给的具体 file:line + 哪个 contract

End Round 1 v1.
