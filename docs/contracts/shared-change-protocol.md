# 共享模块变更协议（Shared Change Protocol） v1.0

**版本**：v1.0
**发布日期**：2026-04-18
**作者**：主 CLI（Pre-Phase-0）
**适用范围**：5 路并行的所有 worktree（`feat/agent{N}-productize`），主 CLI 自身不受限

---

## 0. 为什么需要这份协议

5 路并行开发时，多个 CC 同时改 `shared/` 或根目录共享文件 → merge 冲突 / 接口语义打架 / 回归 bug。

依赖矩阵实测：
- `shared/base_agent.py` 被 5 个子 Agent 全部依赖（极高风险）
- `shared/demo_ui.py` 被 5 个子 Agent 全部依赖（极高风险）
- `shared/kb_scan/*` 被 Agent1/4/5 共用（高风险）
- `shared/sources/router.py` 被 Agent1/3/5 共用（高风险）
- 根目录 `financial_analyzer.py` / `quality_check.py` / `quality_scorer.py` / `truth_fill.py` / `section_generator.py` / `material_kb.py` 被 Agent6 主用，但 Agent3 也消费（中-高风险）

**任何子 CLI 单方面改这些文件**——即使代码本身正确——都视为违反本协议，主 CLI 拒绝合并。

---

## 一、什么算"共享文件"

### 1.1 红区（绝对不许直接改，必须 RFC + 主 CLI 亲手或亲批）

| 路径 | 被谁用 | 改动风险 |
|---|---|---|
| `shared/base_agent.py` | 5/5 子 Agent | 改签名 = 全员 break |
| `shared/demo_ui.py` | 5/5 子 Agent | 改 layout = 全员视觉错位 |
| `shared/api_utils.py` | 5/5 + portal | 改 SSE 编码 = 前端崩 |
| `api_server.py` | portal | 改 mounting = 全 Agent 路由消失 |
| `shared/enterprise_profile.py` | Agent3 / Agent6 | 改字段 = handoff 协议破裂 |
| `shared/report_handoff.py` | Agent3 ← Agent6 | 同上 |
| `agent_report/enterprise_profile.py` | Agent3 / Agent6 | 同上（authoritative 版本） |
| 根目录 `financial_analyzer.py` | Agent3 / Agent6 | 改公式 = 已有报告倒退 |
| 根目录 `quality_check.py` | Agent6（QC Blocker） | 改阈值 = 突然全部不过 |
| 根目录 `quality_scorer.py` | Agent6 | 同上 |
| 根目录 `truth_fill.py` | Agent6 | 改字段映射 = 报告字段错位 |
| 根目录 `section_generator.py` | Agent6 | Evidence-First 三阶段核心 |
| 根目录 `material_kb.py` | Agent6 / Agent3 | 改解析 = 输入入参变 |

### 1.2 黄区（先扫描影响、再改）

| 路径 | 被谁用 | 改动条件 |
|---|---|---|
| `shared/kb_scan/*` | Agent1 / Agent4 / Agent5 | 仅追加新方法 / 新 provider，不删不改既有签名 |
| `shared/sources/router.py` | Agent1 / Agent3 / Agent5 | 仅追加新 source，不改 router 路由策略 |
| `shared/sources/base.py` | 同上 | 仅追加 method，不改 BaseSource Protocol |
| `shared/sources/impls/*.py` | 各源独立 | 改一个 impl 不影响其他，但破坏性变更需 RFC |

### 1.3 绿区（自由改）

- `agent_<own>/`（你自己 Agent 的目录）
- `web/src/app/<own>/`（你自己 Agent 的页面）
- `agent_<own>/api.py`（你自己的 FastAPI 路由模块）
- `agent_<own>/tests/`（你自己的测试）
- 你自己 Agent 的 `evaluation/` 配置 + 结果

---

## 二、什么算"变更"

| 变更类型 | 红区操作 | 黄区操作 | 绿区操作 |
|---|---|---|---|
| 改函数 / 类的**签名** | 🚫 绝对不许 | RFC + 主 CLI 批 | 自由 |
| 改函数 / 类的**返回结构** | 🚫 绝对不许 | RFC + 主 CLI 批 | 自由 |
| 改业务逻辑（不改签名） | RFC + 主 CLI 批 | 自由（但建议跑回归） | 自由 |
| 追加新方法 / 新字段 | RFC + 主 CLI 批 | 自由（向后兼容） | 自由 |
| 删除已有方法 / 字段 | 🚫 绝对不许 | RFC + 主 CLI 批 | 自由 |
| 改 import 来源 / 路径 | RFC + 主 CLI 批 | 自由 | 自由 |
| 改文档 / 注释 | 自由（commit message 注明） | 自由 | 自由 |
| 改 type hint（不改运行时） | 自由 | 自由 | 自由 |

---

## 三、RFC 流程（黄/红区变更必走）

### 3.1 子 CLI 发起 RFC

在自己 worktree 写 `docs/contracts/rfc/YYYYMMDD-<short-desc>.md`：

```markdown
# RFC: <一句话标题>

**发起人**：Agent{N} CC
**日期**：2026-04-XX
**变更类型**：[红区 / 黄区]
**目标文件**：`shared/xxx.py`

## 现状
<引用现状代码 + 行号>

## 提议
<新代码 / 新签名>

## 影响面
- Agent{X} 用了这个函数 N 处：<grep 结果列表>
- Agent{Y} 用了这个函数 M 处：<grep 结果列表>

## 兼容性
- 向后兼容 / 破坏性
- 若破坏性，迁移路径

## 替代方案
<至少给一个 alternative，说明为什么本方案优>

## 验证计划
- 主 CLI 批准后，谁来改、谁来测、什么基线不能倒退
```

### 3.2 主 CLI Review

主 CLI 在 24h 内（工作日）回复：
- ✅ APPROVED + 谁动手（主 CLI 自己 or 委派子 CLI）
- ⚠️ CHANGES_REQUESTED + 改进意见
- ❌ REJECTED + 原因

### 3.3 落地

- **红区变更**：主 CLI 亲自动手（不委派），子 CLI 等
- **黄区变更**：可委派给发起 CC，但需在 PR/commit 引用 RFC 路径
- **跨 Agent 影响**：主 CLI 通知所有受影响 CC rebase + 跑自检

---

## 四、违反协议的处理

| 行为 | 后果 |
|---|---|
| 子 CLI 单方改红区 | 主 CLI **拒绝合并**，要求 revert + 走 RFC |
| 子 CLI 单方改黄区，未跑影响面分析 | 主 CLI 要求补 RFC 后才合并 |
| 子 CLI 改了红区但没标注 | 视为隐瞒，触发 DoD §10 红线（"动公共基础设施未通知主 CLI"）→ **停工** |
| 反复违反（≥2 次） | 主 CLI 收回该 worktree，任务由其他 CC 接手 |

---

## 五、紧急例外

仅以下情况允许子 CLI 直接改红区（事后补 RFC）：

1. **CVE 级安全 bug**（硬编码密钥泄漏、SQL 注入等）：先修 + commit + 立即 ping 主 CLI
2. **生产已挂**（demo.liuye.me 504 / 500）：先恢复 + commit + 事后写复盘
3. **主 CLI 离线 > 24h** 且阻塞自己 Phase 1 任务推进：先在自己 branch 改 + 不 merge + ping

非以上情况，等 RFC 通过。

---

## 六、自检清单（commit 前自问）

```
我即将 commit 的文件里，有没有：
  □ shared/ 下任何文件？           → 黄/红区，先 RFC
  □ 根目录 financial_analyzer.py
    或 quality_check.py
    或 truth_fill.py
    或 section_generator.py
    或 material_kb.py？            → 红区，先 RFC
  □ api_server.py？               → 红区，先 RFC
  □ agent_report/enterprise_profile.py？ → 红区，先 RFC

如果以上全部 NO → 自由 commit
任意 YES → 停下，写 RFC
```

---

## 七、版本演进

- v1.0 (2026-04-18)：建立基线，划分红/黄/绿区，定 RFC 流程
- 子 CLI 发现新共享文件未列入：发 RFC 申请加入红/黄区，主 CLI 评估后入库
- Phase 1 结束后复盘：哪些红区文件 RFC 通过率高 → 考虑下放到黄区
