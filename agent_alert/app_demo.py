# -*- coding: utf-8 -*-
"""Agent4 贷中风险预警雷达 — Portal Demo Tab (v2.0)

核心设计：
- 顶部：场景卡（小微信贷 100 家扫描） + KB 上传（客户名录 / 规则 / 制度）
- 中部：扫描进度条 + 统计仪表盘（🔴/🟡/🟢 大数字）
- 下部左：红黄绿三栏榜单（红黄展开 / 绿折叠）
- 下部右：选中客户的详情卡片 + 处置建议
- 底部：实时 tick 流 Accordion + 导出按钮

被 portal_app.py 通过 build_tab(api_key_state, provider_state) 调用。
"""

from __future__ import annotations

import os
import sys
import json
import time
import html
from pathlib import Path
from typing import Generator

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import gradio as gr

from shared.demo_ui import (
    ZHONGAN_BLUE,
    ZHONGAN_BLUE_DARK,
    ZHONGAN_BLUE_LIGHT,
    ZHONGAN_ORANGE,
    ZHONGAN_GREEN,
    ZHONGAN_RED,
    ZHONGAN_YELLOW,
    ZHONGAN_GRAY,
    ZHONGAN_TEXT,
    ZHONGAN_TEXT_LIGHT,
)
from agent_alert.agent import AlertRadarAgent
from shared.kb_scan.models import HitList, HitItem, RiskLevel


# ---------------------------------------------------------------------------
# 场景卡片加载
# ---------------------------------------------------------------------------

SCENARIO_DIR = PROJECT_ROOT / "demo_data" / "agent_alert"


def _load_scenario() -> dict:
    p = SCENARIO_DIR / "scenario.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# 统计仪表盘 HTML
# ---------------------------------------------------------------------------

def _render_stats_bar(
    total: int = 0, red: int = 0, yellow: int = 0, green: int = 0,
    duration_s: float = 0.0, status: str = "idle",
) -> str:
    """渲染顶部仪表盘：扫描总数 / 3 灯统计 / 耗时。status: idle / running / done"""
    if status == "idle":
        status_badge = (
            f'<span style="background:{ZHONGAN_GRAY}; color:{ZHONGAN_TEXT_LIGHT}; '
            f'padding:4px 12px; border-radius:20px; font-size:12px;">待扫描</span>'
        )
    elif status == "running":
        status_badge = (
            f'<span style="background:{ZHONGAN_BLUE_LIGHT}; color:{ZHONGAN_BLUE}; '
            f'padding:4px 12px; border-radius:20px; font-size:12px;">扫描中...</span>'
        )
    else:
        status_badge = (
            f'<span style="background:#E8F5E9; color:{ZHONGAN_GREEN}; '
            f'padding:4px 12px; border-radius:20px; font-size:12px;">扫描完成</span>'
        )
    dur_text = f"用时 {duration_s:.1f}s" if duration_s > 0 else "—"
    return f"""
    <div style="background: white; border-radius: 12px; padding: 20px 24px;
                border: 1px solid #E5E7EB; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="display:flex; align-items:center; gap:12px;">
                <div style="font-size:16px; font-weight:700; color:{ZHONGAN_TEXT};">
                    在贷客户风险体检
                </div>
                {status_badge}
            </div>
            <div style="color:{ZHONGAN_TEXT_LIGHT}; font-size:13px;">{dur_text}</div>
        </div>
        <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:16px; margin-top:16px;">
            <div style="text-align:center; padding:14px 8px; background:{ZHONGAN_GRAY};
                        border-radius:10px;">
                <div style="font-size:28px; font-weight:700; color:{ZHONGAN_TEXT};">{total}</div>
                <div style="font-size:12px; color:{ZHONGAN_TEXT_LIGHT}; margin-top:4px;">扫描总数</div>
            </div>
            <div style="text-align:center; padding:14px 8px; background:#FFEBEE;
                        border-radius:10px;">
                <div style="font-size:28px; font-weight:700; color:{ZHONGAN_RED};">🔴 {red}</div>
                <div style="font-size:12px; color:{ZHONGAN_RED}; margin-top:4px;">高风险</div>
            </div>
            <div style="text-align:center; padding:14px 8px; background:#FFF8E1;
                        border-radius:10px;">
                <div style="font-size:28px; font-weight:700; color:{ZHONGAN_YELLOW};">🟡 {yellow}</div>
                <div style="font-size:12px; color:{ZHONGAN_YELLOW}; margin-top:4px;">中风险</div>
            </div>
            <div style="text-align:center; padding:14px 8px; background:#E8F5E9;
                        border-radius:10px;">
                <div style="font-size:28px; font-weight:700; color:{ZHONGAN_GREEN};">🟢 {green}</div>
                <div style="font-size:12px; color:{ZHONGAN_GREEN}; margin-top:4px;">低风险</div>
            </div>
        </div>
    </div>
    """


# ---------------------------------------------------------------------------
# 场景卡 HTML
# ---------------------------------------------------------------------------

def _render_scenario_card(scenario: dict) -> str:
    if not scenario:
        return f"""
        <div style="padding:14px; background:white; border:1px dashed #E5E7EB;
                    border-radius:10px; color:{ZHONGAN_TEXT_LIGHT}; text-align:center;">
            未发现预置场景（请先运行 demo_data/agent_alert/_build_customers.py）
        </div>
        """
    title = html.escape(scenario.get("title", "预置场景"))
    desc = html.escape(scenario.get("description", ""))
    exp = scenario.get("expected", {})
    return f"""
    <div style="padding:16px 18px; background:linear-gradient(135deg,{ZHONGAN_BLUE_LIGHT},#F5F9FF);
                border:1px solid {ZHONGAN_BLUE_LIGHT}; border-radius:12px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <div style="font-weight:700; font-size:15px; color:{ZHONGAN_BLUE_DARK};">
                    🎯 {title}
                </div>
                <div style="font-size:12px; color:{ZHONGAN_TEXT}; margin-top:6px;">{desc}</div>
            </div>
            <div style="display:flex; gap:8px; font-size:12px;">
                <span style="background:white; padding:4px 10px; border-radius:12px;
                             color:{ZHONGAN_RED}; border:1px solid #FFCDD2;">
                    🔴 预期 {exp.get('red', 0)}
                </span>
                <span style="background:white; padding:4px 10px; border-radius:12px;
                             color:{ZHONGAN_YELLOW}; border:1px solid #FFE082;">
                    🟡 预期 {exp.get('yellow', 0)}
                </span>
                <span style="background:white; padding:4px 10px; border-radius:12px;
                             color:{ZHONGAN_GREEN}; border:1px solid #C8E6C9;">
                    🟢 预期 {exp.get('green', 0)}
                </span>
            </div>
        </div>
    </div>
    """


# ---------------------------------------------------------------------------
# 实时 tick 流渲染（最近 N 条）
# ---------------------------------------------------------------------------

def _render_tick_stream(ticks: list[dict], max_show: int = 15) -> str:
    if not ticks:
        return f"""
        <div style="color:{ZHONGAN_TEXT_LIGHT}; padding:16px; text-align:center; font-size:13px;">
            等待扫描开始...
        </div>
        """
    # 只显示最近 N 条
    recent = ticks[-max_show:]
    rows = []
    for t in recent:
        ttype = t.get("type", "")
        if ttype == "scan_tick":
            idx = t.get("index", 0)
            total = t.get("total", 0)
            name = html.escape(t.get("customer_name", ""))
            lv = t.get("level", "")
            icon = {"red": "🔴", "yellow": "🟡", "green": "🟢"}.get(lv, "⚪")
            color = {"red": ZHONGAN_RED, "yellow": ZHONGAN_YELLOW,
                     "green": ZHONGAN_GREEN}.get(lv, ZHONGAN_TEXT_LIGHT)
            rows.append(
                f'<div style="padding:4px 10px; border-left:3px solid {color}; '
                f'margin-bottom:4px; font-size:12px; background:white; border-radius:4px;">'
                f'<span style="color:{ZHONGAN_TEXT_LIGHT};">[{idx}/{total}]</span> '
                f'{icon} {name}</div>'
            )
        elif ttype == "scan_hit":
            name = html.escape(t.get("customer_name", ""))
            rules = ", ".join(t.get("rules", [])[:3])
            lv = t.get("level", "")
            color = {"red": ZHONGAN_RED, "yellow": ZHONGAN_YELLOW}.get(lv, ZHONGAN_TEXT_LIGHT)
            rows.append(
                f'<div style="padding:4px 10px; border-left:3px solid {color}; '
                f'margin-bottom:4px; font-size:12px; background:white; border-radius:4px;">'
                f'<b style="color:{color};">✦ 命中：{name}</b> '
                f'<span style="color:{ZHONGAN_TEXT_LIGHT};">[{html.escape(rules)}]</span></div>'
            )
        elif ttype in ("thinking", "tool_call", "tool_result"):
            content = t.get("content") or t.get("result") or t.get("name", "")
            rows.append(
                f'<div style="padding:4px 10px; color:{ZHONGAN_TEXT_LIGHT}; '
                f'font-size:12px; font-style:italic;">💭 {html.escape(str(content)[:100])}</div>'
            )
    return (
        '<div style="max-height: 280px; overflow-y: auto; padding: 8px; '
        f'background: {ZHONGAN_GRAY}; border-radius: 8px;">'
        + "".join(rows)
        + "</div>"
    )


# ---------------------------------------------------------------------------
# 榜单 HTML（红黄绿三段）
# ---------------------------------------------------------------------------

def _render_hit_row(h: HitItem) -> str:
    p = h.target.payload
    extras = (p.get("extras") or {}) if isinstance(p, dict) else {}
    name = html.escape(p.get("company_name", ""))
    credit = extras.get("credit_line", "") or "—"
    outstanding = extras.get("outstanding", "") or "—"
    due = extras.get("due_date", "") or "—"
    manager = html.escape(str(extras.get("manager", "") or "—"))
    rules = ", ".join(h.matched_rules[:4]) or "—"
    reason = " · ".join(h.reasons[:2]) if h.reasons else "—"
    reason = html.escape(reason)[:160]
    lv_color = {
        RiskLevel.RED: ZHONGAN_RED,
        RiskLevel.YELLOW: ZHONGAN_YELLOW,
        RiskLevel.GREEN: ZHONGAN_GREEN,
    }.get(h.level, ZHONGAN_TEXT_LIGHT)
    return f"""
    <div style="padding:10px 12px; background:white; border-left:4px solid {lv_color};
                border-radius:6px; margin-bottom:6px; box-shadow:0 1px 2px rgba(0,0,0,0.04);">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div style="flex:1;">
                <div style="font-weight:600; color:{ZHONGAN_TEXT}; font-size:13px;">
                    #{h.rank} {name}
                </div>
                <div style="font-size:11px; color:{ZHONGAN_TEXT_LIGHT}; margin-top:4px;">
                    授信 {credit}万 / 余额 {outstanding}万 / 到期 {due} / 客户经理 {manager}
                </div>
                <div style="font-size:11px; color:{ZHONGAN_TEXT_LIGHT}; margin-top:4px;">
                    命中：<span style="color:{lv_color}; font-weight:600;">{html.escape(rules)}</span>
                </div>
                <div style="font-size:11px; color:{ZHONGAN_TEXT}; margin-top:4px;">
                    {reason}
                </div>
            </div>
        </div>
    </div>
    """


def _render_ledger(hl: HitList | None) -> str:
    if hl is None:
        return f"""
        <div style="color:{ZHONGAN_TEXT_LIGHT}; padding:32px; text-align:center;
                    background:white; border:1px dashed #E5E7EB; border-radius:10px;">
            <div style="font-size:32px;">📋</div>
            <div style="margin-top:8px; font-size:13px;">等待扫描生成榜单...</div>
        </div>
        """
    red = [h for h in hl.hits if h.level == RiskLevel.RED]
    yellow = [h for h in hl.hits if h.level == RiskLevel.YELLOW]
    green = [h for h in hl.hits if h.level == RiskLevel.GREEN]

    def section(title: str, color: str, items: list[HitItem], open_by_default: bool) -> str:
        if not items:
            body = f'<div style="color:{ZHONGAN_TEXT_LIGHT}; padding:10px; font-size:12px;">（无）</div>'
        else:
            body = "".join(_render_hit_row(h) for h in items[:30])
        attr = " open" if open_by_default else ""
        return f"""
        <details{attr} style="margin-bottom:10px;">
            <summary style="padding:10px 14px; background:white; border-radius:8px;
                            border:1px solid #E5E7EB; cursor:pointer; font-weight:600;
                            color:{color};">
                {title}（{len(items)} 家）
            </summary>
            <div style="margin-top:8px; padding:0 4px;">{body}</div>
        </details>
        """

    return (
        section(f"🔴 高风险", ZHONGAN_RED, red, open_by_default=True)
        + section(f"🟡 中风险", ZHONGAN_YELLOW, yellow, open_by_default=True)
        + section(f"🟢 低风险", ZHONGAN_GREEN, green, open_by_default=False)
    )


# ---------------------------------------------------------------------------
# 详情 / 处置建议
# ---------------------------------------------------------------------------

def _find_hit(hl: HitList | None, name: str) -> HitItem | None:
    if hl is None or not name:
        return None
    for h in hl.hits:
        if h.target.payload.get("company_name") == name:
            return h
    return None


def _render_detail(hl: HitList | None, name: str) -> str:
    h = _find_hit(hl, name)
    if h is None:
        return f"""
        <div style="color:{ZHONGAN_TEXT_LIGHT}; padding:32px; text-align:center;
                    background:white; border:1px dashed #E5E7EB; border-radius:10px;">
            <div style="font-size:32px;">🔍</div>
            <div style="margin-top:8px; font-size:13px;">从左侧榜单选择客户查看详情</div>
        </div>
        """
    p = h.target.payload
    extras = (p.get("extras") or {}) if isinstance(p, dict) else {}
    ext_hits = (h.extras or {}).get("external_hits", [])
    int_hits = (h.extras or {}).get("internal_hits", [])
    rule_titles = (h.extras or {}).get("rule_titles", {})
    lv_color = {
        RiskLevel.RED: ZHONGAN_RED,
        RiskLevel.YELLOW: ZHONGAN_YELLOW,
        RiskLevel.GREEN: ZHONGAN_GREEN,
    }.get(h.level, ZHONGAN_TEXT_LIGHT)
    lv_label = {"red": "🔴 高风险", "yellow": "🟡 中风险", "green": "🟢 低风险"}.get(
        h.level.value, h.level.value
    )

    def rule_chip(rid: str) -> str:
        t = html.escape(rule_titles.get(rid, rid))
        return (
            f'<span style="display:inline-block; padding:2px 8px; margin:2px 4px 2px 0; '
            f'background:{ZHONGAN_BLUE_LIGHT}; color:{ZHONGAN_BLUE_DARK}; '
            f'font-size:11px; border-radius:10px;">{html.escape(rid)} · {t}</span>'
        )

    reasons_html = "".join(
        f'<li style="margin-bottom:4px; font-size:12px; color:{ZHONGAN_TEXT};">{html.escape(r)}</li>'
        for r in (h.reasons or [])
    ) or f'<li style="color:{ZHONGAN_TEXT_LIGHT};">（无理由）</li>'

    evidence_html = ""
    for ev in (h.evidences or [])[:5]:
        src = html.escape(ev.source or "")
        snip = html.escape((ev.snippet or "")[:150])
        url = ev.url or ""
        url_html = (
            f'<a href="{html.escape(url)}" target="_blank" '
            f'style="color:{ZHONGAN_BLUE}; font-size:11px;">查看原文 ↗</a>'
        ) if url else ""
        evidence_html += f"""
        <div style="padding:8px 10px; background:{ZHONGAN_GRAY}; border-radius:6px;
                    margin-bottom:6px; font-size:12px;">
            <div style="color:{ZHONGAN_TEXT_LIGHT}; font-size:11px;">{src} {url_html}</div>
            <div style="color:{ZHONGAN_TEXT}; margin-top:4px;">{snip}</div>
        </div>
        """
    if not evidence_html:
        evidence_html = f'<div style="color:{ZHONGAN_TEXT_LIGHT}; font-size:12px;">（无证据）</div>'

    return f"""
    <div style="background:white; padding:16px; border-radius:10px; border:1px solid #E5E7EB;">
        <div style="display:flex; justify-content:space-between; align-items:center;
                    padding-bottom:10px; border-bottom:1px solid #F0F0F0;">
            <div style="font-weight:700; font-size:15px; color:{ZHONGAN_TEXT};">
                {html.escape(p.get("company_name", ""))}
            </div>
            <div style="color:{lv_color}; font-weight:700; font-size:14px;">{lv_label}</div>
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin:12px 0;
                    font-size:12px; color:{ZHONGAN_TEXT};">
            <div>授信额度：<b>{extras.get('credit_line','—')} 万</b></div>
            <div>贷款余额：<b>{extras.get('outstanding','—')} 万</b></div>
            <div>到期日：<b>{extras.get('due_date','—')}</b></div>
            <div>客户经理：<b>{html.escape(str(extras.get('manager','—')))}</b></div>
            <div>内评：<b>{html.escape(str(extras.get('internal_rating','—')))}</b></div>
            <div>行业：<b>{html.escape(str(p.get('industry','—')))}</b></div>
        </div>
        <div style="margin-top:10px;">
            <div style="font-size:12px; font-weight:600; color:{ZHONGAN_TEXT_LIGHT};
                        margin-bottom:4px;">外部命中 ({len(ext_hits)})</div>
            <div>{"".join(rule_chip(r) for r in ext_hits) or '<span style="color:#999; font-size:12px;">（无）</span>'}</div>
        </div>
        <div style="margin-top:10px;">
            <div style="font-size:12px; font-weight:600; color:{ZHONGAN_TEXT_LIGHT};
                        margin-bottom:4px;">内部命中 ({len(int_hits)})</div>
            <div>{"".join(rule_chip(r) for r in int_hits) or '<span style="color:#999; font-size:12px;">（无）</span>'}</div>
        </div>
        <div style="margin-top:14px;">
            <div style="font-size:12px; font-weight:600; color:{ZHONGAN_TEXT_LIGHT};
                        margin-bottom:4px;">命中理由</div>
            <ul style="margin:0; padding-left:18px;">{reasons_html}</ul>
        </div>
        <div style="margin-top:14px;">
            <div style="font-size:12px; font-weight:600; color:{ZHONGAN_TEXT_LIGHT};
                        margin-bottom:6px;">证据</div>
            {evidence_html}
        </div>
    </div>
    """


def _render_disposition(dispositions: dict, name: str) -> str:
    plan = (dispositions or {}).get(name)
    if plan is None:
        return f"""
        <div style="background:white; padding:16px; border-radius:10px;
                    border:1px solid #E5E7EB; color:{ZHONGAN_TEXT_LIGHT}; font-size:12px;
                    text-align:center;">
            （绿灯客户或未选中客户，不展示处置建议）
        </div>
        """
    urgency_color = {
        "立即": ZHONGAN_RED,
        "一周内": ZHONGAN_YELLOW,
        "持续关注": ZHONGAN_GREEN,
    }
    actions_html = ""
    for a in plan.actions[:6]:
        color = urgency_color.get(a.urgency, ZHONGAN_TEXT_LIGHT)
        actions_html += f"""
        <div style="padding:10px 12px; background:{ZHONGAN_GRAY}; border-radius:8px;
                    margin-bottom:6px; border-left:3px solid {color};">
            <div style="display:flex; justify-content:space-between; font-size:12px;">
                <span style="font-weight:600; color:{ZHONGAN_TEXT};">{html.escape(a.action_type)}</span>
                <span style="color:{color}; font-weight:600;">{html.escape(a.urgency)}</span>
            </div>
            <div style="font-size:12px; color:{ZHONGAN_TEXT}; margin-top:4px;">
                {html.escape(a.description)}
            </div>
            <div style="font-size:11px; color:{ZHONGAN_TEXT_LIGHT}; margin-top:4px;">
                责任方：{html.escape(a.responsible)}
            </div>
        </div>
        """
    follow = html.escape(plan.follow_up_date or "—")
    return f"""
    <div style="background:white; padding:16px; border-radius:10px; border:1px solid #E5E7EB;">
        <div style="font-weight:700; font-size:14px; color:{ZHONGAN_TEXT}; margin-bottom:10px;">
            🧭 处置建议
        </div>
        {actions_html or '<div style="color:#999; font-size:12px;">（暂无行动项）</div>'}
        <div style="font-size:12px; color:{ZHONGAN_TEXT_LIGHT}; margin-top:8px;">
            跟进日期：<b>{follow}</b>
        </div>
    </div>
    """


# ---------------------------------------------------------------------------
# 主运行：generator，串接 agent.process_message
# ---------------------------------------------------------------------------

def _hit_names_for_dropdown(hl: HitList | None) -> list[str]:
    if hl is None:
        return []
    # 红→黄→绿顺序
    order = {RiskLevel.RED: 0, RiskLevel.YELLOW: 1, RiskLevel.GREEN: 2}
    return [h.target.payload.get("company_name", "")
            for h in sorted(hl.hits, key=lambda x: (order.get(x.level, 9), x.rank))
            if h.target.payload.get("company_name")]


def _run_scan(
    uploaded_files: list | None,
    scenario_key: str,
    api_key: str,
    provider: str,
):
    """主扫描 generator。

    yields tuple:
        (stats_bar_html, ledger_html, detail_html, disp_html,
         tick_stream_html, customer_dropdown_update, hitlist_state, disp_state,
         export_status)
    """
    ticks: list[dict] = []
    t0 = time.time()
    # 初始状态
    yield (
        _render_stats_bar(status="running"),
        _render_ledger(None),
        _render_detail(None, ""),
        _render_disposition({}, ""),
        _render_tick_stream(ticks),
        gr.update(choices=[], value=None),
        None,
        {},
        "",
    )
    try:
        agent = AlertRadarAgent(api_key=api_key or "", model_provider=provider or "deepseek")
    except Exception as e:
        yield (
            _render_stats_bar(status="idle"),
            _render_ledger(None),
            f'<div style="color:{ZHONGAN_RED}; padding:16px;">Agent 初始化失败：{html.escape(str(e))}</div>',
            _render_disposition({}, ""),
            _render_tick_stream(ticks),
            gr.update(choices=[], value=None),
            None, {}, "",
        )
        return

    file_paths = []
    if uploaded_files:
        for f in uploaded_files:
            if hasattr(f, "name"):
                file_paths.append(f.name)
            elif isinstance(f, str):
                file_paths.append(f)

    # 如果没上传任何文件且场景可用，走预置场景
    user_msg = scenario_key or "micro_credit_100"

    hitlist: HitList | None = None
    dispositions: dict = {}
    total = 0
    red = yellow = green = 0

    try:
        for evt in agent.process_message(user_message=user_msg, uploaded_files=file_paths or None):
            etype = evt.get("type", "")
            ticks.append(evt)
            if etype == "scan_tick":
                total = evt.get("total", total)
                lv = evt.get("level", "")
                if lv == "red":
                    red += 1
                elif lv == "yellow":
                    yellow += 1
                elif lv == "green":
                    green += 1
                yield (
                    _render_stats_bar(
                        total=total, red=red, yellow=yellow, green=green,
                        duration_s=time.time() - t0, status="running",
                    ),
                    _render_ledger(None),
                    _render_detail(None, ""),
                    _render_disposition({}, ""),
                    _render_tick_stream(ticks),
                    gr.update(),
                    None, {}, "",
                )
            elif etype == "hitlist":
                hitlist = evt.get("hitlist")
                dispositions = evt.get("dispositions") or {}
            elif etype == "done":
                break
            # 其他事件（thinking / tool_result）只在 tick 流里刷
            elif etype in ("thinking", "tool_result", "tool_call", "scan_hit"):
                yield (
                    _render_stats_bar(
                        total=total, red=red, yellow=yellow, green=green,
                        duration_s=time.time() - t0, status="running",
                    ),
                    _render_ledger(None),
                    _render_detail(None, ""),
                    _render_disposition({}, ""),
                    _render_tick_stream(ticks),
                    gr.update(),
                    None, {}, "",
                )
    except Exception as e:
        yield (
            _render_stats_bar(total=total, red=red, yellow=yellow, green=green,
                              duration_s=time.time() - t0, status="idle"),
            _render_ledger(None),
            f'<div style="color:{ZHONGAN_RED}; padding:16px;">扫描异常：{html.escape(str(e))}</div>',
            _render_disposition({}, ""),
            _render_tick_stream(ticks),
            gr.update(choices=[], value=None),
            None, {}, "",
        )
        return

    # 扫描结束
    if hitlist is None:
        yield (
            _render_stats_bar(total=total, red=red, yellow=yellow, green=green,
                              duration_s=time.time() - t0, status="idle"),
            _render_ledger(None),
            '<div style="padding:16px; color:#E53935;">未生成榜单（HitList 缺失）</div>',
            _render_disposition({}, ""),
            _render_tick_stream(ticks),
            gr.update(choices=[], value=None),
            None, {}, "",
        )
        return

    duration = time.time() - t0
    names = _hit_names_for_dropdown(hitlist)
    default_name = ""
    # 自动选中第一个红灯客户展示详情
    for h in hitlist.hits:
        if h.level == RiskLevel.RED:
            default_name = h.target.payload.get("company_name", "")
            break
    if not default_name and names:
        default_name = names[0]

    yield (
        _render_stats_bar(
            total=hitlist.total_scanned, red=hitlist.red_count,
            yellow=hitlist.yellow_count, green=hitlist.green_count,
            duration_s=duration, status="done",
        ),
        _render_ledger(hitlist),
        _render_detail(hitlist, default_name),
        _render_disposition(dispositions, default_name),
        _render_tick_stream(ticks),
        gr.update(choices=names, value=default_name),
        hitlist,
        dispositions,
        "",
    )


# ---------------------------------------------------------------------------
# 事件：选择客户
# ---------------------------------------------------------------------------

def _on_select(name: str, hitlist: HitList | None, dispositions: dict):
    return _render_detail(hitlist, name), _render_disposition(dispositions or {}, name)


# ---------------------------------------------------------------------------
# 事件：导出 Excel
# ---------------------------------------------------------------------------

def _on_export(hitlist: HitList | None, dispositions: dict):
    if hitlist is None:
        return gr.update(value=None, visible=False), (
            f'<div style="color:{ZHONGAN_RED}; font-size:12px;">⚠️ 请先完成扫描</div>'
        )
    try:
        from agent_alert.ledger_exporter import export_ledger_excel
        path = export_ledger_excel(hitlist, dispositions or {}, output_dir="outputs")
        status = (
            f'<div style="color:{ZHONGAN_GREEN}; font-size:12px;">'
            f'✅ 已导出：{html.escape(Path(path).name)}</div>'
        )
        return gr.update(value=path, visible=True), status
    except Exception as e:
        return gr.update(value=None, visible=False), (
            f'<div style="color:{ZHONGAN_RED}; font-size:12px;">⚠️ 导出失败：{html.escape(str(e))}</div>'
        )


# ---------------------------------------------------------------------------
# build_tab — portal 入口
# ---------------------------------------------------------------------------

def build_tab(api_key_state, provider_state):
    scenario = _load_scenario()

    gr.HTML(f"""
    <div style="padding:16px 20px; background:linear-gradient(135deg,{ZHONGAN_BLUE} 0%,{ZHONGAN_BLUE_DARK} 100%);
                border-radius:12px; color:white; margin-bottom:16px;">
        <div style="font-size:20px; font-weight:700;">📡 贷中风险预警雷达</div>
        <div style="font-size:13px; margin-top:6px; opacity:0.9;">
            对全量在贷客户做"外部（裁判文书+舆情）× 内部（本行管理制度）"双路交叉扫描，
            一次出红/黄/绿榜单 + 处置建议。
        </div>
    </div>
    """)

    # --- 场景区 + 上传区 ---
    with gr.Row():
        with gr.Column(scale=7):
            gr.HTML(_render_scenario_card(scenario))
        with gr.Column(scale=3):
            files_upload = gr.Files(
                label="上传自有 KB（可选：客户名录 Excel / 规则 JSON / 制度 Word）",
                file_types=[".xlsx", ".xls", ".csv", ".json", ".md", ".docx", ".pdf"],
                file_count="multiple",
                height=90,
            )

    with gr.Row():
        run_btn = gr.Button("🚀 开始批量扫描", variant="primary", size="lg")
        export_btn = gr.Button("📥 导出在贷榜单 Excel", size="lg")

    # --- 统计仪表盘 ---
    stats_bar = gr.HTML(_render_stats_bar(status="idle"))

    # --- 下部：左榜单 / 右详情+处置 ---
    with gr.Row():
        with gr.Column(scale=5):
            gr.Markdown("### 🎯 分级榜单")
            customer_dropdown = gr.Dropdown(
                label="选择客户查看详情",
                choices=[], value=None, interactive=True, allow_custom_value=False,
            )
            ledger_html = gr.HTML(_render_ledger(None))
        with gr.Column(scale=5):
            gr.Markdown("### 🔍 客户详情")
            detail_html = gr.HTML(_render_detail(None, ""))
            gr.Markdown("### 🧭 处置建议")
            disp_html = gr.HTML(_render_disposition({}, ""))

    # --- 实时 tick 流 ---
    with gr.Accordion("📡 实时扫描事件流", open=False):
        tick_stream_html = gr.HTML(_render_tick_stream([]))

    # --- 导出下载 ---
    with gr.Row():
        export_file = gr.File(label="扫描报告下载", visible=False, interactive=False)
        export_status = gr.HTML("")

    # --- 状态 ---
    hitlist_state = gr.State(None)
    disp_state = gr.State({})
    scenario_state = gr.State(scenario.get("scenario_id", "micro_credit_100"))

    # --- 事件绑定 ---
    run_btn.click(
        fn=_run_scan,
        inputs=[files_upload, scenario_state, api_key_state, provider_state],
        outputs=[
            stats_bar, ledger_html, detail_html, disp_html,
            tick_stream_html, customer_dropdown,
            hitlist_state, disp_state, export_status,
        ],
    )

    customer_dropdown.change(
        fn=_on_select,
        inputs=[customer_dropdown, hitlist_state, disp_state],
        outputs=[detail_html, disp_html],
    )

    export_btn.click(
        fn=_on_export,
        inputs=[hitlist_state, disp_state],
        outputs=[export_file, export_status],
    )


# ---------------------------------------------------------------------------
# 独立启动
# ---------------------------------------------------------------------------

def create_app() -> gr.Blocks:
    with gr.Blocks(title="贷中风险预警雷达") as demo:
        api_key_state = gr.State("")
        provider_state = gr.State("deepseek")
        build_tab(api_key_state, provider_state)
    return demo


if __name__ == "__main__":
    app = create_app()
    app.launch(server_name="0.0.0.0", server_port=7863, show_error=True)
