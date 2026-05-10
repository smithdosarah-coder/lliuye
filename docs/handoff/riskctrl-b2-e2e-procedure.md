# Phase B.2 · riskctrl admin 真号 E2E 4 件套 · 执行手册

> **Worker**: riskctrl
> **Phase**: B.2
> **Refs**: ALLIN-2026-05-10
> **Status**: spec ready · 待 main CLI 在 ECS / 本地 live 跑 · 留 4 件套证据
> **Spec 文件**: `web/tests/regression/riskctrl-b2-e2e.spec.ts`

---

## 为何 worker 不能自己跑 4 件套

riskctrl worker (worktree `D:/claude code/credit_report_agent_work_mesh/riskctrl`) 缺以下生产基线:

| 缺什么 | 影响 | 谁能补 |
|---|---|---|
| live backend 进程 | 无法跑真 LLM dsl_gen + 真 backtest | main CLI / ECS |
| `web/node_modules` 完整 install | Playwright 跑不起来 (worker 仅 symlink 父 node_modules 给 tsc 用) | main CLI 在父 worktree 跑 |
| admin 真号 LLM key (DEEPSEEK_API_KEY 等) | demo/run 真打 LLM 不通 | PM 持有 / ECS env |
| 屏幕录制硬件 | 无法录 webm 真录屏 | main CLI / 人工 |
| `test-results/` 上传基础设施 | E2E_EVIDENCE_URL 来源 (cloud storage / cf-pages link) | PM / DevOps |

worker 写完 spec + 这份手册即 BLOCKED · 等 main CLI 接力跑 4 件套.

---

## 4 件套清单 (per dispatch B.2)

| # | 件 | 内容 | spec 自动 | 上传 |
|---|---|---|---|---|
| 1 | 录屏 | 完整 demo 流程 (mode toggle → seed select → demo run → 结果展示) webm | playwright video on | YES |
| 2 | 截图 | 6 张关键节点 png (default real / demo loaded / running / done / back-to-real / error) | spec page.screenshot 7 张 | YES |
| 3 | HAR | /api/riskctrl/demo/{seeds,run} 真打的 network archive | playwright recordHar | YES |
| 4 | run log | backend uvicorn stdout (含 LLM call audit + ledger 写) + frontend playwright stdout | 人工抓 + spec stdout | YES |

---

## 执行步骤 (main CLI)

### 0. 前置条件

```bash
# 0.1 在父 worktree 跑 (带完整 node_modules)
cd D:/claude\ code/credit_report_agent_work
# 0.2 cherry-pick riskctrl B.2 commits 到 main 或 ALLIN integration 分支
git fetch . feat/allin-riskctrl
git cherry-pick c1a8563 3798e90
# 0.3 verify env
echo $DEEPSEEK_API_KEY  # 必须非空
echo $DASHSCOPE_API_KEY  # 备用
ls data/mock/agent2-samples/loans.csv  # 必须存在
```

### 1. 启 backend

```bash
# 在 fresh terminal
py scripts/start_uvicorn.py
# 等 "Uvicorn running on http://0.0.0.0:8000"
# 监听 LLM call audit log: tail -f .logs/audit/llm_calls.jsonl 另开 terminal
```

### 2. 启 frontend

```bash
# 在 fresh terminal
cd web && npm run dev
# 等 "ready in N ms" + "Local: http://localhost:3000"
```

### 3. seed admin auth (浏览器开 devtools console)

```js
localStorage.setItem('platform.auth.v1', JSON.stringify({
  state: { currentUser: {
    id: 'u_admin', name: '管理员', role: 'admin',
    team: '总行·风控总部', avatar: '管',
  }},
  version: 0,
}));
```

### 4. 跑 Playwright spec

```bash
cd web
npx playwright test tests/regression/riskctrl-b2-e2e.spec.ts \
  --headed \
  --trace=on \
  --video=on \
  --reporter=html
```

输出:
- `test-results/<test>/video.webm` ← 录屏
- `test-results/riskctrl-b2-0{1..7}-*.png` ← 截图 (spec 内 page.screenshot 加节点)
- `test-results/<test>/trace.zip` ← 含 HAR + DOM snapshot
- `test-results/<test>/test.log` ← run log
- `playwright-report/index.html` ← 汇总报告

### 5. 抓 backend log

```bash
# 抓 LLM call audit (期间应有 dsl_gen + 多次 deepseek-chat call)
cat .logs/audit/llm_calls.jsonl | tail -50 > test-results/riskctrl-b2-backend-llm-audit.jsonl
# 抓 uvicorn stdout (含 endpoint trace + ledger silent-fail or success)
cat uvicorn.log | grep -E "demo/run|demo/seeds" > test-results/riskctrl-b2-backend-uvicorn.log
```

### 6. 上传

```bash
# 选择: cloudflare R2 / 飞书 wiki / GitHub release artifact
# 推荐 cloudflare R2 (已配 cloudflared tunnel · 直传)
zip -r riskctrl-b2-e2e-evidence.zip test-results/ playwright-report/
# 上传后获 URL · 填 E2E_EVIDENCE_URL trailer
```

### 7. fire READY signal commit

```bash
git commit --allow-empty -m "$(cat <<'EOF'
chore(mesh): signal worker riskctrl Phase B.2 ready

Worker: riskctrl
Phase: B.2
Refs: ALLIN-2026-05-10
Signal: READY
Root: 40f881f
E2E_EVIDENCE_URL: https://r2.liuye.me/e2e/riskctrl-b2-2026-05-10.zip

# Body 7 段 per signal-commit-contract §2:
# 1. 完成摘要 (3 commit · step 2 + step 3+4 + spec)
# 2. 改文件清单 (见 git log --stat)
# 3. 测试 verify (tsc exit 0 · spec 3 test pass · backend smoke loaded)
# 4. 红线自检 10 条 (silent fallback / fixtures / ModePill / NotImplementedError / KS=0 / ledger / E2E trailer / Q-040 MAX_ROWS=50000 / PIPL / 评分一样)
# 5. 依赖合同 (entity-resolution v1.1 · candidate-identity v1.1 · sse-envelope v1.0 · llm-prompt-contract v1.0 · decision-ledger v1.0)
# 6. base dashboard 行 record_id (待主 CLI 创表后填)
# 7. 证据 (E2E_EVIDENCE_URL 上 4 件套 + decisions-log Q-NNN 引用)
EOF
)"
```

---

## 验收硬线 (任 1 fail = REJECT)

- [ ] video 完整录到 demo 流程 (无中断 · 无空白)
- [ ] /api/riskctrl/demo/run HAR 真有 LLM call (response > 1KB · 非 fixture-shape)
- [ ] KS / AUC / 通过率 数字非 0 (spec assert · 真 backtest 算)
- [ ] 截图无 RISKCTRL_EVIDENCE 残留文本 ("[mock] demo 默认策略" 不出现)
- [ ] 错误 path 测试 pass (LLM down → typed banner · seed load fail → typed banner)
- [ ] data-source badge 显 'live' (不是 mock_forced)
- [ ] backend audit log 含 dsl_gen + deepseek-chat call (LLM 真打)
- [ ] ledger sqlite 含本次 demo decision (silent-fail 不阻 stream · 但成功路径应有)

---

## fallback (E2E 跑不起来)

如 main CLI 跑 spec 失败 (env / network / LLM 限流) · 改用 manual run + curl 留证:

```bash
# 1. curl /api/riskctrl/demo/seeds (admin token 自带)
curl -H "Cookie: ..." http://localhost:8000/api/riskctrl/demo/seeds | jq > seeds.json
# 2. curl /api/riskctrl/demo/run · SSE stream
curl -H "Cookie: ..." -X POST http://localhost:8000/api/riskctrl/demo/run \
  -d '{"seed_id":"credit_v15"}' \
  -H 'content-type: application/json' \
  --no-buffer > demo-run-sse.log
# 3. 截图浏览器最终结果页
# 4. zip 三件 (seeds.json / demo-run-sse.log / final-screenshot.png) 当 E2E_EVIDENCE_URL
```

降级标准: manual run 缺录屏 · 但保留 SSE log + screenshot · trailer 加 `E2E_FALLBACK: manual_curl` 标记.

---

## 文档元

- 本 doc 路径: `docs/handoff/riskctrl-b2-e2e-procedure.md`
- 跨 worker 通用 · 其他 5 worker (channel/credit/report/alert/compliance) 应有类似 procedure
- 写入 git history · 不归 working/ untracked
