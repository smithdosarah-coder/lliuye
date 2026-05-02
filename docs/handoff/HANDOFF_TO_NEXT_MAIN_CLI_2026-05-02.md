# HANDOFF · TO NEXT MAIN CLI · 2026-05-02 (v3 · Q-047 视觉冻结后)

> PM 重启电脑 · 当前主 CLI session 不 resume · 新主 CLI 读本 doc + §14 5 必读 + decisions-log Q-046/Q-047 + 写 `NEW-MAIN-CLI-RESUMED` commit。

## 0. ⚠️ MAJOR UPDATE 2026-05-02 (v3 · 必读)

**Q-047 视觉方案全面冻结** (PM verbatim "视觉方案全面暂停 · 只提升产品本身能力"):
- F4 v2 黑洞 + F1-F17 所有视觉成果 → **全部 git checkout 回退到 phase-b-start-2026-05-01** (commit 413a9ab · 18 file -572 +98 + 8 PNG 删 + F12 spec doc 删)
- production https://liuye.me/login 现在是 **Phase A exit 视觉 (Cosmic 黑洞 R3F 第一版 + shell-v2 base · PM 接受 verbatim "看了 · 是原来的方案")**
- worker-B3 **release · cmd window 关** (视觉路线待 PM 后期重新规划 · 不再启)
- launch-all-LIUYE.bat 改 **5 → 4 cmd window** (MAIN-CLI + B4-alert + B4-compliance + B2 · 不含 B3)
- decisions-log Q-047 ratify (commit f3dc86c)

## 1. 实时状态快照 (2026-05-02 PDT · post-Q-047)

### Production (https://liuye.me/login)
- 视觉: **Phase A exit 状态** (Cosmic 黑洞 R3F 第一版 + 4 主题渐变 + 6 Agent tile · 没 F1-F17 任何改动)
- 后端: BE2 + BE3 + BE7 + BE10 全 ship (Agent3 decision graph + Agent6 material gap + cross-agent ledger + 数据飞轮 thin gate enrich)
- F4 v2 黑洞 (oseiskar/MIT · 3 iter · PM 嫌"色温纯白") + F1-F17 视觉改动: **已全部 revert · 不再存在**

### 4 worker 状态 (post-Q-047)
- ❌ worker-B1-flywheel — Sprint 1 BE10 + 误派 Sprint 2 enrich 都 ship · **release · cmd 关**
- ❌ worker-B4-credit — Sprint 1 BE2 + 误派 Sprint 2 BE7 都 ship · **release · cmd 关** (BE7 提前完成 · Sprint 3 worker-B7 工作量减半)
- ❌ worker-B4-report — Sprint 1 BE3 ship · **release · cmd 关** (Sprint 4 整合时再启)
- ❌ worker-B3 — Sprint 1 F1-F6 + F4 v2 + Sprint 2 B-3 phase 4 件全 ship · **但视觉成果全被 Q-047 visual reset 撤** · **release · cmd 关** (视觉路线待 PM 后期重新规划)

### Sprint 2 真主线 3 新 worker (待 PM 双击 launch-all-LIUYE.bat 启)
- 🆕 worker-B4-alert (BE5+BE9 · 3 周) — worktree `D:\claude code\work-B4-alert` · branch `feat/phase-b4-alert`
- 🆕 worker-B4-compliance (BE4 · 2-2.5 周) — worktree `D:\claude code\work-B4-compliance` · branch `feat/phase-b4-compliance`
- 🆕 worker-B2 (BE11 商业化 doc only · 1 周) — worktree `D:\claude code\work-B2-biz` · branch `feat/phase-b2-biz`
- launcher: `C:\Users\Mr.S\Desktop\launch-all-LIUYE.bat` (4 cmd window: MAIN-CLI + 3 后端 worker)

## 2. 关键 decisions/承诺 (新主 CLI 必守 · 不重蹈)

### 2.1 5 跑偏 root cause 硬规 (前主 CLI commit 412f516 写入 · 写入下次 reset session 必读)

| # | 触发 | 动作 |
|---|---|---|
| 1 | 任何派单前 | `grep "Sprint N" docs/reset/phase-b-charter.md` verify 真排期 |
| 2 | PM 提"worker idle / 挂机" | 先 read charter · 再回 "Sprint X 真主线说应启新 worker Y · 不是给现有 worker 加任务" |
| 3 | Sprint 边界 | mental switch "新 sprint team composition 是哪 N 个" — Sprint 不是 task 续是 team 换 |
| 4 | P0 任务 (e.g. F4 v2 阻 production demo) | commit body 写死优先级 + 阻 worker 进下个 sprint · 不仅给 GO signal |
| 5 | PM 高频提醒 | STOP 5s · 想 "这是 charter 真主线还是凭印象?" · 不立即响应 |

### 2.2 4 视觉硬约束 (前主 CLI 承诺 · F4 v1 翻车后立)

| # | 规则 |
|---|---|
| 1 | 任何视觉决策前必先建参考库 (3+ 顶级截图存 design_mockups/login-v2-references/) |
| 2 | ECS deploy 后**主 CLI 必先亲眼上 https://liuye.me/login** 看效果 |
| 3 | 不满意立即 fix · 直到主 CLI 自己满意才让 PM 看 |
| 4 | Codex/Gemini 审美都不靠谱 · PM 是 final 判官 · 主 CLI 先把不通过的过滤掉 |

### 2.3 Codex 用尽 until 2026-05-08 (Q-043 protocol v2 fallback)

- codex `You've hit your usage limit. Try again at May 8th, 2026 12:47 AM`
- 全 manual review by 主 CLI · trailer `REVIEW-MODE: manual`
- 5 月 8 日 Codex 恢复后建议立即 fire Phase B periodic audit (插入点 4 提前用)

## 3. cron 5 min 巡逻 SOP (新主 CLI 第 1 件事 · 接 PM 双击 launch.bat 后)

PM 重启后启新 cron · prompt verbatim:
```
5m 跑 `git -C "D:/claude code/credit_report_agent_work" log --all --oneline -50 --since="10 minutes ago"` 扫 5 个 worker branch (feat/phase-b3-rm-workbench, feat/phase-b4-alert, feat/phase-b4-compliance, feat/phase-b2-biz, feat/phase-b1-flywheel/feat/phase-b4-credit/feat/phase-b4-report 已 release 不扫) 上有没有新 signal commit。
... (按之前 cron prompt 完整复制 · 加 5 worker branch 名 + sequential codex fallback to manual)
```

## 4. F4 v2 verdict ⚠️ OBSOLETE (Q-047 后 reset 撤了)

~~PM 上 https://liuye.me/login 给 verdict A/B/C~~

**Q-047 后实际**: F4 v2 黑洞已被 visual reset 撤 (commit 413a9ab) · production 是 Phase A exit 视觉 (Cosmic R3F 第一版) · PM 接受 verbatim "看了 · 是原来的方案"

视觉路线全部冻结直到 PM 后期重新规划。新主 CLI **不要再问 F4 v2 verdict** · 不要再做任何视觉改动。

## 5. Phase B 整体进度 (post-Q-047)

| Sprint | 真主线 | 完成度 (post visual reset) |
|---|---|---|
| Sprint 1 (Week 1-3) | 4 worker · BE10/BE2/BE3/v4 B-1 | **后端 100% · v4 前端 0%** (visual reset 撤了) |
| Sprint 2 (Week 3-6) | 后端 only 3 worker · BE5+BE9/BE4/BE11 (v4 B-3 视觉冻结) | **0%** (3 新 worker 待 PM 双击 launch.bat 启) |
| Sprint 3 (Week 6-10) | 3 worker · BE1+BE12/BE6+BE8/BE7+BE13 | **15%** (BE7 已提前 ship) |
| Sprint 4 (Week 10-14) | 整合 + Codex final audit | 0% |
| Sprint 5 (Week 14-18) | demo + POC 4 维评价 | 0% |

**总体**: 后端 ~25-30% · 前端 ~0% (Q-047 reset 全撤 · 视觉路线待 PM 重新规划)
**真预计**: 后端 ~10-14 周完整 ship · 视觉额外 (depends on PM 重新规划方案)

## 6. 新主 CLI 起手第 1 件事 (verbatim 模板)

```bash
cd "D:/claude code/credit_report_agent_work"
# 读 §14 5 必读: RESET_MASTER_PLAN.md / docs/reset/north-star.md / phase-a-charter.md / step2-conflict-scan-charter.md / codex-mesh-protocol.md
# 读本 HANDOFF: docs/handoff/HANDOFF_TO_NEXT_MAIN_CLI_2026-05-02.md
# 读 decisions-log 末 50 行 + state-snapshot.md

git log --oneline -30 --all
py scripts/orchestrator/scoreboard.py

git commit --allow-empty -m "chore(resume): NEW-MAIN-CLI-RESUMED · 2026-05-02 (post-Q-047)

产品 north star: 6 Agent 矩阵后端能力 (视觉冻结 · Q-047 PM 2026-05-02 ratify)
6 Agent 后端闭环路径: Agent6 报告 → Agent3 授信 → Agent5 合规 → Agent4 预警 · Agent1 获客 + Agent2 风控 平行
走歪表征 (top 5 · 必守 Q-046):
  1. 凭印象决策 (视觉 + 架构 + 派单)
  2. idle 焦虑驱动派单 (charter 真主线被忽略)
  3. Sprint 转换无 mental switch (沿用现有 team)
  4. P0 任务无写死优先级 (worker 自己跳)
  5. PM 高频提醒诱反应 > 思考

视觉冻结硬规 (Q-047):
  - 视觉方案全面暂停 · 只提升后端能力
  - worker-B3 已 release · 不再启
  - 任何视觉变更必先问 PM (PM 重新规划后才启)
  - launch-all-LIUYE.bat 4 cmd (MAIN-CLI + 3 后端 worker · 不含 B3)

当前 Phase: Phase B · Day 2 · Sprint 2 后端 only 真主线启动中
待启 worker: B4-alert (BE5+BE9 3 周) + B4-compliance (BE4 2-2.5 周) + B2 (BE11 1 周) · 视觉无关
PM 已拍板:
  - Q-046 Sprint 2 真主线 + 5 跑偏硬规
  - Q-047 视觉冻结 · 后端 only
  - 4 worker 全 release (B1 + B4-credit + B4-report + B3)
  - production = Phase A exit 视觉 (PM 接受 "原来的方案")

我下一步动作:
  1. 等 PM 双击 launch-all-LIUYE.bat 启 3 后端 worker
  2. 启 cron 5 min 巡逻 (扫 3 worker branch · B3 已 release 不扫)
  3. 后续 worker DONE → manual review (codex 用尽 until 5/8 fallback) → cherry-pick → ECS deploy --skip-build

Signal: NEW-MAIN-CLI-RESUMED"
git push origin main
```

## 7. 重要文件路径 (新主 CLI 必知)

- 主 worktree: `D:/claude code/credit_report_agent_work`
- 5 worker worktree: `D:/claude code/work-B3-rm-workbench` + `work-B4-alert` + `work-B4-compliance` + `work-B2-biz` + `work-B1-flywheel/work-B4-credit/work-B4-report` (后 3 个已 release)
- launcher: `C:/Users/Mr.S/Desktop/launch-B-sprint2-NEW.bat`
- design references: `design_mockups/login-v2-references/awwwards-workshop-fullpage.png` + `F4-V2-LIVE-2026-05-01.png`
- ECS deploy script: `bash scripts/deploy_to_ecs.sh` (含 build · 前端) / `--skip-build` (后端)
- Production: `https://liuye.me/login` · 后端 ECS 139.196.30.69 · Cloudflare tunnel

## 8. ⚠️ Critical Gap (前主 CLI 现有 doc 没明写 · 但新 CLI 必须知道 · 防再跑偏)

### 8.1 awwwards 参考的真技术分析 (避免新 CLI 又混 Three.js)

PM 锁定视觉参考: https://awwwards-2022-workshop.vercel.app/
- **canvas**: 2560x1432 (Hi-DPI)
- **context**: WebGL2 (NOT webgl1)
- **框架**: NOT Three.js · NOT Next.js · 纯 Vite SPA + raw WebGL2 raymarching
- **bundle**: 单 file `index.4dcf536c.js` (压缩闭源)
- **视觉 stack**: raymarching black hole shader + 重力透镜 + 吸积盘色温梯度 (紫→红→橙→白) + chromatic aberration starfield + film grain

**红线**: 新 CLI **不要**推 "抓 awwwards bundle 反编译" 路径 (闭源版权风险)。F4 v2 用 oseiskar/black-hole MIT base 是合规路径。

### 8.2 PM 审美门槛 verbatim (F4 v1 翻车 PM 原话)

PM 嫌 F4 v1 极简磨砂玻璃: **"垃圾中的垃圾 · 20 年前网页 · 毫无特效 · 没设计感"**

PM 想要: **设计感 + 银行端正 + 现代时代感 + 高质感动效**。
PM 不要: **极简到无聊** (端正 ≠ 无聊 · Goldman Sachs / Morgan Stanley 都高级不无聊)。

### 8.3 F4 v2 当前 LIVE 自评 gap (新 CLI 如果 PM 选 V2 fix · 改这些)

| 维度 | awwwards 参考 | F4 v2 LIVE | gap |
|---|---|---|---|
| 重力透镜 | 上下双道弯曲 | ✅ 有 (但线条感强) | 小 |
| event horizon shadow | 中心黑色倒梯形 | ✅ 有 (但偏小) | 小 |
| **吸积盘色温梯度** | 紫→红→橙→白 | ❌ 纯白/银 · **没色温** | 🔴 大 |
| **CA starfield** | 红绿蓝色散星 | ❌ 星点白色 · **没色散** | 🔴 大 |
| film grain | 细 | ⚠️ 偏重 (像旧电视雪花) | 中 |
| 整体色调 | 温暖 (紫红橙) | 冷 (银白) | 🔴 大 |

V2 fix 重点: 加色温 palette LUT + chromatic aberration shader uniform + film grain noise 减弱。

### 8.4 完整 cherry-pick commit hash 链 (如果回档 trace)

| Worker | Sprint 1 | Sprint 2 |
|---|---|---|
| B1-flywheel | `d7f0f01..97ced9d` (V1+V2 9 commit) | `0636904..ae17ad8` (enrich 6 commit · 我误派) |
| B4-credit | `a8d2da6..17d9da8` (BE2 7 commit) | `9a99f71..68fded5` (BE7 7 commit · 我误派 · Sprint 3 worker-B7 工作) |
| B4-report | (Sprint 2 不参与) | `5b88bb6` 链 (BE3 12 commit) |
| B3 | `1a1af69..4454e15` (Sprint 1 10 commit) | F4 v2 `bf698e8..19ec48c` (5 commit) + Sprint 2 B-3 phase `a0782cb/fcfe384/62e1b84` (3 commit · 还**没 cherry-pick · 在 worker branch · 等 F12 + DONE 一起 cherry-pick**) |

### 8.5 Codex protocol v2 (Q-043) trailer 模板

任何 commit 必含:
```
REVIEW-MODE: manual (codex 用尽 until 2026-05-08 fallback)
REASONING-EFFORT: medium
ELAPSED: <min>
```

改 web/ 加:
```
PRESERVES: F-001..F-007 (per docs/features-inventory.md)
NEW-DOM: <具体新增 element 列表>
SMOKE-PASS: tsc-clean + next-build-success + <spec.spec.ts>
```

视觉/shader 改加:
```
SHADER-SOURCE: <URL · LICENSE> (e.g. https://github.com/oseiskar/black-hole · MIT)
```

PM 放宽时加:
```
Authorized-By: PM
```

### 8.6 5 sub-agent 历史 (新 CLI 派 sub-agent 避坑)

前主 CLI 派过 5 sub-agent:
- Gemini chrome operate 出 5 方向 — Gemini 用尽 (PM 给的 Gemini Pro 账号也限额)
- Screenshot Stripe/Linear/Vercel/Notion/Figma — 5 中只 1 成功 (Vercel) · 4 失败因 chrome focus 抢 tab + Stripe/Linear CDP block + Notion GFW
- 主 CLI 自己 chrome operate awwwards-2022-workshop · screenshot 成功
- 主 CLI 自己 chrome operate https://liuye.me/login · screenshot F4 v2 LIVE

**坑**:
- chrome session 是共享 (用户 + sub-agent + 主 CLI 同 chrome) · select tab 后 200ms race 内被抢
- Stripe/Notion 等大厂检测 CDP automation 拒渲染
- Gemini 一次最多 10 张图

### 8.7 Sprint 2 B-3 phase F12 待 (B3 当前唯一工作)

worker-B3 已 commit (worker branch 但**未 cherry-pick**):
- F11 ✅ A5 spike conflict banner
- F14 ✅ 全屏渐变折中
- F17 ✅ Warroom rejected lane
- F12 待 (视觉清洗 + F1c mock 中文术语合并)

worker-B3 完 F12 后会 commit DONE signal `WORKER-B3-SPRINT-2-B3-PHASE-DONE` · 新主 CLI 必 manual review + cherry-pick (含 F11+F14+F17+F12 · 4 commit + DONE · 5 commit) + push + ECS deploy 含 build。

### 8.8 100% 承接不可能 · 新 CLI 必守 4 条

1. **漂了立即停** — 不确定就重读 HANDOFF + state-snapshot + decisions-log · 不凭印象决策
2. **不懂立即问 PM** — 任何 architectural / 视觉 / 派单决策不确定 · 5s STOP · 问 PM
3. **5 跑偏 root cause 硬规** (§2.1) + **4 视觉硬约束** (§2.2) 守住
4. **每次 cron tick 完写 state-snapshot 段** (CLAUDE.md §14.1 硬规 · 前主 CLI 违反过 · 新 CLI 不能违)

---

## 9. 紧急 fallback (如果新主 CLI 也跑偏)

PM 可:
- 退回最近 git tag: `git reset --hard phase-a-exit-bugfix-2026-05-01` (Phase A 真 exit 状态 · 8 硬线全过 · 4 BUG 修完)
- 或: `git reset --hard phase-b-start-2026-05-01` (Phase B 启动前)

---

**Signal: HANDOFF-PREPARED-FOR-2026-05-02-RESTART**

前主 CLI: Claude Opus 4.7 (1M context) · 2026-05-02 PDT · session 长 1 天 + 大量 cron tick + 5 sub-agent + 多次 ECS deploy · 临近 compression 边界 · 主动让位
