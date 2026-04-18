# 字段命名 / 单位 / 类型契约 v1.0

**版本**：v1.0
**发布日期**：2026-04-18
**作者**：主 CLI（Pre-Phase-0）
**适用范围**：6 Agent 全部前后端 + SSE 事件 + JSON 文件

---

## 0. 为什么需要这份文档

前端 6 个 Agent 页面在 unified platform pivot 之前各自定义字段，已扫出 4 类冲突（见 §一）。
5 路并行启动前不冻结，merge 时必打架。

**修改本文件需主 CLI 批准**——子 CLI 发现新冲突走 `docs/contracts/shared-change-protocol.md` RFC 流程，不准单方面增删。

---

## 一、当前冲突清单（必须冻结）

| # | 字段 | 冲突表现 | 统一方案 | 优先级 |
|---|---|---|---|---|
| 1 | `mock` | 前端 boolean / 后端部分接收 int(0/1) | **统一 boolean**：前端传 `true/false`，后端 FastAPI 自动转 query bool；旧 `Query(int)` 一律改 `Query(bool)` | P0 |
| 2 | `business_line` | 多处硬编码字符串，前端无 TypeScript 枚举 | **统一 enum**：`"corporate" \| "inclusive" \| "retail" \| "reserved"`；定义在 `web/src/lib/credit-types.ts` + `agent_report/enterprise_profile.py` BUSINESS_LINE_TO_PRESET 双向同步 | P0 |
| 3 | `session_id` | 长度 / 格式无约束，下载端点用严格正则 | **统一 UUID v4**（hex+dash，36 字符）：`xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`；服务端生成、前端透传不修改 | P0 |
| 4 | `provider` | `/api/credit/decision` 缺默认；`/api/channel/run` 默认 `"deepseek"` | **统一默认 `"deepseek"`**；可选值文档化：`"deepseek" \| "openai" \| "claude"`（境内仅 deepseek 合规可用于客户数据） | P1 |
| 5 | `amount` | 不同 Agent 单位歧义（元 vs 万元） | **统一元**（int 或 float，精度自定义）；显示层面前端做 `formatWan()` 转换；JSON 字段名带后缀消歧：`amount_yuan` / `amount_wan` 二选一 | P0 |
| 6 | `is_hard` + `severity` | 红线触发既有 bool 开关又有等级，语义重复 | **删 `is_hard`**，仅保留 `severity` enum（`"red" \| "yellow" \| "green"` 或 `"hard" \| "soft" \| "info"` 二选一，§三定） | P1 |

---

## 二、全局命名规则（新字段必须遵守）

### 2.1 命名风格

| 场景 | 风格 | 示例 |
|---|---|---|
| Python 后端字段 | snake_case | `enterprise_name`, `decision_at` |
| TypeScript 前端字段 | snake_case（与后端 1:1，前端不做 camelCase 转换） | `enterprise_name` |
| URL 路径 | kebab-case 或 snake_case，与现有保持一致 | `/api/credit/policy_scan` |
| SSE event 名 | snake_case | `profile_loaded`, `stage`, `done`, `error` |
| 枚举值 | 全小写 snake_case | `"corporate"`, `"red"`, `"approved"` |

### 2.2 单位 / 时间 / 金额

| 类型 | 字段后缀 | 示例 |
|---|---|---|
| 金额 | `_yuan` 或 `_wan` 必带 | `approved_amount_yuan: 5000000` |
| 比率 / 占比 | `_rate` 或 `_pct` | `approval_rate: 0.85`（小数）/ `pass_pct: 85`（百分数） |
| 期数 | `_months` / `_days` / `_years` | `term_months: 36` |
| 时间戳 | `_at`（ISO 8601）/ `_ts`（Unix int） | `created_at: "2026-04-18T10:30:00Z"`, `submitted_ts: 1745678400` |
| 计数 | `_count` | `customer_count: 120` |

### 2.3 布尔字段

- 必须用 `is_*` / `has_*` / `can_*` 前缀
- ❌ `verified`, ❌ `enabled`
- ✅ `is_verified`, ✅ `has_collateral`, ✅ `can_export`

---

## 三、关键 enum 字典（冻结 v1.0）

### 3.1 `business_line`

```typescript
type BusinessLine = "corporate" | "inclusive" | "retail" | "reserved";
//                  对公          普惠         零售         预留（未来扩展）
```

后端：`agent_report.enterprise_profile.BUSINESS_LINE_TO_PRESET` 维护映射。

### 3.2 `segment`（仅 Agent3 用）

```typescript
type Segment = "corporate" | "retail";
//             对公          对私
```

注：`segment` 是 Agent3 内部细分，与 `business_line` 不互通。

### 3.3 `severity`

```typescript
type Severity = "red" | "yellow" | "green";
//              硬红线   软警告      信息提示
```

⚠️ **统一信号灯隐喻**——不要混用 `"hard" / "soft" / "info"`。

### 3.4 `decision_verdict`

```typescript
type DecisionVerdict =
  | "approved"           // 批准
  | "approved_with_conditions"  // 有条件批准
  | "rejected"           // 拒绝
  | "pending_review"     // 待复核
  | "insufficient_info"; // 信息不足，无法判定
```

### 3.5 `provider`（LLM）

```typescript
type LLMProvider = "deepseek" | "openai" | "claude";
// 客户材料处理仅允许 "deepseek"（境内合规）；其他仅用于非敏感推理
```

### 3.6 `event`（SSE）

各 Agent 通用事件名：

```typescript
type SSEEvent =
  | "profile_loaded"  // 画像加载完成
  | "stage"           // 进入新阶段
  | "stream"          // LLM 流式 token
  | "tool_call"       // 工具调用
  | "tool_result"     // 工具结果
  | "done"            // 任务结束
  | "error";          // 错误
```

各 Agent 自定义阶段名走 `stage` 事件 payload 的 `stage` 字段，不要新增 event 名。

---

## 四、ID / 标识符规范

| 字段 | 格式 | 长度 | 生成方 |
|---|---|---|---|
| `session_id` | UUID v4 hex+dash | 36 | 服务端 |
| `profile_id` | UUID v4 hex+dash | 36 | Agent6 生成，下游消费 |
| `user_id` | string，无格式约束（占位阶段） | ≤ 64 | Phase 1c 后由 Shell CC 接管 |
| `correlation_id` | UUID v4，跨 Agent 链路追踪 | 36 | 服务端，调用链首站生成 |

正则（用于 URL path 防穿越）：
```
^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$
```

---

## 五、错误响应统一结构

所有 4xx / 5xx HTTP 响应：

```json
{
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "segment must be corporate or retail",
    "details": {"field": "segment", "got": "private"}
  }
}
```

`code` 用全大写 SNAKE_CASE，业务方可枚举：
- `VALIDATION_FAILED` (400)
- `UNAUTHORIZED` (401)
- `FORBIDDEN` (403)
- `NOT_FOUND` (404)
- `RATE_LIMITED` (429)
- `LLM_UPSTREAM_ERROR` (502)
- `LLM_TIMEOUT` (504)
- `INTERNAL_ERROR` (500)

⚠️ 现存 `HTTPException(500, "load presets failed: ...")` 简洁字符串风格 Phase 1 内不强制改造，但**新增端点必须遵守**。

---

## 六、SSE 事件 payload 标准

```json
{
  "event": "stage",
  "stage": "evidence_gathering",
  "progress": 0.3,
  "message": "正在召回 12 条相关材料",
  "payload": { /* stage-specific */ }
}
```

- `progress`：0-1 浮点（不是 0-100）
- `message`：用户可见中文
- `payload`：stage-specific 数据，JSON-safe（用 `shared.api_utils.to_jsonable`）

---

## 七、版本演进

- v1.0 (2026-04-18)：建立基线，冻结 6 项现存冲突 + 全局命名规则
- 任何新增 enum / 字段命名变更走 RFC：`docs/contracts/rfc/YYYYMMDD-<desc>.md`，主 CLI 批准后入库
- 破坏性变更升 major（v2.0），其他升 minor
