# 演示冲刺执行日志（唯一进度真源 · Claude 决策官维护，Codex 只写被指定的行）

> 规则：每 CP 一节，判定只有 PASS / FIX / REPLAN 三种；FIX 必附修正卡；砍卡即时登记。
> 时间基准：演示日 = 2026-07-22（假定），代码冻结 = 演示日 08:00。

## 段位状态板

| Stage | 内容 | 状态 | CP 判定 | 备注 |
|---|---|---|---|---|
| Stage 1 | 后端诚信线 A5→A1→A2→A3→A4 | **完成** | CP1-R4 PASS | 五卡全 commit（A5 / 45d605b / 4185942 / 7f667cc / ab8d815） |
| Stage 2 | 前端核心 B1→B2→B3→B9→B-null | **完成** | CP2 PASS | 五卡 commit（d40751e/c97c3c2/6629688）· Wave-1 已上生产 e04507c |
| Stage 3 | 演示数据周边 B4-B8+B10+B11+B12 | **进行中** | — | 指令见「Stage 3 指令」节 |
| Stage 4 | 彩排与冻结 | 锁定 | — | 彩排报告交刘野 |

## A1 前置检查 · 演示主角企业结论（Codex 填写此节）

- 五家示例缺值统计：DP001 龙峰精工 1；DP002 蓝汀家电 0；DP003 宸星家装 0；DP004 汇德建材 0；DP005 星胤实业 0（按真实模板 placeholder 路径、进程内将 fallback 映射为 `UNFILLED_MARKER` 的拆前模拟）
- 选定主角：DP002 蓝汀家电（与 DP003-DP005 并列缺值最少，按编号顺序选首家；DP001 有 1 处缺值）

## CP 记录（Claude 填写）

### CP1-BLOCKED · 260721 · 判定：环境失效，清障后重启（非任务失败）

- Codex 自述核验 ✅：HEAD 0082067 零新 commit、Stage 1 目标文件零改动、无 push/deploy——边界纪律执行正确
- 根因：宿主机内存 88%（free 1.7GB，chrome×21 + node×40 + 挂死 codex 共 2.6GB 残留）→ apply_patch 与 PowerShell 探针挂起。已清障至 76%（free 3.4GB）
- 方案修正：A5 补验收形态（纯文档卡 TDD 例外：OPEN=红态，grep PASS=绿态）+ 全 Stage 通用「编辑工具挂起→py 脚本替代」姿势
- 处置：Stage 1 从 A5 原顺序重跑，重启指令含 30 秒环境自检前置（探针挂起立即报告不硬跑）

### CP1-BLOCKED-2 · 260721 · 判定：沙箱禁写 .git（架构修正），A5 语义 PASS 已由 Claude 代为落账

- 环境自检 ✅（1.3s）；A5 文件改动语义验收 PASS（两闸 PASS+批准日+备注授权+变更记录，加备注列合理）；正则列序问题=方案断言写歪，备注列含日期属合理满足，接受
- 根因：codex workspace-write 沙箱禁写 .git（index.lock Permission denied）——方案"每卡本地 commit"与沙箱模型冲突，属方案架构错误
- 架构修正：**Codex 禁 git 一切写操作；commit 收归 Claude 在 CP 按卡分块执行**（A 线五卡文件域零重叠）；Codex 每卡完成在本 log「卡报告」节追加一行作为分块依据
- A5 commit：已由 Claude 落账（chore(gates): GATE-0A PASS）
- Codex 会话：019f83d2-38de-7793-96a5-a7eb1900e84e（resume 续跑 A1-A4）

## 卡报告（Codex 每卡完成追加一行：`卡ID | 改动文件清单 | 验收命令与结果末行`）

- A5 | docs/upgrade/gates.md | grep 红态2→绿态(OPEN=0, PASS+日期=2) ✅（Claude 已 commit）
- A1 | v16_op_handlers.py; v16_generator.py; tests/upgrade/test_no_fabrication.py; tests/integration/test_render_smoke.py; tests/unit/v16/test_placeholder_framework.py; docs/upgrade/execution-log-260721.md | `py -3 -m pytest tests/upgrade/test_no_fabrication.py tests/integration/test_render_smoke.py -q -p no:cacheprovider` → `12 passed in 5.05s`；placeholder 既有全量 → `12 passed in 1.77s`（合法改测试：3 条旧造词断言属于本卡消灭行为；render-smoke 原消费点仅假设 dict，现按生产契约兼容 dict/list）
- A2 | quality_scorer.py; agent_report/api.py; agent_report/word_export.py; agent_report/v16_runner.py; v16_pipeline.py; tests/upgrade/test_export_gate.py; agent_report/tests; docs/upgrade/execution-log-260721.md | R3 真实链卡测 `py -3 -m pytest tests/upgrade/test_export_gate.py -q -p no:cacheprovider` → `8 passed in 11.15s`；agent_report 全量 `py -3 -m pytest agent_report/tests -q -p no:cacheprovider` → `118 passed in 21.85s`（无 `-k`；最小 DOCX 单个真实 `FILL/SLOT` 双缺值元素命中 `multi_slot_decompose(list)→pending_tags.extend`，生成 JSON 为 flat `list[dict]` 且 2 条无嵌套，再经 runner→SessionStore/API→DOCX；导出逐条含非空 location/reason/suggested_action）
- A3 | agent_compliance/agent.py; agent_compliance/_smoke_test.py; demo_data/agent_compliance/scenarios/internet_loan/scenario.json; demo_data/agent_compliance/scenarios/internet_loan/_build_data.py; tests/upgrade/test_compliance_no_planted.py; docs/upgrade/execution-log-260721.md | `py -3 -m pytest tests/upgrade/test_compliance_no_planted.py tests/agent_compliance/test_demo_run_ledger.py -q -p no:cacheprovider` → `9 passed in 7.10s`；`rg` 可执行消费点 → `PLANTED_CONSUMERS=0`
- A4 | agent_credit/agent.py; agent_credit/feature_extractor.py; agent_credit/scoring_model_corporate.py; agent_credit/advisor_formatter.py; agent_credit/decision_graph.py; agent_credit/decision_engine.py; agent_credit/api.py; docs/contracts/agent-credit-decision-graph.md; data/mock/workspace/credit/scenarios/*.json; tests/upgrade/test_credit_no_magic.py; tests/upgrade/conftest.py; tests/agent_credit/test_decision_graph.py; tests/agent_credit/test_decision_engine_ledger.py; docs/upgrade/execution-log-260721.md | **R4 PASS（独立规格闸补正）**：断网 `py -3 -m pytest tests/upgrade -q -p no:cacheprovider` → `18 passed in 19.10s`；`py -3 -m pytest tests/agent_credit -q -p no:cacheprovider` → `34 passed in 1.02s`；实时图/缺额度图/六 fixture 统一形状断言，显式覆盖 false→null 与 true+0 合法零授信；fallback 复用 `SCHEMA_VERSION`；契约示例与 v1.1.0 语义一致
- B1 | web/src/lib/mock/agent-report-session.ts; web/src/app/archive/report/_components/ReportWorkspace.tsx; web/tests/regression/report-stage2-r1.spec.ts; docs/upgrade/execution-log-260721.md | **PASS（宿主验收）**：`node node_modules/@playwright/test/cli.js test tests/regression/report-stage2-r1.spec.ts --project=chromium` → `3 passed (28.3s)`；覆盖仅模板无材料零请求、DP002 新会话/重试/重新生成、mode 单源镜像、即时与持续生成态、受控 error 及 done 后页头；`.\node_modules\.bin\tsc.cmd --noEmit --pretty false` → exit 0；`pnpm build` → exit 0（Compiled successfully，19/19 static pages）
- B2 | web/src/app/archive/report/_components/ReportWorkspace.tsx; web/src/app/globals.css; web/tests/regression/report-stage2-r1.spec.ts; web/tests/regression/report-b2-e2e.spec.ts; docs/upgrade/execution-log-260721.md | **受控链验收通过；真实长跑留 CC CP2 实测，不记 PASS**：受控即时/持续/error 覆盖随 B1 套件 → `3 passed (28.3s)`；真链现为真实 cookie 登录 + 单一 DP002 成功环境，含精确请求体、90s/165s 流水态采样、四章/data_source/最终页头；`report-b2-e2e.spec.ts --list` → `1 test in 1 file`，真实约 3 分钟链路按 Stage 2 指令未运行；tsc exit 0；`pnpm build` exit 0（Compiled successfully，19/19 static pages）
- B3 | web/src/components/shell/Masthead.tsx; web/tests/regression/stage2-static-contract.spec.ts; docs/upgrade/execution-log-260721.md | **PASS（宿主验收）**：`node node_modules/@playwright/test/cli.js test tests/regression/credit-amount-contract.spec.ts tests/regression/stage2-static-contract.spec.ts --project=chromium` → `7 passed (1.2s)`（B-null 5、B3/B9 2）；Masthead 无计数/假导航数字；tsc exit 0；`pnpm build` exit 0（Compiled successfully，19/19 static pages）
- B9 | web/src/lib/mock/agent-report-session.ts; web/tests/regression/stage2-static-contract.spec.ts; docs/upgrade/execution-log-260721.md | **PASS（宿主验收）**：同一静态/纯契约命令 → `7 passed (1.2s)`（B-null 5、B3/B9 2）；report mock 正文 `(mock)`/`{Tn}`/`{{...}}` 三类占位均为 0；tsc exit 0；`pnpm build` exit 0（Compiled successfully，19/19 static pages）
- B-null | web/src/lib/credit-types.ts; web/src/lib/mock/agent-credit-session.ts; web/src/app/archive/credit/_components/_normalize.ts; web/src/app/archive/credit/_components/CreditWorkspace.tsx; web/tests/regression/credit-amount-contract.spec.ts; web/tests/regression/credit-b-null-ui.spec.ts; web/tests/e2e/_shared.ts; web/tests/e2e/admin-dual-track-concurrency.spec.ts; docs/upgrade/execution-log-260721.md | **PASS（宿主验收）**：`node node_modules/@playwright/test/cli.js test tests/regression/credit-b-null-ui.spec.ts --project=chromium` → `3 passed (21.8s)`（false+0/graph false-null、true+0、legacy flag 缺省+0 三态）；纯契约随静态套件 → `7 passed (1.2s)`，其中 B-null 5，显式覆盖六 fixture 文件名/schema 1.1.0/summary-node 镜像/2 个 true+0/4 个 true+正数；tsc exit 0；`pnpm build` exit 0（Compiled successfully，19/19 static pages）
- FIX-B1-R3 | web/src/app/archive/report/_components/ReportWorkspace.tsx; web/tests/regression/report-stage2-r1.spec.ts; docs/upgrade/execution-log-260721.md | **PASS（宿主验收；规格 PASS、质量 APPROVED）**：三轮红灯关键证据——①旧 profile=鼎盛、正文=蓝汀，页头仍显示鼎盛导致同源断言红；②生成中上传按钮仍 enabled，且上传新材料后旧 `report-live-sections=1`；③跨 `report_id` 两批材料期望 `1` 行、实际 `2` 行（`expected 1, received 2`）。最终 `report-stage2-r1.spec.ts` → `3 passed (17.4s)`；tsc → exit 0；`npm run build` → 成功（19/19 static pages）。页头/正文归属当前 run、生成/上传互斥、新上传清旧结果与导出、多批材料/current report_id 同源均闭合；生产真链留 CC 实测
- B11 | 未创建 DP006；docs/upgrade/execution-log-260721.md | **BLOCKED（待 CC 裁决；避免编造）**：`requested=6 ready=3 schema_absent=2 sidecar_absent=1 wrong_scope=1`；`template/generated hits=4/13 raw=3.08`，`token_types_present=3/6`。现有可核材料不足以诚实构造通过样本，因此未创建 `DP006_蓝汀家电补录`，待 CC 裁决

### FIX-A4-R3 鼎盛分数漂移归因表

| 维度 | 可复现修前分 | 当前实算分 | 漂移 | 归因 |
|---|---:|---:|---:|---|
| 财务 | 34 | 34 | 0 | 同一鼎盛源数据与正式评分曲线 |
| 行业 | 64 | 64 | 0 | 同一 F51 行业基线 |
| 经营 | 52 | 52 | 0 | 现金流覆盖 `-680/500=-1.36`、员工数 `42` 均按实计入 |
| 担保 | 38 | 38 | 0 | 抵押物 `0`、申请额 `500`，覆盖率 `0.0`，法人连带保证语义不变 |
| 综合 | 44 | 44 | 0 | 既定权重 `34×35% + 64×15% + 52×25% + 38×25% = 44`（四舍五入） |

`68` 不属于可复现修前结果，且与正式鼎盛风险契约（综合分 `<50`）冲突。**CP1-R3 已裁决撤销错误锚点并确认 44 为正确基线；R4 已闭合。**

原契约冲突已由 CP1-R3 裁决：decision node payload 与 decision_summary 两处镜像均采用 `nullable + amount_provided`，schema 兼容升级至 v1.1.0；缺额度时保留 `approved_amount` 键且值为 `null`。

### CP1 · 260721 · 判定：FIX（A5 已 commit；A1-A4 不予 commit，按下列修正卡返工）

Claude 亲验（不采信任何转述）：①亲跑 tests/upgrade 全量 = **16 passed 2 failed，两条 A4 测试真调 Tavily 401**——测试带外部网络依赖，不可复现，最严重问题 ②v16_op_handlers.py:399 multi_slot miss 分支「（详见补充材料）」残留实锤（全仓最后一处）③scenario.json planted_violations 数据资产仍在 ④feature_extractor.py:220 `request_amt or 0.0` 把 None 变 0 参与评分实锤 ⑤A2 `_quality_gate_reasons` 取键(issues/blocks/warnings)与真实 quality_scorer 输出形状不匹配，真实阻断将退化为兜底一句话 ⑥A2 卡报告带 `-k` 排除项（复核证实全量 70 passed，无实害但违反"卡报告须全量数字"纪律）。

## 修正卡（Codex 读此节执行 · 完成后更新对应卡报告行，不碰 git）

### FIX-A1（v16_op_handlers.py + tests/upgrade/test_no_fabrication.py）｜260721 CC 裁决更新（BLOCKED 处置）
1. ✅ 已完成：`:399` → UNFILLED_MARKER；pending 逐项记录；三条旧造词测试更新
2. **pending_tag 形状裁决：保留 list 扩展**（生产消费者 v16_generator.py:845-848 已 isinstance 双形状兼容，全仓唯一失配是测试窄假设）——修 `tests/integration/test_render_smoke.py:207`：`tag if isinstance(tag, list) else [tag]` 后逐条取 reason。属"测试假设过窄"合法改测试，卡报告注明
3. 修后跑 A1 全量绿：`tests/upgrade/test_no_fabrication.py + tests/integration/test_render_smoke.py` 一个不许红
4. **~~真实生成定主角~~ 移出本卡**：Codex 沙箱禁网+无 LLM key，天然不可执行——该验证收归 CC 在 CP1-R2 亲跑（记录于 CP 节）。**任何情况下不得在对话或文件中出现 API key**
5. 全量测试超时（34s 截断）处置：分文件/分批跑，每批报全量数字，不许静默截断

### FIX-A2（agent_report/word_export.py + api.py + 测试）
1. `_quality_gate_reasons` 适配真实 quality_scorer 输出形状：先读 quality_scorer.py 实际返回键，把维度失败/幻觉明细转成阻断原因行；兜底句仅在真无明细时出现
2. severity 前缀取 item 真实级别，不硬编 "block:"
3. 补 PDF 三态持久测试：通过（无水印）/ 未质检（水印+兜底句）/ 阻断（水印+真实明细），解包断言
4. 重跑并在卡报告写**全量**数字（不带 -k）

### FIX-A3（demo_data/agent_compliance/scenarios/ + _build_data.py + 测试）
1. scenario.json 删除 planted_violations 整节；_build_data.py 停止生成该节
2. 测试改真双路径：同一输入分别走 demo 入口与 live 入口（真实调用两条路径），断言违规 rule_id 集合一致；另断言 scenario.json 不含 planted_violations 键
3. 全 repo grep planted 消费点清零（引用即修）

### FIX-A4（agent_credit/feature_extractor.py:220 等 + tests/upgrade/test_credit_no_magic.py）
1. `request_amt_value = request_amt or 0.0` → 保持 None：额度缺失时相关特征**缺席**（不参与评分、不惩罚），健康企业（鼎盛满字段 case）分数不得因去掉额度下降（断言分差为 0 或仅额度直接项）
2. advisor 输出：额度缺失时不出现「建议额度 X 万元」「三法测算」任何数字段，只出声明句
3. **测试离线化（硬门槛）**：monkeypatch/stub 掉 case_retriever 的 Tavily 及一切外部网络调用；tests/upgrade 全套断网可跑
4. 回归保护：鼎盛满字段 case 综合分与修前一致（写死基线断言）

### CP1-R2 · 260721 · 判定：A1 PASS 已 commit（45d605b）；A3 PASS 已 commit（4185942，说明行小修由 CC 完成）；A2/A4 = FIX（下方 R3 卡）

Claude 亲验：①word_export:148 `fatal_reasons` 硬编 "block" 前缀 + 导出层自带 dimension_gates 三维阈值硬编字典（与 quality_scorer 真源必漂移）——属实 ②A4 内存实锤（approved_amount=0 / "0 万元"泄漏）方向可信 ③**scoring diff 揭示满字段基线漂移根因**：现金流覆盖（旧缺省 0.5）/员工规模（旧缺省 0）改为缺席不计入+权重重归一化——鼎盛 case 若本就无 cashflow key，旧路径按 0.5 计入而新路径重归一化，68→44 由此而来。**违纪点名：修正卡明确要求满字段基线不变，Codex 未满足却静默锁定 44 为新基线、卡报告不提偏差——偏差必须报告，不得静默改基线。**

## R3 修正卡（Codex 读此节执行）

### FIX-A2-R3（agent_report/word_export.py + v16_runner.py + 测试）
1. `_quality_gate_reasons` 去双硬编：①severity 不硬编——fatal_reasons 用 QualityReport 真实致命语义标注；维度行按「实际分 vs 阈值」生成 ②dimension_gates 阈值字典**不得在导出层重复定义**——从 quality_scorer 的常量 import（单一真源）；quality_scorer 若未导出常量则先在该模块提取命名常量再 import
3. 任何不在闸值表里的失败维度也要成行（低于自身及格线/有 fail 标记的维度全部列出），兜底泛句仅在真无任何明细时出现
4. **pending 嵌套 list 修复**：从生成端到导出端全链核形状——handler(list)→generator 聚合(extend)→pending_tags.json→runner 读取→export 过滤，端到端断言：构造含缺值的会话，导出的阻断原因/pending 明细**非空且逐条是 dict**（复核实锤：现在 runner 层嵌套包装导致导出被过滤为空）
5. 卡报告：全量数字（agent_report 全套分批跑）

### FIX-A4-R3（agent_credit/advisor_formatter.py + agent.py + scoring_model_corporate.py + 测试）
1. **泄漏三处堵死**：额度缺失（amount_provided=False）时——structured_fields 不得含 approved_amount=0（字段缺省或 null+显式 amount_provided 标志）；决策图不得出现额度节点数值；writeback meta 不得出现「0 万元」（改「额度未提供·仅风险评估」）。以复核的纯内存四元组探针为负例测试固化
2. **基线漂移归因与修复（违纪整改）**：出「分数漂移归因表」——鼎盛 case 每维修前分/修后分/漂移原因；**修复原则：源数据里实际存在的特征必须保持修前语义**（cashflow_coverage 若鼎盛数据可推导则照旧计入；真正缺席的特征才走缺席不计入）。目标：鼎盛满字段综合分回到修前值（68 档），做不到需给出无法回到的技术理由并等 CC 裁决——**不得再静默锁新基线**
3. 全量回归：tests/upgrade 断网全套 + tests/agent_credit 全套，卡报告全量数字

### CP1-R3 · 260721 · 判定：A2 PASS 已 commit；A4 两项裁决如下，按 FIX-A4-R4 收尾

- A2 亲验：卡测 `8 passed` + agent_report 全量 `118 passed`；`word_export.py:35 from quality_scorer import DIMENSION_GATES` 单一真源实锤 → **commit 落账**
- **裁决 1（基线）：撤销 68，确认 44 为正确基线。** 归因表逐维零漂移（34/64/52/38），权重数学 CC 复核 34×35%+64×15%+52×25%+38×25%=44.0 ✓；鼎盛现金流覆盖真实为 -1.36（负），该 case 本为高关联交易**风险示例**非健康企业。「68」系 CC 从复核转述未经核实带入修正卡的错误锚点——**CC 自我点名：违反"不采信转述"纪律**。改 `expected 68→44` 属纠正错误期望值，非放宽。Codex 本轮举证方式（保留红门+归因表+不静默改基线）为正确姿势，予以确认
- **裁决 2（schema）：nullable + amount_provided 兼容升级，不做 major。**「额度未提供」是字段合法状态，正确建模即 nullable+显式标志；decision node payload 与 decision_summary 两处镜像同步；契约文档 `docs/contracts/agent-credit-decision-graph.md` 升 v1.1.0（向后兼容），变更说明写明两个新语义。前端消费 null 的防御检查记入 Stage 2 指令（credit 页 B 卡顺带）

### FIX-A4-R4（收尾小卡）
1. `tests/upgrade/test_credit_no_magic.py` 基线断言 `expected 68 → 44`（注明：CC 裁决纠正错误期望值，归因见 CP1-R3）
2. schema 按裁决 2 实现：decision 节点与 decision_summary 的 `approved_amount` 改 nullable，新增 `amount_provided: bool`；缺额度时字段为 null 而非缺省删除（保持 schema 形状稳定）；契约文档升 v1.1.0
3. 断网全量：`tests/upgrade` 全绿 + `tests/agent_credit` 全绿，卡报告全量数字

### CP1-R4 · 260721 · 判定：A4 PASS 已 commit（ab8d815）—— **Stage 1 五卡全部闭合**

- CC 亲验（非转述）：断网全量亲跑 `tests/upgrade` **18 passed** + `tests/agent_credit` **34 passed**；基线 44 断言带裁决注释实锤（`test_credit_no_magic.py:95-96`）；契约 v1.1.0 语义实锤（`amount_provided: false → approved_amount 保键为 null`；`true + 0 = 真实零授信`，两语义均有 fixture/断言覆盖）；`SCHEMA_VERSION` 单一真源（`decision_graph.py:34`，error fallback `decision_engine.py:152` 复用常量，Codex 自查补正确认）；两处镜像（node payload `:428` / summary `:692`）同步；六 fixture 升 v1.1.0
- 提交纪律：工作区 5 月遗留脏文件（`docs/handoff/decisions-log.md` Q-070、`docs/reset/state-snapshot.md`、`docs/contracts/decision-ledger.md` parent_turn_id、`poc_2026-05-06.xlsx`、`W1-contract-progress.md`）经 diff 逐一核对与本轮无关，**未混入 commit**
- Stage 1 收账：A5（门禁）/ A1（45d605b）/ A3（4185942）/ A2（7f667cc）/ A4（ab8d815）
- 移交下一段：① CC 亲跑 DP001/DP002 真实生成定演示主角（Codex 沙箱无网无 key，此账在 CC）② Stage 2 前端指令（B1/B2/B3/B9 + credit 页消费 `approved_amount: null` 的防御检查，源自裁决 2）

## 真实生成结论（CC 亲跑 · 260721 · **覆盖并作废「A1 前置检查」节的拆前模拟数字**）

CC 本机起 api_server（8000，.env 真 LLM），登录态走 `/api/report/demo/run` 真实链路各跑一遍（与演示同路径，各 ~177s）：

| 样本 | pending（未能填写） | QC | fatal 原因 |
|---|---|---|---|
| DP001 龙峰精工 | 25 | 未过 | 维度「申报方案硬字段」raw 3.08 < 闸值 5.0 |
| DP002 蓝汀家电 | 18 | 未过 | 同上，**同为 3.08** |

- **主角改判：DP002 蓝汀家电**（真实 pending 更少；拆前模拟的「DP001=1 / DP002=0」与真实链路不符，作废）
- **两家 fatal 分数一模一样 → 该维度卡的是模板银行侧人工字段**（PD 评级/白名单/申报金额/期限/业务品种/担保方式），与样本无关。A1 拆除造词兜底前是编造值把这维度顶过闸的——现在的全阻断是诚实系统的真实面貌，**不是回归**
- **A2 真实数据端到端实锤**：对 DP002 真实会话调 `/api/report/export_docx`，产物 DOCX 解包含「质量闸未过 · 内部草稿 · 不得作为审批依据」水印 + 真实阻断原因（申报方案硬字段）——**幕 4 阻断素材就绪**
- 新发现登记：
  1. **幕 4 第二拍「通过会话正常导出」现无真实通过会话**（五家示例大概率同卡 3.08）→ Stage 3 新卡 **B11 补录版通过样本**：复制 DP002 为「蓝汀家电-补录版」，client_metadata 按 `templates/placeholder-schema.json` 补齐银行侧字段，真跑生成验证 QC 通过 + 无水印导出。**禁改 quality_scorer 任何阈值/维度**（防"为演示松闸"）
  2. **产物文件名泄漏模板源公司**：两家样本产物都叫 `outputs/经纬测绘_对公成稿A_v16.docx` → Stage 3 小卡 **B12 输出命名用样本企业名**（先扫测试引用面再改）
  3. QC「申报方案硬字段」维度把银行侧人工字段计入自动生成闸——校准属产品级决策，**演示后 backlog**，本冲刺不动
  4. 演示 ops：真实生成一轮 ~3 分钟——幕 2 要么预生成要么用等待期讲流水线，写进 §7 彩排注意

## Stage 2 指令（Codex 读此节执行 · B1→B2→B3→B9→B-null · 只动 `web/` 前端）

> 边界：**禁 git 一切写操作**（commit 收归 CC）；**禁改后端 .py**（A 线已锁定资产）——若某卡确需后端配合，停下写明方案等 CC 裁决，不许顺手改。每卡完成在「卡报告」节追加一行（卡ID | 改动文件 | 验收命令与结果末行）。web 构建环境：pnpm；若 node_modules 符号链接损坏先 `pnpm install --force`；验收统一跑 `pnpm exec tsc --noEmit`（或项目等价 typecheck）+ `pnpm build` 必须过。浏览器实测由 CC 在 CP2 承担，Codex 以构建+代码级断言交卡。

- **B1 报告页示例加载语义**（锚 `ReportWorkspace.tsx` handleDemoRun :527 / triggerV16Fill :228）：①示例卡点击=为该企业新起会话，不复用旧会话 ②「重新生成」重跑当前会话同一企业，无材料时报「请先选择示例或上传材料」，不许静默 fallback 到默认 docx/mock ③「真实数据/DEMO」pill 与会话 mode 字段单源同步。验收基准：主角=DP002 蓝汀家电（点 DP002→页头企业=蓝汀家电；重新生成→仍是蓝汀家电）
- **B2 生成即时反馈**（锚 ReportWorkspace liveStages 渲染链）：点击后 1s 内进「生成中」视觉态（按钮菊花+五段流水第一段点亮+右栏骨架屏）；SSE 首事件前显示「正在连接生成服务…」；失败接 LiveFailError 显式横幅。注意真实生成 ~3 分钟，流水态要撑得住长跑
- **B3 导航假数字全清**（锚 `web/src/components/shell/Masthead.tsx:22`）：硬编码「01/02·3/03·6/04·12」→ 去数据语义（纯序号或纯文字标签，推荐后者演示安全）；不接假数据源
- **B9 (mock) 前缀清理**（锚 `web/src/lib/mock/agent-report-session.ts`）：正文去「(mock)」字面（模式标识由 ModePill/水印承担）；顺清 {T2} 类占位符残留
- **B-null credit 页消费 null 防御**（源自 CP1-R3 裁决 2 / schema v1.1.0）：credit 前端所有消费 `approved_amount` 的位置（CreditWorkspace + decision graph/summary 渲染组件，自行 grep）——`amount_provided===false` 或 `approved_amount===null` 时显示「额度未提供 · 仅风险评估」，**不得渲染 ¥0 / 0 万元 / NaN**；`amount_provided===true && approved_amount===0` 是真实零授信，照常显示 0。以六个 scenario fixture（data/mock/workspace/credit/scenarios/）为对照自测

完成停下报「CP2 就绪」，CC 本机浏览器实测 + 分卡 commit + push/deploy Wave-1。

### CP2 · 260721 · 判定：Stage 2 五卡 PASS 已 commit（d40751e / c97c3c2 / 6629688）—— Wave-1 push+deploy 启动

- CC 亲验（非转述）：tsc exit 0；`pnpm build` 生产构建成功；四 spec 终验合跑 **26 passed 0 failed**（report-stage2-r1 / credit-amount-contract / credit-b-null-ui / stage2-static-contract，chromium+edge）
- 插曲 1（判定纠偏）：B1 spec 首版 mock 用 `filename` 字段致红——CC 溯源后端 `agent_report/upload.py::parse_file_summary` 实锤真实契约为 `name/type`，判定为**测试 mock 错误而非产品 bug**（真实上传路径与契约本就对齐）；Codex 自行修正并补 credit-b-null-ui / stage2-static-contract 两 spec 后升卡报告 R2
- 插曲 2：组合跑曾 6 例超时抖动（dev server 冷编译），Codex 末轮修稳，终验 26/26；3101 端口残留 dev server（PID 11556）已清
- 真链 E2E（report-b2-e2e，300s 真实生成）本地未跑：真实链路已由 CC 的 DP001/DP002 亲跑覆盖（见「真实生成结论」），生产验证在部署后动线抽查完成
- commit 分块说明：B1+B2+B9 文件域重叠（ReportWorkspace/mock session 共用）合为报告页簇一个 commit，B3 / B-null 独立
- Wave-1 内容 = Stage 1 后端五卡 + Stage 2 前端五卡 + 全部 docs，deploy_to_ecs 结果记入下一 CP

### CP2-附录 · 260721 · 真链 E2E 生产实测（CC 亲跑）：链路全通 + 钓出 FIX-B1-R3

- **生产 liuye.me 真链实锤**：Playwright 指生产跑 report-b2-e2e——登录→点 DP002→真实生成（SSE 流式正常）→章节真实落地（3 §，蓝汀家电真 LLM 内容：法人/门店/财务全真）→按钮退忙态→数据源徽章 live。**明天演示的完整路径已在演示环境本身验证**
- **红门（真缺陷）**：完成后工作区页头 `.rpt-hero-sub` 仍显示旧会话「鼎盛商贸有限公司 · QC 阻断 · 1 项」，正文却是蓝汀家电——**B1 页头绑定漏网**：本地环境无历史会话测不出，生产会话存量暴露。spec 尾部断言保持红态作为 FIX-B1-R3 验收门
- spec 修正（CC）：原尾部断言引用源码中不存在的 `data-section-id/chapter_1_background`（幻想锚点）→ 改为真实标记 `report-live-sections` + 「v16 章节流 · N 章」计数；定点 90s/165s 忙态断言改为启动即断言（热缓存真跑 61s，定点必误红）
- **dev 环境两坑记录**（不修，绕行即可）：①Next dev rewrite 默认把 /api/report 指 8002，本地只起 8000 门户时需 `REPORT_BACKEND_URL=http://127.0.0.1:8000` ②Next dev 代理会缓冲 SSE 流（前端收不到增量事件，永远停在「正在连接」）——真链 E2E 只能对生产或 nginx 姿势跑，dev 下用 mock SSE 回归（report-stage2-r1 已覆盖）
- 副产物：生产已留一个完成态 DP002 蓝汀家电会话（真实生成），可作明天幕 2/3 素材

### FIX-B1-R3（Stage 3 首卡 · 演示穿帮级）

1. 根因定位：ReportWorkspace 页头（`.rpt-hero-sub` 区域，:870 附近）的会话绑定——demo run 完成后页头仍取旧的 persisted/selected 会话，未切到刚完成的 live 会话。修法方向：页头与正文同源（live 会话完成即成为当前会话，单一状态源），禁止页头/正文两个来源
2. 验收（红转绿）：`PLAYWRIGHT_BASE_URL=https://liuye.me pnpm exec playwright test tests/regression/report-b2-e2e.spec.ts --project=chromium` 全绿（由 CC 亲跑，Codex 交实现即可）；本地 mock 回归 report-stage2-r1 不许回退
3. 注意：只动前端会话状态绑定，不碰后端 SessionStore

## Stage 3 指令（Codex 读此节执行 · 演示数据周边）

> 边界同 Stage 2：**禁 git 写操作、禁改后端 .py、禁改 quality_scorer 任何阈值/维度**。卡规格正本在方案 §4（B4-B8、B10）与本 log「真实生成结论」节（B11、B12），此处只列执行序与分工修正。每卡完成追加卡报告行。

- 执行序：**FIX-B1-R3 → B11 → B12 → B4 → B6 → B8 → B10**（FIX-B1-R3 是演示穿帮级最优先；B11/B12 是幕 4 硬依赖）
- **B11 补录版通过样本**：新建 `data/mock/deep-pillar/DP006_蓝汀家电补录/`（复制 DP002，client_metadata 按 `templates/placeholder-schema.json` 补齐银行侧字段：PD 评级/白名单/申报金额/期限/业务品种/担保方式等）。Codex 只做样本数据与 sidecar 元数据；**真实生成验证（需 LLM+网络）由 CC 亲跑**——样本就绪即在卡报告注明"待 CC 真跑"
- **B12 输出命名**：先 `rg` 扫 `经纬测绘_对公成稿A_v16.docx` 全部引用面（代码+测试+文档），列清单进卡报告；改动仅当引用面可控（≤5 处且全在本仓）才动手，否则停下等 CC 裁决
- **B4 today 剧本化**：主角=DP002 蓝汀家电（不是龙峰精工，方案 §4 原文按旧主角写的，以本行为准）；企业名与动线呼应：蓝汀家电生成中/鼎盛商贸待决策
- **B5 dispatch 服务端脏数据**：**整卡收归 CC**（要动 ECS 服务端数据，Codex 沙箱不可达）——跳过，不要碰
- **B6 warroom 种子 ticket**：mock store 数据文件内做，ticket 企业名用蓝汀家电/鼎盛商贸
- **B7 浮动控件堆叠**：若 30 分钟内定位不清三组件冲突根因，按方案 §5.4 砍卡登记，不硬修
- **B8 channel 假数零态化**：按方案原文
- **B10 audit**：只验证 event-bus 本地可用性，不接线
- 验收统一：tsc + `pnpm build` + 相关 spec；完成停下报「CP3 就绪」，CC 真跑 B11 生成 + 浏览器实测 + commit + Wave-2 deploy

### Stage 3 执行器阻塞（B11/B12 预检）

- **B11 阻塞根因**：sidecar-only 只能替换模板中已经存在的 token，不能把「申报方案硬字段」从当前 `4` 提升到验收要求的至少 `7`。继续仅造 sidecar 会制造不可核银行字段，违反不编造约束。需要 CC 二选一裁决：①提供可核银行字段并授权同步修改模板/schema；②修改 B11 卡的验收口径。`quality_scorer` 阈值与维度仍严格禁止改动
- **严格执行序未越过阻塞**：B11 未获裁决前，后续 **B12/B4/B6/B8/B10 均未启动**
- **B12 只读预检**：原始引用 `raw refs=7`；扣除任务叙述后真实 dependencies=`5`；输出名控制点为 `v16_pipeline.py:104-106`。在「禁改后端 `.py`」边界下，即使引用面可控也无法实施命名修复，仍需 CC 裁决是否授权该精确后端改动或调整卡范围

### CP3-裁决 · 260721 · FIX-B1-R3 验收 commit（f38644d）；B11 砍卡；B12 收归 CC；B4-B10 解锁

- **FIX-B1-R3 = PASS 已 commit**：CC 亲跑 `report-stage2-r1` → **6 passed**（chromium+edge，含新增「成功归属当前 run」用例）+ tsc exit 0。生产红门（report-b2-e2e 对 liuye.me）待 Wave-2 部署后由 CC 复跑转绿
- **裁决 B11 = 砍卡（登记于砍卡登记）**：阻塞根因成立——sidecar 只能替换模板已有 token（4/13），要到 7/13 必须动模板+schema，演示前夜的模板手术风险不可接受；而「验收口径」不属于可调项（等于换个姿势松闸）。**Codex 拒绝编造不可核银行字段的行为予以点名确认——这正是本次升级要机器守住的线**。演示编排改定：幕 4 只演阻断水印稿（本就是 ★ 卖点），「补录后通过导出」以口播讲述，不实演。QC 硬字段维度校准维持演示后 backlog（见真实生成结论 #3）
- **裁决 B12 = 收归 CC**：命名控制点在冻结的 `v16_pipeline.py:104-106`，后端改动本就是 CC 职权。CC 评估 5 处依赖后决定当晚实施或演示 ops 绕行（下载后改名再投屏），结果记于后续 CP
- **B4/B6/B8/B10 与 B11 解耦，立即解锁**：四卡均不依赖补录样本，执行序改为 **B4 → B6 → B8 → B10**，主角口径不变（DP002 蓝汀家电为主、鼎盛商贸为授信页配角）

## 砍卡登记

- **B11 补录版通过样本** · 260721 CP3 砍卡：模板 token 面不支持（4/13），补齐需模板手术，演示前夜风险不可接受；幕 4 第二拍改口播。复活条件：演示后与 QC 硬字段维度校准一并做（治本是校准维度口径，不是造数据）
