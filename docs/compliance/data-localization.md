# 客户数据本地处理 · 数据驻留与境内 API 清单

**版本**：v1.0
**发布日期**：2026-04-26
**对应 DoD**：L2-15
**适用范围**：6 Agent 矩阵全产品（Agent1-6）+ shared/sources 数据源层
**关联文档**：
- `docs/compliance/data-grading.md`（L2-14 数据分级 · 一般 / 重要 / 核心三级）
- `docs/compliance/partners.md`（L2-13 合作机构清单 · 第三方服务备案）
- `docs/commercial-readiness.md` §3 数据驻留方案（销售 RFP 应答框架）

---

## 1. 政策依据（真实条文引用）

| 法规 | 关键条款 | 我方对应 |
|---|---|---|
| 《数据安全法》（2021）第 31 条 | 关键信息基础设施运营者在境内运营中收集和产生的重要数据应当在境内存储；出境安全评估走 CAC《数据出境安全评估办法》（2022） | §3.1 默认境内 only |
| 《个人信息保护法》（2021）第 38 条 + 第 40 条 | 第 38 条 个人信息出境 4 条件（标准合同 / 安全评估 / 认证 / 其他法律行政法规）；第 40 条 CIIO + 处理量达标准的处理者出境评估（第 39 条 单独同意 不属"4 条件"清单） | §3.2 客户内网部署 + §4 例外流程 |
| 《关键信息基础设施安全保护条例》（2021 · 国务院令 745 号） | 关基保护范畴 / 安全检测和风险评估等（重要数据 + 个保境内存储义务实际来自《数安法》第 31 条 + 《个保法》第 40 条 · 非本条例特定条款 · P1 review fix-forward 2026-04-26） | §3.4 数据传输加密 + 物理隔离 |
| 《金融机构数据安全管理办法》+ 金管总局 93 号文 | 重要 / 核心数据本地化 | §3.4 + L2-14 数据分级映射 |
| 金管总局《助贷新规》2025-10 | 合作机构备案 + 数据传输边界 | docs/compliance/partners.md |
| CAC《人工智能安全治理框架 2.0》2025-09 | AI 应用安全设计内嵌 + 训练 / 推理数据合规 | §2 LLM 底座选型 |
| CAC《生成式 AI 服务管理办法》2023-08 | 训练数据合法性 + 生成内容标识 + 服务备案 | §2 DeepSeek 网信办备案 |

**违规后果**：罚款（百万至千万 · 最高上年度营业额 5%）+ 暂停业务资质 + 吊销许可。

---

## 2. 境内 API 清单（生产可用）

### 2.1 LLM 底座

| 服务 | 服务商 | 机房 | 备案 |
|---|---|---|---|
| DeepSeek-Chat（默认） | 深度求索（境内） | 上海 / 北京 | 网信办生成式 AI 备案完成 |
| 通义千问（备份切换） | 阿里云（境内） | 杭州 / 北京 | 网信办备案完成 |
| GLM-4（备份切换） | 智谱 AI（境内） | 北京 | 网信办备案完成 |
| 豆包私有部署（客户内网） | 字节跳动（境内 + 客户私有） | 客户机房 | 客户合规部审 |

**配置位置**：`.env` 中 `DEEPSEEK_API_KEY` + `DEEPSEEK_BASE_URL`（默认 `https://api.deepseek.com`）。切换走 `agent_*/llm_provider.py` adapter。

### 2.2 外部信号 / 搜索

| 服务 | 用途 | 数据敏感度 |
|---|---|---|
| Tavily 国内 endpoint | 行业新闻 / 政策检索（公开信息） | 一般（不传客户数据） |
| 企查查 API | 工商档案 / 司法诉讼 | 一般（公开信息） |
| 国家企业信用信息公示系统 | 工商变更 / 经营异常 | 一般（公开） |
| 中国裁判文书网 | 司法诉讼 | 一般（公开） |
| 央行 / 国家金融监督管理总局公开 API | 政策原文 / 监管文件 | 一般（公开） |
| akshare（开源境内数据） | 行业财务 baseline | 一般（公开） |

**配置位置**：`shared/sources/impls/{tavily,enterprise_info,gov_cn,pbc_gov,flk_npc,akshare}.py`，按 Agent 偏好链 `agent_*/sources_config.py` 调用。

### 2.3 客户数据存储

- 客户上传材料 → `data/sessions/<session_id>/`（本地文件系统 · session TTL 30 min 自动销毁）
- 评估基线 → `evaluation/baselines/`（git 落盘 · 不含 PII）
- 反馈 jsonl → `data/feedback/YYYY-MM-DD.jsonl`（本地 · 不含 PII · 仅修改 delta）
- 审计日志 → `data/audit/YYYY-MM-DD.jsonl`（本地 · input_hash + output_hash · 不落 PII 明文）

---

## 3. 境外 API 禁用清单（红线）

| 服务 | 状态 | 原因 |
|---|---|---|
| OpenAI (GPT-4 / GPT-3.5) 公网 endpoint | ❌ 禁用 | LLM 在境外（美国） · 客户数据出境 = 违 数安法 + 助贷新规 |
| Anthropic Claude 公网 endpoint | ❌ 禁用 | 同上 |
| Google Gemini 公网 endpoint | ❌ 禁用 | 同上 |
| 任何 IP 在境外的 LLM API | ❌ 禁用 | 同上 |
| Tavily 美国 endpoint（默认） | ❌ 禁用 | 我方走 Tavily 国内 endpoint · 不走美国 |
| AWS Bedrock / Azure OpenAI 全球版 | ❌ 禁用 | 同上 |

**Code 层禁用证据**：
- `grep -r "api.openai.com\|api.anthropic.com\|generativelanguage.googleapis.com" agent_*/ shared/`：0 命中
- `agent_*/llm_provider.py` 显式 whitelist 境内 endpoint domain
- CI 增量 lint：PR diff 中含上列境外 endpoint 触发 reject

---

## 4. 例外申请流程（如客户场景需用境外 LLM）

**触发条件**：客户跨国业务场景（如汇丰中国 / 渣打中国 等跨国行）合理需求境外 LLM。

**流程**：
1. **客户合规部书面授权**：客户出具《数据出境授权函》指定数据范围 + 出境目的地 + 加密方式
2. **我方 RFC 走 Q-NNN-RAISED**：在 `docs/handoff/decisions-log.md` 记录例外背景 + 风险评估
3. **法律评估**：法务部审《个保法》第 38-40 条出境 4 条件适用性
4. **CAC 数据出境安全评估**（如适用客户为关键信息基础设施运营者）
5. **签订《数据处理协议》（DPA）**：客户 ↔ 我方 ↔ LLM 厂商 三方
6. **审计留痕**：例外调用全量审计日志 · 保留 3 年（数安法要求）
7. **退出条款**：合同终止 30 天内全量删除境外副本 + 第三方审计验证

**审批人**：客户合规部 + 我方法务 VP + 我方安全工程负责人 三方联签

---

## 5. 数据传输加密要求

| 链路 | 协议 | 强度 |
|---|---|---|
| 客户 → 我方 API（HTTPS） | TLS 1.2+（推荐 1.3） | RSA 2048+ / ECC 256+ |
| 我方 API → LLM 底座 | HTTPS + 域名白名单 | TLS 1.2+ |
| 我方 API → 客户内网（v16 离线模式） | mTLS（双向证书）+ 客户专线 / VPN | 客户合规部审定 |
| 数据库连接 | TLS（Postgres SSL on）/ TDE 透明加密 | AES-256 |
| 文件存储（落盘） | 客户机房磁盘加密 / OSS 服务端加密 | AES-256 |
| 敏感字段（身份证 / 银行账户） | 应用层脱敏 / hash + 字段级加密 | SHA-256 + AES-GCM |

---

## 6. 数据分级与本地化映射

参照 `docs/compliance/data-grading.md` 三级分级，本地化策略：

| 数据级 | 例子 | 处理位置 | 是否可出境 |
|---|---|---|---|
| 一般 | 行业分析 / 公开政策 / 6 Agent 输出文案 | 境内云 OK | 可境内云外发 |
| 重要 | 客户企业名 / 财务比率 / 决策结果（脱敏后）| 客户内网 only | 不出客户内网 |
| 核心 | 身份证 / 银行账户 / 完整授信记录 / PII | 客户内网 + 物理隔离 | 不出物理边界 |

**映射规则**：每个 Agent 的输入 / 输出字段在 `agent_*/data_classification.yaml` 标级（待 Wave 3+ 各 Agent 自检 · 当前 Agent6 已落 · 5 Agent 待补）。

---

## 7. 第三方服务边界（与 partners.md 互联）

**境内服务可消费的客户数据范围**：
- DeepSeek 推理：仅 Agent 生成阶段的 prompt（不含 PII 明文 · prompt 内 PII 字段经 `truth_fill.py` 脱敏处理）
- Tavily 国内 / 企查查：仅 Agent1 / Agent5 检索词（公开信息查询 · 无客户 PII）
- akshare：仅行业代码 + 时间窗口（公开 baseline · 无客户数据）

**禁止透传**：客户原始材料 PDF / xlsx / docx 全文 → 任何第三方 API。所有材料解析在本地 `material_kb.py` + `truth_fill.py` 完成。

---

## 8. 审计与合规验证

### 8.1 审计日志（DoD L2-12）

- 落盘位置：`data/audit/YYYY-MM-DD.jsonl`
- 字段：`timestamp / session_id / user_id / endpoint / input_hash / output_hash / latency_ms`
- input / output 仅 hash · 不落 PII 明文
- 保留期：3 年（数安法 + 个保法要求）
- 客户合规部可调阅（API + 现场）

### 8.2 第三方测评

| 标准 | 状态 | 时间表 |
|---|---|---|
| 等保 2.0 三级 | 自检通过 · 实测 pending | `[TEAM-INPUT-NEEDED: 安全工程 - 测评公司协同时间表]` |
| ISO 27001 | 计划 | `[TEAM-INPUT-NEEDED: 安全工程]` |
| SOC 2 Type II | 客户驱动（视客户要求启动） | 客户合同前 |
| GDPR 合规设计 | 仅跨国行场景启动 | 跨国客户接入前 |

### 8.3 客户审计支持

参照 `docs/commercial-readiness.md` §4.2 · 审计前 30 天 / 审计期 5 工作日 / 审计后 30 天 三阶段 SOP。

---

## 9. 版本演进

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-04-26 | 初版 · L2-15 落地 · 与 partners.md / data-grading.md 三件套配套 |

**升级触发**：监管新规发布 / 客户场景例外被批准 / 第三方测评结果出来 / 重大数据安全事件后根因修订。

---

**END OF DOCUMENT**
