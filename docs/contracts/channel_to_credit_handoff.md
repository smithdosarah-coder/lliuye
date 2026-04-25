# Agent1 → Agent3 · Handoff 契约 v1.0

**版本**：v1.0
**发布日期**：2026-04-18
**作者**：Agent1 Phase 1 CC（按主 CLI 批示"绿区包装红区"模式落地）
**适用范围**：Agent1（获客）→ Agent3（授信决策）跨 Agent 数据流

---

## 0. 为什么要有这份契约

Agent1 输出的候选企业要进入 Agent3 的四维评分与授信决策流程。如果两端直接共享一个数据模型：
- 污染红区 `shared/enterprise_profile.py`（Agent3/6 不消费 Agent1 的 match_score / signal_timeline）
- 耦合 Agent1 的绿区演进与 Agent3 的评分模型

**解法（主 CLI 拍板）**：绿区 `agent_channel.CandidateProfile` 包装红区 `shared.EnterpriseProfile`。

---

## 一、JSON 结构

### 1.1 存放路径

```
data/handoff/channel_to_credit/{session_id}/{profile_id}.json
```

- `session_id`：Agent1 本次搜索会话 ID（UUID v4，由 Agent1 服务端生成）
- `profile_id`：每个候选企业一份 JSON（UUID v4，由 `CandidateProfile` 默认工厂生成）

`session_id` 目录承载该次搜索的所有候选；Agent3 可按 session_id 批量读取，也可按 profile_id 单个读取。

### 1.2 JSON 顶层结构

```json
{
  "schema_version": "1.0",
  "profile_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_id": "7f4c7a2d-c2f5-4c8e-9d2a-b3e6f1a0c9d7",
  "created_at": "2026-04-18T10:30:00Z",
  "candidate_profile": { /* Agent1 完整版 */ },
  "enterprise_profile": { /* EnterpriseProfile 严格 subset，Agent3 消费这个 */ }
}
```

### 1.3 enterprise_profile 字段（Agent3 消费契约）

就是 `shared/enterprise_profile.py::EnterpriseProfile` 的 `model_dump()` 输出。字段清单（全量见 EnterpriseProfile 源码）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `company_name` | str | 工商注册全名 |
| `unified_credit_code` | str | USCC（18 位，可能为空） |
| `legal_representative` | str | 法人 |
| `registered_capital` | str | 注册资本（带单位字符串） |
| `establishment_date` | str | 成立日期 |
| `industry` | str | 行业 |
| `region` | str | 所在地区 |
| `employee_count` | int | 员工数 |
| `main_business` | str | 主营业务 |
| `financial_summary` | dict | 财务摘要（Agent1 不填，Agent3/6 填） |
| `risk_tags` | list[dict] | 风险标签（Agent1 不填） |
| ... | ... | 完整见 EnterpriseProfile |

**Agent1 不填的字段（financial_summary / risk_tags / credit_history / ...）以默认值（空字典 / 空列表）出现，Agent3 不应假定已填。**

### 1.4 candidate_profile 字段（Agent1 专属，不稳定）

Agent1 的完整载体，结构参见 `agent_channel/candidate_profile.py::CandidateProfile`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `match_score` | int 0-100 | Agent1 给出的匹配分 |
| `business_line` | enum | `"corporate" / "inclusive" / "retail" / "reserved"`，Agent1 默认 corporate |
| `signal_count` | int | 信号总条数 |
| `signal_types` | list[str] | 去重排序后的信号类型 |
| `signal_timeline` | list[SignalItem] | 按日期倒序 |
| `source_urls` | list[str] | 去重后的证据 URL 列表 |
| `approved_amount_yuan` | int | Agent1 给出的授信上限建议（启发式，非硬承诺） |
| `recommended_products` | list[str] | 产品推荐 |
| `pitch` | str | 外呼话术 |
| `data_sources` | list[str] | 数据来源标签（如 `"内部 Mock 客户库"`） |
| `below_diversity_gate` | bool | 是否低于信号多样性阈值的回填候选 |

⚠️ **Agent3 不应依赖这些字段。** Agent1 的绿区演进可能随时改结构。如需复用 Agent1 的判定，Agent3 读 `enterprise_profile` 即可。

---

## 二、消费规则

### 2.1 Agent3 侧

```python
import json
from pathlib import Path
from shared.enterprise_profile import EnterpriseProfile

def load_handoff(session_id: str, profile_id: str) -> EnterpriseProfile:
    path = Path(f"data/handoff/channel_to_credit/{session_id}/{profile_id}.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    # 只读 enterprise_profile 子字段
    return EnterpriseProfile.model_validate(data["enterprise_profile"])
```

Agent3 Phase 1 的 #1 任务（由 Agent3 CC 实现）应该就是这段消费代码。

### 2.2 Agent1 侧

Agent1 写入由 `POST /api/channel/handoff` 端点完成（C6 任务），内部调用：

```python
from agent_channel.candidate_profile import CandidateProfile

profile = CandidateProfile.from_candidate_dict(candidate_dict, session_id=session_id)
handoff_path.write_text(json.dumps(profile.to_handoff_json(), ensure_ascii=False, indent=2))
```

---

## 三、生命周期与保留

| 阶段 | 动作 | 责任方 |
|---|---|---|
| 创建 | Agent1 点"移交授信评估"时写入 | Agent1 |
| 消费 | Agent3 按 profile_id 读取 | Agent3 |
| 归档 | Agent3 消费后打标 `.consumed` 文件 | Agent3 Phase 2 |
| 滚动清理 | 30 天未 consume 的 session 目录自动删 | Phase 2 定时任务 |

**当前 Phase 1 不实现归档 / 清理**，仅保证写入正确 + Agent3 能读。

---

## 四、版本演进与破坏性变更

- **v1.0 (2026-04-18)**：建立基线。`enterprise_profile` 子字段等同于当前 `shared/enterprise_profile.py` 的 `model_dump()` 输出。
- **`schema_version` 字段**用于向前兼容：未来破坏性变更（例如 EnterpriseProfile schema 调整、handoff JSON 顶层字段重排）必须同时 bump `schema_version`。
- **破坏性变更**走 `docs/contracts/shared-change-protocol.md` 的 RFC 流程。
- **非破坏性追加**（在 `candidate_profile` 里加字段）自由，Agent1 CC 无需 RFC。
- **Agent3 不得向 Agent1 反向写 handoff 文件。** 反向流（Agent3 → Agent1）另开契约。

---

## 五、合规约束

- `data/handoff/` 已在 `.gitignore` 内，不进仓库
- 写入 JSON 不得含 L3 核心数据（客户内部编号 / 征信报告等），详见 `docs/data_classification/agent1.md`
- `session_id` / `profile_id` 严格 UUID v4，防目录穿越攻击（下游消费方校验正则见 `field-naming.md §4`）
