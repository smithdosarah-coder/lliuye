# Worker-A5 Onboarding · Letterpress 真清 (Phase A Week 2-3)

> Phase A Week 2-3 · 与 worker-A6 + worker-A7 并行 · 不依赖 A1/A2/A3
>
> 主 CLI dispatch commit signal: `PHASE-A-A5-DISPATCHED`

---

## 0. 复用 worktree (已建好 · 在新 branch)

- worktree 物理路径: `D:\claude code\work-A5-design` (主 CLI 已 `git worktree add` 创建)
- 已 checkout branch: `feat/phase-a5-design` (派生 chore/l0-infra HEAD 84334cb)
- **resume 第一步**: cd 到 worktree · 跑 `git status` 确认 clean · 直接开干
- 不需要 git fetch / git pull (本地已最新)

---

## 1. 任务 (verbatim from `docs/reset/phase-a-charter.md` §3 worker-A5)

| # | 交付 | 内容要点 |
|---|---|---|
| 1 | `web/src/app/globals.css` legacy 段全删 | `--color-brass` / `--color-ink-*` / `.letterpress-*` / `ink-brush-hr` 等 legacy 定义全删 (注意 globals.css:12-13 注释明言"旧 6 Agent 页继续消费" · 你要先迁完 12 consumer 才能删 · 顺序 = consumer 全迁完 → 删 legacy 段) |
| 2 | 12 consumer 迁 shell-v2 token | 改成 `--g0..--g7` / `--ink` / `--chalk` / `--accent` / `--t-{agent}` 功能色 |
| 3 | 4 themes 视觉一致 | canvas / matcha / dusk / ink 主题切换无穿帮 |
| 4 | Playwright visual regression smoke | 4 themes × 6 agent workspace tile 截屏对比 |

**Phase A 验收硬线 #5** (`docs/reset/phase-a-charter.md` §1): "Letterpress 真清 · 12 consumer 全迁 shell-v2 token · `grep --color-brass --color-ink` 0 命中"

---

## 2. 必读

- `RESET_MASTER_PLAN.md`
- `docs/reset/north-star.md` §2.4 设计层 + §3.4 修正方向
- `docs/reset/phase-a-charter.md` §3 worker-A5 段 + §1 硬线 #5
- `docs/audit/conflict-register-v1.md` (你 owner: cat 14 全部 5 entries + 部分 cat 8 6 处 color token)
- `docs/audit/sub-agent-step2-round1/production-shape.md` (Cat 14 verbatim · 你扫源)
- `docs/audit/sub-agent-step2-round1/naming-route.md` (Cat 8 6 处 accent legacy token · 跟 cat 14 重叠)
- `CLAUDE.md` §7 (前端 canon · `--t-*` 功能色 + 4 themes 详解)
- `web/src/app/globals.css` (法定 token 现状 · 含 legacy 段需删)
- `design_mockups/rm-assistant-final-2026-04-19.html` (视觉 1:1 复刻源 · 不偏离)

## 3. 12 consumer 已在 audit 列出 (你直接对照)

来自 `docs/audit/conflict-register-v1.md` Cat 14 + Cat 8:

- `web/src/lib/agents.ts:47/60/75/88/101/114` (6 个 agent accent token · 改 `--t-{report,channel,credit,alert,riskctrl,compli}`)
- `web/src/components/viz/VerdictBadge.tsx:12/27/45` (bg/text/glow · 3 处)
- `web/src/components/viz/PipelineRail.tsx:42-44` (`--color-ink/-ink-muted` · 3 处)
- `web/src/components/ui/Button.tsx:35` (focus ring `--color-brass`)
- `web/src/app/globals.css:12-13` (legacy 段注释 "旧 6 Agent 页继续消费" · 全迁完后删整段)

可能还有未列的 consumer · 自己 grep verify:
```bash
grep -rn "color-brass\|color-ink\|color-sage\|color-amber\|color-ember\|color-brass-dim\|letterpress\|ink-brush-hr" web/src --include="*.tsx" --include="*.ts" --include="*.css"
```

---

## 4. PM 拍板 (你必须遵守)

1. 杜绝拖死 4 机制
2. Phase A/B 严切阶段
3. active decision 必回写 root CLAUDE.md (你改 globals.css legacy 段 · 同 commit 回写 §7 token 列表)
4. 命名 SSOT 8 列 (worker-A1 干 · 你改 token 时遵 SSOT 中 `--t-{agent}` 命名)
5. legacy_gradio 全栈隔离 (worker-A7 干 · 跟你无关)

---

## 5. 协作纪律 (red lines)

- ❌ 不跨 worktree 改文件
- ❌ commit 不带 `Signal:` trailer
- ❌ **改 web/ 必带 trailer** `PRESERVES: F-XXX` + `NEW-DOM: data-testid="..."` + `SMOKE-PASS: <spec>.spec.ts` (per CLAUDE.md §13 + features-inventory.md)
- ❌ 视觉 1:1 复刻源是 `design_mockups/rm-assistant-final-2026-04-19.html` (sha256 25155e74...) · 不偏离 (CLAUDE.md §7)
- ❌ 直接 push origin

---

## 6. ACK 协议

- 每 consumer 完一个 commit 一次 · trailer `Signal: WORKER-A5-CONSUMER-<N>-MIGRATED`
- globals.css legacy 段删 · 单独 commit `Signal: WORKER-A5-LEGACY-CSS-PURGED`
- 全完 + Playwright smoke pass · 最后 commit `Signal: WORKER-A5-DESIGN-LETTERPRESS-DONE` · trailer:
  ```
  CONSUMERS-MIGRATED: 12 (列具体 file:line)
  GREP-LEGACY-COUNT: 0 (grep --color-brass / --color-ink 应 0 命中)
  THEMES-VERIFIED: canvas + matcha + dusk + ink (4 themes 截屏 attach)
  SMOKE-PASS: web/tests/regression/letterpress-purge.spec.ts
  HARDLINE-5-MET: yes
  PRESERVES: F-XXX (列 audit 没破坏的 features-inventory ID)
  ```
- 不在 chat 报"已完成"

---

## 7. Codex 协作

主 CLI 已 fire codex pre-dispatch draft (插入点 1) · 你不见。落 `docs/audit/codex-drafts/A5-design.md`。

DONE 后主 CLI fire codex post-DONE peer review (插入点 2)。

---

## 8. DONE 后主 CLI 后续

cherry-pick 到 chore/l0-infra · push origin · ECS sync (改 web/ · CLAUDE.md §13.1 全流程含 npm build · ~5-10 min)。

---

**Author**: 主 CLI · 2026-04-29
**Phase A Week 2-3 · 与 A6 + A7 并行**
