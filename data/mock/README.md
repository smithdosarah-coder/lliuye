# `data/mock/` · 拟真数据底座（v2 · Entity-first + 环境边界）

**维护**：data-foundation worker（worktree `demo-data-foundation`）
**上游决策**：`docs/handoff/decisions-log.md` · Q-028 / A-028（2026-04-24 REJECT-V2 复盘）
**Onboarding**：`docs/onboarding/data-foundation-phase-1-v2.md`
**Runbook**：`docs/runbook/data-foundation.md`
**首建时间**：2026-04-24（v1 同日覆盖 · 形态错误）
**元规则**：项目 `CLAUDE.md` §3.5 反结果导向 5 原则

---

## v1 为什么被推翻（一眼看）

v1 产的是"YAML 清洗版"（100 家 companies.yaml + schemas + shortlist + 15 pits）——
看起来工整、校验通过，但**形态错**：

| Agent | v1 给的形态 | 真实消费形态 | 为什么错 |
|---|---|---|---|
| Agent6 报告 | `companies.yaml` 的企业结构化字段 | **客户提交的完整材料包**（pdf/xlsx/docx/扫描件文件夹 · 命名混乱 · 三方数字矛盾） | 绕过 `material_kb.py` 的解析能力，答案直接递嘴边 |
| Agent3 授信 | 同上（按 ReportJSON 消费） | 同上 | 同上 |
| Agent1 获客 | `wide-base/companies.yaml` 100 家"外部候选池" | 外部候选**应由 SearchProvider 实搜**；内部 KB 应是银行已成交画像 + 营销偏好 + 产品目录 | Agent1 核心能力（外搜 + 相似度匹配）被偷掉 |
| Agent5 合规 | 没 mock 任何内部制度库 / 也没约束外部政策不 mock | 内部制度库（SOP / 准入 / KYC / 风偏 / 审查清单）；新政策**应由 SearchProvider 实搜** | 越界 + 内部 context 缺失 |

新元规则（CLAUDE.md §3.5 第 5 条 **环境边界**）：
**mock 给 Agent "稳态内部 context"，不替它做"本该外搜的工作"。**

---

## v2 新结构（3 组 mock · 环境边界 aware）

```
data/mock/
├── README.md              ← 本文件（v2 · 2026-04-24）
├── deep-pillar/           ← Agent6 + Agent3 共用：5 家客户材料包（真实异构形态）
│   └── DP001_.../  DP002_.../  DP003_.../  DP004_.../  DP005_.../
├── channel-kb/            ← Agent1 内部 KB：历史客户 + 营销倾向 + 产品目录
│   ├── historical-clients/
│   ├── marketing-preferences/
│   └── product-catalog/
└── compliance-kb/         ← Agent5 内部制度库：SOP / 准入 / KYC / 风偏 / 审查清单
    ├── credit-sop/
    ├── customer-admission/
    ├── kyc-aml/
    ├── risk-preference/
    └── review-checklists/
```

**重点不变**：Agent1 **不 mock 外部候选企业池**；Agent5 **不 mock 外部新政策**——这两个是 Agent 的**核心能力**，不是 mock 的地盘。

---

## 形态硬线（v2 · 零答案字段）

v2 的所有 mock 产物必须同时满足：

| # | 形态要求 | 反面（一律拒收） |
|---|---|---|
| 1 | **真实消费形态** | Agent6/3 必须文件夹+异构文件；Agent1/5 必须文档库（docx 为主） |
| 2 | **零答案字段** | ❌ 不含 `difficulty / tags / benchmark_ref / match_score / risk_level / conflict_points / optimal_dsl` |
| 3 | **命名噪声** | ❌ 不得统一规整命名（`DP001_01_营业执照.pdf` 这种是懒惰结果导向）；✅ 允许序号前缀混乱 / 日期拼接 / 中文空格混用 |
| 4 | **三方合理矛盾** | ✅ 营收在财报/申报表/流水之间 4800/5000/5200 万级差异；❌ 不要清洗成三方完全对齐 |
| 5 | **跨年度** | ✅ 2022-2025 四年都有，但不强求每年齐全 |
| 6 | **扩展名混用** | ✅ `.pdf / .xlsx / .xls / .docx / .jpg` 混用；`.pdf` 要有真 PDF 头；`.xlsx` 要能被 openpyxl 读；`.docx` 要能被 python-docx 读 |
| 7 | **脱敏再造** | ✅ 企业名脱敏（不与真实存续企业同名）/ 法人身份证/卡号全 mock / 数字保量级打乱；❌ 不抄真实客户资料 |

---

## 消费方指南

### Agent6 报告（deep-pillar/）

```python
# 伪代码 · 消费真实形态
from pathlib import Path
from material_kb import parse_client_folder

client_dir = Path("data/mock/deep-pillar/DP003_<某企业>")
kb = parse_client_folder(client_dir)  # material_kb 的核心能力：从异构文件解析
```

**不得**预读"这是 medium 档"之类的元数据——那是 PM 内部追踪，产物里没有。

### Agent3 授信（deep-pillar/ + Agent6 ReportJSON）

先跑 Agent6 取 ReportJSON，再消费同一家 `DP00X/` 的原始材料做四维评分。

### Agent1 获客（channel-kb/）

```python
# 内部 KB 消费
from channel_kb import load_historical, load_preferences, load_catalog

hist = load_historical("data/mock/channel-kb/historical-clients/")
prefs = load_preferences("data/mock/channel-kb/marketing-preferences/")
products = load_catalog("data/mock/channel-kb/product-catalog/")

# 外部候选企业走 SearchProvider 实搜（本底座不 mock）
candidates = search_provider.search(seed=hist, criteria=prefs)
```

### Agent5 合规（compliance-kb/）

```python
# 内部制度库消费
from compliance_kb import load_sops

sops = load_sops("data/mock/compliance-kb/")  # 5 个子目录全 docx

# 外部新政策走 SearchProvider 实搜（本底座不 mock）
new_policies = search_provider.search_regulatory(since="2025-01-01")
```

### Agent4 预警 / Agent2 风控

**本次 v2 Phase 1 不覆盖**。Agent4 的在贷客户池 + 信号流、Agent2 的历史样本 CSV 放到后续 Phase 2 / Phase 3 另起 onboarding 单独规划。

---

## 红线（v2 强化）

| # | 红线 | 为什么 |
|---|---|---|
| R1 | ❌ 不产 yaml 清洗版本 | 形态错误根因 |
| R2 | ❌ 不 mock 外部候选企业池 / 外部新政策 | 环境边界原则（§3.5 #5）|
| R3 | ❌ 不标难度档 / 坑位答案字段 | 盲测法（§3.5 #1）|
| R4 | ❌ 不与真实存续企业同名 | 脱敏再造（§3.5 #4）|
| R5 | ❌ 不改 `agent_*/` / `web/**` / `evaluation/` | worker 边界 |
| R6 | ❌ 不复制 `D:/刘野/众安/新建文件夹/2026.3.25续贷材料` 任何内容 | ground truth 仅供形态参考 |
| R7 | ✅ 可以 `ls` 中锐续贷包看形态（命名 / 分类 / 子目录 / 扩展名） | 真实来源锚定（§3.5 #3）|
| R8 | ✅ 可以用 Python 生成脚本批量产材料（reportlab/openpyxl/python-docx） | 工具层手段，不是产出物 |

---

## 版本与迭代

- **v2.0**（2026-04-24）：REJECT-V2 返工；3 组 mock 形态对齐真实消费口径；5 原则 + 环境边界首次入 CLAUDE.md §3.5
- **v2.1**（待定）：Phase 2 Agent4 / Phase 3 Agent2 mock 底座补齐
- **v2.2+**：按客户反馈扩 deep-pillar 至 10-20 家 / 接真实企查查等外部源做混合底座

重大调整走 `decisions-log.md` Q/A 流程，不现场改规则。

---

## 工作流记录（供 review）

本次 Batch 1-V2 产物：
- Task A `DATA-LEGACY-PURGED` + `DATA-SCHEMA-V2-DONE`：删 v1 yaml 层 + 建 v2 骨架
- Task B `DATA-DEEP-PILLAR-5-DONE`：5 家深柱材料包（生成脚本在 `_gen/`）
- Task C `CHANNEL-KB-DONE`：Agent1 channel-kb
- Task D `COMPLIANCE-KB-DONE`：Agent5 compliance-kb
- Task E `READY-FOR-DATA-FOUNDATION-B1-V2-REVIEW`：全轨完成

各 Task 独立 commit · trailer 对齐 · 见 `git log feat/data-foundation`。
