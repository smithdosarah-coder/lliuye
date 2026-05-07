# 产品就绪度真辩论 · Claude × Codex × 3 Round

> **PM 命题**: 评估当前产品 (排版 / 前端 API / 后端实用性) 是否达 "实打实能跑产品" 标准
> **辩论方式** (PM 5/7 强调): 双方独立思考 → 互看方案 → 讨论差异 (= 1 轮) · 重复 3 轮
> **建立**: 2026-05-07 · 全文记录辩论过程 · 不是事后总结

---

# Round 1 · 独立思考 → 互看 → Discuss

## 1.1 Claude R1 (独立 lock · 不看 Codex)

**verdict**: 未达 "实打实能跑" · Demo + 部分 production-grade

- 排版 **C** · 4 自加 component 全 inline · 5 RoleHome / 6 workspace 不一致
- 前端 API **C-** · 局部 client + 新组件直 fetch · 错误处理散
- 后端 **D+** · 内存 store + ai_decision mock + audit silent + Phase C 模块没真应用 + prompt 没改

**Top 致命**: "看似闭环 不可追责不可恢复" (内存 + mock + silent 三组合)
**Low-hanging**: audit 非 silent + metadata honest (~2h)
**PM 漏的 critical gap**: 模式不透明 (envelope) + prompt 没改
**ROI 前 3**: audit non-silent → metadata honest → API envelope mode

## 1.2 Codex R1 (独立 lock · 我没暗示 Claude 立场)

**verdict**: 未达 "实打实能跑" · 集成原型 + 局部生产模块

- 排版 **C+** / 前端 API **C** / 后端 **C-/D+**
- **Top 致命**: 状态不可恢复 + 决策可信度错配
- **Low-hanging**: metadata honest + 前端 API 收口
- **Critical gap**: correlation_id + 失败模式定义
- **ROI 前 3**: 持久化 sqlite → ai_decision LLM 接 → 前端 API 收口

## 1.3 R1 互看 · 比对差异 · Discuss

| 维度 | Claude | Codex | 差异 |
|---|---|---|---|
| 评级 | C/C-/D+ | C+/C/C-/D+ | ≈ 共识 |
| Top 致命 | 三组合 | 状态不可恢复 + 决策可信度 | ≈ 共识 (措辞不同) |
| **分歧 1** | 前端 API 收口 1d+ 不算 low | 前端 API 收口算 low | 🔴 |
| **分歧 2** | gap = 模式透明 + prompt | gap = correlation_id + 失败模式 | 🟡 互补 |
| **分歧 3** | ROI 先 Tier 0 (~2h) | ROI 先 Tier 1 (持久化 1-2d) | 🔴 |

**Discuss 结果** (Codex 立场):
- 分歧 1: **Codex 修正接受 Claude** "1d+ 不算 low · 高 ROI 但不 low-hanging"
- 分歧 2: 互补 · 但优先级 = 模式透明 > correlation_id > prompt (Codex 排序)
- 分歧 3: **Codex 接受 Claude Tier 0 先** · 但持久化是 Tier 1 紧随 · 不允许长拖

**R1 共识** (5 件):
- 前端 API 收口高 ROI 但不 low-hanging
- Tier 0 先 (audit non-silent / metadata honest / envelope mode)
- Tier 1 必紧随 (sqlite / 真 LLM / API client)
- 失败不可 silent · metadata 不撒谎
- envelope 是契约级 critical

**R2 各独立想 4 件**: envelope 字段契约 / 失败 taxonomy / Tier 0+1 验收标准 / sqlite schema

---

# Round 2 · 独立思考 4 件 → 互看 → Discuss

## 2.1 Claude R2 (独立)

1. **envelope**: `{ data, meta: { mode, degraded, reason, correlation_id, timestamp } }` · mode 4 状态 (production / demo / mock_fallback / degraded)
2. **失败 taxonomy** (按系统层 5 类): LLM / audit / 持久化 / 数据 / 业务
3. **Tier 0 验收**: audit fail-loud test + envelope mode contract test + metadata honest contract
4. **sqlite reviews schema**: id + decision_id + reviewer + action + reason + ledger_decision_id (review event 模型)

## 2.2 Codex R2 (独立)

1. **envelope**: `{ ok, data, error, meta }` 二元 ok + error category · 不要 warnings/partial/debug 第二套错误系统
2. **失败 taxonomy** (按业务行为 8 类): validation / auth / dependency_unavailable / timeout / rate_limited / data_incomplete / data_stale / internal
3. **Tier 0 验收** (用字段表达): request_id / actor / source / generated_at / 不可伪造 / 不再散装错误
4. **sqlite reviews** (generic step 模型): id + session_id + status + source + input_hash + result_json + error_json

## 2.3 R2 互看 · 比对 · Discuss

| 维度 | Claude | Codex | 差异 |
|---|---|---|---|
| **envelope 结构** | meta.mode 4 状态 | ok 二元 + error category | 🟡 不同抽象 |
| **taxonomy 切法** | 系统层 5 类 | 业务行为 8 类 | 🟡 不同维度 |
| **验收抽象** | test 描述 | 字段定义 | 🟡 互补 |
| **reviews 模型** | review event | generic step | 🟡 不同模型 |

**Discuss 结果** (Codex 立场):
- **envelope**: 双方融合 → `{ ok, data, error, meta }` + `meta.mode` 4 状态 (Codex 接受 Claude mode · Claude 接受 Codex 主结构 · 互让)
- **taxonomy**: Codex 主张业务行为为主 (调用方更可决策) · 系统层做 `error.origin` 内部归因
- **验收**: 验收用 test 描述 + 字段做 contract (Codex 接受 Claude test 表达更适合 PM)
- **reviews**: Codex 接受 Claude review event 模型 · 不混 generic step

**R2 共识** (5 件):
- envelope: `{ ok, data, error, meta + meta.mode }`
- error taxonomy: 业务行为 (调用方) + origin (内部)
- Tier 0 验收 = test + 字段 contract
- reviews 用 event 模型
- 失败永不 silent · metadata 永不撒谎

**R3 各独立想 4 件**: degraded+ok 组合规则 / mock_fallback 是否入 ledger / error retry 策略矩阵 / audit fail-loud 阻断边界

---

# Round 3 · 独立思考 4 件 → 互看 → Discuss

## 3.1 Claude R3 (独立)

1. **degraded+ok**: ok=true 时 mode 任意 · ok=false 必 production
2. **mock_fallback 入 ledger**: 允许 · 标 "mock_fallback" + alert ops
3. **error retry 矩阵** (8 类):
   - validation/auth/internal → block · no retry
   - dependency_unavail → retry 3x → degrade+banner
   - timeout → retry 1x → degrade+banner
   - rate_limited → exponential backoff
   - data_incomplete → 关键 block · 非关键 degrade
   - data_stale → degrade+banner (标时间)
4. **audit fail-loud 阻断**: 默认不阻 (per BE7 wrapper) + 红线决策例外 block

## 3.2 Codex R3 (独立)

1. **degraded+ok**: ok=true+degraded ✅ · ok=true+mock_fallback **默认禁正式业务** (仅 demo/sandbox tenant) · 正式 tenant mock 应返 ok=false 或 blocked_for_business=true
2. **mock_fallback 入 ledger**: **默认禁正式 ledger** · 写 diagnostics/audit_shadow ledger · 物理或权限隔离 · 不参与正式 余额/报表/决策
3. **error retry 矩阵** (10 类): 加 conflict / llm_invalid_output / business_rule / unknown
4. **audit fail-loud 阻断** (6 类必 block + 5 类 banner):
   - **必 block**: ledger write / 权限身份 / money 决策 / report finalize / **对外发送**
   - **仅 banner**: audit enrich / explainability trace / analytics / metadata 辅助 / 草稿态

## 3.3 R3 互看 · 比对 · Discuss

| 维度 | Claude | Codex | 差异 |
|---|---|---|---|
| degraded+ok | ok=true 时 mode 任意 (含 mock) | mock 仅 demo tenant · 正式禁 | 🟡 |
| **mock 入 ledger** | 允许 + 标 | **默认禁正式 ledger + shadow ledger** | 🔴 大分歧 |
| error retry | 8 类 | 10 类 (+ conflict/llm_invalid_output/business_rule/unknown) | 🟡 |
| audit fail-loud | 默认不阻 + 红线例外 | 6 类必 block + 5 类 banner · 含 "对外发送" | 🟡 |

**Discuss 结果** (Claude 接受 Codex 多数 · 但定义"对外发送" 模糊):
- **大分歧 mock 入 ledger**: **Codex 坚持禁** · 理由: 银行场景 ledger 被下游风控/对账/报表采信 · 即使强标也易被二次消费误当事实. **Claude 接受 Codex** · 折中: 写 shadow ledger (字段全 + 隔离 + 不参与正式 决策/报表)
- **degraded+ok**: **Claude 接受 Codex** · ok=true 不能语义过宽 · 正式 tenant mock 返 ok=false 或 blocked_for_business=true
- **error retry**: business_rule 保留 (Codex 解释: 业务政策拒绝 ≠ validation 格式错 · e.g. 额度不足/KYC 未过/账户冻结) · unknown 降级为 internal_unknown 兜底 · 1 retry 上限
- **"对外发送" 定义** (Codex): 离开受控系统边界 = 邮件/短信/webhook/客户 portal/监管文件/第三方系统 · 不含内部草稿/预览/diagnostics

**R3 共识** (4 件):
- mock_fallback 默认禁正式 ledger · 写 shadow ledger (隔离)
- 正式 tenant mock 返 ok=false 或 blocked_for_business=true
- error 9 类 (业务行为 8 + internal_unknown 兜底)
- audit fail-loud 6 类必 block (ledger / auth / money / report finalize / 对外发送) + 5 类 banner

**R4 1 件 deep dive 留 implement 时定**:
- shadow ledger schema / 权限 / retention / 查询入口

---

# 综合 verdict (R1+R2+R3 真辩论 · Claude+Codex 共识)

## A · 当前产品状态

- 排版 C / 前端 API C- / 后端 D+
- 未达 "实打实能跑" 标准 · Demo + 集成原型 · 闭环不通
- Top 致命: 内存 + mock + silent 三组合 → 看似闭环 实际不可追责不可恢复

## B · Tier 0 立即修 (~2-3h · 我可直接开干)

| # | 项 | 验收标准 |
|---|---|---|
| 0.1 | audit_log 非 silent | 失败必抛 + UI banner · request_id/actor/result/失败必落 audit |
| 0.2 | API envelope `{ ok, data, error, meta }` | 4 critical endpoint 含 meta.mode 4 状态 (production/demo/mock_fallback/degraded) + 测试 contract |
| 0.3 | ai_decision metadata honest | model: "rule-fallback-no-llm" + UI 显式 + 不可伪造 |

## C · Tier 1 必紧随 (~1-2d · 客户走访前必)

| # | 项 |
|---|---|
| 1.1 | sqlite 持久化 sessions/reviews/business_metrics · reviews 用 event 模型 (Claude) · 重启不丢 |
| 1.2 | ai_decision 真接 shared/llm_caller (DeepSeek) · LLM fail fallback rule + metadata 标 llm-error-fallback |
| 1.3 | 6 Agent endpoint 真应用 D1/D2/D4 (evidence_date 校验) |

## D · Tier 2 触发条件 (无承诺日期)

- 统一 API client + 错误 envelope (4-5 component 迁)
- 新组件强制 shell-v2 token
- prompt 注入 8 段 SSOT + 时效约束

## E · 失败模式 taxonomy 9 类 + retry 矩阵

```
validation        → no retry · block
auth              → no retry · block (re-auth banner)
dependency_unavail → retry 3x · 核心 block / 非核心 degrade+banner
timeout           → retry 1x · degrade+banner
rate_limited      → exponential backoff
data_incomplete   → 关键 block · 非关键 degrade
data_stale        → degrade+banner (标时间)
conflict          → no blind retry · reload/merge · block
business_rule     → no retry · block (额度不足/KYC 未过/账户冻结)
llm_invalid_output → retry stricter prompt/schema
internal_unknown  → 1 retry 上限 · block + banner
```

## F · audit fail-loud 阻断边界

- **必 block (6 类)**: ledger write / 权限身份 / money 决策 / report finalize / 对外发送 (邮件/短信/webhook/客户 portal/监管文件/第三方写入)
- **仅 banner (5 类)**: audit enrich / explainability trace 非核心 / analytics/telemetry / review 辅助 metadata / 非 finalize 草稿态

## G · degraded + ok 组合规则

- ✅ allowed: `ok=true + mode=production` · `ok=true + mode=degraded` (有 banner) · `ok=true + mode=mock_fallback` (仅 demo/sandbox tenant)
- ❌ forbid: `ok=true + error≠null` · `ok=false + data.primary_result≠null` · 正式 tenant `mode=mock_fallback + ok=true`
- 正式 tenant mock 必返: `ok=false` 或 `degraded=true + blocked_for_business=true`

## H · sqlite minimum schema

```sql
sessions    (id, created_at, updated_at, status, user_label, metadata_json)
reviews     (id, decision_id, reviewer, action, reason, ledger_decision_id, created_at)
business_metrics (id, session_id, review_id, metric_name, metric_value, metric_unit,
                  source, confidence, generated_at, metadata_json)
shadow_ledger (id, mode, tenant_type, reason, source, not_for_audit,
               original_decision_id, recorded_at)  -- mock_fallback 专用
```

## I · PM 必拍 5 件 (Tier 0 ship 后)

1. 审计日志保留多久 + 谁可查
2. 失败恢复目标 (重跑整 case · 还是阶段恢复)
3. LLM 降级边界 (规则 fallback 客户接受多大 simplicity)
4. 数据脱敏白名单 (统社/手机/身份证号 必脱 · 哪些可落)
5. Tier 1 是否绑定客户 demo / 上线场景

## J · 下一步

1. **PM 看本辩论报告 (~15 min)** · 重点看 R3 大分歧 mock_fallback 入 ledger 决议 (Codex 立场胜)
2. PM 拍 Tier 0 立即开干 (我自跑 ~2-3h · 安全 · 后端 + 不动 visual)
3. PM 拍 §I 5 件 Open Questions 1-2 件
4. Tier 0 ship 后 PM 验收 + Tier 1 启

---

**Source**: Claude × Codex 真辩论 R1+R2+R3 · 各独立 + 互看差异 + Discuss
**File**: `docs/reset/product-readiness-debate-2026-05-07.md`
**Signal**: PRODUCT-DEBATE-3-ROUND-DONE
