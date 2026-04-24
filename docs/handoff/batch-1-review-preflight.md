# Batch 1 Review Preflight · 4 Worker 验收预案

> 本文档定义 Product Hardening Phase 1 Batch 1 四轨 `READY-FOR-X-REVIEW` 信号到达后
> 主 CLI 的 APPROVE / REJECT-V2 判决标准。写于 2026-04-24，4 worker 预计 7-10 天内陆续触达 READY。
> 信号到达时主 CLI 1-2 小时内判决，本文档是"判决表"而非"调查表"。

---

## §0 导言

### 0.1 映射 DoD 五层

DoD 五层（`docs/scorecard/definition-of-done.md`）落地到 4 worker 的覆盖：

| 层 | 条目数 | code-urgent | code-arch | data-foundation | evaluation | Batch 1 不覆盖（推后） |
|---|---|---|---|---|---|---|
| L0 工程基础 | 14 | L0-5/6/14（占位符扫描 + 不扁平堆叠） | L0-14（工具域收敛） | L0-7（mock 数据不进 git） | L0-2（测试覆盖率） | L0-1/4/10/11/12/13（推 Batch 2/3） |
| L1 Demo 完整 | 12 | L1-1/11（archive 6 路由 + handoff 预填） | 不覆盖 | L1-10（Mock 模式底座） | 不覆盖 | 大部分推 Batch 2（前端视觉验收） |
| L2 合规 | 15 | L2-4/5（QC Blocker + 占位符 0 残留） | L2-1/2/3/6（Evidence 三阶段） | L2-14（数据分级标签，随 schema 落） | L2-1/2（evidence_rate / halluc 指标定义） | L2-7~15（reason code / 审计日志推 Batch 2/3） |
| L3 客户 POC | 12 | L3-6（Mock/Web 双模） | L3-8（feedback 飞轮自动化） | L3-1 的数据前置 | L3-1/2/3/4（基线跑分 + 回归） | L3-5/7/9/10/11/12（P95 / E2E / 模型卡片推 Batch 2/3） |
| L4 商业交付 | 8 | 不覆盖 | 不覆盖 | 不覆盖 | 不覆盖 | 全量推后 |

**Batch 1 交付硬边界**：4 worker 合并完等于"L0 过大半 + L2 零幻觉底座立起来 + L3 评估基线立起来"，但还够不到"L1 Demo 可对外演示"。演示化是 Batch 2 议题。

### 0.2 验收顺序（关键）

**必须串行 review**，不要 4 worker 同时接 signal 乱 rebase：

1. **code-urgent 最先**（独立 + Task 0 archive 归位是前端编译前置，影响所有后续手动验证）
2. **data-foundation 次**（独立，schema YAML 是 evaluation 消费输入）
3. **code-arch 第三**（依赖 code-urgent 的 archive 归位产物 + data-foundation schema 形态对齐 `evidence_trail` 字段）
4. **evaluation 最后**（依赖 code-arch 的 `shared/evidence/protocol.py` 定义的 `evidence_trail` schema，以及 data-foundation 的 mock 数据 shape）

若 evaluation 先到达 signal，主 CLI **先读 diff 但暂缓 APPROVE**，等 code-arch 合流后再 rebase 重验。

### 0.3 红线（所有 worker 共用，违反即 REJECT-V2 不讨论）

| 红线 | 判定 |
|---|---|
| 不编字段（填不了标"未能自动填写"） | grep 代码/输出，任何伪造数字 → REJECT |
| 不写关键词/正则黑名单兜底幻觉 | grep 新增 regex 是否用于"防幻觉"而非结构识别 → REJECT |
| 不绕 decisions-log | 任何超 onboarding scope 的决定未走 RFC/Q-NNN → REJECT |
| 红区未走 RFC（`financial_analyzer.py` / `quality_scorer.py` / `truth_fill.py` / `web/src/lib/store/*`） | diff 命中红区 → REJECT |
| commit 缺 Signal trailer | `git log --format=%B` 未见 `Signal: xxx-DONE` → REJECT |
| 动 Agent6 v16 pipeline 行为（跑分数字变） | evaluation Task B 比对 v16 结果 > 1% 漂移 → REJECT |
| 真实客户数据入 git | grep `企业名 / 身份证 / 金额` 真值 → REJECT + 事故复盘 |

### 0.4 已知风险 · 预拦 Q-024 / Q-025（evaluation worker 专用）

Preflight 审计发现 `docs/onboarding/evaluation-phase-1.md` 与仓库现状冲突，worker 粘 GO prompt 开 Task A 就会踩。已同批写入 `decisions-log.md` Q-024/A-024 + Q-025/A-025，**路径对 evaluation worker 先于 onboarding 字面生效**：

- **Q-024 evaluation 路径冲突**：`evaluation/runner/base_evaluator.py` ABC 骨架已生产就绪（182 行，agent2/4/6 adapter 已验证），Task B **不另起**，只在 `evaluation/runner/adapters/` 下**补 agent1_channel / agent3_credit / agent5_compliance 三个 adapter**。CLI 入口用 `py -m evaluation.runner --agent <id>`
- **Q-025 rubric schema 兼容**：新写 YAML（agent1/2/3/4/5）一律按新 schema `description / method / baseline_target / blocker_threshold`；`agent6_report.yaml` **保留** `desc / target` 老字段（v16 pipeline 继续读）并**追加**新字段做双写；`BaseEvaluator._metrics_config()` 实现 fallback：优先读新字段，退回到老字段解析

其他 3 worker（code-urgent / code-arch / data-foundation）**不受影响**，路径不重叠。

**evaluation worker GO prompt 必须增强**：ACK 后、Task A 开工前加一步 `git fetch origin chore/l0-infra && git log origin/chore/l0-infra -5` 查 Q-024/A-024 + Q-025/A-025（见主 CLI 生成的"增强版 GO prompt"）。

---

## §1 code-urgent 验收预案

### 1.1 Task 清单

| Task | Signal | 核心交付物 |
|---|---|---|
| 0 | `ARCHIVE-WORKSPACE-REHOMED` | `web/src/app/archive/*/_components/*Workspace.tsx` × 6 + 缺失 api client / shared 组件 |
| A | `CREDIT-FINANCIAL-ANALYZER-INTEGRATED` | `agent_credit/scoring_model_corporate.py` `_score_financial` 改调 `financial_analyzer.format_for_prompt()` · `agent_credit/advisor_formatter.py` 消费三件套 |
| B | `QC-PLACEHOLDER-GUARD-5AGENTS-DONE` | `shared/qc/placeholder_guard.py` + 5 Agent 输出前挂载 + `tests/test_placeholder_guard.py` |
| C | `AGENT2-AGENT4-API-WIRED` | `agent_alert/api.py` + `agent_riskctrl/api.py` 新建 + `api_server.py:187-188` TODO 解除 |

### 1.2 硬指标清单（13 项）

| # | 指标 | 阈值 | 判定工具 |
|---|---|---|---|
| CU-1 | 6 个 `/archive/[agent]` 路由能打开 | 全绿无 import error | `cd web && npm run dev` 手访问 |
| CU-2 | tsc 无错 | 0 error | `cd web && npx tsc --noEmit` |
| CU-3 | Task 0 diff 只在 `web/src/app/archive/` + 必要 lib/components shim | 无其他目录漂移 | `git diff --name-only chore/l0-infra..` |
| CU-4 | Agent3 财务比率与 Agent6 跑同一组财报误差 | < 0.01% | 取 `samples/经纬测绘_对公成稿A.docx` 分别跑 v16 pipeline（Agent6）与 agent_credit 决策链（Agent3），对比 `financial_analyzer` 注入结果中 `current_ratio/debt_ratio/roe` 等比率字段 |
| CU-5 | Agent3 prompt 不含"请计算流动比率/资产负债率"类让 LLM 算的指令 | 0 命中 | `grep -r "计算.*比率\|计算.*负债率" agent_credit/` |
| CU-6 | 5 Agent 故意喂 `[待补充]` mock 全被 QC 拦截 | 5/5 | `py -m pytest tests/test_placeholder_guard.py -v` |
| CU-7 | 正常输出不误报 | 0 误报 | 同上 tests 覆盖 negative case |
| CU-8 | `shared/qc/placeholder_guard.py` 有 `scan(text) -> list[str]` 接口 | 函数签名存在 | `py -c "from shared.qc.placeholder_guard import scan; print(scan('[待补充]'))"` |
| CU-9 | `api_server.py` 启动显示 6/6 Agent sub-app 挂载 | log 含 "Agent2 RiskCtrl" + "Agent4 Alert" | `py scripts/start_uvicorn.py` 看启动 log |
| CU-10 | `/api/riskctrl/dsl_gen` SSE 能流 | 首字节 ≤ 3s | `curl -N -X POST http://127.0.0.1:8000/api/riskctrl/dsl_gen -H "Content-Type: application/json" -d '{}'` |
| CU-11 | `/api/alert/scan` SSE 能流 | 首字节 ≤ 3s | `curl -N -X POST http://127.0.0.1:8000/api/alert/scan -H "Content-Type: application/json" -d '{}'` |
| CU-12 | 所有修改归属正确（不动 Agent6 / financial_analyzer / lib/store） | diff 不命中 | `git diff --name-only` |
| CU-13 | ruff clean | 0 E722/BLE001 | `ruff check agent_credit/ agent_alert/ agent_riskctrl/ shared/qc/` |

### 1.3 自动化验收命令

```bash
# 1. archive 归位（Task 0）
cd "D:/claude code/credit_report_agent_work" && git checkout feat/code-urgent
cd web && npm install && npx tsc --noEmit && npm run build
# 另起窗口
cd web && npm run dev
# 浏览器打开 http://localhost:3000/archive/channel|credit|alert|compliance|report|riskctrl 逐个点

# 2. §3.1 反模式修复（Task A）
grep -rn "流动比率\|资产负债率\|计算.*比率" agent_credit/ | grep -v "#" | grep -v "format_for_prompt"
# 期望：0 命中 LLM prompt 体；只有注释或调用 financial_analyzer

# 财务比率一致性对比
py v16_pipeline.py --source samples/经纬测绘_对公成稿A.docx --material samples --out /tmp/v16_fin.json
# 按 agent_credit 现行 CLI 入口跑 Agent3 决策链（参考 agent_credit/app.py 或 api.py）输出到 /tmp/credit_fin.json
# py -c "import json; a=json.load(open('/tmp/v16_fin.json')); b=json.load(open('/tmp/credit_fin.json')); ..." 比对 financial_analyzer 产出字段

# 3. 占位符 QC（Task B）
py -m pytest tests/test_placeholder_guard.py -v
py -c "from shared.qc.placeholder_guard import scan; print(scan('张 XX 营收 [待补充]'))"

# 4. Agent2/4 api wiring（Task C）
py scripts/start_uvicorn.py &
sleep 5
curl -N -X POST http://127.0.0.1:8000/api/riskctrl/dsl_gen -H "Content-Type: application/json" -d '{"requirement":"test"}'
curl -N -X POST http://127.0.0.1:8000/api/alert/scan -H "Content-Type: application/json" -d '{"scope":"test"}'
curl -s http://127.0.0.1:8000/api/riskctrl/health
curl -s http://127.0.0.1:8000/api/alert/health

# 5. 静态检查
ruff check agent_credit/ agent_alert/ agent_riskctrl/ shared/qc/
# 若项目根有 mypy.ini / pyproject.toml [tool.mypy] 则跑 mypy；当前未见配置，静态检查以 ruff 为准
```

### 1.4 人工抽检点（4 项）

1. **6 个 archive 路由渲染质感**：不只是"不报错"，每个页面至少有一个核心交互元件（对话框 / 报表区 / 按钮触发）能点，不是纯空白。对比 `feat/agent6-dialog-shell` 上的形态，确认没退化。
2. **占位符 QC false-positive 抽检**：故意给一份**真实有中文人名 + 数字区间 + 三点省略**的合法报表段落，看是否误拦。比如"张伟审批金额为 100-500 万区间，备注：见附件..."——这不是占位符，是正常文字。
3. **Agent3 消费 `financial_analyzer` 的证据注入形态**：读 `advisor_formatter.py` diff，确认是通过 `format_for_prompt()` 三件套传入（确定性财务 + 行业基准 + 材料锚定），不是只把 `financial_analyzer` 结果字符串拼进 prompt。
4. **Agent2/4 SSE 事件类型**：`curl` 抓到的 event stream 是否符合项目惯用事件名（参考 `agent_report/api.py` / `agent_channel/api.py` 现有 event 类型），不自创 event。

### 1.5 REJECT-V2 触发条件

- **F1**：`npm run build` 失败 / 任一 archive 路由 500 / tsc 报错 → 写 `docs/onboarding/code-urgent-phase-1-v2.md`，指明"Task 0 archive 归位未闭环，补齐具体缺失文件清单"+ `Signal: PHASE-1-CODE-URGENT-REJECTED-V2-DISPATCHED`
- **F2**：Agent3 财务比率对比误差 ≥ 0.01% 或 prompt 仍含"计算比率"指令 → v2 明确要求"完整 trace 一次 financial_analyzer.format_for_prompt 调用链"
- **F3**：5 Agent 任一未挂 placeholder_guard 或 false-positive > 5% → v2 要求补 regex 白名单机制（但**仍禁**用业务关键词黑名单）
- **F4**：Agent2/4 SSE 流断 / api_server log 仍只有 4 个 Agent → v2 要求补健康检查端点和事件命名对齐
- **F5**：越红线（动 `financial_analyzer.py` / `web/src/lib/store/` / Agent6）→ 直接 REJECT 不讨论，commit 作废重开

---

## §2 data-foundation 验收预案

> **v2 版**（2026-04-24 rewrite · 原 yaml 形态 DF-1~13 作废）。
> 批次已判 REJECT-V2(Q-028 / A-028)——v1 产物形态错(yaml 把答案喂到模型嘴边)。
> v2 worker 在 `D:/claude code/demo-data-foundation` worktree 覆盖式返工,Phase 1 交付 3 组 mock(深柱 5 家 + Agent1 内部 KB + Agent5 内部制度库),**不做宽基 100 家**。
> 判决依据:`docs/onboarding/data-foundation-phase-1-v2.md` + `docs/handoff/data-foundation-v2-kickoff.md` + CLAUDE.md §3.5 反结果导向 5 原则。

### 2.1 v2 Task 清单

| Task | Signal | 核心交付物 |
|---|---|---|
| A | `DATA-SCHEMA-V2-DONE`(embedded `DATA-LEGACY-PURGED`) | 删 v1 老产物(`wide-base/` / `schemas/` / `deep-pillar/shortlist.md` / `deep-pillar/pits/`)+ 新建 `data/mock/{deep-pillar,channel-kb,compliance-kb}/` 空目录骨架 + `data/mock/README.md` |
| B | `DATA-DEEP-PILLAR-5-DONE` | `data/mock/deep-pillar/DP001_<脱敏名>/` ~ `DP005_<脱敏名>/` · 每家 20-40 份异构材料(6 大类:资质/场所/财务/纳税/银行流水/补充)· 命名混乱 · 跨 2022-2025 · 三方数字合理矛盾 · 零答案字段 |
| C | `CHANNEL-KB-DONE` | `data/mock/channel-kb/{historical-clients, marketing-preferences, product-catalog}/` · 10-15 家历史画像 + 3-5 份营销倾向 docx + 1 份产品目录 · **不含**外部候选企业池 |
| D | `COMPLIANCE-KB-DONE` | `data/mock/compliance-kb/{credit-sop, customer-admission, kyc-aml, risk-preference, review-checklists}/` · 仿银行内部 SOP 体例 docx · **不含**外部新政策 |
| E | `READY-FOR-DATA-FOUNDATION-B1-V2-REVIEW` | 全轨 ACK |

入口 Signal:`PRODUCT-HARDENING-BATCH-1-V2-ACK`(worker resume doc-only commit trailer)

### 2.2 硬指标清单(15 项 · DF-V2-1~15)

| # | 指标 | 阈值 | 判定 |
|---|---|---|---|
| DF-V2-1 | 老产物全删 | `wide-base/` / `schemas/` / `deep-pillar/shortlist.md` / `deep-pillar/pits/` 全部 `git status` 显示 `deleted:` · 不留残余 | `git log --diff-filter=D --name-only feat/data-foundation` 命中这 5 处 |
| DF-V2-2 | 新目录骨架齐 | `data/mock/deep-pillar/` + `channel-kb/` 3 子目录(historical-clients / marketing-preferences / product-catalog)+ `compliance-kb/` 5 子目录(credit-sop / customer-admission / kyc-aml / risk-preference / review-checklists)全部存在 | `ls data/mock/` 目录树对齐 |
| DF-V2-3 | 5 家深柱文件夹存在 | `DP001_* ~ DP005_*` 5 个文件夹 · 脱敏名前缀 `DP00N_` 规则统一 | `ls data/mock/deep-pillar/` 计数 = 5 |
| DF-V2-4 | 每家材料份数 | 20 ≤ 份数 ≤ 40 / 每家 | `find data/mock/deep-pillar/DP00N_*/ -type f \| wc -l` 每家结果在区间 |
| DF-V2-5 | 扩展名多样性 | 每家 ≥ 3 种扩展名(pdf / xlsx / docx 必居其二,可追加 xls / jpg) | `find data/mock/deep-pillar/DP00N_*/ -type f \| awk -F. '{print $NF}' \| sort -u` 每家 ≥ 3 |
| DF-V2-6 | 6 大类子目录覆盖 | 每家包含资质 / 场所 / 财务 / 纳税 / 银行流水 / 补充 6 大类材料(子目录或序号前缀形式均可,至少能 `ls` 识别) | 人工读 `ls -R` 输出逐家核 |
| DF-V2-7 | 命名混乱度 | 每家内同时出现 ≥ 2 种命名风格(如"00、xxx.xlsx" + "1、xxx.pdf" + "审计报告2023年-xxx.pdf"无序号直写)· **禁止**统一规整命名(`DP001_01_营业执照.pdf` 这种 = 结果导向偷懒) | 抽 3 家列出所有文件名 · 人工判 |
| DF-V2-8 | 多年跨度 | 时间戳覆盖 ≥ 3 年份(2022/2023/2024/2025 中至少 3 个)· 不强求每家齐全 | `ls` 每家 + grep 文件名里 20XX 年份字符 |
| DF-V2-9 | 三方数字合理矛盾 | 财报 vs 申报表 vs 流水三方营收量级一致但具体数字不完全对齐(例:4800/5000/5200 万)· **不得清洗成三方完全对齐** | 抽 2 家 read 关键文件(财报 xlsx + 申报表 pdf + 流水 pdf)人工核 |
| DF-V2-10 | 零答案字段 | **0 命中**以下字段名在任何产物(deep-pillar + channel-kb + compliance-kb + README):`difficulty` / `match_score` / `risk_level` / `tags` / `benchmark_ref` / `conflict_points` / `optimal_dsl` | `grep -rE "difficulty\|match_score\|risk_level\|tags:\|benchmark_ref\|conflict_points\|optimal_dsl" data/mock/` 结果为空 |
| DF-V2-11 | channel-kb 不含外部候选 | `historical-clients/` 仅"已成交客户" · 目录/文件名不含 `candidate` / `候选企业` / `候选池` / `外部企业` / `potential_client` 等词 · 0 命中 | `find data/mock/channel-kb/ -iname "*candidate*" -o -iname "*候选*" -o -iname "*外部企业*" -o -iname "*potential*"` 结果为空 |
| DF-V2-12 | compliance-kb 不含外部政策 | 目录/文件名不含 `银保监` / `央行` / `国务院` / `CBIRC` / `PBOC` / `NFRA` / `gov.cn` 等官方机构字样 · 不含 `2026新规` / `xx号令` / `xx通知(外发)` 等外部政策文件命名 · 0 命中 | `find data/mock/compliance-kb/ -iname "*银保监*" -o -iname "*央行*" -o -iname "*国务院*" -o -iname "*CBIRC*" -o -iname "*PBOC*" -o -iname "*NFRA*"` 结果为空 |
| DF-V2-13 | 脱敏企业名 | PM 随机抽 5 家 google 搜,**不得命中真实存续企业**(避免法律风险)· 企业名风格允许"行业+地区+编号"自造拼接 | PM 亲自 sign off(主 CLI 不代签) |
| DF-V2-14 | 不越界 | 仅动 `data/mock/` + `docs/` · 不动 `agent_*/` / `web/` / `shared/` / `evaluation/` / `scripts/` | `git diff --name-only chore/l0-infra..feat/data-foundation \| grep -vE "^(data/mock/\|docs/)"` 期望空 |
| DF-V2-15 | 反结果导向 5 原则合规 | 盲测法(零答案字段)/ 难度分层(PM 内部 1/2/1/1 档,**产物不写**)/ 真实来源锚定(中锐形态)/ 脱敏再造 / 环境边界(Agent1/5 不 mock 外部)五条**全 ✓** | 主 CLI 逐条 review(见 §2.4) |

### 2.3 自动化验收命令

```bash
cd "D:/claude code/demo-data-foundation" && git checkout feat/data-foundation && git pull

# 1. 老产物是否全删(DF-V2-1)
git log --diff-filter=D --name-only feat/data-foundation | grep -E "wide-base/|schemas/|deep-pillar/shortlist.md|deep-pillar/pits/"
# 期望:5 处都命中

# 2. 新目录骨架齐(DF-V2-2)
ls -d data/mock/deep-pillar/ data/mock/channel-kb/ data/mock/compliance-kb/
ls -d data/mock/channel-kb/{historical-clients,marketing-preferences,product-catalog}
ls -d data/mock/compliance-kb/{credit-sop,customer-admission,kyc-aml,risk-preference,review-checklists}

# 3. 5 家深柱文件夹(DF-V2-3)
ls -d data/mock/deep-pillar/DP00* | wc -l   # 期望 5

# 4. 每家份数 + 扩展名多样性(DF-V2-4 / DF-V2-5)
for dir in data/mock/deep-pillar/DP00*/; do
  cnt=$(find "$dir" -type f | wc -l)
  exts=$(find "$dir" -type f | awk -F. '{print tolower($NF)}' | sort -u | wc -l)
  echo "$dir files=$cnt exts=$exts"
done
# 期望每家:20 ≤ files ≤ 40 · exts ≥ 3

# 5. 零答案字段(DF-V2-10)· 核心红线
grep -rE "difficulty|match_score|risk_level|tags:|benchmark_ref|conflict_points|optimal_dsl" data/mock/
# 期望:空(任何命中都 REJECT-V3)

# 6. channel-kb 不含外部候选(DF-V2-11)
find data/mock/channel-kb/ \( -iname "*candidate*" -o -iname "*候选*" -o -iname "*外部企业*" -o -iname "*potential*" \)
# 期望:空

# 7. compliance-kb 不含外部政策(DF-V2-12)
find data/mock/compliance-kb/ \( -iname "*银保监*" -o -iname "*央行*" -o -iname "*国务院*" -o -iname "*CBIRC*" -o -iname "*PBOC*" -o -iname "*NFRA*" -o -iname "*gov.cn*" \)
# 期望:空

# 8. 多年跨度抽检(DF-V2-8)
for dir in data/mock/deep-pillar/DP00*/; do
  years=$(find "$dir" -type f | grep -oE "20(22|23|24|25)" | sort -u | wc -l)
  echo "$dir years_covered=$years"
done
# 期望:每家 years ≥ 3

# 9. 不越界(DF-V2-14)
git diff --name-only chore/l0-infra..feat/data-foundation | grep -vE "^(data/mock/|docs/)" | wc -l
# 期望:0

# 10. README 可读性(人工配合,见 §2.4)
cat data/mock/README.md | head -40
```

### 2.4 人工抽检点(5 项)

1. **反结果导向 5 原则逐条核**(v2 新增第 5 条 · **最关键**):
   - 盲测法:`grep -rE "difficulty|tags:|benchmark_ref"` 为空 ✓/✗(DF-V2-10 机控 + 人工 double check README 措辞不暗示档位)
   - 难度分层:PM 内部维护 1/2/1/1 档位(easy / medium / hard / extreme),**产物里不得出现档位字面值** ✓/✗
   - 真实来源锚定:随机挑 3 家 deep-pillar,对照 `D:\刘野\众安\新建文件夹\2026.3.25续贷材料` 中锐续贷包看命名风格 / 6 大类分布 / 扫描件形态是否同源仿真,不能整洁过度 ✓/✗
   - 脱敏再造:PM 随机抽 5 家企业名 google 搜,不能是真实存续企业 ✓/✗(DF-V2-13 · **必须 PM 签字**,主 CLI 不代签)
   - **环境边界** 🆕:channel-kb 不出现候选企业池 + compliance-kb 不出现外部政策 ✓/✗(DF-V2-11 / DF-V2-12 机控 + 人工 read README 确认消费方约束写清)
2. **命名真实度对比中锐包**:抽 1 家 deep-pillar(如 DP003),列出所有文件名,与 `D:\刘野\众安\新建文件夹\2026.3.25续贷材料` 下真实客户包命名对比——序号前缀混乱度 / 中文日期混用 / 扩展名分布 / 扫描件占比是否同量级。不能过度"整洁化"。
3. **三方数字矛盾抽检**:抽 2 家 deep-pillar,read 财报 xlsx + 增值税申报表 pdf + 银行流水 3 家文件,核营收 / 所得税 / 进项量级是否一致但具体数字**不完全对齐**(4800 vs 5000 vs 5200 万级别差异)。若三方清洗到一致数字 = 把答案喂嘴边,F3 触发。
4. **内部 KB / 制度库不越界**:
   - channel-kb:read `historical-clients/` 5 份画像,确认全部"已成交客户"立场(有授信额度 / 签约产品 / 历史业务特征),不是"外部候选评估池"口吻
   - compliance-kb:read 每个子目录 1 份 docx,确认"银行内部 SOP"体例(文号 + 章节编号 + 修订日期 + 密级水印),不含"银保监 2026 年 X 号文"这类外部政策
5. **格式仿真度 + README 可读性**:
   - deep-pillar 扫描件 pdf 是否有 OCR 可识别文字但格式不齐(审计报告 / 完税证明首选此形态)
   - xlsx 是否混行合并 / 部分列空白 / sheet 名五花八门
   - `data/mock/README.md` 新人 10 分钟内读完能理解"3 组 mock 消费方对应 / 为什么没有外部候选池 / 为什么没有外部政策"三件事

### 2.5 REJECT-V3 触发条件

- **F1 · 再犯 yaml 形态**:新增任何 `companies.yaml` / `entities.yaml` / `prefilled.yaml` / `shortlist.md`(或等价结构化清洗文件)→ 直接 REJECT-V3 + commit 作废 + 事故复盘(与 Q-028 同根错误)
- **F2 · 出现答案字段**:grep 命中 `difficulty` / `match_score` / `risk_level` / `tags` / `benchmark_ref` / `conflict_points` / `optimal_dsl` 任一 → v3 要求全量洗 + 重审产物 · worker 不得辩驳"只是注释"
- **F3 · 三方数字太整齐**:财报 / 申报表 / 流水 营收数字完全一致(清洗到三方对齐)→ v3 要求按 `±3-8%` 合理幅度重播数字 · 保量级不保完全一致
- **F4 · 违反环境边界(新第 5 原则)**:channel-kb 出现候选企业池 / compliance-kb 出现外部政策文件 → 直接 REJECT-V3 + 重审反 5 原则培训 · 同时触发 CLAUDE.md §3.5 培训 gap 复盘
- **F5 · 越界业务代码**:diff 命中 `agent_*/` / `web/` / `shared/` / `evaluation/` / `scripts/` → 直接 REJECT + commit 作废 · 与 v1 F4 等同红线

REJECT-V3 文档路径:`docs/onboarding/data-foundation-phase-1-v3.md` + `Signal: PHASE-1-DATA-FOUNDATION-REJECTED-V3-DISPATCHED`(若触发)

---

## §3 code-arch 验收预案

### 3.1 Task 清单

| Task | Signal | 核心交付物 |
|---|---|---|
| A | `TOOL-DOMAIN-SPLIT-DONE` | 5 Agent 目录重组按 §3.2 子域 · `agent_<name>/domains/*.py` 或等价组织 · `__init__.py` 导出路径更新 |
| B | `EVIDENCE-PROTOCOL-5AGENTS-DONE` | `shared/evidence/protocol.py` 基类 + 5 Agent 继承（`agent_*/evidence_pipeline.py`）+ `agent_report/section_generator.py` 结构对齐 |
| C | `FEEDBACK-FEWSHOT-PIPELINE-DONE` | `scripts/feedback_to_fewshot.py` + `scripts/inject_fewshot_to_prompts.py` + `docs/runbook/feedback-flywheel.md` |

### 3.2 硬指标清单（12 项）

| # | 指标 | 阈值 | 判定 |
|---|---|---|---|
| CA-1 | 5 Agent 工具函数命名符合 `<域>_<动作>` | ≥ 90% | `grep -rn "^def " agent_channel/ agent_credit/ agent_alert/ agent_compliance/ agent_riskctrl/` + 人工分子计数 |
| CA-2 | 每 Agent 子域对齐 CLAUDE.md §3.2 表格 | 全匹配 | 人工对照 |
| CA-3 | 跨域不直调其他域内部实现 | 0 命中 | 人工 review import 语句 |
| CA-4 | `shared/evidence/protocol.py` 基类有 `collect()` / `generate_grounded()` / `self_audit()` 抽象方法 | 3/3 | `grep -n "def collect\|def generate_grounded\|def self_audit" shared/evidence/protocol.py` |
| CA-5 | 5 Agent `evidence_pipeline.py` 继承基类 | 5/5 | `grep -l "EvidenceFirstPipeline" agent_channel/ agent_credit/ agent_alert/ agent_compliance/ agent_riskctrl/` |
| CA-6 | 每 Agent 输出带 `evidence_trail` 结构化字段 | 字段存在且非空 | `curl` 各 Agent `/api/<name>/` SSE 端点抓最终 payload，grep `"evidence_trail"` 存在 |
| CA-7 | 自审阶段检出后能标"未能自动填写" | 至少 1 个 case | pytest 用例 |
| CA-8 | Agent6 v16 pipeline 跑分与重构前一致 | 误差 < 1% | `py v16_pipeline.py --source samples/经纬测绘_对公成稿A.docx --material samples` 跑分对比 |
| CA-9 | `scripts/feedback_to_fewshot.py` dry-run 能跑通 | exit 0 | 埋 10 条 `data/feedback/2026-04-23.jsonl` 测试样本后执行 |
| CA-10 | 能在某 Agent `prompts.py` 看到新增 few-shot 段（inject 后） | diff 可见 | `git diff agent_*/prompts.py` |
| CA-11 | 飞轮 runbook 有"多久跑一次 + PM review 哪些节点"SOP | 文档齐 | 人工读 `docs/runbook/feedback-flywheel.md` |
| CA-12 | 不动 Agent6 行为 / 红区模块 | 0 命中 | `git diff --name-only` 不含 `financial_analyzer.py` / `quality_scorer.py` / `truth_fill.py` / `web/**` |

### 3.3 自动化验收命令

```bash
cd "D:/claude code/credit_report_agent_work" && git checkout feat/code-arch

# 1. 工具域命名抽检（Task A）
grep -rn "^def " agent_channel/ agent_credit/ agent_alert/ agent_compliance/ agent_riskctrl/ \
  | grep -v "__" \
  | awk -F: '{print $3}' \
  | awk '{print $2}' \
  | sort -u > /tmp/func_names.txt
# 人工核命名：<域>_<动作> 占比 ≥ 90%

# 2. Evidence 基类（Task B）
grep -n "def collect\|def generate_grounded\|def self_audit" shared/evidence/protocol.py
ls agent_*/evidence_pipeline.py   # 期望 5 个

# 3. Agent6 行为不变（Task B 最关键的回归）
py v16_pipeline.py --source samples/经纬测绘_对公成稿A.docx --material samples --out /tmp/v16_after.json
# 对比 chore/l0-infra baseline：
git stash && git checkout chore/l0-infra
py v16_pipeline.py --source samples/经纬测绘_对公成稿A.docx --material samples --out /tmp/v16_before.json
git checkout feat/code-arch && git stash pop 2>/dev/null || true
py -c "
import json
b = json.load(open('/tmp/v16_before.json'))
a = json.load(open('/tmp/v16_after.json'))
# 对比 evidence_rate / halluc / unfilled_marker / quality_score_total 等关键数字
for k in ['evidence_rate','hallucination_rate','unfilled_marker','quality_score_total']:
    if k in b and k in a:
        print(k, b[k], a[k], abs(b[k]-a[k]) < 0.01)
"

# 4. 飞轮脚本（Task C）
mkdir -p data/feedback
# 埋 10 条样本 feedback jsonl（格式按 §6 协议：session_id / agent / field_path / original / revised / timestamp）
py -c "
import json, datetime
with open('data/feedback/2026-04-23.jsonl','w',encoding='utf-8') as f:
    for i in range(10):
        f.write(json.dumps({'session_id':f'test-{i}','agent':'credit','field_path':'risk_opinion','original':'低风险','revised':'中等风险，关联交易需复核','ts':datetime.datetime.now().isoformat()},ensure_ascii=False)+'\n')
"
py scripts/feedback_to_fewshot.py --agent credit --dry-run
py scripts/inject_fewshot_to_prompts.py --agent credit --dry-run
git diff agent_credit/prompts.py   # dry-run 理论不动文件，实跑后可见 diff

# 5. 红区不越界
git diff --name-only chore/l0-infra..feat/code-arch | grep -E "financial_analyzer|quality_scorer|truth_fill|web/" | wc -l
# 期望 0
```

### 3.4 人工抽检点（4 项）

1. **基类设计合理性**：`shared/evidence/protocol.py` 的三阶段抽象方法签名是否与 Agent6 `section_generator.py` 现有实现形态兼容（不是强行"套壳" Agent6 独有的 v16 三阶段）。命名规范 onboarding 未明——建议抽检时确认 base class 名为 `EvidenceFirstPipeline`（Task B 指标 CA-5 默认假设）或 worker 另选名字是否在 RFC 声明过。
2. **工具域边界主观判断**：Agent1 的"信号搜索域"和"企业画像域"有些函数会跨边界（一个函数既搜索又构画像），确认 worker 如何切。建议 sample 3 个边界函数看判断理由。
3. **飞轮脚本幂等性**：同一批 feedback 连跑两次 `inject_fewshot_to_prompts.py`，不应产生重复 few-shot（应去重 / merge）。
4. **Agent6 `section_generator.py` 结构对齐"副作用评估"**：onboarding 说"不改行为，只做结构对齐"——但继承基类必然改 import / 可能改签名，抽检改动是否可 diff 到"只是加了继承声明和抽象方法实现"，不是重写逻辑。

### 3.5 REJECT-V2 触发条件

- **F1**：Agent6 v16 跑分漂移 ≥ 1% → 直接 REJECT（踩了最硬红线）→ v2 要求"纯结构对齐，0 行为改动"
- **F2**：工具域命名符合率 < 90% → v2 要求补命名规范清单并全量改
- **F3**：`shared/evidence/protocol.py` 缺任一抽象方法 → v2 要求按 RFC `20260418-v16-llm-abstraction-upgrade.md` 形态补齐
- **F4**：飞轮脚本非 dry-run 安全（未 `--dry-run` 就默认写盘）→ v2 要求 dry-run default + confirm flag
- **F5**：任一 Agent 输出无 `evidence_trail` 字段 → v2 要求补齐 + tests 覆盖

REJECT-V2 文档：`docs/onboarding/code-arch-phase-1-v2.md` + `Signal: PHASE-1-CODE-ARCH-REJECTED-V2-DISPATCHED`

---

## §4 evaluation 验收预案

### 4.1 Task 清单

| Task | Signal | 核心交付物 |
|---|---|---|
| A | `EVAL-RUBRIC-YAML-6AGENT-DONE` | `evaluation/agent{1..6}_*.yaml`（覆盖 6 Agent，Agent6 已存在对齐格式即可）+ `evaluation/README.md` |
| B | `EVAL-RUNNER-BASE-DONE` | `evaluation/base_evaluator.py` + `evaluation/adapters/*.py` × 6 + `evaluation/cli.py` |
| C | `EVAL-BASELINE-FIRST-RUN` | `evaluation/baselines/2026-04-23-first-run.json` + `.md` |

**路径规范（A-024 已定）**：`evaluation/runner/base_evaluator.py` ABC 生产就绪 + agent2/4/6 adapter 已实现。Task B 只补 `evaluation/runner/adapters/agent1_channel.py` / `agent3_credit.py` / `agent5_compliance.py` 三个 adapter；**不新建** `evaluation/base_evaluator.py` 或 `evaluation/cli.py`。CLI 入口 `py -m evaluation.runner --agent <id>`。详见 `docs/handoff/decisions-log.md` Q-024/A-024。

### 4.2 硬指标清单（13 项）

| # | 指标 | 阈值 | 判定 |
|---|---|---|---|
| EV-1 | 6 份 rubric YAML yamllint 通过 | 0 error | `yamllint evaluation/*.yaml` |
| EV-2 | 每份 YAML 10 条指标（5 通用 + 5 领域） | 严格 10 | grep counts |
| EV-3 | 每条指标有 `method` + `baseline_target` + `blocker_threshold` 三字段（**agent1/2/3/4/5** 新 YAML 严格；**agent6_report.yaml** 豁免 - 保留老 `desc/target` + 追加新字段做双写，见 A-025） | agent1-5 严格 3/3 / agent6 新老双写 | YAML schema 校验 + grep 老字段是否保留 |
| EV-4 | 5 通用指标名称在 6 YAML 统一 | 命名一致 | grep cross-file |
| EV-5 | 领域指标覆盖 CLAUDE.md §5.2 列举（财务比率正确率 / 红线判定 / 信号多样性 / 政策覆盖等） | 全覆盖 | 人工核 |
| EV-6 | `base_evaluator` CLI 跑 Agent6 与 v16 pipeline 数字一致 | 误差 < 1% | 跑分对比 |
| EV-7 | 6 Agent adapter 全跑通（不 crash） | 6/6 | CLI 逐个调 |
| EV-8 | 首轮 baseline JSON 结构化可 parse | JSON valid + 字段齐 | `py -c "import json; json.load(open('evaluation/baselines/2026-04-23-first-run.json'))"` |
| EV-9 | 6 Agent × 10 指标 = 60 数值 JSON 全覆盖 | 60 数值点 | py count |
| EV-10 | baseline `.md` 含每 Agent 3 条最大 gap + 改进建议 | 18 条建议 | 人工核 |
| EV-11 | 不改 `v16_pipeline.py` / `v16_generator.py` / `agent_*/` 业务代码 | 0 命中 | `git diff --name-only` 不含 v16_* / agent_* 核心 |
| EV-12 | 财务比率正确率指标与 `financial_analyzer` 比对一致 | ≥ 99% | 抽 Agent3/6 的 financial_ratio_consistency 跑 |
| EV-13 | baseline JSON 能被至少一种图表工具 parse（plotly/matplotlib） | 脚本能跑出图 | `py -c "import json,matplotlib.pyplot as plt; d=json.load(open('evaluation/baselines/2026-04-23-first-run.json')); plt.bar([a for a in d],[d[a]['evidence_rate']['value'] for a in d]); plt.savefig('/tmp/eval_chart.png')"`（字段路径按最终 schema 调整） |

### 4.3 自动化验收命令

```bash
cd "D:/claude code/credit_report_agent_work" && git checkout feat/evaluation

# 1. YAML schema
yamllint evaluation/agent1_channel.yaml evaluation/agent2_riskctrl.yaml \
         evaluation/agent3_credit.yaml evaluation/agent4_alert.yaml \
         evaluation/agent5_compliance.yaml evaluation/agent6_report.yaml

# 2. 10 条指标 + 3 字段齐全
py -c "
import yaml
from pathlib import Path
for p in Path('evaluation').glob('agent*.yaml'):
    doc = yaml.safe_load(p.read_text(encoding='utf-8'))
    metrics = (doc.get('metrics', {}).get('common', []) or []) + (doc.get('metrics', {}).get('domain', []) or [])
    print(p.name, 'n_metrics=', len(metrics))
    for m in metrics:
        missing = [k for k in ['method','baseline_target','blocker_threshold'] if k not in m]
        if missing:
            print('  缺字段', m.get('name'), missing)
"
# A-025 规则：agent1-5 严格新 schema；agent6_report.yaml 双写（老 desc/target 保留 + 新字段追加）

# 3. base_evaluator CLI 跑 Agent6
# A-024 已定：CLI 入口 py -m evaluation.runner
py -m evaluation.runner --agent report --rubric evaluation/agent6_report.yaml --out /tmp/eval_report.json

# 4. Agent6 v16 一致性
py v16_pipeline.py --source samples/经纬测绘_对公成稿A.docx --material samples --out /tmp/v16.json
py -c "
import json
e = json.load(open('/tmp/eval_report.json'))
v = json.load(open('/tmp/v16.json'))
for k in ['evidence_rate','hallucination_rate','unfilled_marker','quality_score_total']:
    if k in e and k in v:
        print(k, 'eval=',e[k],'v16=',v[k],'ok=',abs(e[k]-v[k])<0.01)
"

# 5. 6 Agent adapter 全跑
for agent in channel riskctrl credit alert compliance report; do
    py -m evaluation.cli --agent $agent --samples samples/ --out /tmp/eval_$agent.json
done

# 6. 首轮 baseline 结构
py -c "
import json
d = json.load(open('evaluation/baselines/2026-04-23-first-run.json', encoding='utf-8'))
assert len(d) == 6, f'Agent 数 {len(d)} != 6'
for agent, metrics in d.items():
    assert len(metrics) == 10, f'{agent} 指标数 {len(metrics)} != 10'
print('baseline JSON 校验通过')
"

# 7. 不越界
git diff --name-only chore/l0-infra..feat/evaluation | grep -E "v16_|agent_channel/|agent_credit/|agent_alert/|agent_compliance/|agent_riskctrl/|data/mock/" | wc -l
# 期望 0
```

### 4.4 人工抽检点（4 项）

1. **rubric schema 新老字段冲突判决**：onboarding 示例用 `method/baseline_target/blocker_threshold`，现有 `agent6_report.yaml` 用 `desc/target`。worker 应该统一迁到新 schema（同时 Agent6 旧 key 保留以不破 v16 pipeline 消费）或开 RFC 说明，review 时核对是否有 RFC。
2. **领域指标定义合理性**：随机挑 2 Agent 的 5 个领域指标，看 `method` 字段是否**可代码化**（不是"人工评审通过率"这种不可自动化的）。可代码化是 PM 产品决策数字来源的前提。
3. **baseline markdown 可读性**：PM 10 分钟读完后能回答"哪个 Agent 当前最弱 / 最大 3 个 gap 是什么 / 第一步该改什么"。读不完或拿不到这三问答案 → 报告没写好。
4. **首轮数字偏乐观声明**：markdown 必须明写"本轮数字偏乐观，Batch 2 真脏数据重跑后才作为产品达标证据"（见 onboarding `warning` 段），防止 PM 误把此数据当客户 POC 证据。

### 4.5 REJECT-V2 触发条件

- **F1**：任一 YAML 缺 `method/baseline_target/blocker_threshold` 字段 → v2 要求全量补齐
- **F2**：base_evaluator 跑 Agent6 数字漂移 ≥ 1% → v2 要求"以 v16 pipeline 为 ground truth 对齐"
- **F3**：6 Agent adapter 有任一 crash → v2 要求补错误边界 + 容错
- **F4**：baseline JSON 不是 6×10 严格 schema → v2 要求结构化
- **F5**：越界动 `v16_*` / `agent_*/` 业务代码 → 直接 REJECT + commit 作废
- **F6**：worker 另起 `evaluation/base_evaluator.py` 或 `evaluation/cli.py` 违反 A-024 路径规范 → 直接 REJECT（规范已下发，抗令即违反 signal 纪律）

REJECT-V2 文档：`docs/onboarding/evaluation-phase-1-v2.md` + `Signal: PHASE-1-EVALUATION-REJECTED-V2-DISPATCHED`

---

## §5 Rebase 合流顺序 + 冲突预判

### 5.1 推荐合流顺序

1. `feat/code-urgent` → `chore/l0-infra`（独立 + archive 归位是前端手动验证前置）
2. `feat/data-foundation` → `chore/l0-infra`（独立，schema 给 evaluation 用）
3. `feat/code-arch` → `chore/l0-infra`（依赖 code-urgent 的 archive 落地；`shared/evidence/` 新增形态与 code-urgent 的 `shared/qc/` 同父目录需 rebase）
4. `feat/evaluation` → `chore/l0-infra`（依赖 code-arch 的 `shared/evidence/protocol.py` 定义的 `evidence_trail` schema，用 data-foundation 的 mock 数据输入）

### 5.2 可预判的冲突热点（6 条）

| # | 热点 | 可能冲突的 worker | 处理策略 |
|---|---|---|---|
| 1 | `shared/` 下两新目录 `shared/qc/` vs `shared/evidence/` | code-urgent + code-arch | 不同子目录不冲突，但 `shared/__init__.py` 可能同时追加 import → 手动合并 |
| 2 | `api_server.py` 挂载点 | code-urgent（挂 Agent2/4）+ 潜在 code-arch（结构重构时调整 import） | code-urgent 先合，code-arch rebase 时 accept ours |
| 3 | `agent_alert/api.py` / `agent_riskctrl/api.py` 新建 | code-urgent（新建）+ code-arch（可能因工具域重拆改动） | code-urgent 先合，code-arch 若涉及相同文件须 worker 自己 rebase（onboarding 有红线 code-arch 不抢 code-urgent 地盘 → 理论无冲突，review 时 grep 确认） |
| 4 | `agent_report/section_generator.py` | code-arch（继承基类结构对齐） | 独立改，code-arch 必须在 Agent6 v16 跑分不漂的前提下动 |
| 5 | `evaluation/` vs `evaluation/runner/` 路径 | evaluation 单轨（已由 A-024 锁定续建 runner/） | worker 严格走 `evaluation/runner/adapters/` 续建，无路径冲突；rebase 直合 |
| 6 | `agent_credit/scoring_model_corporate.py` + `advisor_formatter.py` | code-urgent（Task A 修）+ code-arch（Task A 工具域重拆可能动 agent_credit） | code-urgent 先合（短平快），code-arch rebase 时 keep code-urgent 的 _score_financial 修复，只重组目录 |

### 5.3 冲突处理默认策略

- **主 CLI 合流**：4 worker `READY` signal 全齐前，暂不并行 rebase。按 §5.1 顺序串行合流
- **单 worker REJECT-V2 期间**：继续推其他 worker 合流，REJECT 那条线独立返工
- **worker 侧 rebase**：如某 worker 需 rebase 到更新后的 `chore/l0-infra`，主 CLI 发 `Signal: REBASE-REQUIRED-FOR-<worker>` 附 base SHA，worker 自主 rebase + 回 `Signal: REBASED-CLEAN-<worker>` 后主 CLI 再拉
- **冲突责任划分**：按信号到达时间先到先拿 tree（code-urgent 为首），后来者必须兼容，不允许后来者 overwrite
- **Agent6 行为回归**：每次合流后**强制**跑 `py v16_pipeline.py --source samples/经纬测绘_对公成稿A.docx --material samples` 对比数字 < 1%。一旦漂移 → 立刻 revert 最后一次 merge，定位到具体 worker 的 F1（Agent6 红线）

---

**本文档维护者**：主 CLI（chore/l0-infra 唯一可写）
**下次更新触发**：4 worker 任一 READY 信号到达，按本文档判决；判决完 append 一段 `docs/handoff/batch-1-review-<worker>-verdict.md` 留痕
