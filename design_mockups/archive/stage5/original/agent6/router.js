/* ═══════════════════════════════════════════════════════════════════
   Agent6 · Router + 6 View Renderers
   ═══════════════════════════════════════════════════════════════════ */
(function(){

const AGENTS = {
  report:  {cn:"尽调 · 编撰",   en:"Dossier Scrivener", seal:"尽", tone:"t-report",   bg:"#B08640", fg:"#7A5A24", skill:"中小企业经营画像与授信支撑", state:"运行中", stateCls:""},
  alert:   {cn:"舆情 · 哨兵",   en:"Sentry",            seal:"哨", tone:"t-alert",    bg:"#C85A3C", fg:"#8A3318", skill:"裁判文书 · 环保 · 股东舆情合流监听", state:"3 条新信号", stateCls:"warn"},
  compli:  {cn:"合规 · 校对",   en:"Canon",             seal:"规", tone:"t-compli",   bg:"#5B7A48", fg:"#3D5A2A", skill:"报告齐备性与口径合规双层校验", state:"待核 2 份", stateCls:""},
  credit:  {cn:"额度 · 量尺",   en:"Ledger",            seal:"额", tone:"t-credit",   bg:"#3E6292", fg:"#27456D", skill:"按行业常模给出额度建议区间", state:"空闲", stateCls:"idle"},
  risk:    {cn:"贷后 · 巡检",   en:"Watcher",           seal:"巡", tone:"t-riskctrl", bg:"#6B4A6D", fg:"#462946", skill:"对资金流向与履约节奏做月度复盘", state:"9 户在管", stateCls:""},
  chan:    {cn:"渠道 · 邀约",   en:"Herald",            seal:"渠", tone:"t-channel",  bg:"#3C7B7B", fg:"#1F5A5A", skill:"依画像生成邀约话术与沟通节奏", state:"空闲", stateCls:"idle"}
};
const ORDER = ["report","alert","compli","credit","risk","chan"];

/* ---------- HOME · 6 气泡 ---------- */
function viewHome(){
  const bubs = [
    {id:"report", nums:[["Today","4","次"],["Cover","96","%"],["Latency","42","秒"]],
     line:"把 <em>流水 · 税 · 征信 · 合同</em> 揉成一份可签字底稿。每步留凭据。"},
    {id:"alert",  nums:[["Watched","28","户"],["New/24h","3","hot"],["Hit","14","次"]],
     line:"六个公开源合流，给每条信号打 <em>级</em>，按规则推到对应责任人。"},
    {id:"compli", nums:[["Queue","2","份"],["Pass","92","%"],["Avg","18","秒"]],
     line:"底稿对口径 —— <em>齐备性 · 合规性</em> 双层校对，异议点红点标注。"},
    {id:"credit", nums:[["Model","3","档"],["Range","800–3200","万"],["Run","6","次"]],
     line:"按行业常模给出 <em>授信结构</em> 建议，滑杆反算利率、月供与覆盖。"},
    {id:"risk",   nums:[["In-book","9","户"],["Warn","2","户"],["Coverage","87","%"]],
     line:"逐月把 <em>资金流向 · 履约节奏</em> 做一遍。异常户自动升级。"},
    {id:"chan",   nums:[["Templates","12","条"],["Hit-rate","34","%"],["Pipeline","46","户"]],
     line:"画像写画像的话，节奏排节奏的序。话术可 <em>A/B</em>，也能一键候场。"}
  ];

  const html = bubs.map(b => {
    const a = AGENTS[b.id];
    const pulse = a.stateCls === "idle" ? "idle" : (b.id==="alert" || b.id==="compli" ? "warn" : "");
    return `
      <button class="hub-bub ${a.tone}" data-go="a/${b.id}" aria-label="${a.cn}">
        <div class="bub-top">
          <div class="seal">${a.seal}</div>
          <div class="kcode"><span class="pulse ${pulse}"></span>${a.state}</div>
        </div>
        <div class="bub-ti"><span class="cn">${a.cn.split(" · ")[0]}</span><em>${a.cn.split(" · ")[1]||""} · ${a.en}</em></div>
        <div class="bub-line">${b.line}</div>
        <div class="bub-nums">
          ${b.nums.map(n=>`<div class="n"><div class="l">${n[0]}</div><div class="v ${n[2]==='hot'?'hot':''}">${n[1]}${n[2] && n[2]!=='hot'?`<sub>${n[2]}</sub>`:''}</div></div>`).join("")}
        </div>
        <span class="enter">进入 <span class="a">↗</span></span>
      </button>`;
  }).join("");

  return `
    <div class="view v-home on">
      <div class="hub">${html}</div>
      <div class="hub-belt">
        <div class="c"><div class="k">Today Runs</div><div class="v">14<sub>次</sub></div><div class="n">14 次协作，全部留痕。</div></div>
        <div class="c"><div class="k">Cite Coverage</div><div class="v">96<sub>%</sub></div><div class="n">主结论 <em>引得出证</em>。</div></div>
        <div class="c"><div class="k">Avg Latency</div><div class="v">42<sub>秒</sub></div><div class="n">从材料到底稿。</div></div>
        <div class="c"><div class="k">On-book</div><div class="v">9<sub>户</sub></div><div class="n">巡检覆盖，<em>2 户</em> 需复盘。</div></div>
      </div>
    </div>`;
}

/* ---------- Agent head 通用 ---------- */
function apHead(id, extraMeta){
  const a = AGENTS[id];
  const meta = extraMeta || [["擅长", a.skill],["数据源","14 接入","ok"],["今日","4 次 · 全部留痕"]];
  return `
    <header class="ap-head" style="--seal-bg:color-mix(in srgb,${a.bg} 26%,var(--chalk));--seal-fg:${a.fg};">
      <div class="seal">${a.seal}</div>
      <div class="id">
        <div class="nm"><span class="cn">${a.cn}</span><em>${a.en}</em><span class="ver">v2.4</span></div>
        <div class="meta">${meta.map(m=>`<span class="mt"><span class="k">${m[0]}</span><span class="v ${m[2]||''}">${m[1]}</span></span>`).join("")}</div>
      </div>
      <button class="cta"><span>跑一次</span><span class="a">↗</span></button>
    </header>`;
}

/* ---------- AGENT 1 · 尽调 · 编撰 ---------- */
function viewReport(){
  return `
    <div class="view v-report ap a-report">
      ${apHead("report")}

      <section class="ap-card">
        <div class="cap"><div class="t"><span class="cn">三阶段</span> <em>— Ingest / Audit / Package</em></div><div class="k">SU-2024-1142</div></div>
        <div class="stage-flow">
          <div class="stg done"><div class="hd"><span class="n">01</span><span class="nm">收集</span><em>— Ingest</em></div><div class="dot"></div><div class="sub"><em>凭据齐全</em>·6 份材料已带回·其中 1 份须复核</div></div>
          <div class="stg live"><div class="hd"><span class="n">02</span><span class="nm">审阅</span><em>— Audit</em></div><div class="dot"></div><div class="sub">正在把 <em>流水 · 税单 · 征信</em> 逐笔对齐·已完成 <b id="auditPct" style="font-family:var(--mono);">62%</b></div></div>
          <div class="stg"><div class="hd"><span class="n">03</span><span class="nm">成稿</span><em>— Package</em></div><div class="dot"></div><div class="sub">输出 <em>尽调卷 · 额度建议 · 风险清单</em>，由你签字定稿</div></div>
        </div>

        <div class="board">
          <div class="blk">
            <div class="hd"><div class="t">今日卷宗 <em>— 苏州睿联电子 · SU-2024-1142</em></div><div class="k">Working</div></div>
            <div style="display:flex;flex-direction:column;gap:5px;">
              <div class="docline ok"><span class="spine"></span><span class="ix">01</span><span class="nm">工商登记 + 变更台账<span class="sub">国家企业信用公示 · 2024-11-28</span></span><span class="st">已核对</span></div>
              <div class="docline ok"><span class="spine"></span><span class="ix">02</span><span class="nm">对公账户流水 12 个月<span class="sub">招行 · 苏州分行</span></span><span class="st">已核对</span></div>
              <div class="docline"><span class="spine"></span><span class="ix">03</span><span class="nm">纳税申报 · 增值税 / 所得税<span class="sub">电子税局 · 近 24 期</span></span><span class="st">解析中</span></div>
              <div class="docline warn"><span class="spine"></span><span class="ix">04</span><span class="nm">人行征信 · 企业版<span class="sub">报告 SZ-20241128-0417</span></span><span class="st">须复核</span></div>
              <div class="docline ok"><span class="spine"></span><span class="ix">05</span><span class="nm">上下游合同样本 5 份<span class="sub">长电 / 歌尔 / 立讯</span></span><span class="st">已核对</span></div>
              <div class="docline wait"><span class="spine"></span><span class="ix">06</span><span class="nm">舆情 · 裁判文书 · 环保处罚<span class="sub">6 个公开源同步</span></span><span class="st">排队</span></div>
            </div>
            <div style="margin-top:6px;padding-top:12px;border-top:1px solid var(--ink-14);">
              <div style="display:flex;justify-content:space-between;margin-bottom:10px;">
                <div style="font-family:var(--cjkserif);font-weight:600;font-size:13.5px;">推理流水 <em style="font-family:var(--italic);font-style:italic;font-weight:400;color:var(--ink-65);font-size:12px;margin-left:6px;">— Trace</em></div>
                <div style="font-family:var(--mono);font-size:9.5px;letter-spacing:.16em;color:var(--ink-48);text-transform:uppercase;">Live · auto-scroll</div>
              </div>
              <div class="trace">
                <div class="trace-line"><span class="ts">10:23:41</span><span class="tx">读取 <b>流水 · 12 期</b>，对公入账合计 <b>8,142 万</b> <span class="src">SRC · 招行</span></span></div>
                <div class="trace-line"><span class="ts">10:23:58</span><span class="tx">与 <b>纳税申报</b> 核对，营收口径差 <em>4.2%</em>，容忍带内 <span class="src">SRC · 税局</span></span></div>
                <div class="trace-line"><span class="ts">10:24:03</span><span class="tx">提取 <b>Top 5 下游</b>：长电 / 歌尔 / 立讯 / 华勤 / 和硕 <span class="src">SRC · 合同</span></span></div>
                <div class="trace-line"><span class="ts">10:24:12</span><span class="tx">关注：应收账期 <em>偏长</em>，歌尔系占比 <b>32%</b> <span class="src">SRC · 流水</span></span></div>
                <div class="trace-line"><span class="ts">10:24:19</span><span class="tx">征信报告里发现 <em>1 条关联担保</em>，同城关联公司<span class="trace-typing"></span></span></div>
              </div>
            </div>
          </div>
          <div class="blk">
            <div class="hd"><div class="t">今日建议 <em>— Recommendation</em></div><div class="k">Draft</div></div>
            <div class="verdict">
              <div class="k">Verdict · 主结论</div>
              <div class="v">可授信 <em>2,400 万</em></div>
              <div class="tip">建议采 <b>1,800 万经营循环 + 600 万应收池</b>；以 <em>歌尔 / 立讯</em> 两条应收线做主回款锚。账期偏长，纳入 <b>月度巡检</b>。</div>
            </div>
            <div class="metrics3">
              <div class="m"><div class="k">Coverage</div><div class="v">96<sub>%</sub></div></div>
              <div class="m"><div class="k">Confidence</div><div class="v">0.87</div></div>
              <div class="m"><div class="k">Risk</div><div class="v hot">中</div></div>
            </div>
            <div class="cta-row">
              <button class="cta">复核底稿</button>
              <button class="cta primary">签发建议稿 ↗</button>
            </div>
          </div>
        </div>
      </section>
    </div>`;
}

/* ---------- AGENT 2 · 舆情 · 哨兵 ---------- */
function viewAlert(){
  const signals = [
    {ts:"10:24", lv:"hi",  lvtx:"高", cn:"长三角环保通报：苏州工业园区 <b>某电子企业</b> 被列入待复核名单", s:"关键词命中：长电 · 连接器·污水 → 关联客户 <em>睿联电子</em>", src:"江苏环保"},
    {ts:"10:17", lv:"mid", lvtx:"中", cn:"裁判文书网：<b>歌尔股份</b> 买卖合同纠纷 2 宗新增", s:"非主诉方，但我们 3 户客户与其上下游相关", src:"裁判文书"},
    {ts:"09:58", lv:"mid", lvtx:"中", cn:"股东舆情：<b>华勤技术</b> 董事减持 <em>1.2%</em>", s:"我们 1 户客户主供华勤，触发 <em>集中度-联动</em> 规则", src:"巨潮"},
    {ts:"09:41", lv:"lo",  lvtx:"低", cn:"招标公告：<b>立讯精密</b> 新增 5 起小额采购", s:"正向信号，入线索池", src:"招标网"},
    {ts:"08:52", lv:"hi",  lvtx:"高", cn:"行政处罚：<b>苏州某显示企业</b> 因环评超标被罚 <em>38 万</em>", s:"非在册客户，标注供参考", src:"生态环境局"}
  ];
  const rules = [
    {nm:"环保处罚", when:"罚额 ≥ 30 万 · 在册", to:"风险 → 客户经理 + 风控"},
    {nm:"司法涉诉", when:"买卖 / 借贷 · 金额 ≥ 100 万", to:"风险 → 客户经理"},
    {nm:"股东变动", when:"减持 ≥ 1% 或 董事辞任", to:"提示 → 客户经理"},
    {nm:"集中度联动", when:"单一下游占比 ≥ 30%", to:"提示 → 客户经理 · 风控"}
  ];
  // 热图 24 小时
  const heat = Array.from({length:24}, (_,i)=>{
    const v = [8,16,17,21,22].includes(i) ? 3 : [9,10,14,15].includes(i) ? 2 : [11,13,18].includes(i) ? 1 : 0;
    return `<div class="cell" data-l="${v||''}"></div>`;
  }).join("");

  return `
    <div class="view v-alert ap a-alert">
      ${apHead("alert", [["监听","6 公开源 · 14 客户"],["响应","30 秒内","ok"],["今日","14 命中 · 3 高"]])}
      <div class="a-alert-grid">
        <section class="ap-card">
          <div class="cap"><div class="t"><span class="cn">信号流</span> <em>— Live signals · 近 2 小时</em></div><div class="k">Auto</div></div>
          <div class="stream">
            ${signals.map((x,i)=>`
              <div class="sig-row" style="animation-delay:${i*.1}s">
                <span class="ts">${x.ts}</span>
                <span class="lv ${x.lv}">${x.lvtx} 级</span>
                <div class="cn">${x.cn}<span class="s">${x.s}</span></div>
                <span class="src">SRC · ${x.src}</span>
              </div>`).join("")}
          </div>
        </section>
        <div style="display:flex;flex-direction:column;gap:18px;">
          <section class="ap-card">
            <div class="cap"><div class="t"><span class="cn">24h 热度</span> <em>— signal density</em></div><div class="k">UTC+8</div></div>
            <div class="shelf">
              <div class="heat">${heat}</div>
              <div class="heat-legend"><span>00</span><span>06</span><span>12</span><span>18</span><span>24</span></div>
            </div>
          </section>
          <section class="ap-card">
            <div class="cap"><div class="t"><span class="cn">触发规则</span> <em>— Routing</em></div><div class="k">4 / 12</div></div>
            <div class="shelf">
              <div class="rules-list">
                ${rules.map((r,i)=>`<div class="rule-it ${i===0?'on':''}"><span class="nm">${r.nm}<span class="when">· ${r.when}</span></span><span class="to">${r.to.replace('→','<b>→</b>')}</span></div>`).join("")}
              </div>
            </div>
          </section>
          <section class="ap-card">
            <div class="cap"><div class="t"><span class="cn">投递记录</span> <em>— Deliveries</em></div><div class="k">今日</div></div>
            <div class="send-log">
              <div class="ln"><span class="ts">10:24</span><span>→ <b>周岚</b> · 企业微信 · <em>高级信号</em> 已送达</span></div>
              <div class="ln"><span class="ts">09:58</span><span>→ <b>周岚</b> + 风控王哲 · 邮件</span></div>
              <div class="ln"><span class="ts">09:41</span><span>→ <b>周岚</b> · 入线索池，不打扰</span></div>
              <div class="ln"><span class="ts">08:52</span><span>→ 归档 · 非在册客户</span></div>
            </div>
          </section>
        </div>
      </div>
    </div>`;
}

/* ---------- AGENT 3 · 合规 · 校对 ---------- */
function viewCompli(){
  return `
    <div class="view v-compli ap a-compli">
      ${apHead("compli", [["模板","信贷局口径 2024Q4"],["规则","228 条","ok"],["今日","6 稿 · 2 待核"]])}
      <div class="a-compli-grid">
        <section class="ap-card" style="padding:0;overflow:visible;">
          <div class="canon-page">
            <div class="pg-tab">原稿 · Draft</div>
            <h4>一、授信主体情况</h4>
            <p>苏州睿联电子股份有限公司，成立于 <span class="num">2011</span> 年，注册资本 <span class="num">5,000</span> 万元。主营<span class="approve">电子元器件制造与销售</span>。</p>
            <h4>二、经营情况</h4>
            <p>根据对公账户流水，近十二个月入账合计 <span class="flag" data-n="1">81.4 亿元</span>，与纳税申报营收 <span class="num">7.82 亿元</span> 口径差异 <span class="flag" data-n="2">约 4.1%</span>。</p>
            <p>下游集中度：前五客户占比 <span class="num">78%</span>，<span class="flag" data-n="3">单一下游占比 32%（歌尔系）</span>。</p>
            <h4>三、授信方案</h4>
            <p>建议额度 <span class="approve">2,400 万元</span>，采取 <span class="approve">1,800 万循环贷 + 600 万应收池</span> 结构。</p>
          </div>
        </section>
        <section class="ap-card" style="padding:0;overflow:visible;">
          <div class="canon-page">
            <div class="pg-tab">规则对照 · Canon</div>
            <h4>R-021 金额单位</h4>
            <p>流水入账口径应以 <b>人民币万元</b> 表述，不得混用"亿"；<span class="num">81.4 亿元</span> 应改为 <span class="approve">81,420 万元</span>。</p>
            <h4>R-047 数据口径</h4>
            <p>流水与税务营收差异 ≥ <span class="num">3%</span> 须书面说明；本稿差异 <span class="num">4.1%</span>，需补充 <b>差异形成原因</b> 章节。</p>
            <h4>R-104 集中度披露</h4>
            <p>单一下游占比 ≥ <span class="num">30%</span> 须在主结论前独立提示，<b>不得仅并入下游列表</b>。</p>
            <h4>R-301 授信结构</h4>
            <p>循环贷 + 应收池混合授信须附 <b>资金用途承诺函</b> 模板；本稿<span class="approve">已附</span>。</p>
          </div>
        </section>
        <div style="display:flex;flex-direction:column;gap:18px;">
          <section class="ap-card">
            <div class="cap"><div class="t"><span class="cn">批注</span> <em>— 3 red · 1 ok</em></div><div class="k">SU-1142</div></div>
            <div class="annots">
              <div class="annot">
                <div class="n">1</div>
                <div>
                  <div class="nm">口径：单位 <em>R-021</em></div>
                  <div class="tx"><b>81.4 亿元</b> → 规范为 <b>81,420 万元</b>。</div>
                  <div class="act"><button class="apply">一键替换</button><button>保留原文</button></div>
                </div>
              </div>
              <div class="annot">
                <div class="n">2</div>
                <div>
                  <div class="nm">差异说明 <em>R-047</em></div>
                  <div class="tx">差异 4.1% 超阈，需补 <b>差异形成原因</b> 段落。</div>
                  <div class="act"><button class="apply">生成段落</button><button>手动补</button></div>
                </div>
              </div>
              <div class="annot">
                <div class="n">3</div>
                <div>
                  <div class="nm">集中度披露 <em>R-104</em></div>
                  <div class="tx">需在主结论前置段独立提示 <b>歌尔系占比 32%</b>。</div>
                  <div class="act"><button class="apply">插入提示</button><button>查规则</button></div>
                </div>
              </div>
              <div class="annot ok">
                <div class="n">✓</div>
                <div>
                  <div class="nm">承诺函 <em>R-301</em></div>
                  <div class="tx">资金用途承诺函已附，通过。</div>
                </div>
              </div>
            </div>
            <div class="compli-stat">
              <div class="b"><div class="k">Score</div><div class="v ok">86<sub>/ 100</sub></div></div>
              <div class="b"><div class="k">Flags</div><div class="v hot">3<sub>待改</sub></div></div>
            </div>
            <div style="padding:12px 16px 18px;"><div class="cta-row"><button class="cta">查看完整规则</button><button class="cta primary">一键修稿 ↗</button></div></div>
          </section>
        </div>
      </div>
    </div>`;
}

/* ---------- AGENT 4 · 额度 · 量尺 ---------- */
function viewCredit(){
  // 小柱状图 12 月营收
  const months = [640,580,720,810,760,890,920,870,950,1020,980,1080];
  const maxM = Math.max(...months);
  const bars = months.map((v,i)=>{
    const h = v/maxM*42;
    const x = i*22 + 8;
    return `<rect x="${x}" y="${48-h}" width="14" height="${h}" class="${i>=9?'hot':''}"/><text x="${x+7}" y="62" text-anchor="middle">${i+1}</text>`;
  }).join("");

  return `
    <div class="view v-credit ap a-credit">
      ${apHead("credit", [["模型","SME-2024 · 电子元件"],["常模","江苏同业 P75","ok"],["今日","6 次测算"]])}
      <div class="a-credit-grid">
        <section class="ap-card">
          <div class="cap"><div class="t"><span class="cn">测算参数</span> <em>— Dials</em></div><div class="k">Live</div></div>
          <div class="dials">
            <div class="dial">
              <div class="lbl">授信额度 <em>principal</em></div>
              <div class="val"><span id="c-amt">2,400</span><sub>万元</sub></div>
              <div class="track">
                <input type="range" id="c-amt-i" min="800" max="3200" step="100" value="2400">
                <div class="mark"><span>800</span><span>1600</span><span>2400</span><span>3200 万</span></div>
              </div>
            </div>
            <div class="dial">
              <div class="lbl">期限 <em>tenor</em></div>
              <div class="val"><span id="c-ten">24</span><sub>月</sub></div>
              <div class="track">
                <input type="range" id="c-ten-i" min="6" max="36" step="3" value="24">
                <div class="mark"><span>6</span><span>12</span><span>24</span><span>36 月</span></div>
              </div>
            </div>
            <div class="dial">
              <div class="lbl">定价 <em>rate</em></div>
              <div class="val"><span id="c-rate">4.85</span><sub>% / 年</sub></div>
              <div class="track">
                <input type="range" id="c-rate-i" min="360" max="620" step="5" value="485">
                <div class="mark"><span>3.6</span><span>4.2</span><span>4.85</span><span>6.2 %</span></div>
              </div>
            </div>
          </div>

          <div class="cap" style="padding:10px 22px 12px;"><div class="t"><span class="cn">档位建议</span> <em>— by model</em></div><div class="k">P75</div></div>
          <div class="tier-row">
            <div class="tier" data-tier="0"><div class="k">保守</div><div class="v">1,800<sub>万</sub></div><div class="n">主循环 · 月供压力小</div></div>
            <div class="tier on" data-tier="1"><div class="k">推荐</div><div class="v">2,400<sub>万</sub></div><div class="n">循环 + 应收池混合</div></div>
            <div class="tier" data-tier="2"><div class="k">进取</div><div class="v">3,000<sub>万</sub></div><div class="n">需加强集中度监控</div></div>
          </div>
        </section>
        <section class="ap-card">
          <div class="cap"><div class="t"><span class="cn">测算结果</span> <em>— Outputs</em></div><div class="k">Live</div></div>
          <div class="calc">
            <div class="big">
              <div class="l">月均还款 <em>monthly payment</em></div>
              <div class="v"><span id="c-mth">105.2</span><sub>万</sub></div>
            </div>
            <div class="row">
              <div class="it"><div class="k">年度利息</div><div class="v"><span id="c-int">116.4</span><sub>万</sub></div></div>
              <div class="it"><div class="k">利息合计</div><div class="v"><span id="c-tot">124.8</span><sub>万</sub></div></div>
              <div class="it"><div class="k">现金覆盖</div><div class="v hot"><span id="c-cov">2.8</span><sub>×</sub></div></div>
            </div>
            <div style="padding-top:10px;border-top:1px dashed var(--ink-14);">
              <div style="font-family:var(--mono);font-size:9.5px;letter-spacing:.14em;color:var(--ink-48);text-transform:uppercase;margin-bottom:8px;">对公流水 · 近 12 月（万）</div>
              <svg class="chart-sm" viewBox="0 0 272 68">${bars}</svg>
            </div>
            <div class="cta-row">
              <button class="cta">存为方案</button>
              <button class="cta primary">送交审核 ↗</button>
            </div>
          </div>
        </section>
      </div>
    </div>`;
}

/* ---------- AGENT 5 · 贷后 · 巡检 ---------- */
function viewRisk(){
  const custs = [
    {nm:"睿联电子",   s:"SU-2024-1142 · 电子元件", amt:"2,400", h:82, hcls:"",     due:"12-15", stcls:"",     st:"正常"},
    {nm:"恒越精机",   s:"SU-2024-1098 · 机械",   amt:"1,600", h:71, hcls:"",     due:"12-18", stcls:"",     st:"正常"},
    {nm:"朗景光学",   s:"SU-2024-0871 · 光学",   amt:"800",   h:46, hcls:"warn", due:"11-30", stcls:"warn", st:"关注"},
    {nm:"汇业纺织",   s:"SU-2024-0533 · 纺织",   amt:"1,200", h:58, hcls:"warn", due:"12-02", stcls:"warn", st:"关注"},
    {nm:"云启科技",   s:"SU-2024-1201 · 软件",   amt:"500",   h:89, hcls:"",     due:"12-24", stcls:"",     st:"正常"},
    {nm:"吉昌建材",   s:"SU-2024-0329 · 建材",   amt:"900",   h:28, hcls:"bad",  due:"11-25", stcls:"bad",  st:"预警"},
    {nm:"盛达冷链",   s:"SU-2024-0912 · 物流",   amt:"1,500", h:77, hcls:"",     due:"12-20", stcls:"",     st:"正常"},
    {nm:"沛然食品",   s:"SU-2024-0664 · 食品",   amt:"600",   h:64, hcls:"",     due:"12-10", stcls:"",     st:"正常"},
    {nm:"伯纳新材",   s:"SU-2024-1033 · 新材料", amt:"1,800", h:74, hcls:"",     due:"12-12", stcls:"",     st:"正常"}
  ];
  // 散点图
  const w=420, h=260, pad=40;
  const plot = custs.map((c,i)=>{
    const x = pad + (parseFloat(c.amt.replace(",",""))/3200)*(w-pad-20);
    const y = h - pad - (c.h/100)*(h-pad-30);
    const col = c.hcls==="bad" ? "#C85A3C" : c.hcls==="warn" ? "#B08640" : "#5B7A48";
    return `<circle cx="${x}" cy="${y}" r="${6 + parseFloat(c.amt.replace(",",""))/800}" fill="${col}"/><text class="lbl" x="${x+10}" y="${y+3}">${c.nm}</text>`;
  }).join("");

  return `
    <div class="view v-risk ap a-risk">
      ${apHead("risk", [["在管","9 户 · 11,300 万"],["告警","2 户","warn"],["上次巡检","11-25"]])}
      <div class="a-risk-grid">
        <section class="ap-card">
          <div class="cap"><div class="t"><span class="cn">在管客户</span> <em>— Portfolio</em></div><div class="k">9 / 9</div></div>
          <div class="cust-matrix">
            <div class="cust-head"><div>客户</div><div style="text-align:right;">额度</div><div>健康度</div><div style="text-align:right;">到期</div><div style="text-align:right;">状态</div></div>
            ${custs.map(c=>`
              <div class="cust">
                <div class="nm">${c.nm}<span class="s">${c.s}</span></div>
                <div class="amt">${c.amt}<sub>万</sub></div>
                <div class="health ${c.hcls}"><div class="bar" style="--h:${c.h}%"></div><span>${c.h}</span></div>
                <div class="due">${c.due}</div>
                <div class="st ${c.stcls}">${c.st}</div>
              </div>`).join("")}
          </div>
        </section>
        <div style="display:flex;flex-direction:column;gap:18px;">
          <section class="ap-card">
            <div class="cap"><div class="t"><span class="cn">健康散点</span> <em>— Amount × Health</em></div><div class="k">Live</div></div>
            <div class="health-plot">
              <svg class="plot-svg" viewBox="0 0 ${w} ${h}">
                <line class="axis" x1="${pad}" y1="${pad-10}" x2="${pad}" y2="${h-pad}"/>
                <line class="axis" x1="${pad}" y1="${h-pad}" x2="${w-10}" y2="${h-pad}"/>
                <line class="grid" x1="${pad}" y1="${h-pad-80}" x2="${w-10}" y2="${h-pad-80}"/>
                <line class="grid" x1="${pad}" y1="${h-pad-160}" x2="${w-10}" y2="${h-pad-160}"/>
                <text class="tick" x="${pad-6}" y="${h-pad+4}" text-anchor="end">0</text>
                <text class="tick" x="${pad-6}" y="${h-pad-80+4}" text-anchor="end">50</text>
                <text class="tick" x="${pad-6}" y="${h-pad-160+4}" text-anchor="end">100</text>
                <text class="axis-lbl" x="${pad}" y="${pad-16}">Health ↑</text>
                <text class="axis-lbl" x="${w-10}" y="${h-10}" text-anchor="end">Amount →</text>
                ${plot}
              </svg>
            </div>
          </section>
          <section class="ap-card">
            <div class="cap"><div class="t"><span class="cn">巡检日志</span> <em>— This month</em></div><div class="k">11 月</div></div>
            <div class="inspect-log">
              <div class="ln"><span class="ts">11-25</span><span><b>吉昌建材</b>·流水骤降 <em>42%</em>，触发 <em>资金流向偏离</em>，已升级至风控</span></div>
              <div class="ln"><span class="ts">11-22</span><span><b>朗景光学</b>·连续 2 期开票集中在月末，拟线下走访</span></div>
              <div class="ln"><span class="ts">11-18</span><span><b>汇业纺织</b>·应收账期同比增加 <em>18 天</em></span></div>
              <div class="ln"><span class="ts">11-14</span><span><b>睿联电子</b>·月度例检通过，无异常</span></div>
              <div class="ln"><span class="ts">11-08</span><span>月初 9 户全扫一遍，基础面 <em>正常</em></span></div>
            </div>
            <div style="padding:12px 22px 20px;"><div class="cta-row"><button class="cta">生成月报</button><button class="cta primary">触发巡检 ↗</button></div></div>
          </section>
        </div>
      </div>
    </div>`;
}

/* ---------- AGENT 6 · 渠道 · 邀约 ---------- */
function viewChan(){
  return `
    <div class="view v-chan ap a-chan">
      ${apHead("chan", [["画像","42 维 · 实时"],["渠道","企业微信 · 电话 · 邮件"],["今日","12 邀 · 4 到场"]])}
      <div class="a-chan-grid">
        <section class="ap-card portrait">
          <div class="ava">
            <div class="ph">沈</div>
            <div class="nm">沈志远<span class="s">吉昌建材 · 创始人</span></div>
          </div>
          <div class="kv">
            <div class="k">年龄</div><div>42 · <b>苏州本地</b></div>
            <div class="k">决策</div><div><b>主决策</b> · 习惯晚 7 点后电话</div>
            <div class="k">上次</div><div>11-18 · 企业微信已读未回</div>
            <div class="k">偏好</div><div>面对面 > 邮件 > 电话</div>
            <div class="k">关切</div><div><b>账期</b> · 政府补贴</div>
          </div>
          <div class="traits">
            <span class="tg hot">现金流紧</span>
            <span class="tg hot">到期临近</span>
            <span class="tg">价格敏感</span>
            <span class="tg">家族式</span>
            <span class="tg">议价偏好</span>
          </div>
        </section>

        <section class="ap-card script-card">
          <div class="script-head">
            <button class="tab on" data-tab="A">版本 A · 稳重</button>
            <button class="tab" data-tab="B">版本 B · 亲切</button>
            <button class="tab" data-tab="C">版本 C · 直接</button>
          </div>
          <div class="script-box" id="script-A">
            <span class="tag hot">触达窗口 · 本周四 19:30 后</span>
            <p><b>沈总，您好，我是苏州分行周岚。</b></p>
            <p>上次您提到<em>账期比以往更紧</em>这件事，我把您近十二个月的<b>开票与回款节奏</b>做了一份小结，发现 <em>11 月至 1 月</em> 会是较紧的一段。</p>
            <p>我们这边针对您这种情况，准备了 <b>应收池 + 短期周转</b> 的组合，一句话讲就是——<em>让应收账变成可用现金</em>，利率 <b>4.85% 起</b>，先审后用不收费。</p>
            <p>想约您 <b>周四晚上 7 点半</b>，在厂里 20 分钟把方案捋一遍，您看行吗？</p>
          </div>
          <div class="script-tools">
            <div class="toggles">
              <button class="tg on">强调账期</button>
              <button class="tg">提利率</button>
              <button class="tg on">留面谈</button>
              <button class="tg">不群发</button>
            </div>
            <div class="send-row">
              <button class="cta">保存模板</button>
              <button class="cta primary">发送 ↗</button>
            </div>
          </div>
        </section>

        <section class="ap-card">
          <div class="cap"><div class="t"><span class="cn">沟通节奏</span> <em>— Cadence</em></div><div class="k">7 天</div></div>
          <div class="cadence">
            <div class="step"><div class="when">今<span class="d">周四</span>19:30</div><div class="what">电话邀约 <em>— 版本 A</em><span class="s">由客户经理周岚亲发</span></div></div>
            <div class="step"><div class="when">+1<span class="d">周五</span>10:00</div><div class="what">已读回执监听<span class="s">若未回，自动切到企业微信"方案已留厂门口"</span></div></div>
            <div class="step"><div class="when">+3<span class="d">周日</span>14:00</div><div class="what">预约上门 <em>— 20 min</em><span class="s">带 <b>应收池测算单</b> 与 <b>承诺函</b></span></div></div>
            <div class="step"><div class="when">+5<span class="d">周二</span></div><div class="what">进授信流程 <em>— Agent 1 接手</em><span class="s">自动把本次沟通纪要归档</span></div></div>
          </div>
        </section>
      </div>
    </div>`;
}

/* ---------- Router 核心 ---------- */
const VIEWS = {
  "home":     viewHome,
  "a/report": viewReport,
  "a/alert":  viewAlert,
  "a/compli": viewCompli,
  "a/credit": viewCredit,
  "a/risk":   viewRisk,
  "a/chan":   viewChan
};

function render(){
  const raw = (location.hash || "#/home").replace(/^#\/?/, "");
  const key = VIEWS[raw] ? raw : "home";
  const root = document.getElementById("router");
  root.setAttribute("data-view", key);
  document.body.setAttribute("data-view", key);
  root.innerHTML = VIEWS[key]();
  const v = root.querySelector(".view");
  if (v) v.classList.add("on");
  attachHandlers();
  if (key === "a/report") startAuditPct();
  if (key === "a/credit") bindCreditDials();
  if (key === "a/chan")   bindScriptTabs();

  // 更新 agent-bar on 状态
  document.querySelectorAll(".agent-bar .ab").forEach(x => x.classList.toggle("on", "a/"+x.dataset.go === key));
  window.scrollTo({top:0, behavior: "smooth"});
}

function attachHandlers(){
  document.querySelectorAll("[data-go]").forEach(el=>{
    el.onclick = () => { location.hash = "#/" + el.dataset.go; };
  });
}

/* ---------- agent 专属小绑定 ---------- */
function startAuditPct(){
  const el = document.getElementById("auditPct"); if (!el) return;
  let p = 62;
  const t = setInterval(()=>{
    if (!document.body.contains(el)) { clearInterval(t); return; }
    if (p >= 99) { el.textContent = "100%"; clearInterval(t); return; }
    p += Math.random() < .55 ? 1 : 0;
    el.textContent = p + "%";
  }, 1400);
}

function bindCreditDials(){
  const amt = document.getElementById("c-amt-i");
  const ten = document.getElementById("c-ten-i");
  const rate= document.getElementById("c-rate-i");
  if (!amt) return;

  const tiers = document.querySelectorAll(".tier");
  tiers.forEach(t=>{
    t.onclick = ()=>{
      tiers.forEach(x=>x.classList.remove("on"));
      t.classList.add("on");
      const v = [1800, 2400, 3000][+t.dataset.tier];
      amt.value = v; recalc();
    };
  });

  function recalc(){
    const P = +amt.value;                // 万
    const N = +ten.value;                // 月
    const R = (+rate.value) / 100 / 12;  // 月利率 (rate 是 % × 100，所以 /100 得 %, 再 /100 得小数)
    // rate slider 360 → 3.6%，所以先 /10000 × 12 拿年利?  注意：c-rate 显示为 +rate/100
    const rateShown = (+rate.value) / 100;
    const monthRate = rateShown / 100 / 12;
    // 等额本息
    const pow = Math.pow(1+monthRate, N);
    const pay = P * monthRate * pow / (pow - 1);
    const totalInt = pay * N - P;
    const yearInt  = P * rateShown / 100;
    const cover    = (1080 * 12 * 0.08) / (pay * 12); // mock: 月流水 1080 万 × 8% 净现

    document.getElementById("c-amt").textContent = P.toLocaleString();
    document.getElementById("c-ten").textContent = N;
    document.getElementById("c-rate").textContent = rateShown.toFixed(2);
    document.getElementById("c-mth").textContent = pay.toFixed(1);
    document.getElementById("c-int").textContent = yearInt.toFixed(1);
    document.getElementById("c-tot").textContent = totalInt.toFixed(1);
    document.getElementById("c-cov").textContent = (cover).toFixed(1);
  }
  [amt, ten, rate].forEach(i => i.addEventListener("input", recalc));
  recalc();
}

function bindScriptTabs(){
  const tabs = document.querySelectorAll(".script-head .tab");
  const variants = {
    A: [
      {tag:"触达窗口 · 本周四 19:30 后", hot:true},
      {p:"<b>沈总，您好，我是苏州分行周岚。</b>"},
      {p:"上次您提到<em>账期比以往更紧</em>这件事，我把您近十二个月的<b>开票与回款节奏</b>做了一份小结，发现 <em>11 月至 1 月</em> 会是较紧的一段。"},
      {p:"我们这边针对您这种情况，准备了 <b>应收池 + 短期周转</b> 的组合，一句话讲就是——<em>让应收账变成可用现金</em>，利率 <b>4.85% 起</b>，先审后用不收费。"},
      {p:"想约您 <b>周四晚上 7 点半</b>，在厂里 20 分钟把方案捋一遍，您看行吗？"}
    ],
    B: [
      {tag:"亲切口吻 · 适合熟客户", hot:false},
      {p:"<b>沈总，周岚啊。</b>"},
      {p:"晚上打扰了 —— 我这两天一直在看您的账，发现最近<em>回款有点往后拖</em>。想着别等到真紧了才讲，今天先打这个电话。"},
      {p:"我们有个<b>应收池</b>，简单讲就是把已开票的应收账 <em>提前一步变现</em>，利息比普通贷款低一档。您要不要让我去厂里，坐 20 分钟，我带着数算给您看。"},
      {p:"不急，您方便的时候我就过去，<b>这周还是下周都行</b>。"}
    ],
    C: [
      {tag:"直接型 · 适合决策快的", hot:false},
      {p:"<b>沈总，周岚。</b>"},
      {p:"三句话：您 <em>11-1 月</em> 资金会紧；我们有 <b>2,400 万</b> 的应收 + 周转组合；<em>利率 4.85% 起</em>。"},
      {p:"我<b>周四晚 7 点半</b>去厂里，20 分钟讲完，不办也没关系。"},
      {p:"方便的话回复个 <b>行</b>。"}
    ]
  };
  tabs.forEach(tb=>{
    tb.onclick = () => {
      tabs.forEach(x=>x.classList.remove("on"));
      tb.classList.add("on");
      const key = tb.dataset.tab;
      const box = document.querySelector(".script-box");
      box.innerHTML = variants[key].map(x => {
        if (x.tag) return `<span class="tag ${x.hot?'hot':''}">${x.tag}</span>`;
        return `<p>${x.p}</p>`;
      }).join("");
    };
  });
}

/* ---------- 顶部 agent 切换条 ---------- */
function buildAgentBar(){
  const bar = document.createElement("div");
  bar.className = "agent-bar";
  bar.innerHTML = `
    <button class="back" data-go="home"><span class="a">←</span><span>回到协作者</span></button>
    <div class="ab-list">
      ${ORDER.map(id => {
        const a = AGENTS[id];
        return `<button class="ab ${a.tone}" data-go="a/${id}"><span class="chip">${a.seal}</span><span>${a.cn.split(" · ")[0]}</span></button>`;
      }).join("")}
    </div>`;
  const stage = document.querySelector(".stage");
  const router = document.getElementById("router");
  stage.insertBefore(bar, router);
}

/* ---------- boot ---------- */
function boot(){
  // 主题切换（Palette）
  document.querySelectorAll(".theme-sw button").forEach(b=>{
    b.addEventListener("click", () => {
      document.querySelectorAll(".theme-sw button").forEach(x=>x.classList.remove("on"));
      b.classList.add("on");
      document.body.setAttribute("data-theme", b.dataset.t);
    });
  });
  // 时钟
  const t = document.getElementById("t");
  const tick = () => { t.textContent = new Date().toTimeString().slice(0,8); };
  tick(); setInterval(tick, 1000);

  buildAgentBar();
  render();
  window.addEventListener("hashchange", render);
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
else boot();

})();
