# -*- coding: utf-8 -*-
"""Agent5 合规巡检雷达 v2.0 — Portal Demo Tab

矩阵扫描 UI：
    顶部统计条：规则 × 事件 = 矩阵单元 · 耗时 · 🔴 严重 🟡 一般 🟢 观察
    左侧违规榜单（三列分级 Radio）
    中部违规详情（条款原文 + 涉及单号 + 证据链）
    右侧整改建议（责任部门 + 时限）
    底部：导出 Excel / Word
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import gradio as gr

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.demo_ui import (
    render_header_html,
    ZHONGAN_BLUE,
    ZHONGAN_RED,
    ZHONGAN_YELLOW,
    ZHONGAN_GREEN,
    ZHONGAN_TEXT,
    ZHONGAN_TEXT_LIGHT,
    ZHONGAN_GRAY,
)
from agent_compliance.agent import ComplianceRadarAgent


# ---------------------------------------------------------------------------
# 场景卡（内嵌）
# ---------------------------------------------------------------------------

PRESET_SCENARIOS = [
    {
        "scenario_id": "internet_loan",
        "title": "互联网贷款合规专项巡检",
        "description": "3 份政策 + 145 条业务事件 → 9860 单元矩阵扫描，输出 🔴5 🟡8 🟢12 分级榜单",
        "stats_hint": "规则 68 · 事件 145 · 矩阵 9860",
    },
]


# ---------------------------------------------------------------------------
# 内部状态容器
# ---------------------------------------------------------------------------

_AGENT_SINGLETON: ComplianceRadarAgent | None = None


def _get_agent() -> ComplianceRadarAgent:
    global _AGENT_SINGLETON
    if _AGENT_SINGLETON is None:
        _AGENT_SINGLETON = ComplianceRadarAgent()
    return _AGENT_SINGLETON


# ---------------------------------------------------------------------------
# 渲染工具
# ---------------------------------------------------------------------------

def _stats_html(rules: int, events: int, cells: int,
                 severe: int, normal: int, observation: int,
                 duration: str = "—") -> str:
    """顶部统计条"""
    return f"""
<div style="display:grid; grid-template-columns: 2fr 1fr 1fr 1fr 1fr; gap:12px;
            padding:14px 18px; background:{ZHONGAN_GRAY}; border-radius:10px;
            border:1px solid #E5E7EB;">
    <div>
        <div style="color:{ZHONGAN_TEXT_LIGHT}; font-size:12px;">矩阵规模 / 用时</div>
        <div style="color:{ZHONGAN_TEXT}; font-size:16px; font-weight:600; margin-top:4px;">
            {rules} 规则 × {events} 事件 = <b style="color:{ZHONGAN_BLUE}">{cells:,}</b> 单元
            <span style="color:{ZHONGAN_TEXT_LIGHT}; font-size:13px; margin-left:12px;">⏱ {duration}</span>
        </div>
    </div>
    <div class="signal-light signal-red{' active' if severe > 0 else ''}">
        <div class="count">{severe}</div>
        <div class="label">🔴 严重</div>
    </div>
    <div class="signal-light signal-yellow">
        <div class="count">{normal}</div>
        <div class="label">🟡 一般</div>
    </div>
    <div class="signal-light signal-green">
        <div class="count">{observation}</div>
        <div class="label">🟢 观察</div>
    </div>
    <div style="align-self:center; text-align:right;">
        <div style="color:{ZHONGAN_TEXT_LIGHT}; font-size:12px;">命中总计</div>
        <div style="color:{ZHONGAN_TEXT}; font-size:24px; font-weight:700;">
            {severe + normal + observation}
        </div>
    </div>
</div>
"""


def _idle_stats_html() -> str:
    return _stats_html(0, 0, 0, 0, 0, 0, duration="未开始")


def _violation_choices(ledger) -> list[tuple[str, str]]:
    """把 ledger 中所有违规展平为 Radio 选项 [(label, violation_id), ...]"""
    choices = []
    for v in ledger.severe:
        choices.append((f"🔴 {v.violation_id} · {v.rule.title[:28]}", v.violation_id))
    for v in ledger.normal:
        choices.append((f"🟡 {v.violation_id} · {v.rule.title[:28]}", v.violation_id))
    for v in ledger.observation:
        choices.append((f"🟢 {v.violation_id} · {v.rule.title[:28]}", v.violation_id))
    return choices


def _all_violations(ledger):
    return list(ledger.severe) + list(ledger.normal) + list(ledger.observation)


def _detail_md(ledger, violation_id: str | None) -> tuple[str, str]:
    """返回 (左侧违规详情 md, 右侧整改建议 md)"""
    if ledger is None:
        return ("*尚未开始巡检*", "*尚未开始巡检*")
    if not violation_id:
        return ("*点击左侧任一违规查看详情*", "*点击左侧任一违规查看整改建议*")

    v = None
    for item in _all_violations(ledger):
        if item.violation_id == violation_id:
            v = item
            break
    if v is None:
        return (f"*未找到 {violation_id}*", "")

    sev_icon = {"critical": "🔴 严重", "major": "🟡 一般", "minor": "🟢 观察"}.get(v.severity, v.severity)

    # 左：违规详情
    event_rows = []
    for e in v.events[:20]:
        fields = e.get("fields", {})
        # 取前 4 个字段做证据展示
        kv_preview = "、".join(f"{k}={v2}" for k, v2 in list(fields.items())[:4])
        event_rows.append(
            f"| `{e['event_id']}` | {e.get('event_type','')} | {e.get('event_date','')} | {kv_preview} |"
        )
    evidence_table = (
        "| 单号 | 类型 | 日期 | 关键字段 |\n| --- | --- | --- | --- |\n"
        + "\n".join(event_rows)
    ) if event_rows else "*本条违规暂无业务事件（规则类/观察项）*"

    detail = f"""#### {sev_icon} · {v.violation_id}

**规则条款**：`{v.rule.rule_id}` · {v.rule.title}
**来源**：{v.rule.source_doc} · {v.rule.source_page}
**分类**：{v.rule.category}

> {v.rule.content}

**命中原因**
{v.match_reason}

**涉及业务事件**（{len(v.events)} 条）

{evidence_table}
"""

    # 右：整改建议
    chain_lines = []
    for i, c in enumerate(v.evidence_chain[:5], 1):
        chain_lines.append(
            f"{i}. `{c.get('event_id','')}` — {c.get('evidence','')[:160]}"
        )
    chain_md = "\n".join(chain_lines) if chain_lines else "—"

    remediation = f"""#### 🛠 整改建议 · {v.violation_id}

**责任部门**：{" / ".join(v.responsible_depts)}
**整改时限**：{v.deadline}

**建议措施**

{v.recommendation or '—'}

---

**证据链摘要**

{chain_md}
"""
    return (detail, remediation)


# ---------------------------------------------------------------------------
# 主运行逻辑（流式回调）
# ---------------------------------------------------------------------------

def _run_scenario_stream(scenario_id: str):
    """运行场景，流式 yield UI 更新。

    yields:
        (stats_html, status_md, radio_update, detail_md, remediation_md,
         xlsx_file, docx_file)
    """
    agent = _get_agent()

    # 起始：清空状态
    yield (
        _idle_stats_html(),
        f"⏳ 正在装载知识库并启动矩阵扫描...",
        gr.update(choices=[], value=None),
        "*矩阵扫描运行中...*",
        "*矩阵扫描运行中...*",
        None,
        None,
    )

    t0 = time.time()
    status_lines: list[str] = []
    xlsx_path: str | None = None
    docx_path: str | None = None

    try:
        for event in agent.process_message(
            user_message="", scenario_id=scenario_id
        ):
            etype = event.get("type", "")
            content = event.get("content", "")

            if etype == "thinking":
                status_lines.append(f"💭 {content}")
            elif etype == "message":
                # 保留最近 10 行
                status_lines.append(content)
            elif etype == "tool_call":
                status_lines.append(f"🔧 `{event.get('name','')}` ...")
            elif etype == "tool_result":
                status_lines.append(
                    f"✅ `{event.get('name','')}` → {event.get('result','')}"
                )
            elif etype == "file":
                p = event.get("path") or ""
                if p.endswith(".xlsx"):
                    xlsx_path = p
                elif p.endswith(".docx"):
                    docx_path = p
                status_lines.append(f"📦 导出：`{os.path.basename(p)}`")
            elif etype == "done":
                status_lines.append(f"🏁 {content}")

            # 从 agent 取当前进度
            ledger = agent.last_ledger
            rules = agent.last_rules or []
            events_list = agent.last_events or []
            cells = len(rules) * len(events_list)
            sev = len(ledger.severe) if ledger else 0
            nrm = len(ledger.normal) if ledger else 0
            obs = len(ledger.observation) if ledger else 0

            dur = f"{time.time() - t0:.1f}s"
            status_md = "  \n".join(status_lines[-12:])

            yield (
                _stats_html(len(rules), len(events_list), cells,
                             sev, nrm, obs, duration=dur),
                status_md,
                gr.update(choices=_violation_choices(ledger) if ledger else [],
                           value=None),
                "*扫描中，稍候查看违规详情*",
                "*扫描中，稍候查看整改建议*",
                xlsx_path,
                docx_path,
            )

    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError) as e:
        status_lines.append(f"❌ 异常：{type(e).__name__}: {e}")
        yield (
            _idle_stats_html(),
            "  \n".join(status_lines[-12:]),
            gr.update(choices=[], value=None),
            f"*执行异常：{e}*",
            "*执行异常*",
            None,
            None,
        )
        return

    # 扫描完成：首次详情默认选中第一条严重违规
    ledger = agent.last_ledger
    if ledger and ledger.severe:
        first_id = ledger.severe[0].violation_id
        detail, remed = _detail_md(ledger, first_id)
    else:
        first_id = None
        detail, remed = ("*无严重违规*", "*无严重违规*")

    rules = agent.last_rules or []
    events_list = agent.last_events or []
    cells = len(rules) * len(events_list)
    dur = f"{time.time() - t0:.1f}s"

    yield (
        _stats_html(len(rules), len(events_list), cells,
                     len(ledger.severe) if ledger else 0,
                     len(ledger.normal) if ledger else 0,
                     len(ledger.observation) if ledger else 0,
                     duration=dur),
        "  \n".join(status_lines[-12:]),
        gr.update(choices=_violation_choices(ledger) if ledger else [],
                   value=first_id),
        detail,
        remed,
        xlsx_path,
        docx_path,
    )


# ---------------------------------------------------------------------------
# Portal 入口
# ---------------------------------------------------------------------------

def build_tab(api_key_state, provider_state):
    """Portal 调用此函数构建 Tab 内容。"""

    gr.HTML(render_header_html(
        "合规巡检雷达 v2.0",
        "矩阵扫描 · 规则集 × 事件集 → 分级违规榜单 · 证据链到单号",
    ))

    # ---------- 场景选择 ----------
    gr.Markdown("#### 📋 预置场景")
    scenario_buttons = []
    with gr.Row():
        for sc in PRESET_SCENARIOS:
            with gr.Column(scale=1, min_width=240):
                gr.HTML(f"""
<div style="border:1px solid #E5E7EB; border-radius:10px; padding:14px; background:white;">
    <div style="color:{ZHONGAN_BLUE}; font-weight:600; font-size:15px;">📍 {sc['title']}</div>
    <div style="color:{ZHONGAN_TEXT_LIGHT}; font-size:12px; margin:6px 0 10px 0; line-height:1.5;">
        {sc['description']}
    </div>
    <div style="color:{ZHONGAN_TEXT}; font-size:12px;">
        <b>预期：</b>{sc['stats_hint']}
    </div>
</div>
""")
                btn = gr.Button(
                    f"🚀 启动巡检：{sc['title']}",
                    variant="primary",
                    elem_classes=["zhongan-btn-primary"],
                )
                scenario_buttons.append((btn, sc["scenario_id"]))

    gr.Markdown(
        f"<div class='muted-note'>矩阵扫描基于硬规则 + 预埋非严重项，确保 Demo 稳定输出。"
        f"自定义上传暂通过 Agent 自定义入口使用。</div>"
    )

    # ---------- 顶部统计条 ----------
    stats_html = gr.HTML(_idle_stats_html())

    # ---------- 3 列：榜单 / 详情 / 建议 ----------
    with gr.Row():
        with gr.Column(scale=2):
            gr.Markdown("### 📋 违规榜单")
            violation_radio = gr.Radio(
                label="点击任一违规查看详情",
                choices=[],
                value=None,
                interactive=True,
            )
        with gr.Column(scale=4):
            gr.Markdown("### 🔍 违规详情")
            detail_md = gr.Markdown("*请点击「启动巡检」开始矩阵扫描*")
        with gr.Column(scale=3):
            gr.Markdown("### 🛠 整改建议")
            remediation_md = gr.Markdown("*等待扫描完成后展示*")

    # ---------- 执行日志（折叠） ----------
    with gr.Accordion("🔍 执行过程（实时日志）", open=False):
        status_md = gr.Markdown("*尚未开始运行*")

    # ---------- 导出区 ----------
    gr.Markdown("### 📦 导出")
    with gr.Row():
        xlsx_file = gr.File(label="违规榜单 Excel", interactive=False)
        docx_file = gr.File(label="整改报告 Word", interactive=False)

    # ---------- 事件绑定 ----------
    outputs = [
        stats_html, status_md, violation_radio,
        detail_md, remediation_md, xlsx_file, docx_file,
    ]
    def _make_runner(sid):
        def _runner():
            yield from _run_scenario_stream(sid)
        return _runner

    for btn, sid in scenario_buttons:
        btn.click(
            fn=_make_runner(sid),
            inputs=None,
            outputs=outputs,
        )

    # 点击榜单切换详情
    def _on_select(violation_id):
        agent = _get_agent()
        ledger = agent.last_ledger
        return _detail_md(ledger, violation_id)

    violation_radio.change(
        fn=_on_select,
        inputs=[violation_radio],
        outputs=[detail_md, remediation_md],
    )
