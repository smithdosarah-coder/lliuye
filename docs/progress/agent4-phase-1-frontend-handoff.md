# Agent4 预警 · 前端实装移交 ticket

**发出方**：Agent4 worker CLI（`feat/agent4-productize`，Phase 1）
**接收方**：frontend CLI（Stage 3 Task C/D 或之后）
**发出日期**：2026-04-19
**状态**：📤 已发出 · **本 Phase 1 不实装**；代等 frontend Stage 3 排期

---

## 1. 移交物一览

| 类别 | 位点 | 角色 |
|---|---|---|
| 设计稿（低 fidelity） | `docs/design/alert-dashboard-stub.md` | 3 卡片 ASCII wireframe + 字段级数据源 + 色系 hook |
| 枚举契约 | `docs/design/alert-trigger-reasons-taxonomy.md` | `trigger_reasons` 3 值封闭集语义规约 |
| 数据源 schema | `evaluation/manual/4_YYYYMMDD.yaml` | runtime dump 产物（Task A 落地） |
| adapter 消费点 | `evaluation/runner/adapters/agent4_alert.py` | 同一 yaml 的后端消费参考（pass-through 模式） |
| 色系变量规范 | `docs/design/platform-shell-v1.md` §3 | 4 主题 `--g0..--g7` + `--accent` |

---

## 2. 依赖 commit / 分支

- **本 Phase 1 分支**：`feat/agent4-productize`
- **Task A 落地**（runtime yaml schema 冻结）：`34f85af` · feat(agent4) Phase 1 Task A — runtime dump replaces synthetic fixture
- **Task C 落地**（trigger_reasons 枚举 + taxonomy 文档）：`3ef8799` · feat(agent4) Phase 1 Task C — trigger_reasons 结构推断枚举
- **Task D 落地**（本文 + dashboard stub）：**Phase 1 final commit**（SHA 待 READY-FOR-REVIEW 时回填）

前端实装启动前，请先 `git log --oneline -20 feat/agent4-productize` 确认上述 SHA 在主干（或其下游 integration 分支）已合并。

---

## 3. 需要 frontend CLI 实装的范围

**3 个卡片（对齐 `docs/design/alert-dashboard-stub.md`）：**

1. **卡片 A · 分级客户数**（红/黄/绿 count + 环比昨日）
2. **卡片 B · 触发原因码分布**（3 枚举横向堆叠条，`cross_hit` 高亮）
3. **卡片 C · 近 30 天趋势**（红灯折线 + 原因码来源面积图）

**视图归属**：platform-shell-v1 的「AI 助手 › Agent4 预警」tile，**不开顶栏新 tab**。

---

## 4. 数据源契约（消费侧必读）

### 4.1 runtime yaml schema（Task A 冻结）

```yaml
version: runtime-v1
generated_at: <ISO-8601 UTC>
source:
  agent: alert
  git_commit: <sha>
  kb_scenario: <str>
  search_provider: <str>
whitelist_entity_ids: [<entity_id>, ...]
customers:
  - entity_id: <str>
    name: <str>
    grade: red | yellow | green
    trigger_reasons: [external_signal | internal_rule | cross_hit]  # 封闭集，0~1 项
    evidence:
      - type: external | internal
        signal: <str>
        source: <str>
        url: <str>
    scan_time_ms: <float>
    status: completed | failed:<ExceptionName>
tool_calls:
  total: <int>
  success: <int>
```

**文件命名**：`evaluation/manual/4_YYYYMMDD.yaml`，`YYYYMMDD` = UTC 日期戳，对齐 `generated_at`。

### 4.2 绝对红线

- 前端**不得**自己"推断" `trigger_reasons` —— runtime yaml 已回填、是唯一事实来源（对齐 taxonomy §4）
- 前端**不得**基于 `evidence[].signal` 文本关键词反推 grade / reason（对齐 CLAUDE.md §12）
- 字段缺失 → 显式显示「未能自动填写」占位，不编（对齐 CLAUDE.md §12 + Evidence-First）

### 4.3 未来 API 契约（Phase 2 Batch 2 挂端点后生效，**本 ticket 不涵盖**）

- 路径候选：`GET /api/agent/alert/daily?date=YYYY-MM-DD`
- 返回 body 与 yaml 结构 1:1 对齐（不新增字段，不改字段名）
- 过渡期：前端可先读 yaml（本地部署） / 未来切 API（对外部署）——切换点只是 data fetcher

---

## 5. 建议 Stage / 排期

| Stage | 工作项 | 依赖 |
|---|---|---|
| Stage 3 Task C | 卡片 A + 卡片 B（今日静态数据） | 仅依赖当日 yaml |
| Stage 3 Task D | 卡片 C（30 天趋势） | 依赖 30 日 yaml 序列（需先累积数据或补造历史样本） |
| Stage 4+ | 单客户钻取 / 处置工作流 / RBAC 分桶 | 见 stub §4「不在本 stub 范围」 |

建议：Stage 3 Task C/D 为最小可用单元，可一次 ship 到演示环境。

---

## 6. Phase 1 显式声明：本 Phase **不实装**

- ❌ 不碰 `web/` 任何文件（Phase 1 DoD 要求 `git diff --stat upstream/chore/l0-infra..HEAD -- web/` = 0 行）
- ❌ 不接 `/api/agent/alert/*` 端点
- ❌ 不做前端状态管理 / 路由配置

实装过程中若发现 yaml schema 不够用 / 色系变量缺失 / 卡片切分不合理 → **不要** 擅自改 yaml 或 taxonomy，请提 Q 给主 CLI 走 RFC 流程回到 Agent4 CLI 侧补规约。

---

## 7. 联系 & 交接

- Agent4 worker CLI 在 `feat/agent4-productize` 分支处于 idle 态，Phase 1 READY-FOR-REVIEW 后等主 CLI 合流
- 实装中任何数据源问题 → 提 Q-NNN 给主 CLI，由主 CLI 调度 Agent4 CLI 回应
- 本 ticket 的所有设计约束在 `docs/design/alert-dashboard-stub.md` 和 `docs/design/alert-trigger-reasons-taxonomy.md` —— 两文档是唯一权威
