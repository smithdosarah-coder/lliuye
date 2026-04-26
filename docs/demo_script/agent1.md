# Agent1 · 全渠道获客助手演示脚本（10-15 min Sales Playbook）

**版本**：v1.0
**更新日期**：2026-04-26
**对应 DoD**：L3-12
**目标受众**：银行客户经理 / 营销支持 / 科技部采购
**演示时长**：10-15 min
**演示环境**：`py /tmp/start_uvicorn.py` + `cd web && npm run dev` 或 `demo.liuye.me`

---

## 0. 演示前准备（演示者 5 min 自检）

```bash
py /tmp/start_uvicorn.py    # 后端起来
curl -s http://127.0.0.1:8000/api/channel/health    # {"status":"ok","llm_connected":true}
cd web && npm run dev    # 前端 http://localhost:3000/archive/channel
ls data/mock/agent1-channel/    # 锚点客户 + 知识库 fixture
```

如 `llm_connected: false` → 改走 Mock 模式（`?mock=1`）· 提前告知观众 "今天演示 fixture 场景 · 真实 LLM 流程一致"。

---

## 1. 开场（1 min）：业务痛点

> "客户经理一周拓 50 家陌生企业 · 1 单成交概率 < 5% · ROI 不到 30%。
>
> Agent1 给客户经理一个'锚点客户 + 知识库'· 召回 30+ 相似企业 + 每家 ≥ 2 种信号类型（工商 / 司法 / 招聘 / 媒体 / 招投标）· 客户经理只做'选 + 联'· 不再'找'。
>
> 这不是 cold call list · 是 look-alike 信号驱动的精准拓客。"

## 2. Demo 一步一步（8 min）

### Step 1：上传锚点客户 + 知识库（1 min）

打开 `http://localhost:3000/archive/channel`。
- 锚点客户：1-3 家行内已成交客户（如某地市制造业 2 家）
- 知识库：上传 3 类（① 区域名录 xlsx · ② 行业指引 PDF · ③ 营销倾向性文件 PDF）

> 💬 讲稿："锚点 + 知识库就是您的'拓客基因'· Agent1 不是凭空召 · 是按您的成功画像复制。"

### Step 2：触发 lookalike 召回（2 min）

点击"开始召回"· 前端 SSE 5 阶段：
1. `ingest` 知识库构建
2. `signal_search` 多源信号检索（Tavily 国内 + 企查查 + 公示系统）
3. `lookalike_score` 多维度加权评分
4. `signal_diversify` 信号多样性 ≥ 2 enforcement
5. `recommend_product` 产品匹配 + 推荐理由

实时进度条 stage 切换 · 真模式 ~3-5 min · Mock 模式 ~3 秒。

> 💬 讲稿："信号多样性是硬指标——只有工商或者只有招投标的候选自动 SKIP · 这是召回精度的护城河。"

### Step 3：看候选清单 + 信号时间线（2 min）

右侧产出区：
- **候选企业列表**：30+ 家 · 每家显示企业名 + 行业 + 规模 + 匹配分
- **信号时间线**：点候选企业 → 横向时间线展示该企业近 6 月信号（工商变更 / 司法 / 招聘 / 招投标 / 媒体）
- **推荐产品**：Agent1 自动匹配行内产品目录 + 给推荐理由

点任一信号 → 跳转原始 URL（裁判文书网 / 公示系统 / 媒体报道）。

> 💬 讲稿："每条信号都能 30 秒追到原文 · 客户经理上门前已经知道客户在想什么。"

### Step 4：导出 + 跨 Agent handoff（1 min）

- 点"导出 xlsx"→ 下载候选清单（含企业名 / 联系方式 / 信号摘要 / 推荐产品 / 匹配理由）
- 点"送 Agent6"→ 选中候选 → Agent6 一键生成预报告（用于客户经理上门前材料准备）
- 点"送 Agent3"→ 候选授信预评估（适合已成熟客户）

> 💬 讲稿："Agent1 → Agent6 → Agent3 是闭环——拓客 / 调研 / 决策 一站式。"

### Step 5：反馈飞轮（1 min）

客户经理标"已联系不感兴趣" / "已成交" → `/api/feedback` 写 jsonl
- 不感兴趣 → 后续召回降权该类候选
- 已成交 → 追加到锚点客户库 · 持续学习

> 💬 讲稿："越用越准 · 不依赖微调 · 客户经理标注就是数据飞轮。"

### Step 6：合规与隐私（1 min）

- 召回数据全境内 · DeepSeek 上海 + Tavily 国内 + 企查查 API
- 客户 PII 不出本地 · SearchProvider 仅查询关键词出境（公开信息）
- 审计日志 `data/audit/*.jsonl` 落盘

## 3. 合规与监管锚点（1 min）

| 监管 | Agent1 实现 |
|---|---|
| 数据安全法 | 客户数据本地处理 · `docs/compliance/data-localization.md` |
| 个保法 | 公开企业信息 + 客户经理脱敏标注 |
| CAC AI 治理 2.0 | 信号多样性 + reason_codes 字典（待 Wave 3+ 派生） |
| 反不正当竞争法 | 仅用合法公开数据 · 不爬非授权数据 |

## 4. 典型 Q&A（2 min）

- **Q**：召回精度怎么保证？
  **A**：信号多样性 ≥ 2 是硬约束 · 单源信号自动 SKIP。Phase 1 真数据 baseline 后 precision@10 + recall@10 实测对外公开。

- **Q**：客户名单是隐私 · 怎么保证不外泄？
  **A**：锚点客户 + 候选名单全本地。仅 SearchProvider 查询关键词（公开信息检索）经境内 endpoint 出境。无客户 PII 出境。

- **Q**：每月多少新候选？
  **A**：取决于知识库 + SearchProvider 数据时效 · 单家锚点客户每月 ≥ 30 家新候选（基线）。

- **Q**：上线工期？
  **A**：Demo 1 周 · POC 2 周 · 生产 4-6 周（含信创适配 + 客户名录接入）。

## 5. 收尾话术（0.5 min）

> "今天看到的是 Agent1 一个节点。X-Nexus 6 Agent 矩阵：
> Agent1 获客 / Agent2 风控 / Agent3 授信 / Agent4 预警 / Agent5 合规 / Agent6 报告
>
> Agent1 给客户经理'谁'· Agent6/3 给'怎么决策'· Agent4/5 给'怎么管'。
>
> 下一步深入哪部分——召回算法 / Phase 1 真数据 / POC / 报价方案？"

---

## 附录 A · Mock 模式

```bash
curl -N "http://127.0.0.1:8000/api/channel/lookalike?mock=1&anchor=preset_corp_a"
```

## 附录 B · 审计调取

```bash
cat data/audit/$(date +%Y-%m-%d).jsonl | grep "endpoint.*channel"
```

## 附录 C · 演示失败兜底

- Tavily key 失效 → 降级 Mock fixture（UI 明示）
- 候选 < 10 家 → 提示扩大知识库范围
- 任何技术报错走 UI 降级文案 · 不暴露堆栈
