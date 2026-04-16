# PRD：全渠道流量匹配智能体 v2.0

**版本**：v2.0（完全替换 v1.0）
**日期**：2026-04-14
**作者**：刘野 / 众安信科 AI 中台团队
**文档性质**：Demo 改造产品需求文档
**所属系统**：众安信科 · 乾策平台（X-Nexus）· 信贷 AI 智能体矩阵 Agent #1
**代号**：Agent1（channel / lookalike）

---

## 0. 版本说明

### 0.1 为什么要出 v2.0

v1.0 在客户演示的核心问题是：**Demo 形态是"单查工具"，客户一眼识破是假的**。客户最直白的质疑：
- "你输一家企业，我就给你一堆渠道——那还要 AI 干什么？人工也能查啊"
- "银行真正要的，不是'这家企业该给哪个产品'，而是'**我想获客一批和现有优质客户像的**'"
- "你扫的企业池有多大？怎么证明推出来的 10 家是最像的？"

v1.0 的"给企业输入 → 推荐渠道产品"本质上是**产品推荐工具**，不是**获客引擎**。真正的获客场景应当是：

> 客户经理上传"已有 100 家优质制造业客户名录" + "当地政府的专精特新扶持政策" → Agent 抽出"**理想客户画像**" → 遍历**外网企业池** → 找出和画像最像的 Top10 → 对每条线索推荐产品 + 话术。

v2.0 按"**知识库扫描范式**"重写。同时保留 v1.0 中"渠道规则 + 5 维评分"这个真正有业务价值的资产，复用为阶段④的"产品推荐"引擎。

### 0.2 v2.0 核心范式

本 PRD 遵循 **《共享架构_知识库扫描范式_v1.0.md》**。三个 Agent（1/4/5）共享同一套基础设施：`KnowledgeBase → ScanTargets → Matcher → HitList`。

Agent1 的特化定位：**look-alike 获客引擎（知识库驱动）**。

### 0.3 v2.0 与 v1.0 的差异对照（强制阅读）

| 维度 | v1.0 | v2.0 |
|---|---|---|
| **产品定位** | 企业画像→渠道推荐工具 | look-alike 获客引擎（KB 驱动） |
| **输入形态** | 手工填表（企业名/行业/规模） | 上传 3 类文件（客户名录+政策+行业指引） |
| **核心动作** | "推荐哪个渠道" | "找出和我现有客户像的新企业" |
| **扫描对象** | 13 个子渠道 | 外网企业池（Demo 50+ 家 mock） |
| **产出形态** | 5 大类 13 个产品推荐卡 | Top10 新客户线索 × 每条 Top3 产品 |
| **演示说服力** | 客户质疑"这不就是查表" | 证据链："扫了 500 家，Top10 是这 10 家，因为..." |
| **证据链** | 无 | 每条线索注明匹配理由 + 数据来源 |

#### v1.0 模块的保留/重写/废弃矩阵

| 模块 | 文件 | 动作 | 原因 |
|---|---|---|---|
| 渠道规则库 | `channel_rules.py` + `CHANNEL_CATALOG` | **保留（复用）** | 13 子渠道的规则本身是真实业务资产；v2.0 里用于阶段④"产品推荐" |
| 产品评分 | `scoring.py`（5 维权重/政策加分/地域加分） | **保留（复用）** | 真实的业务打分逻辑；v2.0 里用于"企业×产品"匹配度打分 |
| 提示词 | `prompts.py`（CHANNEL_SYSTEM_PROMPT / CHANNEL_ANALYSIS_PROMPT / CHANNEL_PARSE_PROMPT） | **部分保留** | 综合分析提示词逻辑可复用，但需重新组织 |
| Agent 主逻辑 | `agent.py` | **重写** | v1.0 流程是单查；v2.0 流程是 KB→扫描→打榜 |
| Gradio 前端 | `app_demo.py` / `app.py` | **重写** | 新交互范式（文件上传 + 画像卡 + 线索榜），原表单废弃 |
| 数据模型 | `scoring.ChannelRecommendation` | **保留** | 单个产品推荐结构 |
| —— | `knowledge_base.py` | **新建** | 上传文件 → KB 对象（继承共享架构） |
| —— | `search_provider.py` | **新建** | Mock/Web 企业搜索（继承共享架构） |
| —— | `profile_extractor.py` | **新建** | LLM 从 KB 抽"理想客户画像" |
| —— | `lead_finder.py` | **新建** | look-alike 匹配引擎（继承 Matcher） |
| —— | `product_recommender.py` | **新建** | 调 channel_rules + scoring 做产品推荐（包装层） |

---

## 1. 产品定位

### 1.1 一句话定位

**Agent1 是一个 look-alike 获客引擎**——银行客户经理上传已有优质客户名录和当前政策/行业指引，Agent 自动提取"理想客户画像"，扫描外网企业池，输出 Top10 相似新客户线索，每条附 Top3 银行产品推荐 + 差异化切入话术。

### 1.2 典型用户故事

> 某城商行普惠金融部老王，手上有 120 家优质制造业小微贷款客户。他刚看完浙江省发布的《制造业中小企业专精特新扶持实施方案》，想在杭州拓一批新的制造业客户。
>
> 过去：他要找行业协会要名录、去天眼查按行业筛选、手工对照政策条件筛……一周时间。
>
> 现在：他打开 Agent1，拖入"客户名录 Excel + 政策 Word + 行业指引 PDF"→ 30 秒后看到一张"理想客户画像卡"（"小型/年营收 3000-8000 万/浙江省内/具备专精特新或高新资质"）→ 确认画像后点"开始扫描"→ 2 分钟后拿到 Top10 候选企业线索（每条都写清楚"为什么像"+ 推 3 个产品 + 切入话术）→ 导出 Word 报告分给下属客户经理。

### 1.3 区别于 v1.0 的关键差异

v1.0 卖的是"**输入一家企业，输出推荐**"——客户经理脑子里得先有一家具体企业。
v2.0 卖的是"**告诉我你的现有优质客户是什么样的，我帮你找一堆像的**"——这才是银行获客部门的真实诉求。

---

## 2. Demo 目标

### 2.1 目标受众与证明目标

| 受众 | 关注点 | Demo 要证明什么 |
|---|---|---|
| 分管行长 / 普惠金融部负责人 | 获客效率、资源投入产出比 | 2 分钟输出 Top10 优质线索，替代人工一周工作量；证据链可审计 |
| 客户经理 | 线索质量、可直接使用的话术 | 每条线索都有"为什么像"+ 产品推荐 + 切入话术，客户经理打开电话即用 |
| 科技部 / 架构评审 | 技术合理性、可扩展性 | 架构按真实搜索设计，mock 只是填充层，切到生产只改一行；KB 支持行内真实政策库 |
| 合作行方 / 投资人 | 产品成熟度 | 演示流畅、前端专业、有证据链，不是"给个企业查一下"的浅层 demo |

### 2.2 核心论点

1. **知识库驱动**：客户上传自己的优质客户数据 + 当前政策，AI 读懂你的"客户长什么样"。
2. **外网主动扫描**：不是"等客户经理输企业"，而是"主动扫数万企业池，挑出像的"。
3. **look-alike 可解释**：Top10 每条都有相似度分数 + 匹配维度明细 + 原始证据。
4. **产品+话术闭环**：不止给线索，还给"客户经理拿起来就能用"的切入话术。

### 2.3 Demo 成功标准

- 全流程演示 < 4 分钟（含讲解）
- 零配置启动（Demo 内置 key、内置 2 个预置场景）
- 2 个预置场景 100% 跑通，Top10 结果稳定且符合业务直觉
- 可一键导出 Word 线索报告
- 架构通过评审："演示是 mock，但代码架构确实是按真搜索做的"

---

## 3. 核心工作流（5 阶段）

### 3.1 流程总览

```
┌─────────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐
│ ① 知识库加载  │→│ ② 画像抽取 │→│ ③ 外网搜索 │→│ ④ 匹配打分 │→│ ⑤ 产品推荐 │
│  3 类文件    │  │  IdealProfile│  │  候选企业池 │  │  Top10 线索 │  │  +话术    │
└─────────────┘  └───────────┘  └───────────┘  └───────────┘  └───────────┘
   上传           LLM 抽取        SearchProvider   SimilarityScorer  channel_rules
                                                                     + scoring（复用）
```

### 3.2 阶段 ① 知识库加载

**输入**：用户上传 3 类文件（允许任意组合，至少一类）
- **客户名录**：Excel/CSV，必须包含至少 `company_name`+`industry` 两列（其他字段可选）
- **政策文件**：Word/PDF，LLM 抽取扶持方向、目标行业、申报条件
- **行业指引**：Word/PDF，LLM 抽取当前业务重点、行业白名单/黑名单

**处理逻辑**（基于共享架构）：
```python
kb = KnowledgeBase(name="channel")
kb.load_files(uploaded_files)  # 自动分类 → companies/rules/clauses
```

**产出**：`KnowledgeBase` 对象，含：
- `kb.companies`：已有客户列表（`list[CompanyProfile]`）
- `kb.rules`：从政策抽出的规则（如"目标行业=专精特新""申报营收上限=5 亿"）
- `kb.clauses`：原始政策条款（证据溯源用）

**UI 反馈**：
- 文件识别成功显示绿色勾号 + 行数（"客户名录：加载 127 行" / "政策文件：抽取 18 条规则"）
- 失败时显示具体错误（"第 3 列 industry 字段缺失"）

### 3.3 阶段 ② 画像抽取

**输入**：`KnowledgeBase` 对象

**处理逻辑**：
1. 聚合已有客户名录的统计特征（行业分布/规模分布/地域分布/标签频度）
2. 读取政策规则（得出"当前扶持什么/限制什么"）
3. LLM 合成 `IdealProfile`

**LLM 调用（Prompt 1：画像抽取）**：
```
【已有客户名录统计】
- 行业 TOP5: 制造业 42%, 批发 18%, 零售 11%, 建筑 9%, 其他 20%
- 规模分布: 小型 68%, 微型 22%, 中型 10%
- 地域分布: 浙江 65%, 江苏 20%, 上海 15%
- 共性标签: 专精特新(32%) / 高新技术(28%) / 供应链核心供应商(15%)

【当前政策导向】
《浙江省专精特新"小巨人"培育方案》关键条款：
- 目标行业：智能制造、生物医药、新一代信息技术、新材料
- 营收范围：1000 万 - 5 亿
- 要求：2 项以上发明专利 或 省级以上研发机构

【行业指引】
当前季度重点拓展：智能制造、新材料
暂缓拓展：房地产上下游、高污染行业

请综合以上信息，输出"理想客户画像"JSON：
{
  "name": "...",
  "target_industries": [...],
  "target_sub_industries": [...],
  "target_regions": [...],
  "scale_range": [...],
  "revenue_range": [min, max],
  "must_have_tags": [...],
  "nice_to_have_tags": [...],
  "exclude_tags": [...],
  "policy_context": "...",
  "reasoning": "解释为什么这样定义画像"
}
```

**产出**：`IdealProfile` 对象

**UI 反馈**：展示画像卡，**字段可编辑**（客户经理可微调，比如把"营收上限"从 5 亿改成 2 亿）

### 3.4 阶段 ③ 外网搜索

**输入**：`IdealProfile`

**处理逻辑**：
1. 基于画像生成 3-5 条搜索 query
   - 例：`"杭州 专精特新 智能制造 小型企业"`
   - 例：`"浙江 发明专利 新材料 小巨人"`
2. 每条 query 调 `SearchProvider.search_companies()`
3. 去重 + 合并成候选企业池

```python
provider = build_search_provider(demo_mode=settings.DEMO_MODE)
candidates = []
for query in self._generate_queries(ideal_profile):
    results = provider.search_companies(query, filters={
        "industry": ideal_profile.target_industries,
        "region": ideal_profile.target_regions,
        "scale": ideal_profile.scale_range,
    }, limit=50)
    candidates.extend(results)
candidates = self._dedup(candidates)
```

**产出**：候选企业池 `list[CompanyProfile]`（Demo 量级 50-200 家）

**UI 反馈**（实时）：
- "正在搜索 query 1/4：杭州 专精特新 智能制造 小型..." → "找到 38 家"
- "正在搜索 query 2/4：..."
- 累计候选计数实时滚动

### 3.5 阶段 ④ 匹配打分

**输入**：候选企业池 + `IdealProfile` + `kb.companies`（已有客户作为"样本锚"）

**处理逻辑**（两阶段打分）：

**阶段 4a：画像相似度**（基于共享架构 `SimilarityScorer`）
```python
scorer = SimilarityScorer(weights={
    "industry": 0.30, "sub_industry": 0.15,
    "region": 0.20, "scale": 0.15, "tags": 0.20,
})
for cand in candidates:
    profile_score = scorer.score_against_profile(cand, ideal_profile)
```

**阶段 4b：样本锚相似度**（锦上添花，保证"真像"）
```python
# 对每个候选，找 kb.companies 中最像的 3 家作为"相似样本锚"
for cand in candidates:
    top3_anchors = scorer.top_k_similar(cand, kb.companies, k=3)
    anchor_avg = mean(scorer.score(anchor, cand) for anchor in top3_anchors)
    cand.final_score = 0.6 * profile_score + 0.4 * anchor_avg
    cand.evidence = top3_anchors  # 证据链：因为和 XX/YY/ZZ 相似
```

**阶段 4c：判级 + Top10**（共享架构 `HitRanker`）
```python
ranker = HitRanker(top_n=10, red_threshold=80, yellow_threshold=65)
hit_list = ranker.rank(candidates, agent_name="channel", ...)
```

**产出**：Top10 `HitList`

### 3.6 阶段 ⑤ 产品推荐

**输入**：Top10 线索（每条 = 一个 `CompanyProfile`）

**处理逻辑**（复用 v1.0 资产）：
```python
# 对每条线索，调用原 channel_rules.match_channels() + scoring.rank_recommendations()
for hit in hit_list.hits:
    profile = hit.target.payload  # CompanyProfile
    matched_channels = match_channels(profile.model_dump())     # v1.0 保留代码
    recommendations = rank_recommendations(profile.model_dump(), matched_channels)  # v1.0 保留代码
    top3_products = recommendations[:3]

    # LLM 生成切入话术（Prompt 3）
    pitch = self._generate_pitch(profile, top3_products, ideal_profile.policy_context)

    hit.extras["recommended_products"] = [p.model_dump() for p in top3_products]
    hit.extras["pitch_script"] = pitch
```

**产出**：`HitList`（每条 `HitItem.extras` 注入 `recommended_products` 和 `pitch_script`）

---

## 4. 前端交互设计

### 4.1 整体布局（桌面端 1440px 基准）

```
+==========================================================================+
|  [众安信科 LOGO]  乾策平台 / 全渠道流量匹配（look-alike 获客）  [导出 Word] |
+==========================================================================+
|                                                                          |
|  ┌─ A 上传区 ────────────────┐  ┌─ C 理想客户画像 ─────────────────────┐  |
|  │                           │  │  [已抽取画像 / 可编辑]                │  |
|  │ [拖入文件或点击上传]       │  │  画像名:  [浙江制造业 look-alike...]  │  |
|  │                           │  │  目标行业: [智能制造][新材料][...]    │  |
|  │  客户名录.xlsx ✓ (127行)   │  │  目标地域: [浙江][江苏]              │  |
|  │  专精特新方案.docx ✓ (18规则)  │  规模:    [小型][微型]              │  |
|  │  行业指引.pdf ✓            │  │  营收范围: [1000万 - 5亿]            │  |
|  │                           │  │  必备标签: [专精特新 OR 高新]        │  |
|  │  [预置场景快选]            │  │  加分标签: [发明专利≥2][省级研发机构]│  |
|  │  [ 制造业 look-alike ]     │  │  排除: [房地产][高污染]              │  |
|  │  [ 科创企业 look-alike ]   │  │                                      │  |
|  │                           │  │  画像依据:                           │  |
|  │                           │  │  - 已有客户 65%浙江+制造业            │  |
|  │                           │  │  - 政策要求 2 项发明专利              │  |
|  │                           │  │  [编辑画像]      [开始扫描 →]        │  |
|  └───────────────────────────┘  └───────────────────────────────────────┘  |
|                                                                          |
|  ┌─ B 扫描进度 ────────────────────────────────────────────────────────┐  |
|  │  阶段 ③ 外网搜索:                                                  │  |
|  │  ├─ query 1/4: 杭州 专精特新 智能制造 小型...     ✓ 38 家          │  |
|  │  ├─ query 2/4: 浙江 发明专利 新材料...            ✓ 27 家          │  |
|  │  ├─ query 3/4: 苏州 小巨人 智能装备...            ⟳ 搜索中         │  |
|  │  累计候选: 65 家 (去重后)                                          │  |
|  └────────────────────────────────────────────────────────────────────┘  |
|                                                                          |
|  ┌─ D 线索榜单 Top10 ─────────────────────────────────────────────────┐  |
|  │                                                                    │  |
|  │  #1 [RED 91分] 杭州精工智造有限公司                                 │  |
|  │  ┌────────────────────────────────────────────────────────────┐   │  |
|  │  │ 行业: 智能制造 | 地域: 浙江杭州 | 规模: 小型 | 营收: 4200万  │   │  |
|  │  │                                                              │   │  |
|  │  │ 匹配理由:                                                    │   │  |
|  │  │  ✓ 行业与已有客户"宁波华联轴承"等高度相似（行业分 95）         │   │  |
|  │  │  ✓ 地域命中政策扶持区（浙江杭州）                            │   │  |
|  │  │  ✓ 具备 3 项发明专利（命中政策加分）                          │   │  |
|  │  │  ✓ 专精特新小巨人（必备标签）                                │   │  |
|  │  │                                                              │   │  |
|  │  │ 推荐产品 Top 3:                                              │   │  |
|  │  │  [科技金融] 专精特新企业贷  93 分  额度 2000 万              │   │  |
|  │  │  [科技金融] 知识产权质押贷  87 分  额度 1000 万              │   │  |
|  │  │  [普惠金融] 小微企业信用贷  82 分  额度 1000 万              │   │  |
|  │  │                                                              │   │  |
|  │  │ 切入话术:                                                    │   │  |
|  │  │  "张总好，浙江省专精特新小巨人培育方案您肯定熟悉，我们行针对  │   │  |
|  │  │   这批企业有专项产品：最高 2000 万、利率下浮 50BP、知识产权    │   │  |
|  │  │   可作质押。您这边 3 项发明专利正好匹配这个额度..."          │   │  |
|  │  │                                                              │   │  |
|  │  │ [查看证据]    [加入跟进]    [传递给授信决策 Agent3]          │   │  |
|  │  └────────────────────────────────────────────────────────────┘   │  |
|  │                                                                    │  |
|  │  #2 [RED 88分] 宁波智造精密科技...                                 │  |
|  │  ...                                                                │  |
|  │  #10 [YELLOW 72分] ...                                             │  |
|  └────────────────────────────────────────────────────────────────────┘  |
+==========================================================================+
```

### 4.2 组件详细设计

#### 4.2.1 A 区：文件上传区

| 元素 | 规格 |
|---|---|
| 拖拽区 | 虚线边框，悬停变蓝，支持多文件同时拖入 |
| 已上传文件列表 | 每行：文件名 + 类型图标 + 识别结果（"127 行"/"18 规则"/"加载失败: ..."）|
| 文件类型识别 | 后端 `KnowledgeBase._infer_type()` 自动判断，前端展示判断结果，用户可手动改 |
| 预置场景按钮 | 2 个按钮：制造业 look-alike / 科创 look-alike；点击自动填充 3 类文件 |
| 清空按钮 | 右上角 X |

#### 4.2.2 B 区：扫描进度区（实时）

| 阶段 | 进度元素 |
|---|---|
| ① KB 加载 | 每份文件一条进度条（"解析中" → "✓") |
| ② 画像抽取 | 环形进度条 + 状态文字（"LLM 抽取中..." → "✓") |
| ③ 外网搜索 | 每条 query 一行，展示 query 文本 + 结果数 + 累计候选 |
| ④ 匹配打分 | 候选处理进度（"打分中 42/65"）|
| ⑤ 产品推荐 | Top10 逐条处理（"推荐产品 3/10"）|

#### 4.2.3 C 区：理想客户画像卡

- 字段可编辑（点击字段出现编辑框，失焦保存）
- "画像依据"区块展示 LLM 的推理过程（`reasoning` 字段）
- "开始扫描"按钮：只有画像非空时亮起
- "重新抽取"按钮：如果用户改了 KB 文件，可重新抽画像

#### 4.2.4 D 区：Top10 线索榜

每张线索卡结构：

| 区块 | 内容 |
|---|---|
| 头部 | 排名徽章 + 分级色块（RED/YELLOW/GREEN）+ 总分 + 企业名 |
| 基本信息条 | 行业 / 地域 / 规模 / 营收（4 列等宽）|
| 匹配理由 | 3-5 条勾号列表，每条对应一个维度（行业/地域/标签/政策）|
| 产品推荐 Top3 | 3 行迷你卡，每行：类别色块 + 产品名 + 分数 + 额度 |
| 切入话术 | 灰色引用块，斜体排版 |
| 操作按钮 | [查看证据] [加入跟进] [传递给 Agent3] |

**分级色值**：
| 级别 | 色值 | 标签 |
|---|---|---|
| RED（≥80 分） | #F5222D | 强匹配 |
| YELLOW（65-79 分） | #FA8C16 | 中匹配 |
| GREEN（<65 分） | #52C41A | 弱匹配（Top10 内较少出现）|

#### 4.2.5 证据弹窗

点击"查看证据"弹出 Modal：

```
+----------------------------------------------------+
| 匹配证据链 — 杭州精工智造有限公司                   |
+----------------------------------------------------+
| 【原始数据来源】                                    |
| · 搜索来源: SearchProvider(mock) query="杭州 专精特新 智能制造"
| · 数据快照时间: 2026-04-14 10:23:45                  |
|                                                    |
| 【相似样本锚】（从你上传的客户名录找出）             |
| · 宁波华联轴承有限公司     相似度 93                 |
| · 绍兴振华精密机械有限公司 相似度 88                 |
| · 温州永达阀门有限公司     相似度 85                 |
|                                                    |
| 【命中规则】                                        |
| · RULE_007 专精特新小巨人认定（政策文件第 3 章）      |
| · RULE_012 发明专利 ≥ 2 项（政策文件第 5 章）        |
|                                                    |
| 【分数明细】                                        |
| · 画像相似度: 92/100                                |
|   - 行业: 95   地域: 90   规模: 90   标签: 88        |
| · 样本锚相似度: 89/100                              |
| · 综合: 0.6×92 + 0.4×89 = 91                        |
+----------------------------------------------------+
```

### 4.3 交互流程

```
打开页面
  │
  ├── 用户点击"预置场景"按钮 → 自动上传 mock 文件 → 直接进入画像抽取
  │
  └── 用户上传自有文件 → 上传完成后自动进入画像抽取
        │
        ▼
   画像抽取中（LLM 调用 1）                       ← 10-15s
        │
        ▼
   画像卡展示
        │
        ├── 用户编辑画像字段 → 修改生效
        └── 用户点"开始扫描"
              │
              ▼
        外网搜索（阶段③）                         ← 15-30s
              │
              ▼
        匹配打分（阶段④）                         ← 3-5s（确定性计算）
              │
              ▼
        产品推荐（阶段⑤，LLM 调用 2：批量话术）     ← 20-40s
              │
              ▼
        Top10 线索榜单展示
              │
              ├── 用户点卡片 → 展开证据
              ├── 用户点"导出 Word" → 下载线索报告
              └── 用户点"传递给 Agent3" → 跳转授信决策 Agent
```

### 4.4 废弃的 v1.0 UI 元素

| 元素 | 废弃原因 |
|---|---|
| 企业信息手填表单（企业名/行业/地区/规模等 8 个字段）| v2.0 改为 KB 驱动，不再手填单家企业 |
| "开始匹配"按钮 | 流程变为"上传 → 画像 → 扫描"，不再是单次匹配 |
| 通用 Chatbot 输入框 | v2.0 无对话模式 |
| API Key / 模型 / Base URL 输入 | Portal 级别统一配置，Agent 内不暴露 |
| 渠道推荐卡片作为主输出 | 降级为线索卡内的"推荐产品"子区块 |

---

## 5. 后端架构

### 5.1 模块清单

| 层级 | 文件 | 动作 | 说明 |
|---|---|---|---|
| **共享基础设施** | `shared/kb_scan/models.py` | 共享-依赖 | 使用 `CompanyProfile` / `IdealProfile` / `HitItem` / `HitList` |
| | `shared/kb_scan/knowledge_base.py` | 共享-依赖 | 装载 KB |
| | `shared/kb_scan/search_provider.py` | 共享-依赖 | `MockProvider`/`WebProvider` |
| | `shared/kb_scan/rule_extractor.py` | 共享-依赖 | 政策→规则 |
| | `shared/kb_scan/matcher.py` + `SimilarityScorer` | 共享-依赖 | 画像相似度 |
| | `shared/kb_scan/hit_ranker.py` | 共享-依赖 | Top10 打榜 |
| | `shared/kb_scan/exporters.py` | 共享-依赖 | Word 导出 |
| | `shared/base_agent.py` | 保留 | 事件协议 |
| **Agent1 本地** | `agent_channel/agent.py` | **重写** | 新版 `ChannelMatchAgent`（扫描范式）|
| | `agent_channel/profile_extractor.py` | **新建** | 调 LLM 抽 `IdealProfile` |
| | `agent_channel/lead_finder.py` | **新建** | `LookAlikeMatcher` 实现（继承共享 `Matcher`）|
| | `agent_channel/product_recommender.py` | **新建** | 包装 `channel_rules` + `scoring` |
| | `agent_channel/prompts.py` | **重写** | 3 套新 prompts |
| | `agent_channel/app_demo.py` | **重写** | 新 UI |
| | `agent_channel/channel_rules.py` | **保留** | 渠道规则不动 |
| | `agent_channel/scoring.py` | **保留** | 评分不动 |
| | `agent_channel/config.py` | 新建 | Demo 默认配置（api_key/模型/demo_mode） |
| | `demo_data/agent_channel/scenario_manufacturing/` | 新建 | 制造业 look-alike 预置场景 |
| | `demo_data/agent_channel/scenario_tech/` | 新建 | 科创 look-alike 预置场景 |
| | `demo_data/mock_pool/companies.json` | 新建 | 50+ 家 mock 企业池 |

### 5.2 依赖关系图

```
┌──────────────────────────────────────────────────────────────┐
│                   agent_channel/app_demo.py                   │
│                   (Gradio 前端)                               │
└──────────────────────────┬───────────────────────────────────┘
                           │ 调用
                           ▼
┌──────────────────────────────────────────────────────────────┐
│              agent_channel/agent.py                           │
│              class ChannelMatchAgent(BaseAgent)               │
│              process(request: ScanRequest) → HitList          │
└──┬──────────┬──────────┬──────────┬──────────┬───────────────┘
   │          │          │          │          │
   ▼          ▼          ▼          ▼          ▼
┌─────┐  ┌────────┐  ┌────────┐  ┌──────────┐  ┌──────────────┐
│  KB │  │ProfileE│  │ Search │  │LookAlike │  │ ProductReco- │
│     │  │xtractor│  │Provider│  │ Matcher  │  │ mmender      │
└──┬──┘  └───┬────┘  └───┬────┘  └────┬─────┘  └──────┬───────┘
   │         │           │            │               │
   ▼         ▼           ▼            ▼               ▼
 共享      LLM       Mock/Web      Similarity      channel_rules
 KB类      调用       切换         Scorer          + scoring
                                    (共享)         (v1.0 保留)
```

### 5.3 关键类的核心实现

#### 5.3.1 `ChannelMatchAgent`（骨架）

```python
# agent_channel/agent.py
from __future__ import annotations
from typing import Generator
from shared.base_agent import BaseAgent
from shared.kb_scan.knowledge_base import KnowledgeBase
from shared.kb_scan.search_provider import build_search_provider
from shared.kb_scan.hit_ranker import HitRanker
from shared.kb_scan.models import ScanTarget, HitItem, HitList, RiskLevel
from agent_channel.profile_extractor import ProfileExtractor
from agent_channel.lead_finder import LookAlikeMatcher
from agent_channel.product_recommender import ProductRecommender
from agent_channel import config


class ChannelMatchAgent(BaseAgent):
    agent_name = "channel"
    agent_title = "全渠道流量匹配"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.search = build_search_provider(demo_mode=config.DEMO_MODE)
        self.profile_extractor = ProfileExtractor(llm_client=self.llm)
        self.matcher = LookAlikeMatcher()
        self.ranker = HitRanker(top_n=10, red_threshold=80, yellow_threshold=65)
        self.product_recommender = ProductRecommender(llm_client=self.llm)

    def process(self, kb_files: list[str], scan_scope: dict | None = None) -> Generator[dict, None, HitList]:
        # ① KB 装载
        yield self._thinking("装载知识库...")
        kb = KnowledgeBase(name="channel")
        kb.load_files(kb_files)
        yield self._message(f"知识库: {kb.summary()}")

        # ② 画像抽取
        yield self._thinking("LLM 抽取理想客户画像...")
        ideal = self.profile_extractor.extract(kb)
        yield self._profile_card(ideal)   # 自定义事件，前端展示画像卡

        # ③ 外网搜索
        yield self._thinking("基于画像搜索候选企业池...")
        candidates = []
        for q in self._generate_queries(ideal):
            yield self._tool_call("search_companies", status="running")
            results = self.search.search_companies(q, filters=ideal_filters_from(ideal), limit=50)
            yield self._tool_result("search_companies", f"query={q}, 命中 {len(results)} 家")
            candidates.extend(results)
        candidates = self._dedup(candidates)

        # ④ 匹配打分
        yield self._thinking(f"对 {len(candidates)} 家候选打分...")
        targets = [ScanTarget(target_id=c.company_id, target_type="company",
                              payload=c.model_dump()) for c in candidates]
        hits = self.matcher.match_all(targets, kb, ideal)

        # ⑤ 产品推荐 + 话术
        yield self._thinking("生成 Top10 线索的产品推荐与切入话术...")
        hit_list = self.ranker.rank(hits, agent_name=self.agent_name,
                                    kb_summary=kb.summary(),
                                    scan_summary=f"扫描 {len(candidates)} 家候选",
                                    total_scanned=len(candidates))
        for hit in hit_list.hits:
            self.product_recommender.enrich(hit, ideal)

        yield self._hit_list(hit_list)
        yield self._done("look-alike 扫描完成")
        return hit_list

    def _generate_queries(self, ideal) -> list[str]:
        queries = []
        for region in ideal.target_regions[:2]:
            for industry in ideal.target_industries[:2]:
                queries.append(f"{region} {industry} {' '.join(ideal.must_have_tags[:2])}")
        return queries
```

#### 5.3.2 `ProfileExtractor`

```python
# agent_channel/profile_extractor.py
from shared.kb_scan.knowledge_base import KnowledgeBase
from shared.kb_scan.models import IdealProfile
from agent_channel.prompts import PROFILE_EXTRACT_PROMPT


class ProfileExtractor:
    def __init__(self, llm_client):
        self.llm = llm_client

    def extract(self, kb: KnowledgeBase) -> IdealProfile:
        stats = self._aggregate_customer_stats(kb.companies)  # 行业/规模/地域频率
        policy_ctx = self._summarize_rules(kb.rules)
        prompt = PROFILE_EXTRACT_PROMPT.format(
            customer_stats=stats,
            policy_rules=policy_ctx,
        )
        data = self.llm.llm_json(
            system="你是一位银行获客画像分析专家。",
            user=prompt,
        )
        return IdealProfile.model_validate(data)

    def _aggregate_customer_stats(self, companies): ...
    def _summarize_rules(self, rules): ...
```

#### 5.3.3 `LookAlikeMatcher`

```python
# agent_channel/lead_finder.py
from shared.kb_scan.matcher import Matcher, SimilarityScorer
from shared.kb_scan.models import ScanTarget, HitItem, RiskLevel, Evidence, CompanyProfile
from shared.kb_scan.knowledge_base import KnowledgeBase


class LookAlikeMatcher(Matcher):
    def __init__(self):
        self.scorer = SimilarityScorer()

    def match_all(self, targets, kb: KnowledgeBase, ideal):
        hits = []
        for t in targets:
            cand = CompanyProfile.model_validate(t.payload)
            # 4a. 画像相似度
            profile_score = self.scorer.score_against_profile(cand, ideal)
            # 4b. 样本锚相似度
            top3_anchors = self.scorer.top_k_similar(cand, kb.companies, k=3)
            anchor_score = sum(self.scorer.score(a, cand) for a in top3_anchors) / 3 if top3_anchors else 0
            # 综合
            final = round(0.6 * profile_score + 0.4 * anchor_score, 1)

            hit = HitItem(
                hit_id=f"LEAD_{cand.company_id}",
                level=RiskLevel.GREEN,   # 由 Ranker 覆盖
                score=final,
                target=t,
                reasons=self._build_reasons(cand, ideal, top3_anchors),
                evidences=self._build_evidences(cand, top3_anchors, ideal),
                extras={
                    "profile_score": profile_score,
                    "anchor_score": anchor_score,
                    "top3_anchors": [a.company_name for a in top3_anchors],
                },
            )
            hits.append(hit)
        return hits

    def match_one(self, target, rules): ...  # 为满足基类抽象
    def _build_reasons(self, cand, ideal, anchors): ...
    def _build_evidences(self, cand, anchors, ideal): ...
```

#### 5.3.4 `ProductRecommender`（复用 v1.0 代码）

```python
# agent_channel/product_recommender.py
from agent_channel.channel_rules import match_channels         # v1.0 保留
from agent_channel.scoring import rank_recommendations         # v1.0 保留
from agent_channel.prompts import PITCH_GEN_PROMPT


class ProductRecommender:
    def __init__(self, llm_client):
        self.llm = llm_client

    def enrich(self, hit, ideal):
        profile_dict = hit.target.payload
        matched = match_channels(profile_dict)
        recs = rank_recommendations(profile_dict, matched)
        top3 = recs[:3]
        pitch = self._generate_pitch(profile_dict, top3, ideal.policy_context)

        hit.extras["recommended_products"] = [r.model_dump() for r in top3]
        hit.extras["pitch_script"] = pitch

    def _generate_pitch(self, profile, top3_products, policy_ctx) -> str:
        prompt = PITCH_GEN_PROMPT.format(
            company=profile.get("company_name"),
            products="\n".join(f"- {p.channel_name} (额度{p.max_amount})" for p in top3_products),
            policy_ctx=policy_ctx,
        )
        return self.llm.llm_chat(
            system="你是资深银行客户经理，擅长电话首访切入话术。",
            user=prompt,
        )
```

---

## 6. 数据模型

### 6.1 输入（KB）

使用共享架构的 `KnowledgeBase`：
- `kb.companies: list[CompanyProfile]`（已有客户名录）
- `kb.rules: list[RuleItem]`（从政策抽取的规则）
- `kb.clauses: list[dict]`（原始政策条款）

### 6.2 中间产物

- `IdealProfile`（共享架构定义）

### 6.3 输出（LeadCard）

使用共享架构的 `HitItem`，`extras` 扩展如下：

```python
# HitItem.extras schema for Agent1
{
    "profile_score": 92.0,                  # 画像相似度
    "anchor_score": 89.3,                   # 样本锚相似度
    "top3_anchors": ["宁波华联轴承", "绍兴振华", "温州永达"],  # 相似的已有客户
    "recommended_products": [               # 推荐 Top3 产品（ChannelRecommendation.model_dump()）
        {"channel_name": "专精特新企业贷", "category": "科技金融",
         "score": 93, "max_amount": "2000万", "match_reasons": [...]},
        ...
    ],
    "pitch_script": "张总好，浙江省专精特新...",   # 切入话术
    "fit_dimensions": {                     # 各维度分数，用于前端展示
        "industry": 95, "region": 90, "scale": 90, "tags": 88,
    },
}
```

### 6.4 LeadCard 前端渲染模型

```python
class LeadCardView(BaseModel):
    """前端渲染用的聚合视图（由 HitItem 转换而来）。"""
    rank: int
    level: str                       # "red" | "yellow" | "green"
    level_label: str                 # "强匹配" / "中匹配" / "弱匹配"
    score: float
    company_name: str
    industry: str
    region: str
    scale: str
    revenue: str
    reasons: list[str]
    products: list[dict]             # 产品 Top3
    pitch: str
    evidence_available: bool = True
```

---

## 7. LLM 调用设计

### 7.1 调用点清单

| 调用点 | 位置 | 输入 | 输出 | 频次 | 是否必须 |
|---|---|---|---|---|---|
| 画像抽取 | ProfileExtractor | 客户统计 + 政策规则 | `IdealProfile` JSON | 1 次/场景 | 必须 |
| 规则抽取 | RuleExtractor（共享） | 政策文档 chunk | `list[RuleItem]` | 每份政策 N 次（按 chunk）| 可选（无政策文件时跳过）|
| 切入话术 | ProductRecommender | 企业画像 + Top3 产品 + 政策语境 | 自然语言话术 | 10 次/场景（Top10 每条一次）| 必须 |

总计 Demo 场景约 **11-15 次** LLM 调用（1 + N + 10），其中 10 次话术可**批量合并**为 1-2 次调用以加速。

### 7.2 三套 Prompts

#### 7.2.1 Prompt 1：画像抽取（`PROFILE_EXTRACT_PROMPT`）

```
你是一位银行获客画像分析专家。请综合已有客户名录的统计特征和当前政策导向，定义"理想新客户画像"。

【已有客户统计】
{customer_stats}

【政策规则】
{policy_rules}

【任务】
基于以上输入，定义一张可用于外网 look-alike 检索的"理想客户画像"。画像要：
1. 足够聚焦（不要给出"所有制造业企业"这种宽泛的定义）
2. 有硬性指标（行业、规模、地域、必备资质）
3. 有加分项（哪些特征让候选更优质）
4. 有排除项（政策明确不支持的）
5. 有推理解释（为什么这样定义）

严格按以下 JSON schema 输出（只输出 JSON，用 ```json``` 包裹）：
{{
  "name": "画像名称，简短",
  "target_industries": ["..."],
  "target_sub_industries": ["..."],
  "target_regions": ["..."],
  "scale_range": ["小型"|"微型"|"中型"|"大型"],
  "revenue_range": [最小值_万元, 最大值_万元],
  "must_have_tags": ["..."],
  "nice_to_have_tags": ["..."],
  "exclude_tags": ["..."],
  "policy_context": "当前政策环境的一段描述，话术用",
  "reasoning": "解释：为什么这样定义画像，依据哪些客户特征和政策条款"
}}
```

#### 7.2.2 Prompt 2：规则抽取

复用共享架构 `RuleExtractor.RULE_EXTRACT_PROMPT`。

#### 7.2.3 Prompt 3：切入话术（`PITCH_GEN_PROMPT`）

```
你是一位资深银行客户经理，擅长首次电话沟通切入话术。请为以下潜在客户生成一段切入话术（80-120 字）。

【目标客户】
企业名: {company}
行业: {industry}
规模: {scale}
主营: {main_business}

【推荐产品】
{products}

【当前政策语境】
{policy_ctx}

【要求】
1. 开场直接切入客户可能关心的点（政策红利/行业痛点）
2. 介绍 1 个主打产品 + 核心数字（额度/利率）
3. 留钩子引导下一步沟通
4. 口语化，不要书面语
5. 不要虚构数字，只用【推荐产品】里给出的数字
6. 不要说"您好，我是某某银行的"这种客套开场，从业务切入

只输出话术文本，不要任何解释或引号。
```

### 7.3 提示词策略

- **温度**：画像抽取 0.2（要稳定），话术生成 0.5（要有变化）
- **输出格式约束**：画像抽取必须是 JSON（走 `llm_json`），话术是纯文本
- **幻觉控制**：话术 prompt 明确"不要虚构数字"，只使用 prompt 中已提供的产品参数
- **批量优化**：Top10 话术可合并为 1-2 次调用（prompt 里打包 Top10 企业列表，一次返回 10 段话术）

### 7.4 容错设计

| 故障场景 | 处理策略 |
|---|---|
| 画像抽取 LLM 失败 | 3 次重试 → 回退：用规则兜底（从客户统计取 TOP 字段 + 固定模板）|
| 规则抽取单 chunk 失败 | 该 chunk 跳过，不影响其他 chunk |
| 话术生成单条失败 | 该线索卡话术字段填"话术生成失败，请人工编辑"，不阻断整体流程 |
| SearchProvider 超时 | 当前 query 返回空，其他 query 继续；最终候选池 <5 时提示"搜索异常，建议重试" |
| 候选池为 0 | 前端红色提示："未找到匹配候选，建议放宽画像筛选条件" + 附编辑画像入口 |

---

## 8. Mock 数据规格

### 8.1 Mock 企业池（`demo_data/mock_pool/companies.json`）

**规模**：至少 50 家 mock 企业（最终目标 100+）

**分布**：

| 维度 | 分布 |
|---|---|
| 行业 | 制造业 30%、信息技术 20%、新材料 10%、生物医药 8%、环保/新能源 10%、批发零售 10%、其他 12% |
| 地域 | 浙江 25%、江苏 20%、广东 20%、上海 10%、北京 8%、四川/重庆 7%、其他 10% |
| 规模 | 小型 55%、微型 25%、中型 18%、大型 2% |
| 标签 | 专精特新小巨人 18%、高新技术 35%、发明专利≥2 40%、省级研发机构 12% |

**数据结构**：对齐共享架构 `CompanyProfile`

```json
{
  "company_id": "MOCK_001",
  "company_name": "杭州精工智造有限公司",
  "unified_credit_code": "91330109MA28XXXX",
  "industry": "制造业",
  "sub_industry": "精密机械加工",
  "region": "浙江省杭州市滨江区",
  "scale": "小型",
  "revenue_latest": "4200万",
  "employee_count": 78,
  "ownership_type": "民营",
  "keywords": ["精密加工", "数控机床", "专精特新", "汽车零部件"],
  "qualifications": ["国家高新技术企业", "专精特新小巨人"],
  "tags": ["制造业", "专精特新", "发明专利"],
  "establishment_date": "2014-06-20",
  "registered_capital": "1000万",
  "main_business": "精密零部件 CNC 加工、模具制造",
  "upstream": [{"name": "宝钢股份", "amount": "年采购 800 万", "type": "原材料"}],
  "downstream": [{"name": "吉利汽车", "amount": "年供货 1500 万", "type": "整车厂"}]
}
```

**不完美设计**：部分 mock 企业故意缺字段（如 `revenue_latest=""`、`qualifications=[]`），模拟真实 API 返回的质量分布。

### 8.2 预置场景 1：制造业 look-alike

**目录**：`demo_data/agent_channel/scenario_manufacturing/`

**KB 文件**：
- `customers.xlsx` — 30 家浙江制造业小微客户（已脱敏），含行业/规模/标签列
- `policy_smallgiant.docx` — 《浙江省专精特新"小巨人"培育实施方案（2024-2026）》mock 版
- `industry_guide.pdf` — 行内制造业拓展指引 mock 版

**预期画像抽取**：
```json
{
  "name": "浙江制造业专精特新 look-alike 画像",
  "target_industries": ["制造业", "高端装备", "新材料"],
  "target_regions": ["浙江", "杭州", "宁波", "温州", "绍兴"],
  "scale_range": ["小型", "微型"],
  "revenue_range": [1000, 50000],
  "must_have_tags": ["专精特新|高新技术"],
  "nice_to_have_tags": ["发明专利≥2", "省级研发机构"],
  "exclude_tags": ["房地产", "高污染"]
}
```

**预期 Top3 线索**（来自 mock 池）：

| 排名 | 企业 | 分数 | 匹配理由 |
|---|---|---|---|
| 1 | 杭州精工智造有限公司 | 91 | 专精特新小巨人 + 精密加工 + 3 项发明专利 |
| 2 | 宁波智造精密科技有限公司 | 88 | 智能制造 + 省级研发机构 + 高新 |
| 3 | 绍兴振华轴承制造有限公司 | 85 | 轴承制造（行业锚）+ 小微 + 浙江区域 |

### 8.3 预置场景 2：科创企业 look-alike

**目录**：`demo_data/agent_channel/scenario_tech/`

**KB 文件**：
- `customers.xlsx` — 25 家深圳/上海科创小微客户
- `policy_tech.docx` — 《科技型中小企业金融服务支持方案》mock 版
- `industry_guide.pdf` — 行内科创金融专项指引 mock 版

**预期画像抽取**：
```json
{
  "name": "长三角/珠三角科创企业 look-alike 画像",
  "target_industries": ["信息技术", "人工智能", "生物医药", "半导体", "软件"],
  "target_regions": ["深圳", "上海", "苏州", "杭州"],
  "scale_range": ["小型", "中型"],
  "revenue_range": [500, 100000],
  "must_have_tags": ["国家高新技术企业"],
  "nice_to_have_tags": ["发明专利≥5", "融资轮次A+", "专精特新小巨人"]
}
```

---

## 9. 与其他 Agent 的数据接口

### 9.1 输出：`EnterpriseProfile` / `HandoffEnvelope`

Agent1 输出的 Top10 线索（`HitList`）可直接传递给其他 Agent：

```python
# Agent1 -> Agent3（授信决策辅助）
envelope = HandoffEnvelope(
    from_agent="channel",
    to_agent="credit",
    handoff_time=now(),
    payload_type="company_profile",
    payload=CompanyProfile.model_validate(hit.target.payload).model_dump(),
)
```

**可被消费的下游 Agent**：
- **Agent3 授信决策辅助**：接收 `CompanyProfile` 作为尽调起点
- **Agent5 客户经理个人助手**：接收 `CompanyProfile` + `pitch_script` 作为跟进素材

### 9.2 输入：来自 Agent5（客户经理助手）

客户经理在和客户沟通后，如需做 look-alike 扩围，可从 Agent5 传入"典型客户画像"：

```python
# Agent5 -> Agent1
# Agent5 传入一个临时的客户画像作为 KB 的一部分
envelope = HandoffEnvelope(
    from_agent="assistant",
    to_agent="channel",
    payload_type="company_profile",
    payload={"companies": [...]},   # 临时客户名录
)
```

Agent1 收到后，将其 merge 进 `KnowledgeBase.companies`，继续正常流程。

---

## 10. 验收标准

### 10.1 功能验收

| 编号 | 验收项 | 通过条件 | 优先级 |
|---|---|---|---|
| F1 | KB 多文件加载 | Excel+Word+PDF 3 类文件同时上传，识别正确率 100% | P0 |
| F2 | 预置场景一键启动 | 2 个预置场景点击后 30 秒内出画像 | P0 |
| F3 | 画像可编辑 | 画像卡字段可编辑，修改后影响后续扫描 | P0 |
| F4 | 外网搜索（Mock）| Demo 阶段 MockProvider 能返回 ≥50 家候选企业 | P0 |
| F5 | Top10 线索质量 | 2 个场景的 Top10 首条企业 score ≥85，且匹配理由列出至少 3 项 | P0 |
| F6 | 每条线索有产品 Top3 | 10/10 线索均有推荐产品且 ≥3 个 | P0 |
| F7 | 每条线索有话术 | 10/10 线索均有非空话术且长度在 60-150 字 | P0 |
| F8 | 证据链可查 | 点"查看证据"能看到相似样本锚 + 命中规则 + 分数明细 | P0 |
| F9 | Word 导出 | 一键导出含所有线索卡的 Word 报告 | P0 |
| F10 | Agent 间跳转 | 点"传递给 Agent3"能带数据跳转 | P1 |
| F11 | 自定义 KB | 用户上传自有 Excel/Word 能完整跑通（非预置场景） | P1 |
| F12 | 画像兜底 | 画像 LLM 失败时有规则兜底，不阻断流程 | P2 |

### 10.2 性能验收

| 编号 | 验收项 | 通过条件 |
|---|---|---|
| P1 | 画像抽取耗时 | 从上传完成到画像卡出现 < 30 秒 |
| P2 | 全流程耗时（扫描+打分+话术）| 从"开始扫描"到 Top10 线索展示 < 2 分钟 |
| P3 | Word 导出 | < 5 秒 |
| P4 | 首屏加载 | < 2 秒 |
| P5 | LLM 调用总数 | ≤ 15 次/场景（含话术批量优化后 ≤ 5 次）|

### 10.3 体验验收

| 编号 | 验收项 | 通过条件 |
|---|---|---|
| E1 | 零配置启动 | 启动后无需填 API Key、无需选模型，直接可用 |
| E2 | 过程透明 | 每个阶段都有实时进度，无长时间空白 |
| E3 | 画像可读 | 画像卡的字段和依据说明，业务人员能一眼看懂 |
| E4 | 线索卡专业 | 线索卡视觉专业（分级色块、图标、排版）|
| E5 | 话术即用 | 话术口语化、有具体数字、符合电话首访场景 |
| E6 | 证据可审计 | 证据弹窗清楚展示"为什么这个分数" |

### 10.4 架构验收

| 编号 | 验收项 | 通过条件 |
|---|---|---|
| A1 | 共享架构合规 | 使用 `shared/kb_scan/` 的接口，无代码重复 |
| A2 | Mock/Web 可切换 | 改一行 `DEMO_MODE`，切换到 WebProvider stub（真实 API 可以留 TODO，但接口必须存在）|
| A3 | 下游无感知 | 全代码 grep 不到 `isinstance(.*, MockProvider)` |
| A4 | v1.0 资产复用 | `channel_rules.py` / `scoring.py` 未做修改，通过 `ProductRecommender` 包装调用 |

### 10.5 演示流程验收

| 步骤 | 演示动作 | 预期效果 | 耗时上限 |
|---|---|---|---|
| 1 | 打开页面 | 看到上传区 + 2 个预置场景按钮 | 2s |
| 2 | 点"制造业 look-alike"预置场景 | 3 份文件自动加载并识别 | 5s |
| 3 | 等待画像抽取 | 画像卡出现 | 30s |
| 4 | 解说画像依据 | 客户能理解"哦，这个画像是从已有客户和政策推出来的" | - |
| 5 | 点"开始扫描" | 阶段③搜索进度实时滚动（展示"扫描了多少家"）| 30s |
| 6 | 阶段④打分 | 候选处理进度滚动 | 5s |
| 7 | 阶段⑤话术生成 | Top10 线索卡逐张出现 | 40s |
| 8 | 展开第 1 条线索 | 看到产品 Top3 + 话术 | 即时 |
| 9 | 点"查看证据" | 证据弹窗展示样本锚 + 命中规则 | 即时 |
| 10 | 点"导出 Word" | 下载线索报告 | 5s |
| 11 | 切到"科创 look-alike"场景 | 流程重跑 | 同上 |

**全流程演示总耗时**：< 4 分钟

---

## 11. 交付物清单

### 11.1 代码交付

| 文件 | 状态 |
|---|---|
| `agent_channel/agent.py` | 重写 |
| `agent_channel/profile_extractor.py` | 新建 |
| `agent_channel/lead_finder.py` | 新建 |
| `agent_channel/product_recommender.py` | 新建 |
| `agent_channel/prompts.py` | 重写 |
| `agent_channel/app_demo.py` | 重写 |
| `agent_channel/config.py` | 新建 |
| `agent_channel/channel_rules.py` | **保留（0 改动）** |
| `agent_channel/scoring.py` | **保留（0 改动）** |
| `shared/kb_scan/` 全套 | 新建（跨 Agent 共享）|
| `demo_data/mock_pool/companies.json` | 新建 |
| `demo_data/agent_channel/scenario_manufacturing/` | 新建 |
| `demo_data/agent_channel/scenario_tech/` | 新建 |

### 11.2 文档交付

- 本 PRD
- 《共享架构_知识库扫描范式_v1.0.md》
- Mock 数据规格说明（可作附录）
- 演示脚本（P6 阶段输出）

### 11.3 验证交付

- 2 个预置场景的完整运行录屏
- 验收清单勾选记录
- 架构评审纪要（A1-A4）

---

## 12. 附录 A：技术栈

| 组件 | 技术选型 | 版本 |
|---|---|---|
| 前端框架 | Gradio Blocks | ≥ 4.0 |
| 后端语言 | Python | ≥ 3.10 |
| LLM 服务 | DeepSeek API（内置 key）| deepseek-chat |
| 数据模型 | Pydantic | ≥ 2.0 |
| 文件解析 | python-docx / PyPDF2 / openpyxl / pandas | 最新稳定 |
| Word 导出 | python-docx | 最新稳定 |
| 搜索（生产）| 天眼查 API / 爱企查 API（留 TODO）| — |

---

## 13. 附录 B：改造前后目录结构对比

### 13.1 改造前（v1.0）

```
agent_channel/
├── __init__.py
├── agent.py            # 单查流程
├── app.py              # Gradio 通用聊天
├── app_demo.py         # 演示版（仍是聊天）
├── channel_rules.py    # CHANNEL_CATALOG 硬编码
├── prompts.py          # 3 套 prompt
└── scoring.py          # 5 维评分
```

### 13.2 改造后（v2.0）

```
shared/
└── kb_scan/                         # 三 Agent 共享基础设施（新建）
    ├── __init__.py
    ├── models.py
    ├── knowledge_base.py
    ├── rule_extractor.py
    ├── search_provider.py
    ├── matcher.py
    ├── hit_ranker.py
    └── exporters.py

agent_channel/
├── __init__.py
├── agent.py                         # [重写] KB 扫描范式
├── app_demo.py                      # [重写] 新交互 UI
├── profile_extractor.py             # [新建] 画像抽取
├── lead_finder.py                   # [新建] look-alike 匹配
├── product_recommender.py           # [新建] 产品推荐+话术
├── prompts.py                       # [重写] 3 套新 prompt
├── config.py                        # [新建] Demo 配置
├── channel_rules.py                 # [保留 0 改动]
└── scoring.py                       # [保留 0 改动]

demo_data/
├── mock_pool/
│   └── companies.json               # 50+ mock 企业池（共享 / 三 Agent 可用）
└── agent_channel/
    ├── scenario_manufacturing/
    │   ├── customers.xlsx
    │   ├── policy_smallgiant.docx
    │   └── industry_guide.pdf
    └── scenario_tech/
        ├── customers.xlsx
        ├── policy_tech.docx
        └── industry_guide.pdf
```

---

## 14. 开放问题 / 风险

| 编号 | 问题 | 影响 | 应对 |
|---|---|---|---|
| R1 | 画像抽取质量依赖客户名录数据量 | 名录 < 10 家时画像可能失真 | 提示用户"建议 ≥20 家客户名录"；<10 家时降级为"政策+关键词手工输入" |
| R2 | 话术 LLM 成本较高（Top10 各一次）| Demo 成本可控；生产需评估 | 批量合并为 1-2 次调用；生产阶段加缓存 |
| R3 | Mock 池规模有限（50+）| 某些窄画像可能 Top10 凑不满 | 后续扩充到 200+；前端支持"低于 10 条"的提示 |
| R4 | 生产阶段真实企业 API 未定型 | 生产上线需选型对接 | Demo 不阻塞；WebProvider 预留接口 |
| R5 | 用户上传的政策文件差异大（pdf 扫描件/表格多等）| RuleExtractor 稳定性受影响 | 增加 OCR 预处理 fallback；失败 chunk 跳过 |

---

*文档结束*
