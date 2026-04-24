# data-foundation (拟真数据底座) Phase 1 · **v2 返工版** Onboarding

**状态**：REJECT-V2 GO
**发布日期**：2026-04-24
**Signal 入口**：`PRODUCT-HARDENING-BATCH-1-V2-ACK`
**取代**：`docs/onboarding/data-foundation-phase-1.md`（v1 · 2026-04-23 · 已作废）
**参照决策**：`docs/handoff/decisions-log.md` Q-028 / A-028

---

## 0. 为什么 REJECT-V2（一眼看）

v1 批次的产物（`data/mock/wide-base/companies.yaml` + `data/mock/schemas/*.yaml` + `data/mock/deep-pillar/shortlist.md` + 15 份 pit 模板）**形态错**——错不在工作量，错在把数据底座做成了结构化 YAML，但**真实信贷 Agent 的消费形态不是 YAML**：

- **Agent6 / Agent3** 的输入是**客户提交的完整材料包**——文件夹 + pdf + xlsx + docx + 扫描件形态的异构材料，命名混乱、内容有矛盾（财报 vs 流水 vs 申报表三方口径差异）。`material_kb.py` 的核心能力是"从这堆乱七八糟的东西里解析"。用清洗过的 YAML 喂它 = **答案直接递嘴边** = 跑不出 Agent 的真实解析/抽取/抗噪能力。
- **Agent1 获客**的输入是**银行内部已成交客户画像 + 营销倾向 + 产品目录**（稳态内部 context），外部候选企业必须走 `SearchProvider` 实搜。v1 在 `wide-base/companies.yaml` mock 100 家"外部候选池" = **越界代工** = Agent1 的核心能力（外部实搜 + 相似度匹配）被偷掉。
- **Agent5 合规**的输入是**银行内部业务制度库**（SOP / 准入 / KYC / 风偏 / 审查清单），外部**新政策必须实搜**银保监/央行/国务院官网。v1 没 mock 内部制度、也没约束"不 mock 外部政策"——同样越界。

**Ground truth**：用户本地 `D:\刘野\众安\新建文件夹\2026.3.25续贷材料`（中锐网络续贷包）—— worker **可以 `ls` 看形态**，**不能复制内容**。这是真实客户提交材料的命名/格式/噪声基线。

**浮现的元规则** = **反结果导向第 5 原则 · 环境边界**：mock 给 Agent 稳态内部 context，不替它做"本该外搜的工作"。

详见 Q-028 / A-028 决策记录。

---

## 1. 你是谁

你是 **data-foundation** worker CLI，负责 **5-7 天内** 按 v2 形态重建数据底座——聚焦 3 组 mock（深柱 5 家完整材料包 + Agent1 内部 KB + Agent5 内部制度库），**不做宽基 100 家**（Agent1 不消费，做了也是浪费）。

- Worktree：`D:/claude code/demo-data-foundation`
- 分支：`feat/data-foundation`（延用，覆盖式返工）
- Upstream remote：`D:/claude code/credit_report_agent_work`

---

## 2. 反"结果导向"的 **5 条**设计原则（PM 底线 · 不可违）

| # | 原则 | 本批次具体落地 |
|---|---|---|
| 1 | **盲测法** | PM 设计坑，worker 不看答卷。深柱 5 家**零答案字段**——不写 difficulty、不写 tags、不写 benchmark_ref、README 不标注"这家是 extreme 档" |
| 2 | **难度分层** | 深柱 5 家覆盖 easy 1 / medium 2 / hard 1 / extreme 1（档位由 PM 内部维护，产物里不出现） |
| 3 | **真实来源锚定** | 文件命名 / 格式 / 噪声模式参照 `D:\刘野\众安\新建文件夹\2026.3.25续贷材料`（中锐续贷包）。数字保量级 |
| 4 | **脱敏再造** | 企业名必须脱敏——不能是真实存续企业。财报/流水数字打乱+保量级。法人身份证/银行卡号全部 mock |
| 5 | **环境边界** 🆕 | mock 给 Agent 稳态**内部 context**，不替它做**外搜的工作**：Agent1 只 mock 内部 KB（历史客户 + 营销倾向 + 产品目录），**不 mock 外部候选企业池**；Agent5 只 mock 内部制度库（SOP + 准入 + KYC + 风偏 + 审查清单），**不 mock 外部新政策** |

第 5 条是本次 REJECT-V2 浮现的新原则，已同步入项目 CLAUDE.md §3.4。

---

## 3. 本批次任务

### Task A — 推翻老 schema + 新建 v2 目录结构

**目标**：作废 v1 yaml 层，按 3 组 mock 建新目录骨架 + README。

**模块路径**：

- **删**（`git rm -r`）：
  - `data/mock/wide-base/`
  - `data/mock/schemas/`
  - `data/mock/deep-pillar/shortlist.md`
  - `data/mock/deep-pillar/pits/`
- **保留**：`data/mock/deep-pillar/` 目录本身（Task B 用）
- **新建目录**：
  - `data/mock/deep-pillar/`（Task B 填 5 家材料包）
  - `data/mock/channel-kb/`（Task C 填 Agent1 内部 KB）
  - `data/mock/compliance-kb/`（Task D 填 Agent5 内部制度库）
- **新建 README**：`data/mock/README.md`
  - 架构哲学：Entity-first + 环境边界（引 CLAUDE.md §3.4 新第 5 条）
  - 3 组 mock 的消费方对应（Agent6/3 ← deep-pillar · Agent1 ← channel-kb · Agent5 ← compliance-kb）
  - 明确说明"本目录不含 Agent1 外部候选池 / Agent5 外部政策 —— 那是 `SearchProvider` 的活"
  - **不写** 难度档、不写 benchmark、不写埋坑答案

**指标/验证**：

- v1 5 个产物全部删净（`git status` 应显示 `deleted:` × 5）
- README 阅读第三方能理解"为什么没有宽基 100 家"
- 3 组子目录空壳就绪

**工作量**：S（0.5 天）
**完成信号**：`Signal: DATA-SCHEMA-V2-DONE`（同时 embedded `Signal: DATA-LEGACY-PURGED` 在删除 commit 里）

---

### Task B — 深柱 5 家完整材料包（Agent6 + Agent3 共用）

**目标**：产 5 家企业的**真实形态**材料包，每家一个文件夹，内含 20-40 份异构原始文件。

**目录布局**：

```
data/mock/deep-pillar/
  DP001_<脱敏企业名>/
    <20-40 份材料，命名混乱、跨 2022-2025>
  DP002_<脱敏企业名>/
  DP003_<脱敏企业名>/
  DP004_<脱敏企业名>/
  DP005_<脱敏企业名>/
```

**每家必含 6 大类材料**（参照中锐续贷包形态）：

| 类别 | 形态示例 | 份数参考 |
|---|---|---|
| **资质类** | 营业执照副本 pdf / 公司章程 pdf / 法人身份证 pdf / 资质表 xls / 专利证书明细 xlsx / 高新认定公告 pdf | 5-8 份 |
| **场所类** | 场所租赁合同 pdf（1-3 份，可含历次续签） | 1-3 份 |
| **财务类** | 年度财务报表 xlsx（2022/2023/2024/2025 多年）+ 审计报告 pdf 扫描件形态（2023/2024） | 4-6 份 |
| **纳税类** | 完税证明 pdf（按所属期，多年）+ 增值税及附加税申报表 pdf（按月，多月） | 6-10 份 |
| **银行流水** | 子目录 `4、银行流水/` 下按银行 3-5 家分（工行/交行/建行/招行等），每家 1-3 份流水 pdf 或 xlsx | 5-12 份 |
| **补充材料** | 授信补充问题及材料 docx / 在建项目清单 xlsx / 其他定制补充件 | 2-4 份 |

**命名规则**（必须"真实不整洁"）：

- 允许序号前缀混乱：`00、xxx.xlsx` / `1、xxx.pdf` / `1、xxx（同序号重复）.pdf` / 无序号直写
- 允许中文 + 日期 + 空格混用：`2、审计报告2023年-德赢.pdf` / `3、税收完税证明202501-12所属期.pdf`
- 允许扩展名混用：`.pdf / .xlsx / .xls / .docx / .jpg`（扫描件形态）
- **禁止**统一规整命名（`DP001_01_营业执照.pdf` 这种就是偷懒结果导向）

**内容规则**（必须"有合理噪声与矛盾"）：

- **扫描件**：pdf 含 OCR 可识别文字但格式不齐（审计报告、完税证明首选此形态）
- **三方数字矛盾**（合理幅度）：营收在财报 / 申报表 / 流水之间 4800 / 5000 / 5200 万级别差异——**总量一致、细节不对齐**是常态。不要清洗成三方完全对齐
- **跨年**：2022-2025 四年材料都有，但不强求每年齐全（某些客户只有 3 年、某些有 4 年）
- **格式不齐**：xlsx 里混行合并、部分列空白、sheet 名五花八门

**难度分布**（PM 内部维护，产物零答案字段）：

| 档 | 家数 | PM 内部画像（**不得写进文件**） |
|---|---|---|
| easy | 1 | 资质齐、财务干净、流水规整、数字对得上 |
| medium | 2 | 多数齐，个别年份缺材料 / 申报表 vs 财报口径小偏差 |
| hard | 1 | 扫描件多、命名乱、跨银行流水拼接、个别关联交易线索 |
| extreme | 1 | 资质过期/财报与流水大偏差/担保或虚假授信线索，参照银保监处罚公告 |

**脱敏规则**：

- 企业名必须脱敏——不能是真实存续企业（worker 自造名，可参照行业+地区+编号拼接）
- 法人姓名、身份证号、银行卡号、联系电话全部 mock
- 财报/流水数字打乱但**保量级**（1 亿营收的企业不 mock 成 1 千万）

**零答案字段红线**：

- ❌ 不出现 `difficulty: easy/medium/hard/extreme`
- ❌ 不出现 `tags: [关联交易, 虚假授信, ...]`
- ❌ 不出现 `benchmark_ref: <某 A 股公司>`
- ❌ README 不得描述"DP003 是 hard 档，坑在关联交易"
- 产物对 worker 自己和 PM 以外的读者而言，应**只能看到材料本身**，难度与埋坑档由 PM 私下追踪

**工作量**：L（3-4 天，5 家 × 每家约 6 小时）
**完成信号**：`Signal: DATA-DEEP-PILLAR-5-DONE`

---

### Task C — Agent1 内部 KB（银行侧稳态 context）

**目标**：给 Agent1 的获客匹配能力提供**内部 context**——历史成交客户画像 + 营销倾向 + 产品目录。**不 mock 外部候选企业池**。

**目录布局**：

```
data/mock/channel-kb/
  historical-clients/        # 10-15 家已成交客户简要画像
    <脱敏企业名>.md / .docx
    ...
  marketing-preferences/     # 3-5 份银行营销倾向 docx
    2026-Q1-重点拓展.docx
    2026-Q2-区域重点.docx
    避开清单.docx
  product-catalog/           # 1 份银行自家信贷产品目录
    product-catalog.xlsx (或 .md)
```

**historical-clients/** 规格（10-15 家）：

- **每家 1 份简要画像**（非完整材料包——不是 deep-pillar 形态）
- 字段：企业名（脱敏）/ 行业 / 规模（营收、员工数）/ 成交产品（流贷/授信额度/期限）/ 授信额度 / 主要业务特征 / 风险偏好合规点
- 长度 1-3 页
- 行业分布：制造业占大头，穿插零售/服务/科技/外贸
- 档期跨越：近 3 年成交客户都有

**marketing-preferences/** 规格（3-5 份 docx）：

- 示例主题：
  - `2026-Q1-重点拓展.docx`：**精密制造 + 专精特新 + 年营收 5000万-3亿**
  - `2026-Q2-区域重点.docx`：**长三角 + 珠三角**
  - `避开清单.docx`：**商业地产 + 强周期基建 + 年营收 < 1000万 小微**
- 格式模拟"银行营销部月度/季度要点"——标题 + 条款 + 背景说明 + 落地口径

**product-catalog/** 规格（1 份）：

- xlsx 或 md 均可，字段：产品名 / 定位 / 适用客群 / 额度区间 / 利率 / 期限 / 风控要点
- 5-10 款产品（流贷 / 经营贷 / 专精特新贷 / 科技贷 / 供应链金融 等）

**环境边界红线**：

- ❌ 不生成 `候选企业.yaml` / `外部企业池.xlsx` / 任何看似"候选企业清单"的东西
- ❌ 不替 Agent1 做 `SearchProvider` 实搜的工作——那是 Agent1 的核心能力
- ✅ 只做"银行已知的事"：已成交客户、自家偏好、自家产品

**工作量**：M（1 天）
**完成信号**：`Signal: CHANNEL-KB-DONE`

---

### Task D — Agent5 内部制度库（银行侧稳态 context）

**目标**：给 Agent5 的合规扫描能力提供**内部制度库**——信贷 SOP / 客户准入 / KYC/AML / 风偏 / 审查清单。**不 mock 外部新政策**。

**目录布局**：

```
data/mock/compliance-kb/
  credit-sop/            # 信贷业务操作手册 5-8 份
  customer-admission/    # 客户准入标准 2-3 份
  kyc-aml/               # KYC / AML 操作规范 2-3 份
  risk-preference/       # 风险偏好政策 1-2 份
  review-checklists/     # 合规审查清单 2-3 份
```

**文件规格**：

- 全部 docx 格式（银行内部制度通常 word 下发）
- 每份体例模拟"银行内部 SOP"：
  - 标题带文号（例：`信贷业务操作手册-2025 版`）
  - 章节编号（一、(一)、1、(1)）
  - 修订日期 / 生效版本号 / 失效版本号
  - 条款项格式规范（条、款、项）
  - 页脚带"版本号 / 密级"等水印信息
- 长度 5-20 页不等
- 内容可参照公开银行业协会范本脱敏改写，**保留行文风格与术语浓度**

**示例主题**（worker 自选组合，覆盖 5 个子目录即可）：

- credit-sop：小微企业流贷操作手册、公司贷款调查报告撰写规范、授信审查要点、贷后检查流程、不良资产处置流程
- customer-admission：小微客户准入标准、对公客户准入标准、重点行业限制客群
- kyc-aml：KYC 尽职调查操作规范、AML 可疑交易识别手册、受益所有人识别规范
- risk-preference：2026 年授信风险偏好政策
- review-checklists：贷前合规审查清单、贷后合规审查清单、授信审查会审批要点

**环境边界红线**：

- ❌ 不生成 `银保监最新政策.pdf` / `央行 2026 新规.md` / 任何外部政策
- ❌ 不替 Agent5 做 `SearchProvider` 实搜外部法规的工作
- ✅ 只做"银行自己的制度"

**工作量**：M（1 天）
**完成信号**：`Signal: COMPLIANCE-KB-DONE`

---

### Task E — 全轨完成

所有 Task 做完：`Signal: READY-FOR-DATA-FOUNDATION-B1-V2-REVIEW`

---

## 4. 红线（v2 强化版）

### 老红线（v1 沿用）

- ❌ 不 commit 任何真实客户数据（所有脱敏后再入库）
- ❌ 不改 `agent_*/` / `web/**`（代码层归 code-urgent / code-arch）
- ❌ 不碰 evaluation 的地盘（rubric YAML 归 evaluation worker）
- ✅ `data/mock/` 全权你负责

### v2 新增红线

- ❌ **不做 yaml 清洗版本**：禁止产 `companies.yaml / entities.yaml / prefilled.yaml` 这类把原始材料清洗对齐后的 yaml（那是把答案递嘴边）
- ❌ **不碰外部世界**：Agent1 不 mock 外部候选企业池、Agent5 不 mock 外部政策（环境边界原则）
- ❌ **不标难度档 / 不标坑位答案**（盲测法）
- ✅ **形态真实**：必须文件夹 + 异构格式 + 命名噪声 + 三方数字矛盾 + 零答案字段
- ✅ 可以 `ls` 查看 `D:\刘野\众安\新建文件夹\2026.3.25续贷材料` 体会形态，但**绝不复制其内容**（脱敏再造原则）
- ✅ 可以 read `customer/` / `demo_data/` / `industry_cards/` 作为灵感，但不复用

---

## 5. 老产物处置（Task A 的一部分）

**全删**，不保留。删除命令建议 Task A 首个 commit 执行：

```bash
git rm -r data/mock/wide-base/
git rm -r data/mock/schemas/
git rm data/mock/deep-pillar/shortlist.md
git rm -r data/mock/deep-pillar/pits/
```

commit trailer 带 `Signal: DATA-LEGACY-PURGED`（embedded 在 Task A 的 commit 即可，不单占一 commit）。

**理由**：v1 产物**形态错**（yaml 把答案递嘴边）不是"基础还能用、打个补丁"——保留会造成 Agent 消费时混淆（到底读 yaml 还是读材料包）。整体推翻覆盖返工。

---

## 6. 预期工时

| Task | 工时 | 累计 |
|---|---|---|
| A 推翻+新目录 | 0.5 天 | 0.5 |
| B 深柱 5 家材料包 | 3-4 天 | 3.5-4.5 |
| C Agent1 内部 KB | 1 天 | 4.5-5.5 |
| D Agent5 内部制度库 | 1 天 | 5.5-6.5 |
| E 全轨+自检 | 0.5 天 | 6-7 |

**总工期**：5-7 天。比 v1（约 5 天）长，原因是 Task B 从"100 家 yaml"换成"5 家完整材料包"后单家工作量上来了。

---

## 7. ACK 协议

1. Resume → commit doc-only，trailer `Signal: PRODUCT-HARDENING-BATCH-1-V2-ACK`
2. ACK 后强制先做：
   - `git fetch origin chore/l0-infra`
   - `git log origin/chore/l0-infra --format='%h %s' -10`
   - 读 `docs/handoff/decisions-log.md` Q-028 / A-028
   - 读 本文（v2 onboarding）全文
   - 参照项目 `CLAUDE.md` §3.4 环境边界原则（反结果导向第 5 条）
3. Task A → B → C → D → E 顺序，每 Task 独立 commit 带对应 signal
4. 全 Task 完成 → `READY-FOR-DATA-FOUNDATION-B1-V2-REVIEW`

---

**维护者**：主 CLI
**下次更新触发**：主 CLI APPROVE v2 或用户再判方向变更
