"use client";

/**
 * CompliV2 — DOM port of design_mockups/stage5/mockup-v2/compli.html.
 * Policy-Event Watcher · Parse / Matrix / Verdict 三阶段.
 */

import {
  V2Shell,
  ChatBlk,
  SseBlk,
  DocWrap,
  AuditStrip,
  type ChatMessage,
  type DocSection,
  type TraceLine,
  type QcMetric,
} from "./V2Shell";

const MESSAGES: ChatMessage[] = [
  {
    side: "agent", sig: "规.", nameZh: "合规助手·政策事件驱动", nameEn: "Compli",
    ts: "09:13:18", ref: "3 冲突", spineColor: "var(--t-compli)",
    body: <>政策解析完毕 · 与内控 <b>128</b> 项配对扫完 — 冲突 <b>3</b> 处：① 新规 <em>3.2 条</em>「单户 500 万以上须人审」vs 内控 <em>A-12</em>「500 万以下快贷通道」<b>边界冲突</b> ② 新规 <em>5.1 条</em>「数据采集最小化」vs 内控 <em>D-07</em>「全量画像采集」<b>范围冲突</b> ③ 新规 <em>7.3 条</em>「不良披露 T+5」vs 内控 <em>F-02</em>「T+15」<b>时效冲突</b>。</>,
  },
  {
    side: "user", sig: "王.", nameZh: "王哲", nameEn: "华东客户经理",
    ts: "09:14:02",
    body: <>A-12 本周内改版，其他两条下周处置；<em>500 万边界</em>改为人审触发，不是一刀切切断快贷通道。</>,
  },
  {
    side: "agent", sig: "规.", nameZh: "合规助手·政策事件驱动", nameEn: "Compli",
    ts: "09:14:21", ref: "整改 A-12", spineColor: "var(--t-compli)",
    body: <>收到。A-12 整改单已生成 — 建议加 <em>500 万以上自动走人审</em> 旁路，保留 500 万以下快贷。本周五前推你草案；D-07 + F-02 下周评审排期。已抄送反洗钱 + 法务 + 信贷 IT。</>,
  },
];

const SSE_LINES: TraceLine[] = [
  { ts: "09:12:08", stgTag: "parse · 01",   stage: "ev", tx: <>✓ <b>政策 12 节抽完</b> <span className="src">SRC 银保监官网</span></> },
  { ts: "09:12:24", stgTag: "parse · 02",   stage: "ev", tx: <>✓ <b>关键条款标记</b> 22 条</> },
  { ts: "09:12:51", stgTag: "matrix · 2.1", stage: "gn", tx: <>✓ <b>内控 128 项载入</b> <span className="src">kb_internal_v2</span></> },
  { ts: "09:13:14", stgTag: "verdict · 3.1", stage: "au", tx: <>⚠ <span className="bad">冲突 3 处</span> · <b>3.2/A-12</b> · <b>5.1/D-07</b> · <b>7.3/F-02</b></> },
  { ts: "09:13:32", stgTag: "verdict · 3.2", stage: "au", typing: true, tx: <>🔄 <b>整改单生成</b> · <em>A-12 优先</em></> },
];

const SECTIONS: DocSection[] = [
  {
    n: "01", name: "政策概览", en: "Policy Overview", state: "ok", stateText: "3/3",
    body: <p>银保监 2026-04-18 发布《小微信贷风控新规》，共 <span className="num">3</span> 节：① <em>适用范围</em>——单户授信 500 万元以下的小微企业信贷业务，银行业金融机构在境内开展；② <em>禁止行为</em>——禁止无差别全量数据采集、禁止跳过人工复核自动放款、禁止不良资产披露滞后；③ <em>处罚条款</em>——违反将责令限期整改，累计违规 3 次以上暂停相关业务资质。</p>,
  },
  {
    n: "02", name: "冲突 1 · 边界冲突", en: "Conflict · Threshold", state: "warn", stateText: "P0 本周五前",
    body: <p>新规 <em>3.2 条</em>「单户 500 万以上须人审」vs 内控 <em>A-12</em>「500 万以下快贷通道」。差异：新规以 <span className="num">500</span> 万为刚性人审触发点，内控 A-12 现版为 <span className="num">500</span> 万以下走快贷、以上直接切断通道（无旁路）。影响业务：小微快贷通道（月均 <span className="num">1,200</span> 笔 / <span className="num">8,600</span> 万额度）。建议动作：加 <em>500 万以上自动走人审旁路</em>，保留 500 万以下快贷。负责人：信贷 IT + 业务。整改周期 <b>本周五前</b>。</p>,
  },
  {
    n: "03", name: "冲突 2 · 范围冲突", en: "Conflict · Scope", state: "warn", stateText: "P1 下周",
    body: <p>新规 <em>5.1 条</em>「数据采集最小化」vs 内控 <em>D-07</em>「全量画像采集」。差异：新规要求按授信所需最小字段集采集，D-07 现采集字段 <span className="num">142</span> 项（含非必要项 <span className="num">38</span> 项）。影响：客户画像模块 + 授信决策模型。建议动作：生成 <em>白名单字段清单</em>，砍非必要项；画像模块改造同步接入。周期下周评审排期。</p>,
  },
  {
    n: "04", name: "冲突 3 · 时效冲突", en: "Conflict · Timing", state: "warn", stateText: "P1 下周",
    body: <p>新规 <em>7.3 条</em>「不良披露 T+5」vs 内控 <em>F-02</em>「T+15」。差异：新规要求不良资产生成后 <span className="num">5</span> 个工作日内披露，F-02 现为 <span className="num">15</span> 日。影响：不良资产披露流程 + 报送系统。建议动作：改造报送流程至 <em>T+5 触发器</em>，对接人行征信 + 银保监季报接口。周期下周评审排期。</p>,
  },
  {
    n: "05", name: "一致条款", en: "Aligned", state: "ok", stateText: "85/85",
    body: <p>内控 <span className="num">85</span> 项与新规要求一致（不良率红线 <span className="num">5%</span>、反洗钱尽调、征信异议处理、信息披露基本要求、投诉处置 48h 响应等），无需调整。</p>,
  },
  {
    n: "06", name: "补充条款", en: "Supplement", state: "warn", stateText: "12 新增",
    body: <p>新规引入 <span className="num">12</span> 条现内控未覆盖的新要求：模型可解释性说明、算法备案、员工行为异常监测、季度压力测试回溯等。建议新建内控条款覆盖，纳入下一轮制度汇编。</p>,
  },
  {
    n: "07", name: "无关条款", en: "Out-of-Scope", state: "ok", stateText: "28",
    body: <p>新规 <span className="num">28</span> 条与我行当前业务无直接关联（含涉外业务、代客外汇理财、跨境支付等分行未开展业务），保留归档备查，暂不触发制度修订。</p>,
  },
  {
    n: "08", name: "整改优先级", en: "Priority", state: "warn", stateText: "1 P0 + 2 P1",
    body: <p><em>A-12</em> <b>P0</b>——本周五前推草案，边界旁路改造；<em>D-07</em> <b>P1</b>——下周评审白名单字段；<em>F-02</em> <b>P1</b>——下周评审 T+5 流程。三项合并入 <span className="num">2026Q2</span> 合规整改清单。</p>,
  },
  {
    n: "09", name: "抄送清单", en: "Dispatch", state: "ok", stateText: "4 组",
    body: <p>整改单已抄送：<em>反洗钱办公室</em>（牵头协调）、<em>法务部</em>（条款合规口径）、<em>信贷 IT</em>（快贷通道改造 / 披露报送系统）、<em>数据治理</em>（白名单字段）。邮件流水号 COMPLI-20260420-0917。</p>,
  },
  {
    n: "10", name: "培训要点", en: "Training", state: "ok", stateText: "6 条",
    body: <p>面向客户经理 + 审贷员 <span className="num">6</span> 条培训要点：① 500 万边界新口径；② 快贷通道人审旁路操作；③ 数据采集最小化原则；④ 不良披露 T+5 节奏；⑤ 模型可解释话术；⑥ 违规累计 3 次停业务风险。本月底前完成线上培训。</p>,
  },
  {
    n: "11", name: "人审决议", en: "Committee", state: "pend", stateText: "合规委员会", flag: "pending",
    body: <p>待合规委员会定稿后 → 合规总监签发 → 各部门执行 → 整改回执归档。排期本周五例会。</p>,
  },
  {
    n: "12", name: "证据链", en: "Evidence", state: "ok", stateText: "全量留痕",
    body: <p>证据：政策原文 PDF（银保监官网 2026-04-18 发布）+ 内控原文（kb_internal_v2 · 128 项）+ 差异 diff（条款逐项对照表）+ 建议模板（整改单 / 白名单 / T+5 流程草案）。全部留痕可追溯，供合规委员会与监管稽核调阅。</p>,
  },
];

const QC_METRICS: QcMetric[] = [
  { k: "解析完整",   v: "100",     p: "100%" },
  { k: "配对覆盖",   v: "128/128", p: "100%" },
  { k: "判定置信",   v: "96.4",    p: "96%" },
  { k: "原文溯源",   v: "100",     p: "100%" },
  { k: "术语规范",   v: "99.2",    p: "99%" },
  { k: "时效",       v: "T+0",     p: "100%" },
  { k: "抄送覆盖",   v: "4/4",     p: "100%" },
  { k: "整改可执行", v: "92",      p: "92%" },
  { k: "历史误判",   v: "1.3",     p: "99%", hot: true },
];

export default function CompliV2() {
  return (
    <V2Shell
      agent="compli"
      hero={{
        eyebrowText: "COMPLI AGENT · 政策发布事件驱动",
        heroTitle: (
          <>
            <span className="cn">银保监</span> <em>小微信贷风控新规</em>，与内控 <em>3 处冲突</em>。
          </>
        ),
        heroSub: (
          <>
            04-18 新发布政策 <b>3</b> 节 · 扫内控制度库 <b>128</b> 项 · <b>3</b> 处冲突待处置 · <b>A-12</b> 条款建议本周内改版。
            <span className="bullet" />
            <button type="button" className="pill">生成整改单 ↗</button>
            <button type="button" className="pill ghost">原文对照</button>
          </>
        ),
      }}
      apHead={{
        zh: "合规助手 · 政策事件驱动",
        en: "Policy-Event Watcher",
        ver: "v3.1",
        metas: [
          { k: "擅长", v: "政策发布→内控映射→冲突判定" },
          { k: "当前", v: "3 冲突待处置", state: "warn" },
          { k: "今日", v: "1 政策事件" },
        ],
        health: "LLM 在线 · DeepSeek",
        cta: { label: "生成整改单", arrow: "↗" },
      }}
      cap={{ cn: "三阶段", em: "— Parse / Matrix / Verdict", k: "SESSION · 20260420-1024" }}
      stages={[
        { n: "01", nm: "解析", en: "— Parse", state: "done", sub: <>政策全文 <b>12</b> 节 · 抽 <em>适用范围 / 禁止行为 / 处罚条款</em></> },
        { n: "02", nm: "矩阵", en: "— Matrix", state: "done", sub: <>扫内控 <b>128</b> 项 · 与政策条款 <em>配对</em></> },
        { n: "03", nm: "判定", en: "— Verdict", state: "live", sub: <>冲突 <b>3</b> · 一致 <b>85</b> · 补充 <b>12</b> · <b>28</b> 无关</> },
      ]}
      tplTitle={{
        lbl: "选政策源",
        hint: <>已选 <b>银保监监管规章 · policy-banking-v3.1</b> · 扫 128 内控 · 切换会重新配对</>,
        k: "POLICY SOURCE",
      }}
      tpls={[
        { key: "banking", name: "银保监监管规章", tag: "On",    meta: "policy-banking-v3.1", spec: "3 节 / 128 内控", on: true },
        { key: "pboc",    name: "人行规章",       tag: "PBoC",  meta: "policy-pboc-v2.4",    spec: "反洗钱 + 征信" },
        { key: "cbrc",    name: "监管专项",       tag: "CBRC",  meta: "policy-cbrc-v1.8",    spec: "临时窗口指导" },
        { key: "local",   name: "地方监管",       tag: "Local", meta: "policy-local-v1.0",   spec: "苏州分行属地" },
      ]}
      intake={[
        { kind: "drop", title: "新政策文件 = 《小微信贷风控新规》2026-04-18 发布", sub: ".pdf 已解析 · 可上传新政策替换", btn: "上传新政策" },
        { kind: "opt", on: true, k: "业务矩阵", v: <>内控 v2.0</> },
        { kind: "opt", k: "事件时间", v: <>2026-04-18</> },
        { kind: "opt", k: "Mock 回放", v: <>关</>, toggle: true },
      ]}
      chatSlot={
        <ChatBlk
          title="对话 · 处置冲突"
          subTitle="— Verdict Chat"
          kBadge="3 conflict · A-12 P0"
          messages={MESSAGES}
          seeds={[
            { q: "Q1", body: <>展开<em>A-12</em>旧版原文</> },
            { q: "Q2", body: <>生成<em>员工培训</em>要点</> },
            { q: "Q3", body: <>抄送<em>风控 Agent2</em></> },
          ]}
          placeholder="继续追问 · 例如：A-12 草案模板、D-07 白名单字段…"
        />
      }
      docSlot={
        <>
          <SseBlk
            title={<>事件流 <em>— SSE · parse / matrix / verdict</em></>}
            kBadge="live"
            lines={SSE_LINES}
          />
          <DocWrap
            docTitle="政策-内控冲突清单 · 2026-04-18 银保监新规"
            docSubtitle="Conflict Ledger · policy-banking-v3.1"
            metrics={[
              <>3 冲突</>,
              <>85 一致</>,
              <>12 补充</>,
              <>28 无关</>,
              <span className="hot">整改 1 即时</span>,
            ]}
            sections={SECTIONS}
          />
        </>
      }
      auditSlot={
        <AuditStrip
          verdict={{
            k: "Verdict · 总体",
            v: <>可推合规委 <em>— A-12 本周内整改</em></>,
            tip: <>政策 <b>12</b> 节 · 内控 <b>128</b> 项 · 冲突 <b>3</b> · 整改 <b>1</b> P0 + <b>2</b> P1 · 抄送 <b>4</b> 组。</>,
            ctas: [
              { label: "原文对照" },
              { label: "生成整改单 ↗", primary: true },
            ],
          }}
          coverage={[
            { k: "政策覆盖", v: <>3<sub>/3 节</sub></> },
            { k: "内控覆盖", v: <>128<sub>/128</sub></> },
            { k: "冲突",     v: <>3<sub>处</sub></>, hot: true },
          ]}
          unfilled={{
            k: "未能自动填写 · 典型 3 项",
            items: (
              <>
                <span className="tag">法务口径复核</span>需法务部定稿 · <span className="tag">员工培训教材</span>待培训中心出 · <span className="tag">客户告知模板</span>营销部起草
              </>
            ),
          }}
          qc={QC_METRICS}
        />
      }
    />
  );
}
