# Agent4 预警 · 仪表盘设计稿（低 fidelity）

**所属 Phase**：Phase 1 Task D（L1 bank delivery DoD gap —— 从「能跑」推到「有面可交付」）
**Fidelity**：**低**（文字 + ASCII wireframe），不出 HTML mockup
**数据源**：`evaluation/manual/4_YYYYMMDD.yaml`（Task A runtime dump schema） + 未来 `/api/agent/alert/daily` 端点（**本 Phase 不实装**）
**色系变量源**：`docs/design/platform-shell-v1.md`（4 主题 `data-theme` + `--g0..--g7` 8 档渐变）
**实装归属**：**frontend Stage 3**（见 `docs/progress/agent4-phase-1-frontend-handoff.md` ticket），Phase 1 不碰 `web/`
**日期**：2026-04-19

---

## 0. 全局约定

- **视图归属**：`platform-shell-v1` 的 **「AI 助手 › Agent4 预警」 tile**，不开顶栏新 tab
- **日期游标**：默认 = 当日最新 runtime dump（`generated_at` 最大）；允许下拉切日
- **空态**：runtime yaml 缺失 → 显示「今日未产出扫描结果，请检查 `py -m agent_alert.runtime_dump` pipeline」，不展示假数据
- **前端**：**禁止** 自己推断 grade 分布 / trigger_reasons；所有数字 100% 来自 yaml 字段（对齐 `docs/design/alert-trigger-reasons-taxonomy.md` §4 绝对红线）
- **可访问性**：3 卡片皆支持键盘 tab + ARIA label「红灯客户 X 家 / 较昨日 +Y」；不依赖颜色传递语义

---

## 1. 卡片 A · 分级客户数（Grade Counts）

### 目的
客户经理进入「今日视图」第一眼就知道当前在贷客户池的风险水位；红灯数是处置优先级的第一信号。

### ASCII wireframe

```
┌─────────────────────────────────────────────────────┐
│ 今日扫描 · 2026-04-19 09:03Z       共 100 家客户     │
├─────────────────────────────────────────────────────┤
│                                                      │
│    🔴  红灯 3            🟡  黄灯 7      🟢 绿灯 90  │
│   ↑ +1 较昨日         → 持平           ↓ -1 较昨日   │
│                                                      │
│  [ 处置红灯 → ]   [ 查看黄灯 → ]                     │
└─────────────────────────────────────────────────────┘
```

### 数据源（字段级映射）

| UI 元素 | yaml 字段 | 计算 |
|---|---|---|
| 总客户数 | `len(customers)` | count |
| 红灯数 | `[c for c in customers if c.grade == "red"]` | count |
| 黄灯数 | `c.grade == "yellow"` | count |
| 绿灯数 | `c.grade == "green"` | count |
| 环比 | 取前一日 `evaluation/manual/4_<YYYYMMDD-1>.yaml`，按 entity_id 做 diff | 差值 |
| 扫描时间戳 | `generated_at` | ISO-8601 原样渲染 |

### 前端交互约定
- 卡片标题「今日扫描」点击 → 弹出「数据来源」浮层，展示 yaml 路径 + `generated_at` + `source.git_commit`（审计追溯）
- 红灯数 click → 跳转到「AI 助手 › Agent4 › 红灯榜单」子视图（本 stub 不详述，Stage 3 另议）
- 环比箭头：上升红字 / 下降灰字 / 持平中性；无昨日数据 → 显示「首日扫描，无环比」

### 色系 hook（4 主题）

| 元素 | var | Canvas | Matcha | Dusk | Crimson |
|---|---|---|---|---|---|
| 红灯 badge 底 | `--g7` | `#163025` 墨绿 ❌ **不用做红** → 改用 `--accent` 暖锚色 | | | |
| 红灯 badge 字 | `--ch-96` 白 | | | | |
| 黄灯 badge 底 | `--g4` | `#D4653F` 橙红 | `#5E8A57` | `#B14774` | `#6E1911` |
| 绿灯 badge 底 | `--g2` 浅暖 | | | | |
| 卡片外框 | `--ink-08` 墨色 8% 透明 | | | | |

**红灯颜色提示**：Canvas 主题的 `--g7` 是墨绿而非红，作为「红灯」会产生语义冲突。Stage 3 实装时红灯用 `--accent`（每主题定义的暖锚色，Canvas 是橙红 `#D5321E` 系）+ 🔴 emoji 兜底，避免色变语变。

---

## 2. 卡片 B · 触发原因码分布（Trigger Reasons）

### 目的
客户经理看完「有几家红」之后第二问：「是外部出事还是内部越线？」——交叉命中（`cross_hit`）是 Agent4 核心价值点（外部坏信号 × 内部制度同时响应），必须视觉高亮。

### ASCII wireframe

```
┌─────────────────────────────────────────────────────┐
│ 红/黄灯触发原因分布 (N=10)                            │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ████████████░░░░░░░░░░░░░░  external_signal  5      │
│  ██████░░░░░░░░░░░░░░░░░░░░  internal_rule    3      │
│  ████████████████▓▓▓▓▓▓▓▓▓▓  cross_hit       2  ⭐    │
│                                                      │
│  ⭐ 交叉命中 — 建议优先处置                            │
└─────────────────────────────────────────────────────┘
```

### 数据源

| UI 元素 | yaml 字段 | 计算 |
|---|---|---|
| 分母 N | 红灯 + 黄灯客户数 | `sum(c.grade in ("red","yellow") for c in customers)` |
| external_signal 条 | `sum("external_signal" in c.trigger_reasons for c in red_yellow)` | |
| internal_rule 条 | 同上，key=`internal_rule` | |
| cross_hit 条 | 同上，key=`cross_hit` | |
| 高亮标 | `cross_hit > 0` | bool |

**契约**：`trigger_reasons` 枚举封闭集 = `{external_signal, internal_rule, cross_hit}`，见 `docs/design/alert-trigger-reasons-taxonomy.md`。前端**不做**关键词推断/兜底分类，直接消费 yaml 字段。

### 前端交互约定
- 每条点击 → 展开该枚举下的客户名单（显示 entity_id + name + grade）
- `cross_hit` 条默认展开（核心价值），其他收起
- 分母 N 悬浮 tooltip：「仅统计红/黄灯客户；绿灯客户不参与分布」（解释为何 N ≠ 总客户数）

### 色系 hook（对齐 taxonomy §4）

| 枚举值 | var | 形态 |
|---|---|---|
| `external_signal` | `--g3`（中间档暖色） | 标签 · 外部 |
| `internal_rule` | `--g5`（偏冷档） | 标签 · 内部 |
| `cross_hit` | `--g7`（最深档）+ 粗描边 `--accent` | 标签 · 交叉命中 · ⭐ 优先 |

---

## 3. 卡片 C · 近 30 天趋势（Daily Trend）

### 目的
客户经理要看「这周风险在升还是在降」。单日数据只是点，连续 30 天才能判断趋势并触发上报支行会议。

### ASCII wireframe

```
┌─────────────────────────────────────────────────────┐
│ 近 30 天 · 红灯客户数趋势                             │
├─────────────────────────────────────────────────────┤
│                                                      │
│  红灯数 ●                                             │
│    5 ┤       ●                              ●        │
│    4 ┤     ●   ●●●                        ●          │
│    3 ┤●● ●       ●●●                    ●  ●  ←today │
│    2 ┤    ●        ● ●●                ●             │
│    1 ┤                  ●●●●●●●●●●●                  │
│    0 └──────────────────────────────────────────     │
│      03-21    03-28    04-04    04-11   04-18        │
│                                                      │
│  原因码来源面积图（堆叠）                              │
│   external_signal ▓ internal_rule ░ cross_hit ▒      │
└─────────────────────────────────────────────────────┘
```

### 数据源

| UI 元素 | yaml 字段 / 路径 | 计算 |
|---|---|---|
| X 轴 | 取最近 30 个 `evaluation/manual/4_YYYYMMDD.yaml` 文件的 `generated_at` | glob + sort |
| 红灯折线 Y | 每个 yaml 的 `sum(c.grade == "red")` | count per file |
| 原因码面积堆叠 | 每日 `trigger_reasons` tally 的 3 枚举计数 | count per file per reason |
| 缺失日 | 文件不存在 → 断点（不内插，诚实） | null gap |

**数据源路径契约**：`evaluation/manual/4_{YYYYMMDD}.yaml`，`YYYYMMDD` 为 UTC 日期戳（对齐 `generated_at`）。

### 前端交互约定
- 悬浮某日 → tooltip 显示该日 `{red: X, yellow: Y, green: Z, reasons: {...}}`
- 缺失日 X 轴保留刻度但折线断开，tooltip 提示「该日无扫描产出」
- 「今日」位置标 `←today` 游标，颜色用 `--accent`

### 色系 hook

| 元素 | var |
|---|---|
| 折线 | `--accent` |
| `external_signal` 面积 | `--g3` |
| `internal_rule` 面积 | `--g5` |
| `cross_hit` 面积 | `--g7` |
| 网格线 | `--ink-08` |
| 今日游标 | `--accent` + 粗 |

---

## 4. 不在本 stub 范围

以下列为**已识别但本 Phase 不做**，避免 scope creep：

- ❌ 处置工作流（红灯客户 → 提级审批 → 缓释动作反馈），属 L4 可演进
- ❌ 单客户钻取页（点一家客户看证据链全貌），属 Stage 3 另起 stub
- ❌ 跨支行 / 跨 RM 分桶视图，需先解决 RBAC（Phase 2 Batch 2）
- ❌ 告警推送（飞书 / 邮件 / 短信），需先接通告警通道
- ❌ 仪表盘过滤器（按行业 / 按规模 / 按授信金额），需先定义客户属性字段

---

## 5. 交付物链路

- 本文档 · `docs/design/alert-dashboard-stub.md`（主 CLI 只读）
- ticket 移交 · `docs/progress/agent4-phase-1-frontend-handoff.md`（本 Phase 同期新建）
- 运行时数据源 · `evaluation/manual/4_YYYYMMDD.yaml`（Task A 落地 schema）
- 枚举契约 · `docs/design/alert-trigger-reasons-taxonomy.md`（Task C 落地）
- 色系变量 · `docs/design/platform-shell-v1.md` §3（4 主题 `--g0..--g7`）

---

## 6. 变更约束

- 本 stub 的 3 卡片切分、数据源契约、枚举色系映射为**低 fidelity 定型**；frontend Stage 3 实装可细化交互 / 补空态，但不得擅自增卡片或改字段源
- 任何增卡片 / 改 yaml schema 的 PR 必须先更本 stub 再改代码（对齐 CLAUDE.md「约束先行」）
