# Handoff to Next Main CLI · 2026-04-27

> 上一次主 CLI session 干到这里·user 关窗双击 start-mesh.bat 重启
> mesh 后·你 (新主 CLI) resume · 读这个 + master plan 即可。

---

## 1 · 已 dispatched · 3 worker 在干

3 worker 已注册到 mesh.json · worktree 已 create · onboarding doc 已 commit (`e32025f`)。等 worker resume 后干活·push signal commit 给你接。

| Worker | Worktree | Branch | Task | Signal on done |
|---|---|---|---|---|
| A1-inventory | `D:/claude code/work-A1-inventory` | `feat/inventory-expand-A1` | features-inventory.md F-009~F-040 (32 entries · 6 Workspace + IM + Auth + Layout) | `WORKER-A1-INVENTORY-EXPAND-DONE` |
| A2-contracts | `D:/claude code/work-A2-contracts` | `feat/contracts-bootstrap-A2` | 3 protocol docs (workspace-state · im · auth) | `WORKER-A2-CONTRACTS-BOOTSTRAP-DONE` |
| A3-prd | `D:/claude code/work-A3-prd` | `feat/prd-summaries-A3` | 6 agent PRD summary specs (channel/report/credit/alert/compli/forge) | `WORKER-A3-PRD-SUMMARIES-DONE` |

Onboarding docs (worker 自己读 · 你 review 时也读):
- `docs/onboarding/W-A1-inventory-expand.md`
- `docs/onboarding/W-A2-contracts-bootstrap.md`
- `docs/onboarding/W-A3-prd-summaries.md`

**主 CLI 你的活**：
- 看 `py scripts/orchestrator/scoreboard.py` 跟踪 3 worker 状态
- 收到 `WORKER-AN-*-DONE` signal → review diff (acceptance 在 onboarding doc § Acceptance) → cherry-pick 到 chore/l0-infra
- 如有 worker 卡住 → 写 Q-NNN 到 `docs/handoff/decisions-log.md` + signal commit

---

## 2 · 没做的 · master plan Stage B / C / D 全没动

Master plan: `docs/contracts/master-execution-plan-2026-04-27.md`

### Stage B · Channel Workspace 完整 architecture (3 worker 完成 Stage A 后启动)

- B.1 mock_sessions.ts 扩 3-5 mock 标杆企业 (各自完整 ChannelSession)
- B.2 panel state hoist (5 panel 接 props · 删 CHANNEL_SESSION import)
- B.3 下拉切 session 真切全 panel
- B.4 候选 click → candidate detail drawer (radar / signal timeline 切到该候选)
- **B.4b 候选 detail · "为什么像" 匹配维度明细** (gap 4 漏的) — drawer 内 chip 列 · 各维度命中 + 证据
- **B.4c 候选 detail · Top3 产品推荐 + 切入话术** (gap 5 漏的) — 复用 v1 scoring · 客户经理"打开电话即用"
- B.5 后端 SSE 扩 radar/signals/funnel/match_dimensions/product_recommendations/pitch_scripts
- **B.5b 前端 wire 真 SSE 全字段** (gap 3 漏的) — Radar/Candidates/SignalTimeline/FunnelStrip 都消费 live · 不只 candidates name
- B.6 文件上传 KB 3 类 (gap 1)
- **B.6b IdealProfile LLM 抽画像** (gap 2 漏的) — 后端 `/api/channel/profile` · 前端"理想客户画像卡" + user 确认后才扫描
- B.7 Word 导出 (gap 6)
- B.8 Channel 5+ Playwright smoke
- B.9 features-inventory enrich F-channel-* 全 entries

### Stage C · 5 Agent 复制 Channel pattern (各 1 worker)

- C.1 Agent6 Report (v16 wire + 文件上传 + Word + panel hoist + 候选/材料 detail)
- C.2 Agent3 Credit (后端补 LLM stub + 4 维评分 + 红线 + panel hoist + Word)
- C.3 Agent4 Alert (KB_DEMO 解锁稳定 + 红/黄/绿榜单 + panel hoist)
- C.4 Agent5 Compli (政策事件驱动 + 业务矩阵 + KB_DEMO 解锁 + panel hoist)
- C.5 Agent2 Forge/Riskctrl (后端补 LLM stub + DSL 真生成 + 真回测 + panel hoist)
- C.6 5 Agent 各 5 Playwright smoke (25 spec)
- C.7 features-inventory 全 enrich

### Stage D · 系统级基础 + 收尾

- D.1 5 user RBAC enforce (后端 `/api/auth/login` 真 JWT + frontend AuthGate enforce ACCESS · user 没权限 redirect /403)
- D.2 IM WebSocket 实时 (后端 `/ws/im` FastAPI WebSocket · 前端 dispatch replace polling)
- D.3 thread persistence DB (sqlite or jsonl · `/api/im/threads` `/api/im/messages/{thread_id}`)
- D.4 IM tool calling (`/api/im/send` 升级 LLM function calling · "找/搜/扫" 真触发 agent SSE · 结果回 thread)
- D.5 shared/kb_scan/ 抽共享底座 (6 Agent 共享 KB / SearchProvider / Matcher · 现各自管 · 重构合并)
- D.6 客户走访 dry run (5 user × 6 Agent × 关键 path)
- D.7 ECS production verify (features-inventory 全 entries production 验)
- D.8 走访话术 + commercial-readiness 更新

---

## 3 · 没验证的 (有空补一下)

- [ ] 桌面 `start-mesh.bat` 实际双击是否 work (上次 mojibake 炸 · 已重写纯 ASCII · 没真测)
- [ ] skill validator 真 reject 缺 trailer commit (没 install commit-msg hook · 见 `~/.claude/skills/multi-cli-mesh/checklists/install-hooks.md`)
- [ ] production https://liuye.me 实际跑得对 (e13feec normalize 修 `[object Object]` · user 没 verify)
- [ ] CandidatesPanel live mode 在 `[object Object]` 修后是否真渲染候选 name + 8 维 + signals
- [ ] dispatch IM `@获客` 真路由到 channel system prompt (5d4ae17 deploy 上线 · smoke test 通 · user 浏览器没验)

---

## 4 · 已知坑 / 走访前必须 watch

| 坑 | 现状 | 缓解 |
|---|---|---|
| ECS GitHub 网络偶尔抖 (Empty reply / Connection timed out) | 当前 deploy 用 6 retry × 30s | scripts/deploy_to_ecs.sh 已含 retry |
| Cloudflared tunnel 单点故障 | https://liuye.me 走 CF tunnel · CF 抖一下 demo 全断 | 走访前预备 .com 备份域名 (需 user 手动) |
| LLM key 可能被轮换 (handoff 第 5 教训) | 当前 DEEPSEEK / TAVILY 早晨被 rotate 过 1 次 | 走访前 30 min smoke test all 6 endpoint · 备 fallback key (DashScope/Qwen) |
| 桌面 .bat / .ps1 必须纯 ASCII | 已重写 (handoff 第 1+2 教训) | 改 .bat 永远不要加中文注释 |
| zustand persist 没 skipHydration (handoff 第 8 教训) | 8 处 store · refresh 时可能踢回 /login | P1 hardening 必修 (Stage D 内) |
| ECS git tree 偶尔脏 (前任 scp) | 当前每次 deploy 前 git stash | 完整禁 scp · 严格走 commit→push→pull |

---

## 5 · 已上 production 的 commit (走访能演示的)

```
e32025f feat(mesh): register 3 Stage A workers
e13feec fix: candidates.signals normalize (修 [object Object])
db59c28 fix: revert today empty CTA + ScanCTA 进一步缩
6f96121 feat(IM v2): 5 真密码 + @agent 路由 + archive Channel 真接 LLM
5d4ae17 feat(dispatch): #2 微信气泡 + #5 IM 实装 (DeepSeek 真接)
3a3e357 feat(login): restore Gargantua R3F black-hole shader
ca1308a feat: today 4 块恢复 + 编辑按钮挪 Masthead
534ef5a chore(deploy): scripts/deploy_to_ecs.sh + CLAUDE.md §13.1
```

production HEAD = `e32025f` (GitHub origin/main)
ECS HEAD = ? (需 user 双击新 mesh 后让主 CLI 验)

---

## 6 · 文件路径快查

| 干啥 | 文件 |
|---|---|
| Master 实施 plan | `docs/contracts/master-execution-plan-2026-04-27.md` |
| 已交付功能清单 | `docs/features-inventory.md` (F-001~F-008 · A1 worker 在扩到 F-040) |
| 3 worker onboarding | `docs/onboarding/W-A{1,2,3}-*.md` |
| Mesh state | `docs/handoff/mesh.json` (4 worktree 现 active · 7 frozen/merged 历史) |
| 决策记录 | `docs/handoff/decisions-log.md` |
| ECS 部署脚本 | `scripts/deploy_to_ecs.sh` |
| ECS sync 规则 | `CLAUDE.md` §13 + §13.1 |
| Skill 防回档协议 | `~/.claude/skills/multi-cli-mesh/protocols/anti-regression.md` |
| Skill commit trailer 注册 | `~/.claude/skills/multi-cli-mesh/scripts/orchestrator/commit-signal-registry.yaml` |

---

## 7 · 新主 CLI resume 第一组动作

```bash
# 1. 看 worker 状态
py "C:/Users/Mr.S/.claude/skills/multi-cli-mesh/scripts/orchestrator/scoreboard.py"

# 2. 看最近 signal commit
git log --oneline -20

# 3. 看 decisions log
tail -50 docs/handoff/decisions-log.md

# 4. resume 后等 worker push signal · 或 user 给新指示
```

---

**Authored**: 上一次主 CLI session · 2026-04-27 close-out
