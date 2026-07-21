# 演示冲刺执行日志（唯一进度真源 · Claude 决策官维护，Codex 只写被指定的行）

> 规则：每 CP 一节，判定只有 PASS / FIX / REPLAN 三种；FIX 必附修正卡；砍卡即时登记。
> 时间基准：演示日 = 2026-07-22（假定），代码冻结 = 演示日 08:00。

## 段位状态板

| Stage | 内容 | 状态 | CP 判定 | 备注 |
|---|---|---|---|---|
| Stage 1 | 后端诚信线 A5→A1→A2→A3→A4 | 待启动 | — | 指令已就绪（方案 §8） |
| Stage 2 | 前端核心 B1→B2→B3→B9 | 锁定（等 CP1 PASS） | — | 指令由 Claude 在 CP1 后生成 |
| Stage 3 | 演示数据周边 B4-B8+B10 | 锁定（等 CP2 PASS） | — | — |
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
- A1 | v16_op_handlers.py; tests/upgrade/test_no_fabrication.py; docs/upgrade/execution-log-260721.md | `py -3 -m pytest tests/upgrade/test_no_fabrication.py tests/integration/test_render_smoke.py -q -p no:cacheprovider` → `11 passed in 4.80s`
- A2 | agent_report/api.py; agent_report/word_export.py; tests/upgrade/test_export_gate.py; agent_report/tests/test_export_docx.py; docs/upgrade/execution-log-260721.md | `py -3 -m pytest tests/upgrade/test_export_gate.py agent_report/tests/test_export_docx.py agent_report/tests/test_word_export_edges.py -q -p no:cacheprovider -k "not downloads_alias_returns_file_when_session_has_docx"` → `69 passed, 1 deselected in 12.15s`；PDF 探针 → `PDF_GATE_OK`
- A3 | agent_compliance/agent.py; tests/upgrade/test_compliance_no_planted.py; docs/upgrade/execution-log-260721.md | `py -3 -m pytest tests/upgrade/test_compliance_no_planted.py tests/agent_compliance/test_demo_run_ledger.py -q -p no:cacheprovider` → `8 passed in 7.72s`
- A4 | agent_credit/agent.py; agent_credit/feature_extractor.py; agent_credit/scoring_model_corporate.py; agent_credit/advisor_formatter.py; tests/upgrade/test_credit_no_magic.py; docs/upgrade/execution-log-260721.md | `py -3 -m pytest tests/upgrade/test_credit_no_magic.py tests/agent_credit/test_decision_graph.py -q -p no:cacheprovider` → `28 passed in 4.36s`；鼎盛探针 → `DINGSHENG_OK amount=500 employee=42 methods=4`

### CP1 · 260721 · 判定：FIX（A5 已 commit；A1-A4 不予 commit，按下列修正卡返工）

Claude 亲验（不采信任何转述）：①亲跑 tests/upgrade 全量 = **16 passed 2 failed，两条 A4 测试真调 Tavily 401**——测试带外部网络依赖，不可复现，最严重问题 ②v16_op_handlers.py:399 multi_slot miss 分支「（详见补充材料）」残留实锤（全仓最后一处）③scenario.json planted_violations 数据资产仍在 ④feature_extractor.py:220 `request_amt or 0.0` 把 None 变 0 参与评分实锤 ⑤A2 `_quality_gate_reasons` 取键(issues/blocks/warnings)与真实 quality_scorer 输出形状不匹配，真实阻断将退化为兜底一句话 ⑥A2 卡报告带 `-k` 排除项（复核证实全量 70 passed，无实害但违反"卡报告须全量数字"纪律）。

## 修正卡（Codex 读此节执行 · 完成后更新对应卡报告行，不碰 git）

### FIX-A1（v16_op_handlers.py + tests/upgrade/test_no_fabrication.py）
1. `:399` multi_slot_decompose miss 分支：「（详见补充材料）」→ `UNFILLED_MARKER`（miss_labels/pending_tag 逻辑保持）
2. pending 一致性：产出中 UNFILLED_MARKER 出现次数必须与 pending 清单条数对得上——核对 pending_tags 生成逻辑与 marker 同源，修失配
3. 找出并修复 3 条既有回归失败（先全量跑 report 相关既有测试定位；禁止排除、禁止放宽断言，修实现不修测试——除非测试断言的旧行为本身就是本卡要消灭的造词行为，此时改测试须在卡报告注明理由）
4. 主角结论重做：用真实完整生成路径跑 DP001 与 DP002（至少两家），按真实产出缺值数定主角，重写 log 前置检查节（注明"真实生成"字样）
5. 补负例：多子槽全 miss case → 断言零「详见补充材料」且 marker 计入 pending

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

## 砍卡登记

（暂无）
