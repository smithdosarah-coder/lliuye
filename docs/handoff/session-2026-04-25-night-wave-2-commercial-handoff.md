# Session Handoff · 2026-04-25 night · Wave 2 + Commercial Parallel

> 本文档是 2026-04-25 night 主 CLI（Wave 1 全合后）写给下任主 CLI 的**交班脑图**。
> 新 main CLI resume 后读本文 + `AGENT_IDENTITY.md` 清单所有文件 → 100% 接替。
> 与 `session-2026-04-25-phase-3-final-handoff.md`（白天 P3F 规划版）配套读 · 本文是 Wave 1 closeout + Wave 2 dispatch 双轨续接。

---

## §0. 一眼 Verdict

- **Wave 1**: 🟢 COMPLETE 4/4 worker MERGED（agent6 + agent3 + agent1-cherry + data-foundation V2）
- **User 决策**：**ABC 都要干** = A（commercial-readiness 主 CLI proxy）+ B（Wave 2 frontend-integration worker dispatch）**并行**
- **Handoff 缘起**：当前主 CLI session context ~70%+ · A+B lifecycle 预计 7-10d 多轮 · 必膨胀溢出 → 主 CLI 主动交班 · fresh session 干稳
- **新主 CLI 接手后第一件事**：读本文档 §0-§7 全 + 跑 §7 resume 验证 + 直接执行 §3.A + §3.B（不再问 ABC · user 已 GO）

---

## §1. Wave 1 实际产出（git 已落 · audit 用）

### 1.1 4 worker merged 链（chore/l0-infra）

```
d82ed35 docs(eval): post-Wave-1 v16 baseline quick-run · Q-035 A-035 follow-up
83979bf chore(mesh): P3F Wave 1 COMPLETE · 4/4 worker MERGED 🎉
(merge)  Merge feat/agent6-v16: P3F track 1 unfreeze APPROVED · Wave 1 final 4/4
cdf270b docs(decisions): Q-035/A-035 · agent6 v16 drift red-line semantic re-interpretation
dd42fa3 docs(process): worker askout protocol · enforce commit-trailer over chat
add6bb0 docs(process): onboarding spec self-check checklist · prevent Q-035 class spec gap
7e1f79b chore(mesh): data-foundation V2 merged · Wave 1 3/4 done
c1f87f9 docs(decisions): Q-034/A-034 · accept history leak compromise for data-foundation V2
(merge)  Merge feat/data-agent2-foundation: P3F track 8a Agent2 mock data APPROVED (V2)
c61d56f chore(mesh): P3F Wave 1 partial closeout · 2/4 worker MERGED
fc32b31 docs(decisions): Q-033/A-033 · agent3 L1-3 RiskRadar route to track 4
(merge)  Merge feat/agent3-productize: P3F track 2 unfreeze APPROVED
(merge)  Merge feat/agent1-cherry-pick: P3F track 3 cherry-pick APPROVED
ee1f9c9 chore(mesh): Phase 3-Final dispatch · 6 worktree mesh + Wave 1 ready
9d55b46 docs(p3f): land 8-track kickoffs · Wave 1/2/3 dispatch prompts
d84619f docs(p3f): land Wave 1 onboarding x4 (tracks 4/5/6/7)
```

### 1.2 解 DoD 6+4+4+0 = 14 条

| Worker | 解 DoD |
|---|---|
| agent6 | L2-12 audit_log + L2-13 partners + L2-14 data-classification + L3-8 飞轮 + L3-11 模型卡 + L3-12 演示脚本（6） |
| agent3 | L2-7 reason_codes + L2-8 字典 + L1-4 docx + L1-11 handoff（4 · L1-3 RiskRadar 路由 Q-033 → 轨 4） |
| agent1-cherry | L3-8 飞轮 + L1-4 xlsx + L1-11 handoff + L2-14 bonus（4） |
| data-foundation | 0 直接 DoD · 为轨 8b/8c 铺 Agent2 数据底座 |

### 1.3 决策档（Q-001 ~ Q-035）

新加 3 条（Wave 1 in-flight）：
- **Q-033** Agent3 L1-3 RiskRadar 路由 → Wave 2 轨 4 frontend-integration（596283f 全 web/ · 触红线 auto-dropped · backlog 已加 onboarding §3a）
- **Q-034** data-foundation V2 history leak compromise（HEAD clean · git history 仍含 V1 leak commit · 接受 not rewrite）
- **Q-035** agent6 v16 漂移红线**语义重新解读**（"rebase mechanic drift < 1%" 而不是 vs 历史 baseline 68.6 · 这是 onboarding spec gap · 上任主 CLI 写时考虑不周 · 触发 process 改进）

### 1.4 Process 改进（Q-035 lesson）

- `docs/process/onboarding-spec-self-check.md` · 5 项 main CLI 写 onboarding 完必跑 check
- `docs/process/worker-askout-protocol.md` · worker askout 强制 commit trailer · 禁 chat askout
- `docs/handoff/phase-3-final-kickoffs.md §1.1` · inline 红线 + ref protocol

### 1.5 DoD 推进

| 层 | Wave 1 前 | Wave 1 后 | P3F 终目标 |
|---|---|---|---|
| L0 工程基础 | 75% | ~80% | 90% |
| L1 Demo 完整度 | 60% | ~75% | 90% |
| L2 金融合规 | 75% | **~88%** | 95% |
| L3 客户 POC | 45% | **~65%** | 85% |
| L4 商业交付 | 10% | 10% | 10%（待 A） |

---

## §2. Wave 1 housekeeping 小尾巴（A+B 完后 batch 清）

⚠️ 这些不阻 Wave 2 dispatch · 但不应无限推迟。新主 CLI 干完 A+B 后 batch 处理：

| # | 项 | 工期 | 触发缘起 |
|---|---|---|---|
| 1 | 4 worker 物理 worktree cleanup | ~10min | Wave 1 全合 · `git worktree remove demo-agent6 demo-agent3 code-agent1-cherry data-agent2-foundation` + `git branch -d feat/...` 4 条 + mesh.json 移 entry |
| 2 | agent3 docx_export.py rename | 1 commit · ~30min | Q-033 follow-up · `docx_export.py` → `decision_letter_docx.py` · `render_decision_letter` → `export` · grep imports 修齐 |
| 3 | agent6 onboarding T1-4 + T1-8 措辞修齐 | 1 commit · ~30min | Q-035 follow-up · `docs/onboarding/p3f-agent6-unfreeze.md` §3 T1-4 + §4 红线条改成"rebase mechanic drift" 语义 + T1-8 加 illustrative 注脚 |
| 4 | 路由收敛 deprecation banner | 1h | brainstorming §4 step 1 · 6 legacy page.tsx 加 deprecation banner + 5s redirect 到 /archive/{agent} |
| 5 | demo source chip | 0.5d 前端 | brainstorming §5 step 1 · Agent1 / Agent5 search result 卡片加 source chip（Tavily 实搜 / mock provider 标） |
| 6 | 4 process doc 暂不写 | 0 | brainstorming 反思推迟件 · 等真有第二次相关事件再产（minimum viable）|

总工期约 ~1d（含 worktree cleanup）。

---

## §3. ABC 双轨执行（user 决策已 GO）

### §3.A · commercial-readiness.md（主 CLI proxy · 1d · L4 10% → 30%）

**onboarding 路径**：本任无 worker · 主 CLI 直接产 · 不需要 onboarding doc · 但 scope 锁在本节。

**产物**：`docs/commercial-readiness.md`（~1500-2500 行）

**结构 outline**：

```
§0. verdict + 适用客户范围
§1. Pricing model 4 选 1
   - SaaS 按调用次数（按 6 Agent 各自调用 · pricing tier 3 档）
   - SaaS 按席位（按客户经理 / 审贷员 / 合规官 / 风险经理 4 角色 · 月费）
   - 私有部署 fixed by 银行规模（小行 / 中行 / 大行 / 跨国 4 档 · 一次性 + 年维护）
   - 联合开发（IP 共享 · 客户付开发费 · 共拥有 derivative）
   每选项含：典型客户画像 · 报价区间 · 利弊对比 · 销售触发条件
§2. SLA 3 档
   - 试点档（PoC 30 天 · 99% · 工作日响应）
   - 标准档（正式 1 年 · 99.5% · 24/7 响应 · 故障 1 day SLA）
   - 企业档（多年 · 99.9% · 24/7 + 现场 · 故障 4h SLA + 赔偿）
§3. 数据驻留方案
   - 境内 only（DeepSeek 国内 + Tavily 国内 endpoint · 默认）
   - 客户内网部署（v16 离线模式 · LLM endpoint 切客户私有 · SearchProvider 切客户内网 API · 数据零外发）
   - 混合（敏感数据本地处理 · 非敏感走云）
§4. 合规审计映射
   - SOC 2 · ISO 27001 · 等保 2.0 · GDPR (境外业务) · 各项现状 + gap
   - 客户审计支持流程（提供审计 log + 文档 + 现场配合）
§5. licensing model
   - 软件许可（perpetual + annual maintenance）
   - 模型许可（独立 · 含使用范围限制）
   - 二次开发授权（客户内部 vs 客户对外销售 不同条款）
§6. 培训 + 现场支持 + 二次开发
   - 培训：4 角色 × 3 天标准课程 · 报价框架 · 持续教育（季度 webinar）
   - 现场支持：实施期 30 天驻场 · 上线后远程 24/7 · 现场出差按天计费
   - 二次开发：报价模型（按 Agent 数 + 按需求复杂度 + 按时长）
§7. RFP 应答模板
   - 30+ 银行 RFP 标准题（按客户内部审批流程拆题）
   - 50+ FAQ（按 PoC 客户询问频率排）
   - 标准 30min sales pitch 话术
   - 异议处理（"价格高 / 部署慢 / 数据不安全 / AI 不可信" 4 大异议）
§8. 拉销售 / 法务 / 财务 input
   - 销售：定价 final 决定权 · 折扣权限
   - 法务：licensing 条款 · IP 保护 · 数据合规
   - 财务：成本模型 · 利润率底线 · 长期合同折扣
   - PM + 工程不能 cover · 必须拉团队
```

**预期 ROI**：
- L4 10% → 30%（pricing/SLA/datalocation 三项有框架）
- 客户 RFP 时不再"how much / when / how secure"哑场
- 销售有标准答 · 不每次重新拼

**新主 CLI 行动**：
1. 读本节 outline + brainstorming §3 deep-dive（前任主 CLI 写过更细 reasoning · 在本 session 历史 · git log d82ed35 之前几条 commit body 也有 reference）
2. 直接写 commercial-readiness.md
3. 写完 commit Signal: P3F-COMMERCIAL-READINESS-LANDED
4. 不需要 user review（PM 自决 · doc 写完 user 自然会读）
5. 拉销售 / 法务 / 财务 是 user 工作（PM 视角）· 主 CLI 只产 framework + 留 placeholder

**工期**：~1 天主 CLI session（一气呵成 ·~ 50-100k tokens 写作）

---

### §3.B · Wave 2 dispatch · 轨 4 frontend-integration（worker · 7-8d）

**onboarding 路径**：`docs/onboarding/p3f-frontend-integration.md`（已落 Wave 1 dispatch 时 · §3a 含 Q-033 RiskRadar backlog · 不需要重写）

**kickoff 路径**：`docs/handoff/phase-3-final-kickoffs.md §3.1`（已落 Wave 1 dispatch 时 · 完整 worker prompt · 不需要重写）

**worktree 信息**：
- 名：`code-frontend-integration`
- 路径：`D:/claude code/code-frontend-integration`（不存在 · 新主 CLI 创建）
- 分支：`feat/frontend-integration`（新分支 · fork chore/l0-infra）

**新主 CLI 行动**（按顺序）：

1. **创建 worktree**：
   ```bash
   cd "/d/claude code/credit_report_agent_work"
   git worktree add ../code-frontend-integration -b feat/frontend-integration chore/l0-infra
   ```

2. **写 AGENT_IDENTITY.md** to `D:/claude code/code-frontend-integration/AGENT_IDENTITY.md`：
   - 模板：参考 `D:/claude code/code-agent1-cherry/AGENT_IDENTITY.md`（Wave 1 时本任主 CLI 写的格式）
   - 关键字段：
     - 角色：worker
     - Agent 域：前端整合 · 7 frozen branch 融合
     - branch: feat/frontend-integration（fork chore/l0-infra）
     - 必读清单：CLAUDE.md §7 + p3f-frontend-integration.md + decisions Q-031/032/033 + handoff §3
     - 红线：legacy 顶层 6 页不动 · 后端不动 · 红区 + web/src/lib/store/* 不动（除 panel-layout-store.clearAgent 扩展）· Letterpress / crimson 老 tokens 不动 · Stage 顺序硬性 1→2→3→4→5
     - 等待 next signal: FRONTEND-INTEGRATION-ACK

3. **更新 mesh.json**：
   - 加 entry `code-frontend-integration` · phase_3_final_track: 4 · onboarding pointer
   - 现 4 merged worker 状态保持（不动 · 等 housekeeping batch 清）

4. **commit dispatch**：
   ```
   chore(mesh): Wave 2 dispatch · track 4 frontend-integration

   ...
   Signal: PHASE-3-FINAL-WAVE-2-DISPATCHED
   ```

5. **起 patrol cron**（5min · 监 worker stage signals）：
   ```
   CronCreate cron="*/5 * * * *" recurring=true
   prompt="Check mesh-status.json + git log -20 chore/l0-infra. Surface ONLY if NEW: FE-STAGE-X-DONE / READY-FOR-FRONTEND-INTEGRATION-REVIEW / Q-NNN-RAISED / RFC-* / stuck_event. Silent otherwise."
   ```

6. **告诉 user 开新 worker 窗口**：
   - 桌面 `mesh-credit-agents.bat` 现在配的是 Wave 1 的 4 worker · 已过期
   - 新主 CLI 改 bat 内容 · 改成单 worker `P3F-T4-frontend-integration` · 路径 `D:/claude code/code-frontend-integration`
   - user 双击新 bat → 开 1 worker 窗口 → 粘 §3.1 kickoff prompt

7. **接 worker stage signals**：
   - FRONTEND-INTEGRATION-ACK → 检查 ACK body · 看 worker 是否识别 §7 spec 红线 + Q-033 backlog + EvidenceTrail 兼容承诺
   - FE-STAGE-1-SHELL-BASE-DONE → review（subagent verify shell-free-drag + canvas-mode-toggle 合 OK · tsc + build 0 error）
   - FE-STAGE-2-AGENT-WORKSPACE-DONE → review（**关键 stage** · 含 Q-033 RiskRadar 补 + EvidenceTrail 兼容 · 多 spec 验）
   - FE-STAGE-3-DISPATCH-IM-DONE → review（chat-wechat-style 合 OK）
   - FE-STAGE-4-HERO-POLISH-DONE → review（agent-workspaces-v2 合 · 决策 v2 hero 与 Codex 兼容 vs 降级 cherry-pick）
   - FE-STAGE-5-SMOKE-DONE → review（32 张跨 browser 截屏 · 4 主题 × 4 view × 2 browser）
   - READY-FOR-FRONTEND-INTEGRATION-REVIEW → final subagent pre-review · APPROVE → merge

**预期 worker 工期**：7-8 天（按 onboarding §5）· 允许 REJECT-V2 1 轮

**主 CLI 工作量**：
- dispatch: ~30min
- 每 stage review: ~30min × 5 = 2.5h
- final review + merge: ~1h
- 合计 ~ 4-5h 主 CLI proxy 时间 + 等 worker 的 wait time

---

### §3.C · A + B 并行执行（推荐 · user GO）

**timeline 规划**：

```
Day 0 (now) · 新主 CLI resume + 干 A 写 commercial-readiness.md (1d)
Day 1 · A done · 同时起 B (Wave 2 dispatch · §3.B step 1-6)
Day 2-9 · B worker 跑 7-8d · 主 CLI 接每 stage signal review
Day 9-10 · B final review + merge · Wave 2 完
Day 10 · housekeeping batch 清（§2 6 项 · ~1d）
Day 11+ · Wave 3 dispatch（轨 5 reason_codes · 轨 6 POC evidence · 轨 7 docs-compliance · 轨 8b/8c Agent2 硬化 + evaluation）
```

**A + B 不冲突理由**：
- A 主 CLI proxy 写 doc · 0 worker 依赖
- B worker 跑前端 · 主 CLI 只 dispatch + review · 大量 wait time（worker 跑时主 CLI 闲）
- A 在 worker wait time 间隙做完 · 不抢 main CLI context

---

## §4. 主 CLI 红线（守不变）

- ❌ 不在 worker 分支上动代码
- ❌ 不绕 decisions-log 直接批示
- ❌ 改红区（`financial_analyzer.py` / `quality_scorer.py` / `truth_fill.py` / `web/src/lib/store/*`）必须 RFC
- ❌ 不主动 cherry-pick worker 未 APPROVED 产物
- ❌ 不改 `demo-start.bat`（用户服务器脚本）
- ❌ 不自己 spawn worker CLI（用户双击 bat）
- ❌ **不删 `~/.claude/skills/multi-cli-mesh/scripts/mesh_launch.py`**（事实上已经不在 · 但保留 reminder）
- ✅ 批示必须 commit trailer 带 `Signal: XXX`（单行 · 多 signal 拆 commit）
- ✅ 红线 4 硬闸：GO + TaskCreate + 方案先行 + Authorized-By trailer（针对演示型前端 / 红区）
- ✅ **新加**：写 onboarding 完必跑 `docs/process/onboarding-spec-self-check.md` 5 项 check
- ✅ **新加**：worker askout 必走 commit trailer · 不允许 chat 中转（`docs/process/worker-askout-protocol.md`）

---

## §5. 用户协作 feedback（Wave 1 内化 · 新主 CLI 必读）

- **说人话**：短 + verdict 先行 + 不啰嗦（user 多次纠偏 "说人话"）
- **方案先行**：中等以上任务动手前先方案 · 不接受无方案直接编码
- **PM 视角**：对外银行客户 RFP 级别 · 不只是 demo
- **回避决策 = 失职**：worker askout 主 CLI 必须立即裁决 · 不绕路（Q-035 阻塞 60min 是教训）
- **批量任务一气呵成再汇报**：3+ 步任务派发后 · 每步独立 commit · 中途不请示 · 除非真碰 blocker
- **不写 process > product**：minimum viable process · 第二次同类事件再产 doc · 不预防性堆 process（user 反馈 "你不是 process engineer"）

详见 `~/.claude/projects/D--claude-code-credit-report-agent-work/memory/MEMORY.md` 的 feedback memories 系列。

---

## §6. 旁路资产（新主 CLI 知道即可）

- `~/.claude/skills/multi-cli-mesh/scripts/mesh_launch.py` 实际已不在用户机器（前任 shim · 用户某次清理删掉了）· `mesh-credit-agents.bat` 当前是手写版（4 个 start cmd /k · 全 ASCII · ee1f9c9 dispatch 时本任主 CLI 重写）
- 桌面 bat 现状：
  - `start_claude.bat` · 单主 CLI 启动器（**新主 CLI 用这个**）· 已设 proxy + bash path + 自动更新 CC + cd 项目 + 跑 claude
  - `mesh-credit-agents.bat` · 当前 P3F Wave 1 launcher（4 worker · agent6/3/cherry/data-foundation）· **新主 CLI 干 §3.B step 6 时改成单 worker frontend-integration**
  - `mesh-credit-agents.bat.batch-1-archive` · 原 Batch 1 时代版本备份 · 不动
  - `demo-start.bat` / `demo-stop.bat` · 用户服务器脚本 · 禁动
- demo 跑：双击 `demo-start.bat` → 后端 :8000 + 前端 :3000 + cloudflare 隧道 → 浏览器开 https://demo.liuye.me（或本地 http://localhost:3000/today）

---

## §7. 新主 CLI 接手后第一件事 Hour-by-hour

### Hour 1 · Resume + 读完本文档

1. user 粘万能指令 "读 AGENT_IDENTITY.md 和里面列的所有文件，resume 状态后等我指令"
2. 新主 CLI 读 `AGENT_IDENTITY.md` → 自动跑 `multi-cli-mesh` skill
3. AGENT_IDENTITY 应该指向本 handoff doc + `session-2026-04-25-phase-3-final-handoff.md`（白天版）+ `decisions-log.md` + `dod-current-status-2026-04-24.md` + `MEMORY.md`
4. 本 handoff doc 是新主 CLI 必读 · 顶层 §0-§7 全过
5. 跑 `py ~/.claude/skills/multi-cli-mesh/scripts/orchestrator/scoreboard.py` 看 mesh 状态（应见 6 worktree · 4 merged · 2 historical agent1/main）
6. 跑 `py ~/.claude/skills/contract-audit/scripts/audit.py` 漂移扫描

### Hour 1 · 验证清单

- [ ] `git log --format='%h %s' -10 chore/l0-infra` HEAD 应是本 handoff commit（`ORCHESTRATOR-HANDOFF-WAVE-2-COMMERCIAL-PARALLEL` 或之后的 SHA）
- [ ] `git worktree list` 应见 main + agent1 + demo-agent3/6 + code-agent1-cherry + data-agent2-foundation 共 6 个（housekeeping 未清前）
- [ ] `cat docs/handoff/mesh.json | grep '"name"'` 应见 6 worktree
- [ ] `ls docs/process/` 应见 onboarding-spec-self-check.md + worker-askout-protocol.md
- [ ] `cat docs/handoff/decisions-log.md | grep "## \[Q-"` 应见 Q-001 ~ Q-035

### Hour 2 · 报告 user · 开始 ABC

1. 报告 resume 完成 + Wave 1 状态 + ABC 决策已锁 + 准备直接干
2. 用户 GO 后立即开始 §3.A 写 commercial-readiness.md（主 CLI proxy 一气呵成）
3. 同时 §3.B step 1（git worktree add code-frontend-integration）+ step 2（写 AGENT_IDENTITY）+ step 3（mesh.json 加 entry）+ step 4（dispatch commit）
4. 起 patrol cron（5min）
5. 改桌面 mesh-credit-agents.bat 为单 worker（§3.B step 6）
6. 通知 user 开 worker 窗口 + 粘 §3.1 kickoff

### Hour 3+ · 双轨执行

- A 写作（不阻塞 B worker dispatch）
- B worker resume + ACK + start Stage 1 → 主 CLI patrol 接 stage signals → review × 5

---

## §8. 签名 + 交接锚

- **本任主 CLI 签名**：chore/l0-infra @ 2026-04-25 night（Wave 1 全合 + 3 决策档 + 2 process doc + ABC 决策对齐 · 用户准备重开主 CLI）
- **交接锚 commit**：本 handoff doc 附 `Signal: ORCHESTRATOR-HANDOFF-WAVE-2-COMMERCIAL-PARALLEL`
- **新主 CLI 首次 dispatch commit signals**：
  - A: `P3F-COMMERCIAL-READINESS-LANDED`（commercial-readiness.md commit）
  - B: `PHASE-3-FINAL-WAVE-2-DISPATCHED`（Wave 2 dispatch commit）
- **预期 Wave 2 完结 commit**：`P3F-WAVE-2-COMPLETE-FRONTEND-INTEGRATED`（轨 4 merged 后）
- **性格 hint**：本任主 CLI 是 Opus 4.7 · Wave 1 全程内化 user feedback（说人话 + 方案先行 + PM 视角 + minimum viable process）· brainstorming skill 反思后产 2 process doc · 主动交班保 context · 不硬撑

---

## §9. Brainstorming 补遗（100% 承接 supplement）

> 本节是本任主 CLI 在交接前用 brainstorming 视角自检 handoff 完整性 · 补 7 项可能影响新主 CLI 工作质量的细节 · 但原 §1-§8 没显式覆盖的 supplement。

### §9.1 patrol / scoreboard 实战 workaround（known issue）

**bug**：`multi-cli-mesh/scripts/orchestrator/scoreboard.py` 的 signal scanner 有滞后 · 当 worker 出新 commit 含新 trailer 时 · scoreboard "Last Signal" 列可能仍显示老 signal name。Wave 1 实战遇到 2 次（code-agent1-cherry 和 data-foundation 都出过 READY signal · scoreboard 仍显 START / ACK）。

**workaround**：patrol 不只信 scoreboard 简化 column · 直接 grep trailer 验最新：
```bash
cd "/d/claude code/<worker-worktree>"
git log --format='%H%n%s%n%(trailers:only)' -1
```
或 batch 4 worker：
```bash
cd "/d/claude code/credit_report_agent_work" && for wt in demo-agent6 demo-agent3 code-agent1-cherry data-agent2-foundation; do echo "=== $wt ==="; (cd "../$wt" && git log --format='%h %s [%(trailers:only,key=Signal,valueonly)] %cr' -3); done
```

### §9.2 subagent pre-review 模式（必用 · 节省主 CLI context）

Wave 1 用 5 次 subagent pre-review（agent1-cherry / data-foundation V1 / data-foundation V2 / agent3 / agent6）· 每次节省 ~50-100k tokens 主 CLI context · working very well。新主 CLI **必须**用此模式（不要自己读 worker diff + onboarding 验收 12 项）。

**模板**（基于 Wave 1 5 次实战 distill）：
```
Agent(
  description="Pre-review <worker-name>",
  subagent_type="general-purpose",
  prompt="""
Pre-review <worker> deliverable for <track-name>.

Repo: D:/claude code/credit_report_agent_work
Worker worktree: <path>
Worker branch: <branch>
Closeout commit: <sha> · trailer Signal: <READY-FOR-X>

Context: <1-2 段 worker 任务背景 + 关键 hard-line>

Spec to verify (T<X>-1 .. T<X>-N · onboarding 验收硬指标 inline 全列):
1. <spec> (run: <bash command>)
2. <spec>
...

Output verdict (APPROVE | REJECT-V2 | CONDITIONAL-APPROVE) plus N-line table
marking each criterion ✓/✗/⚠️ with 1-sentence note. If REJECT specify worker
fix; if CONDITIONAL list main CLI merge-time actions. Keep ≤ 500-600 words.
"""
)
```

**触发时机**：worker emit READY-FOR-<X>-REVIEW signal 后 · 立即 spawn（不等任何 user 确认 · 主 CLI 自决）。

### §9.3 commercial-readiness 写作 deeper context（A 质量保证）

§3.A outline 是骨架 · 写好的 commercial-readiness.md 必须含**这些 reasoning 深度**：

- **Pricing 决策框架**：不只列 4 model · 要给"什么客户用什么 model"决策树
  - 城商行 / 农商行 → 私有部署 fixed by 银行规模
  - 跨国 / 国有大行 → 联合开发（IP 共享 · 长期合作）
  - 中小银行 / fintech → SaaS 按调用次数（低门槛起步）
  - 内部团队（如众安自用）→ SaaS 按席位（控成本）
- **数据驻留是销售杀手锏**：境内 only + 客户内网部署能力 = 国内银行 99% RFP 必问 · 必须明示能力
- **PoC 30 天免费 → 6-9 month 采购 cycle**：典型银行采购流程 · 商务团队需要这个 timing 才能预测合同
- **培训方案差异化**：4 角色（客户经理 / 审贷员 / 合规官 / 风险经理）× 3 天课程 = 12 个 module · 不是混在一起教
- **二次开发条款**：客户内部用 vs 客户对外销售 = 不同价位（前者免费 · 后者按销售额抽成）
- **拉销售 / 法务 / 财务 input**：写作时**留 placeholder 不脑补**——pricing 数字、licensing 措辞、SLA 赔偿额度 这些必须等团队 input · 不是 PM 能定的

参考资料（写作前必读）：
- 同盾 / 百融 / 壹账通 / Moody's / FICO 公开 RFP 应答样例（PM 私库 · 不在本 repo）
- 银行业 RFP 标准条款（中国银保监 / 央行公开模板）

### §9.4 patrol cron config（B dispatch 时直接抄）

Wave 2 worker 起来后 · 新主 CLI 立即 fire patrol。cron + prompt 直接复制：

```
CronCreate(
  cron="*/5 * * * *",
  recurring=true,
  prompt="""Check docs/handoff/mesh-status.json plus `git log -20` on the orchestrator branch (chore/l0-infra). Surface ONLY if any of the following is NEW since the last tick: READY-FOR-FRONTEND-INTEGRATION-REVIEW, FE-STAGE-{1,2,3,4,5}-DONE (intermediate · log heartbeat 1 line not surface), Q-NNN-RAISED, RFC-<topic>-RAISED, stuck_event populated, FRONTEND-INTEGRATION-ACK. If nothing new, remain silent. When surfacing, include the signal name + worktree name + suggested orchestrator action."""
)
```

**升级版**（采纳 brainstorming §6-D 优化 · 三档分级）：
- CRITICAL surface（READY / Q-NNN / RFC / stuck）→ 立即 ping + spawn subagent
- PROGRESS heartbeat（FE-STAGE-X-DONE）→ 1 line 简报 · 不催 user
- IDLE silent（无变化）→ 一句"🟢 silent"

**患**：每 5min /loop 5d 共 1440 ticks · 大多 silent · context 占用约 ~10-20k tokens 累积 · 可接受。

### §9.5 mesh.json 非官方字段 schema（新主 CLI 看不会 confused）

`mesh.json` schema_version: 1 · 但实际生产中本任 + 上任主 CLI 加了多个 non-official 字段（scoreboard.py 不识别 · 但 git log + 主 CLI 阅读用）：

| 字段 | 含义 | 加入时间 |
|---|---|---|
| `frozen` | worker 暂停 · 不参与当前 batch | Q-031 时代 |
| `unfreeze_in_progress` | worker 重新激活 · 在 rebase / cherry-pick 中 | P3F dispatch ee1f9c9 |
| `merged` | worker MERGED · 等 housekeeping 清 | Wave 1 partial closeout c61d56f |
| `merged_signal` | merge 时 commit 的 Signal 名 | Wave 1 partial closeout c61d56f |
| `merged_v2` | worker 经过 REJECT-V2 + V2 fix 后 merged | data-foundation V2 7e1f79b |
| `phase_3_final_track` | worker 在 P3F 哪个 track（1-8 + 8a/8b/8c sub-track）| P3F dispatch ee1f9c9 |
| `onboarding` | worker 对应 onboarding doc 路径 | P3F dispatch ee1f9c9 |
| `current_phase` | mesh top-level · 当前 phase 标识 | P3F dispatch ee1f9c9 |
| `current_phase_dispatch_commit_signal` | 当前 phase dispatch 的 anchor commit signal | P3F dispatch ee1f9c9 |
| `wave_1_status` | mesh top-level · Wave 1 完成状态 | Wave 1 final closeout 83979bf |
| `wave_1_completion_commit_signal` | Wave 1 全合 commit signal | Wave 1 final closeout 83979bf |
| `next_phase_step` | mesh top-level · 下一步动作描述 | Wave 1 final closeout 83979bf |
| `cleanup_log` | mesh top-level · 历史 cleanup event 数组 | Q-031 mesh 大清理 996b170 |
| `frozen_branches_no_worktree` | mesh top-level · 有 branch 无 worktree 的 frozen 项 | Q-031 mesh 大清理 996b170 |

**注意**：
- 这些字段**只在 git log 阅读 / 主 CLI human-eye review 时有用** · scoreboard.py 不读
- 新主 CLI Wave 2 期间继续用同样模式加新字段（如 `wave_2_status` 等）即可
- 不需要 schema migrate（schema_version 1 仍然 valid · 新字段是扩展不是不兼容）

### §9.6 brainstorming 11 gap backlog（不消失 · 集中记）

本任 brainstorming retrospective（用户要求"看产品设计是否合理"触发）发现 11 个 product/workflow gap · 推迟其中大部分。**新主 CLI 处理 Wave 2 + Wave 3 时 · 这些 gap 仍存在 · 不消失**：

**Product gap (5)**：
| # | gap | 已完成？ | 路由 |
|---|---|---|---|
| §1 | Agent2/3 边界混淆 | ❌ | P3F 内可做 UI 联动 chip（Wave 2 顺手 · 0.5d 前端） · 长期 P4 评估合并 |
| §2 | dispatch view 主动 vs 被动撕裂 | ❌ | P4 候选 · shell v2 lock 不在 P3F 改 |
| §3 | L4 商业化 roadmap 缺失 | 🟡 部分（A 路径中）| commercial-readiness 是 first piece · 全完整需 P4 拉团队 |
| §4 | 路由收敛 canon vs legacy | ❌ | housekeeping deprecation banner 短期可做（§2 housekeeping #4）· 长期 P4 一次性删 legacy + redirect rules |
| §5 | demo source chip | ❌ | housekeeping 短期可做（§2 housekeeping #5）|

**Workflow gap (6)**：
| # | gap | 已完成？ | 路由 |
|---|---|---|---|
| §6-A | onboarding 速度 vs 严谨度 | ✅ DONE | spec self-check checklist 已落 add6bb0 |
| §6-B | worker chat askout 协议破 | ✅ DONE | worker askout protocol 已落 dd42fa3 |
| §6-C | scoreboard signal scanner 滞后 | ❌ | upstream multi-cli-mesh skill bug · 不在本项目 P3F scope · 工作 around 见 §9.1 |
| §6-D | patrol silent vs surface 二元化 | 🟡 部分（§9.4 三档分级） | 实践中本任已 ad-hoc 分级 · 但没固化协议 · 后续可入 multi-cli-mesh skill upstream |
| §6-E | worker post-merge token 浪费 | ❌ | 当前靠 user 手动 close · 无 commit-driven 自动 close 协议 · P4 候选 |
| §6-F | subagent pre-review 投资 vs 收益 | ✅ 模式确认（§9.2 模板）| 不需进一步动 · 模式 working |

**新主 CLI 注意**：写 commercial-readiness 时 · 把 §3 L4 gap 全 cover · 不要又留 placeholder 给 P4。其他 gap 看时机插入 housekeeping 或 P4 backlog。

### §9.7 Known pitfalls（实战教训 · 防新主 CLI 重蹈）

Wave 1 实战中遇到的具体坑 · 防新主 CLI 重蹈：

| pitfall | 触发场景 | workaround |
|---|---|---|
| **桌面 bat 编码乱码** | mesh-credit-agents.bat 含中文 REM/echo · cmd 用 GBK 解析 UTF-8 中文 · 整个 bat 解析炸成乱码命令 | 桌面 bat **全 ASCII** · 中文输出走 docs · bat 只用 echo 英文 |
| **Windows Terminal 多 tab 聚合** | 4 个 `start cmd /k` 在 Win11 默认 WindowsTerminal 下被聚合到 1 wt 进程 4 tab · PowerShell `Get-Process` 只看到 1 WindowsTerminal | 不能用 process count 判断 worker 窗口数 · 看 git log activity 更准 |
| **bash cwd 漂移** | `cd /d/claude code/<worktree> && git log` 后 · 后续 Bash 调用 cwd 留在 worker · 导致 scoreboard 读 worker 的 stale mesh.json | 每个 patrol 命令前 `cd "/d/claude code/credit_report_agent_work" &&` · 强制 cwd locked |
| **bash 引号嵌套** | PowerShell -c 在 bash 里嵌引号炸 syntax error | PowerShell tool 单独调 · 不嵌 Bash |
| **scoreboard signal 字面 grep 误报** | scoreboard 简化 last signal · 把 commit body 里 literal text "Q-NNN-RAISED" 当真信号 误报 | 验真信号走 `git log --format='%(trailers:only)'` |
| **pytest 不在 main PATH** | main worktree 的 bash PATH 没 pytest · 但 `py -m pytest` 走 Python module 路径 OK | pytest 命令一律 `py -m pytest <path>` |
| **pyproject testpaths 双路径** | agent_credit/tests/ vs tests/agent_channel/ 混用 · pyproject.toml 双 testpaths · merge 后 verify 跑通 | 跑 pytest 时分别试 `tests/<area>/` + `<area>/tests/` |
| **worker fork 时 mesh.json stale** | worker 在 fork 时 mesh.json 是当时的版本 · 后续 main CLI 改 mesh.json 后 · worker 再读会读 stale · 但通常无所谓（worker 不读 mesh）| worker 不依赖 mesh.json · 主 CLI 改不影响 worker |

新主 CLI 看到上述任一现象立即知道是哪个 pitfall · 直接走 workaround · 不浪费时间 debug。

---

## §10. END-OF-HANDOFF

新主 CLI · 你接到的状态：
- Wave 1 全合 · 14 条 DoD 解
- 35 个 Q/A 决策档（最新 Q-035）
- ABC 决策已锁 · 你不需要再问 user 选 A/B/C
- §2 housekeeping 6 项是 batch 清的事 · 不阻 Wave 2
- §9 supplement 7 项细节 · 你照着做就 100% 承接

干完 A + B + housekeeping 后 · 写下一个 handoff doc 给再下任主 CLI（Wave 3 dispatch）· 同样模式 · 同样规模。
