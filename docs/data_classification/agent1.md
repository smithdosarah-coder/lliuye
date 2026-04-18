# Agent1 获客智能体 · 数据分级与合规边界 v1.0

**适用版本**：Agent1 v4.0（2026-04-16 北部湾首演版）
**发布日期**：2026-04-18
**监管依据**：
- 《金融机构数据安全管理办法》（国家金融监督管理总局，2025）
- 《关于银行保险机构数据安全管理工作有关事项的通知》（金管总局 93 号文）
- 《网络安全法》《数据安全法》《个人信息保护法》

---

## 一、Agent1 的数据消费全景

Agent1 是**贷前获客**智能体，核心流程是"自然语言意图 → 信号驱动的候选企业清单"。
**Agent1 不接触银行在贷客户名单 / 申请表 / 征信报告。** 客户数据的流转在 Agent6（报告）/ Agent3（授信）/ Agent4（预警）/ Agent5（合规）之间闭环，与 Agent1 隔离。

Agent1 消费的数据来源与路径：

| 路径 | 调用点 | 数据来源 | 消费方式 |
|---|---|---|---|
| 信号搜索（5 路并行） | `agent_channel.realtime_stream.SIGNAL_QUERIES` | Tavily（公开 web search）+ 域名白名单 | 按关键词搜公开网页 |
| 企业工商补全 | `agent_channel.realtime_stream._fetch_qcc_info` | Router → `enterprise_info` → 上市走 akshare，非上市走 Tavily+LLM 严抽 | 按公司名查工商基础 6 字段 |
| 意图解析 / 信号抽取 / 话术生成 | `llm.LLMClient` | DeepSeek（境内合规 LLM） | prompt 里包含行业 / 区域 / 公司名（公开信息） |
| 产品推荐 | `agent_channel.product_recommender` + 银行内部产品库 | 本地 JSON（`demo_data/agent_channel/scenarios/*/products.json`） | 本地读 |
| 降级兜底 | `shared.kb_scan.search_provider.MockSearchProvider` | 本地合成数据池 | 断网时用，明确标 `data_source=mock_*` |

---

## 二、数据三级分类（按 93 号文口径）

### 2.1 一般数据（L1）

Agent1 大部分输入属于此级。公开可得、汇聚后不引起风险升级。

| 数据项 | 来源 | 本地化要求 |
|---|---|---|
| 公开招投标公告 | chinabidding.cn / bidcenter.com.cn（via Tavily） | 否 |
| 政府政策 / 白名单 | gov.cn 各级子域（via Tavily） | 否 |
| 上市公司公开财报 | akshare（本地 Python 库，抓取新浪 / 东财公开接口） | 本地运行，无境外传输 |
| 公开舆情 / 行业报道 | caixin.com / 36kr.com / yicai.com / cs.com.cn（via Tavily） | 否 |
| 公开专利 | cnipa.gov.cn（via Tavily） | 否 |
| 企业自身发布信息 | 企业官网 / 公开新闻稿 | 否 |
| 客户经理自然语言意图 | 前端用户输入 | 不含个人敏感信息 |

### 2.2 重要数据（L2）

聚合型使用时接近"重要数据"——依 93 号文，**银行对企业经营信息的批量聚合**可能被认定为重要数据。

| 数据项 | 来源 | 本地化要求 | Agent1 的处理 |
|---|---|---|---|
| 企业工商基础信息（法人 / 注册资本 / 成立日期 / USCC 等） | qcc.com / tianyancha.com / aiqicha.com（via Tavily 定向搜） | **是** —— 境内落地优先 | 聚合上限：单次查询 ≤ 1 个公司、批量候选 ≤ 20 条；落盘在 `data/handoff/`（已 `.gitignore`） |
| 上市公司结构化数据 | akshare | 天然本地 | 仅限上市公司，公开合规 |

**合规边界（重要）**：
- Tavily 是境外 API（美国），对 L2 数据的查询路径属于 "查询词经境外"，**查询词只包含公开企业名、不包含客户关联标签**。Agent1 的查询由客户经理自然语言生成，**绝不带银行内部客户名单 / 内部编号**。
- 若未来需要查询银行已存量客户的企业画像，**必须切到全境内源**（企查查商用 API / 本地化部署的天眼查） —— 不走 Tavily。此切换由 `shared/sources/router.py` 的偏好链控制，不改 Agent1 业务逻辑。

### 2.3 核心数据（L3）

**Agent1 绝对不接触**。以下数据仅在 Agent3/4/5/6 流转：

| 数据项 | 为什么 Agent1 不能碰 |
|---|---|
| 银行已在贷 / 申请中客户名单 | Agent1 是前向获客，客户尚未开户；一旦接触即超出职能边界 |
| 客户真实申请表 / 授信报告 | 属于 Agent6（生成）/ Agent3（决策）闭环 |
| 客户征信报告 / 人行二代征信接口响应 | 属于 Agent3 红线检查域 |
| 客户交易流水 / 账户余额 | 属于 Agent4 预警域的内部交易数据路径 |
| 员工内部数据 / 信贷政策全文（内部版） | 属于 Agent5 合规域 |

**强制约束**：若 Agent1 UI 里出现"输入客户名单"类字段，视为越界，触发 DoD §10 红线停工。

---

## 三、境外 API 使用清单（重点合规声明）

| API | 用途 | 数据流方向 | 合规依据 |
|---|---|---|---|
| Tavily（US） | 公开 web search | **仅出站查询词 = 公开企业名 / 行业 / 区域 / 信号关键词**，不含客户数据 | 93 号文：一般数据可跨境，重要数据聚合需评估 → Agent1 聚合上限 ≤ 20 条候选，每次单查询 |
| DeepSeek（境内） | LLM 意图解析 / 信号抽取 / 话术 | 境内闭环 | 合规首选，L2 合规 |
| akshare（本地） | 上市公司基础数据 | 本地运行 | 公开接口，无传输 |
| 企查查 / 天眼查（未开通） | 未来 L2 本地化首选 | 境内 API | 切换点见 §2.2 合规边界 |

OpenAI / Claude 等境外 LLM **不用于 Agent1**（`llm.LLMClient` 强制 `provider="deepseek"`，见 `agent_channel/api.py:65` 默认值；`field-naming.md §3.5` 冻结 provider 枚举，客户材料处理仅允许 deepseek）。

---

## 四、落盘与保留策略

| 路径 | 内容 | 保留期 | 传输边界 |
|---|---|---|---|
| `data/feedback/YYYY-MM-DD.jsonl` | 审贷员对 Agent1 候选的修改反馈 | 90 天滚动 | 本地文件，不进境外 |
| `data/handoff/channel_to_credit/{session_id}/` | Agent1 → Agent3 handoff JSON | 30 天滚动，Agent3 消费后归档 | 本地，已 `.gitignore` |
| `outputs/agent_channel/*.xlsx` | 候选企业导出 | 客户经理桌面下载后删除 | 本地生成，openpyxl 纯离线 |
| `demo_data/agent_channel/` | 场景预置 mock 池 | 永久，明确合成 | 无真实客户 |
| `customer/` | 客户真实材料 | — | `.gitignore` + Agent1 **禁止读** |

**关键约束**：
- `customer/` 目录对 Agent1 运行时不可读（由 `agent_channel/` 代码不引用 `customer/` 路径保证）
- 所有 Agent1 生成物经前端界面输出，禁止通过邮件 / IM 主动推送给银行外部

---

## 五、评估与审计钩子

| 检查项 | 实现 | 频率 |
|---|---|---|
| Agent1 是否触发过 `customer/` 读取 | 静态扫描 + grep | 每次 CI |
| Tavily 查询词是否含疑似客户标识（纯数字 / 长随机串） | `agent_channel/tests/test_query_sanitizer.py`（Phase 2 加） | 每次 CI |
| L2 聚合查询是否超 20 条 | `evaluation/agent1_channel.yaml` 的 `l2_aggregate_cap` 指标 | 每次评估 |
| Provider 是否仅 `deepseek` | Pydantic 字段校验 + 路由中间件（Phase 2） | 运行时 |

---

## 六、违规事件处置

触发以下任一 → **立即停工 + 写 `docs/incidents/YYYYMMDD-agent1-<desc>.md` + ping 主 CLI**：
1. 任何境外 API 收到包含客户内部编号的查询
2. Agent1 代码读取 `customer/` 路径
3. L3 核心数据出现在 Agent1 产出物
4. Tavily 返回结果被直接存入 `data/` 下非 handoff 目录

---

## 七、版本演进

- v1.0 (2026-04-18)：建立基线，冻结三级分类 + 境外 API 清单 + 落盘规则
- Phase 2 预计变更：接入企查查商用 API 后，L2 工商信息查询走境内源，修订 §2.2 与 §3
- 文档修改走 `docs/contracts/shared-change-protocol.md` 的 RFC 流程（跨 Agent 影响时）
