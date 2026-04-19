# Agent6 · 信贷报告助手演示脚本（10-15 min Sales Playbook）

**版本**：v1.0
**更新日期**：2026-04-19
**对应 DoD**：L3-12
**目标受众**：银行客户经理 / 审贷员 / 合规官 / 科技部采购
**演示时长**：10–15 min（含 Q&A 缓冲）
**演示环境**：`py /tmp/start_uvicorn.py` + `cd web && npm run dev`，或跨机器访问 `demo.liuye.me`

---

## 0. 演示前准备（演示者 5 min 自检）

```bash
# 1. 后端起来（带 env wrapper）
py /tmp/start_uvicorn.py

# 2. 健康检查
curl -s http://127.0.0.1:8000/api/report/health
# 期望：{"status":"ok","llm_connected":true,"version":"0.1.0"}

# 3. 前端起来
cd web && npm run dev
# 访问 http://localhost:3000/report

# 4. 样本材料就位
ls samples/
# 至少一份骨架型普惠授信申报书 docx 模板
```

如 `llm_connected: false` → **改走 mock 模式**（`?mock=1`），提前告知观众 "我们今天演示的是 fixture 场景，真实 LLM 流程一致"。

---

## 1. 开场（1 min）：业务痛点

> "审贷员一份企业授信报告要填 **492 项**，平均 2.5 小时手工抄录。Agent6 把这个压到 **10 分钟**，审贷员只做 '改' 不做 '填'。"
>
> "银行买 AI 最大的疑虑不是'能不能做'，是'出错谁负责'。所以 Agent6 的设计锚点是三条线：
> 1. **证据优先**（Evidence-First）—— 每条数字都挂来源
> 2. **质量闸门**（QC Blocker）—— 输出前阻断幻觉
> 3. **审计留痕** —— 每次调用落日志"

## 2. Demo 一步一步（8 min）

### Step 1：上传企业材料（1 min）

打开 `http://localhost:3000/report`。

- 业务线选择器：对公 `corporate` / 普惠 `inclusive` / 预留 `reserved`
- 上传 4 份材料：营业执照 PDF + 3 年财报 xlsx + 征信报告 PDF + 业务介绍 DOCX
- （可选）上传客户自带的模板 docx，否则用业务线对应内置模板

> 💬 讲稿："所有材料在本地 OCR / 解析。财务数字走 Python `financial_analyzer`，不让 LLM 现场算——这是合规红线。"

`[screenshot: upload-step.png]`

### Step 2：触发报告生成（2 min）

点击"开始生成"。前端按 SSE 协议展示 5 阶段：

1. `ingest` —— 材料加载 + KB 构建
2. `extract` —— 结构化预填（`truth_fill.py`）
3. `infer` —— 模板语义分析
4. `write` —— 三阶段 Evidence-First 章节生成
5. `audit` —— QC Blocker 终审

实时进度条展示 stage 切换；真模式 ~6–8 min，Mock 模式 ~3 秒。

> 💬 讲稿："每个 stage 都是一段有明确产出的阶段性任务。停在任何一段都能看到中间态，不是黑盒。"

`[screenshot: pipeline-running.png]`

### Step 3：看结果与证据链（2 min）

右侧产出区展示：

- **四大章节**：一、企业背景 / 二、经营情况 / 三、财务分析 / 四、审批意见
- **填写统计**：total_fields = 492 / auto_filled = 460 / unfilled = 32
- **Pending Questions**：未填字段列"需要客户经理补答"
- **下游 Handoff**：EnterpriseProfile payload 可一键送 Agent3（授信决策）

点任一段落 → 高亮展示**证据出处**（段落文件名 + 抽取位置）。

> 💬 讲稿："这份报告每一条数字都能在 30 秒内追溯到原始材料——这是合规官放行的底线。"

`[screenshot: evidence-trace.png]`

### Step 4：QC Blocker 拦截示范（1.5 min）

故意选一份"缺征信报告"的材料包跑一次。

- 章节"四、审批意见"在征信维度字段会标 `未能自动填写`
- QC Blocker 拦截企业名占位符 / 残留区间数字 / 模板指导文字

> 💬 讲稿："我们宁可标'未能自动填写'，也不让 LLM 编一个看起来对的数——这是金融产品的硬约束。"

### Step 5：反馈飞轮（1 min）

审贷员改一条字段 → 点"提交反馈"。

```bash
# 后台演示审计日志 + 反馈 JSONL
tail -n 1 data/audit/$(date +%Y-%m-%d).jsonl
tail -n 1 data/feedback/$(date +%Y-%m-%d).jsonl
```

> 💬 讲稿："审贷员每次改，都进数据飞轮第 3 环。定期提取 few-shot 示例回灌 prompt，模型越用越准——不依赖微调，也符合境内监管的可解释性要求。"

### Step 6：导出 & 下游联动（0.5 min）

- 点"导出 docx" → 下载填好的申报书
- 点"送 Agent3" → 跳转授信决策页，自动预填 EnterpriseProfile

`[screenshot: handoff-to-agent3.png]`

## 3. 合规与监管锚点（2 min）

> "这不是一个演示 Demo，是按监管硬约束设计的产品。"

| 监管条款 | Agent6 对应实现 |
|---|---|
| 金管总局《助贷新规》2025-10 合作机构备案 | `docs/compliance/partners.md` 合作机构清单 |
| 《金融机构数据安全管理办法》+ 93 号文 数据分级 | `docs/compliance/data-grading.md` 一般/重要/核心三级 |
| CAC《AI 安全治理框架 2.0》可解释性强制 | Evidence-First + 审计日志 `data/audit/` |
| 《生成式 AI 服务管理办法》备案 | DeepSeek 境内底座已完成网信办备案 |
| 金管总局 2025 "AI 只能辅助不能替代" | copilot 定位 + 显式"建议"标识 + 审批人字段 |

## 4. 典型 Q&A（2 min）

- **Q**：LLM 会不会瞎编财务数字？
  **A**：财务比率 100% 走 Python `financial_analyzer.py`，LLM 只消费其计算结果。比率错误率与 Python 一致率 ≥ 99%。

- **Q**：客户材料会上传到境外吗？
  **A**：不会。所有核心数据（财务 / 征信 / 授信）本地处理，LLM 底座 DeepSeek 境内。只有公开行业新闻走 Tavily（境外），参数严格限制为公开关键词。

- **Q**：如果 AI 填错了，出了事故谁负责？
  **A**：Agent6 定位 copilot。审贷员终审 + 电子签章 + 审计日志三重留痕。任何字段都可追溯到原始材料；出错可归因到具体材料解析 / prompt / QC 规则。

- **Q**：上线需要多久？
  **A**：Demo 环境 1 周内跑通，POC 2 周，生产部署 4-6 周（含合规备案 + 信创适配）。

## 5. 收尾话术（0.5 min）

> "今天演示只展示了 Agent6 一个节点。X-Nexus 平台一共 6 个 Agent：
> - Agent1 获客 · Agent2 风控 · Agent3 授信 · Agent4 预警 · Agent5 合规 · Agent6 报告
>
> 每个都按同一套'证据链 + 质量闸门 + 审计日志'设计。做一个是示范，做 6 个是平台。
>
> 下一步可以深入哪一部分——算法细节、合规材料、POC 计划、还是报价方案？"

---

## 附录 A · 切 Mock 模式（外网不稳 / LLM 失联时）

```bash
# 前端直接 ?mock=1，或后端显式调用
curl -N "http://127.0.0.1:8000/api/report/fill?mock=1&preset=dingsheng_trade&business_line=corporate"
```

Mock 模式 3 秒出完整 done payload，所有可视化一致，只是数据来源替换为预置 fixture。

## 附录 B · 审计证据调取

```bash
# 查今天所有 Agent6 调用
cat data/audit/$(date +%Y-%m-%d).jsonl | py -c "import sys,json; [print(json.dumps(json.loads(l),ensure_ascii=False,indent=2)) for l in sys.stdin]"
```

每条记录字段：`timestamp / user_id / endpoint / input_hash / output_status / latency_ms`，input 只落 hash 不落 PII。

## 附录 C · 演示失败兜底

- LLM 超时 → UI 明示"模型响应慢，已切 Mock 兜底"
- 材料解析失败 → 红提示 + 改走 fixture
- 任何技术报错不直接暴露堆栈给客户，转 UI 降级文案
