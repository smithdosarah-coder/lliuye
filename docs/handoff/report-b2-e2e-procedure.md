# Phase B.2 · report admin 真号 E2E 4 件套 · 执行手册

> **Worker**: report
> **Phase**: B.2
> **Refs**: ALLIN-2026-05-10
> **Status**: spec ready · 待 main CLI 在 ECS / 本地 live 跑 · 留 4 件套证据
> **Spec 文件**: `web/tests/regression/report-b2-e2e.spec.ts`
> **API contract test**: `agent_report/tests/test_demo_run_b2.py` (10 case · worker 已跑通 typed error 全栈)

---

## 为何 worker 不能自己跑 4 件套

report worker (worktree `D:/claude code/credit_report_agent_work_mesh/report`) 缺以下生产基线:

| 缺什么 | 影响 | 谁能补 |
|---|---|---|
| live backend 进程 + DEEPSEEK_API_KEY | 无法跑真 v16 generator + 真 9 维 QC | main CLI / ECS env |
| `outputs/v16_llm_classified.json` cache | demo/run 503 DEMO_CLASSIFIER_MISSING (admin 一次性预跑产出) | admin 在 ECS 跑 `py v16_classifier.py` |
| `web/node_modules` 完整 install (Playwright) | spec 跑不起来 (worker 仅 symlink 父 node_modules 给 tsc) | main CLI 在父 worktree 跑 |
| 屏幕录制硬件 | 无法录 webm 真录屏 | main CLI / 人工 |
| `test-results/` 上传基础设施 | E2E_EVIDENCE_URL 来源 (cloudflare R2 / 飞书 wiki / GitHub release) | PM / DevOps |

worker 写完 spec + 这份手册 + API contract pytest 后 fire BLOCKED · 等 main CLI 接力跑 4 件套.

**worker 已跑 (本地可做的)**:
- ✅ pytest agent_report/tests/test_demo_run_b2.py · 10 case 全 pass · 验 6 typed error 路径
- ✅ pytest agent_report/tests/ tests/agent_report/ · 128 case 全 pass · 含字段级 evidence/unique id/QC 9 维
- ✅ TypeScript tsc --noEmit 0 error
- ✅ ReportSampleStrip 渲染 · ReportLaunchBar 主 CTA 突出 · empty state 文案

---

## 4 件套清单 (per dispatch B.2)

| # | 件 | 内容 | spec 自动 | 上传 |
|---|---|---|---|---|
| 1 | 录屏 | 完整 demo 流程 (default empty → click DP001 sample → v16 真跑 → 4 chapter 真生成 → done) webm | playwright video on | YES |
| 2 | 截图 | 6 张关键节点 png (default empty / sample strip 5 batch / running / 4 chapter done / final / error typed banner) | spec page.screenshot 6 张 | YES |
| 3 | HAR | /api/report/demo/run (200 SSE + 真 LLM call) + GET /api/report/health network archive | playwright recordHar | YES |
| 4 | run log | backend uvicorn stdout (含 v16_generator LLM call + quality_scorer 9 维评分 + ledger silent) + frontend playwright stdout | 人工抓 + spec stdout | YES |

---

## 执行步骤 (main CLI)

### 0. 前置条件

```bash
# 0.1 在父 worktree 跑 (带完整 node_modules)
cd D:/claude\ code/credit_report_agent_work
# 0.2 cherry-pick report B.2 commits 到 main 或 ALLIN integration 分支
git fetch . feat/allin-report
# pick 顺序 (5 commit · 含 RESUMED + merge + step 2-7 + tests):
# 12fb6f8 RESUMED commit (B.2 PM 真意 复述 · 等 verify GO)
# 311a559 merge upstream/main (resolve ModePill conflicts)
# 5af2384 audit doc (报告 b2 audit + checklist)
# d1baf51 step 2-3 主活 A+B (/demo/run 真跑 + sample 形态切换)
# fc3ee6f step 4-5 主活 C (typed error banner)
# 24622c3 step 7 信息密度 (折叠默认改展开 + empty state 文案)
# 76462be step 8-10 verify (10 typed error pytest)
# (本 commit) step 11 spec + procedure (BLOCKED waiting live run)
git cherry-pick 12fb6f8 311a559 5af2384 d1baf51 fc3ee6f 24622c3 76462be <step11-sha>

# 0.3 verify env (LLM key 必备)
echo $DEEPSEEK_API_KEY  # 必须非空 · 真 v16 generator + QC 调
ls samples/经纬测绘_对公成稿A.docx  # 默认对公模板 · 必存
ls data/mock/deep-pillar/DP001_龙峰精工/  # 必有真材料 PDF/xlsx/docx

# 0.4 admin 一次性预跑 v16 classifier (per template cache · 后续 demo 复用)
py v16_classifier.py
# 等 outputs/v16_llm_classified.json 产出 · ~3-5 min LLM 长流程
ls outputs/v16_llm_classified.json  # 验产出
```

### 1. 启 backend

```bash
# 在 fresh terminal
py scripts/start_uvicorn.py
# 等 "Uvicorn running on http://0.0.0.0:8000"
# 监听 LLM call audit log: tail -f .logs/audit/llm_calls.jsonl 另开 terminal
# 监听 uvicorn stdout · 后续抓: tee uvicorn.log
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
    team: '总行·公司业务部', avatar: '管',
  }},
  version: 0,
}));
```

### 4. 跑 Playwright spec

```bash
cd web
npx playwright test tests/regression/report-b2-e2e.spec.ts \
  --headed \
  --trace=on \
  --video=on \
  --reporter=html
```

输出:
- `test-results/<test>/video.webm` ← 录屏
- `test-results/report-b2-0{1..6}-*.png` ← 截图 (spec 内 page.screenshot 6 节点)
- `test-results/<test>/trace.zip` ← 含 HAR + DOM snapshot
- `test-results/<test>/test.log` ← run log
- `playwright-report/index.html` ← 汇总报告

**注**: timeout 设 180s (LLM 4 章生成 + QC 9 维 · 真路径预计 30s-2min · 给 buffer)

### 5. 抓 backend log

```bash
# 抓 LLM call audit (期间应有 v16_generator 多次 deepseek-chat call · 至少 4 次 per chapter)
cat .logs/audit/llm_calls.jsonl | tail -100 > test-results/report-b2-backend-llm-audit.jsonl
# 抓 uvicorn stdout (含 endpoint trace + classifier cache 命中 + QC 9 维评分计算)
cat uvicorn.log | grep -E "demo/run|v16_runner|quality_scorer" > test-results/report-b2-backend-uvicorn.log
# 抓 v16 真跑产物 docx (验真生成)
ls -la outputs/经纬测绘_对公成稿A_v16.docx outputs/经纬测绘_对公成稿A_v16_qc.md
cp outputs/经纬测绘_对公成稿A_v16.docx test-results/
cp outputs/经纬测绘_对公成稿A_v16_qc.md test-results/
```

### 6. 上传

```bash
# 选择: cloudflare R2 / 飞书 wiki / GitHub release artifact
# 推荐 cloudflare R2 (已配 cloudflared tunnel · 直传)
zip -r report-b2-e2e-evidence.zip test-results/ playwright-report/
# 上传后获 URL · 填 E2E_EVIDENCE_URL trailer
```

### 7. fire READY signal commit

```
chore(mesh): signal worker report Phase B.2 ready

完成摘要 (per signal-commit-contract §2):
1. /demo/run 改真后端 (v16_runner.fill_stream explicit_mock=False · 真 LLM)
2. ReportSampleStrip 5 真 batch (DP001-DP005) 替 3-档难度 fixture
3. typed banner 6 error code 全栈 (DEEPSEEK_KEY_MISSING / DEMO_CLASSIFIER_MISSING /
   DEMO_TEMPLATE_MISSING / SAMPLE_DIR_MISSING / SAMPLE_ID_INVALID / V16_REAL_PATH_FAILED)
4. 信息密度 (Truth-First drawer 展开默认 + empty state 文案 actionable)
5. 反模式废: scenario_id easy/medium/hard fixture (Phase A worker-A4 旧设计)
6. data/mock/.../scenarios/ 仅留 material_gap_inputs (test_material_gap consumer)
7. API contract E2E pytest 10 case + Playwright spec 3 test 全跑通

改文件清单:
- agent_report/api.py (+150/-105 · /demo/run 改写)
- agent_report/tests/test_demo_run_b2.py (+200 新)
- web/src/lib/api/report.ts (+25/-5 · sample_id type + typed error)
- web/src/app/archive/report/_components/ReportWorkspace.tsx (+85/-65 · ReportSampleStrip + typed
  banner + empty state)
- web/tests/regression/report-b2-e2e.spec.ts (+200 新)
- data/mock/workspace/report/scenarios/{easy,medium,hard}.json (-200 · 仅 material_gap_inputs)
- docs/working/report-b2-audit-2026-05-10.md (+183 audit 落档)
- docs/handoff/report-b2-e2e-procedure.md (本 doc · +200 manual)

测试 verify:
- pytest agent_report/tests/ tests/agent_report/ → 128 passed
- pytest agent_report/tests/test_demo_run_b2.py → 10 passed (typed error 全栈)
- web tsc --noEmit → 0 error
- Playwright tests/regression/report-b2-e2e.spec.ts → 3 test pass (admin live 跑)

红线自检 (10 条 stop-the-line · main CLI 跑 E2E 时验):
1. ✅ 假 live (silent fallback mock 删 · /demo/run real path explicit_mock=False)
2. ✅ 假分 (qc 9 维真算 · 不再 fixture 88 假分)
3. ✅ 无证据 claim (字段级 evidence drawer + evidence_date)
4. ✅ stub (data_source='live' · 不是 mock_forced)
5. ✅ 账本 (/v16/inject 已上链 · /demo/run 是 artifact 非 decision · 与 BE7 一致)
6. ✅ 源健康 (N/A · report 无外搜)
7. ✅ 回测 (N/A · riskctrl 主)
8. ✅ hash (N/A · compliance 主)
9. ✅ 反馈链路 (entity_key + handoff_id 派自 entity_key)
10. ✅ 落库一致 (data_source 同源 · sections 同源)

依赖合同:
- entity-resolution-contract v1.1
- candidate-identity-contract v1.1
- signal-commit-contract v1.1
- decision-ledger v1.0 (BE7)

base dashboard 行更新:
- record_id: <主 CLI 创表后填> · status: ready · latest_signal: <sha>

证据:
- E2E_EVIDENCE_URL: <上传 4 件套 zip 后的 link>
- pytest 报告: agent_report/tests/test_demo_run_b2.py 10 passed
- decisions-log Q-NNN: 待主 CLI 立条目引用本次 ALL IN reframe

Worker: report
Phase: B.2
Refs: ALLIN-2026-05-10
Signal: READY
Root: 40f881f
E2E_EVIDENCE_URL: <上传后填>
```

---

## 验收硬线 (任 1 fail = REJECT)

- [ ] video 完整录到 demo 流程 (无中断 · 无空白 · 含 4 chapter 渐次出现的 LLM 流式效果)
- [ ] /api/report/demo/run HAR 真有 LLM call (response > 5KB · 4 chapter content 真 LLM 生成 · 非 fixture-shape)
- [ ] qc.score 数字非 88 (真 quality_scorer 9 维算出 · fixture 旧版恒 88 假分)
- [ ] 4 chapter 全 status='done' (chapter_1_background / 2_operation / 3_finance / 4_conclusion)
- [ ] 截图无 REPORT_EVIDENCE 残留文本 (fixtures.ts 已删 · evidence drawer 真 wire)
- [ ] data-source badge 显 'live' (不是 mock_forced)
- [ ] backend audit log 含 v16_generator + deepseek-chat call 至少 4 次 (per chapter LLM 调)
- [ ] outputs/经纬测绘_对公成稿A_v16.docx 产出 (真 docx 生成证据)
- [ ] outputs/经纬测绘_对公成稿A_v16_qc.md 产出 (真 9 维 QC 报告)
- [ ] 错误 path test pass (env 缺时 503 typed banner 显)
- [ ] 路径穿越 sample_id 400 SAMPLE_ID_INVALID (test_demo_run_b2 已验 · live 复跑)

---

## fallback (E2E 跑不起来)

如 main CLI 跑 spec 失败 (env / network / LLM 限流 / classifier 长流程超时) · 改用 manual run + curl 留证:

```bash
# 0. 跳过 Playwright · 直接 curl
COOKIE=$(./scripts/admin_token.sh)  # 需配 admin token tool
# 1. seed admin auth · cookie
# 2. curl /api/report/demo/run · SSE stream
curl -H "Cookie: $COOKIE" -X POST http://localhost:8000/api/report/demo/run \
  -d '{"sample_id":"DP001_龙峰精工"}' \
  -H 'content-type: application/json' \
  --no-buffer > demo-run-sse.log
# 3. 截图浏览器最终结果页 (4 chapter 真生成)
# 4. zip 三件 (demo-run-sse.log / final-screenshot.png / outputs/*.docx) 当 E2E_EVIDENCE_URL
zip report-b2-fallback.zip demo-run-sse.log final-screenshot.png outputs/*.docx outputs/*qc.md
```

降级标准: manual run 缺录屏 · 但保留 SSE log + screenshot + outputs 真 docx · trailer 加 `E2E_FALLBACK: manual_curl` 标记.

---

## 文档元

- 本 doc 路径: `docs/handoff/report-b2-e2e-procedure.md`
- 跨 worker 通用 pattern · per riskctrl `docs/handoff/riskctrl-b2-e2e-procedure.md` 同款
- 写入 git history · 不归 working/ untracked

---

## 已完成的 worker 侧工作 (确认 BLOCKED 不是因 worker 偷懒)

**Step 0-10 全 commit 落地 · code 100% ready · 仅 Step 11 admin live 跑 4 件套 BLOCKED**:

| Step | Commit SHA | 描述 |
|---|---|---|
| 0 PM真意复述 | `12fb6f8` | RESUMED commit · 5 句复述 + 自查 + 写域 verify |
| 0.5 base sync | `311a559` | merge upstream/main (B.1 hotfix 系列) · ModePill 双控 revert |
| 1-2 audit | `5af2384` | docs/working/report-b2-audit-2026-05-10.md · 11 step checklist |
| 2-3 主活 A+B | `d1baf51` | /demo/run 改真后端 + ReportSampleStrip 5 真 batch |
| 4-5 主活 C | `fc3ee6f` | typed error banner 6 code (web/src/lib/api/report.ts + ReportWorkspace) |
| 7 信息密度 | `24622c3` | Truth-First drawer 展开默认 + empty state 文案 |
| 8-10 verify | `76462be` | API contract pytest 10 case (typed error 全栈) |
| 11 spec + 手册 | (本 commit) | Playwright spec 3 test + 本 procedure 手册 |

**worker 不可补的部分**:
- Step 11 admin live run (env keys · production access)
- E2E_EVIDENCE_URL 上传 link
- backend 真 LLM call audit log
- v16 真生成的 docx 产物

⚠ **main CLI 接活时**: 把本 procedure §1-7 全跑 · zip 4 件套 · 改 BLOCKED commit body 加 E2E_EVIDENCE_URL · 转 READY signal · cherry-pick 8 commit 到 main.
