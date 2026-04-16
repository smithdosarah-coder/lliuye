# -*- coding: utf-8 -*-
"""Demo UI 共享框架 — 主题色、场景卡、事件流helper

所有 agent_XXX/app_demo.py 共用此模块，确保视觉和交互一致。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Generator

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# 主题色（众安蓝 + 辅色）
# ---------------------------------------------------------------------------

ZHONGAN_BLUE = "#1E5CB3"
ZHONGAN_BLUE_DARK = "#144887"
ZHONGAN_BLUE_LIGHT = "#E8F1FB"
ZHONGAN_ORANGE = "#FF7A45"
ZHONGAN_GREEN = "#52C41A"
ZHONGAN_RED = "#E53935"
ZHONGAN_YELLOW = "#FAAD14"
ZHONGAN_GRAY = "#F5F7FA"
ZHONGAN_TEXT = "#2C3E50"
ZHONGAN_TEXT_LIGHT = "#6B7280"


CUSTOM_CSS = f"""
.gradio-container {{
    font-family: "PingFang SC", "Microsoft YaHei", -apple-system, sans-serif;
    max-width: 1400px !important;
    margin: auto;
}}

.portal-header {{
    background: linear-gradient(135deg, {ZHONGAN_BLUE} 0%, {ZHONGAN_BLUE_DARK} 100%);
    color: white;
    padding: 20px 32px;
    border-radius: 0 0 12px 12px;
    margin-bottom: 16px;
    box-shadow: 0 2px 12px rgba(30, 92, 179, 0.2);
}}
.portal-header h1 {{
    margin: 0;
    font-size: 22px;
    font-weight: 600;
    color: white !important;
}}
.portal-header .subtitle {{
    margin-top: 4px;
    font-size: 13px;
    opacity: 0.85;
}}

.scenario-card {{
    border: 1px solid #E5E7EB;
    border-radius: 10px;
    padding: 16px;
    margin: 8px 4px;
    background: white;
    cursor: pointer;
    transition: all 0.2s;
}}
.scenario-card:hover {{
    border-color: {ZHONGAN_BLUE};
    box-shadow: 0 4px 16px rgba(30, 92, 179, 0.15);
    transform: translateY(-2px);
}}
.scenario-card .title {{
    font-weight: 600;
    color: {ZHONGAN_BLUE};
    font-size: 15px;
    margin-bottom: 6px;
}}
.scenario-card .desc {{
    font-size: 12px;
    color: {ZHONGAN_TEXT_LIGHT};
    line-height: 1.5;
}}

.signal-light {{
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    font-weight: 600;
    color: white;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}}
.signal-red {{ background: linear-gradient(135deg, #E53935 0%, #B71C1C 100%); }}
.signal-yellow {{ background: linear-gradient(135deg, #FAAD14 0%, #D48806 100%); }}
.signal-green {{ background: linear-gradient(135deg, #52C41A 0%, #389E0D 100%); }}
.signal-light .count {{ font-size: 36px; line-height: 1; }}
.signal-light .label {{ font-size: 13px; margin-top: 6px; letter-spacing: 2px; }}

@keyframes pulse-red {{
    0%, 100% {{ box-shadow: 0 0 0 0 rgba(229, 57, 53, 0.5); }}
    50% {{ box-shadow: 0 0 0 20px rgba(229, 57, 53, 0); }}
}}
.signal-red.active {{ animation: pulse-red 2s infinite; }}

.zhongan-btn-primary {{
    background: {ZHONGAN_BLUE} !important;
    color: white !important;
    border: none !important;
}}
.zhongan-btn-primary:hover {{
    background: {ZHONGAN_BLUE_DARK} !important;
}}

.muted-note {{
    color: {ZHONGAN_TEXT_LIGHT};
    font-size: 12px;
    margin-top: 4px;
}}

.result-panel {{
    background: {ZHONGAN_GRAY};
    border-radius: 10px;
    padding: 16px;
    min-height: 300px;
}}
"""


# ---------------------------------------------------------------------------
# 场景数据加载
# ---------------------------------------------------------------------------

def load_scenarios(agent_name: str) -> list[dict]:
    """加载某 agent 的所有预置场景。

    约定：demo_data/{agent_name}/*.json 每个文件一个场景。
    文件结构：
    {
        "scenario_id": "red_light",
        "title": "华联精密红灯预警",
        "description": "制造企业，营收下滑+涉诉+高管变更",
        "input_message": "请分析华联精密机械...",
        "files": ["path/to/mock1.txt"],   # 可选
        "preset_data": { ... }            # 可选
    }
    """
    scenarios_dir = PROJECT_ROOT / "demo_data" / agent_name
    if not scenarios_dir.exists():
        return []
    scenarios = []
    for f in sorted(scenarios_dir.glob("*.json")):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                scenarios.append(json.load(fh))
        except Exception:
            continue
    return scenarios


# ---------------------------------------------------------------------------
# Agent 事件流处理
# ---------------------------------------------------------------------------

def format_event(event: dict) -> str:
    """把 agent 的 yield 事件格式化成可展示的 markdown 行"""
    etype = event.get("type", "")
    if etype == "thinking":
        return f"💭 {event.get('content', '')}\n\n"
    if etype == "message":
        return f"{event.get('content', '')}\n\n"
    if etype == "tool_call":
        return f"🔧 调用 `{event.get('name', '')}` ...\n\n"
    if etype == "tool_result":
        name = event.get("name", "")
        result = event.get("result", "")
        return f"✅ `{name}` 完成：{result}\n\n"
    if etype == "file":
        return f"📄 生成文件：{event.get('path', '')}\n\n"
    if etype == "done":
        return ""
    return ""


def stream_agent(
    agent_class,
    api_key: str,
    provider: str,
    message: str,
    file_paths: list[str] | None = None,
) -> Generator[tuple[str, str], None, None]:
    """运行 agent，流式输出 (process_log, final_message) 两个内容。

    yields:
        (process_log, final_message_or_empty)
    """
    if not api_key:
        yield "⚠️ 请先在右上角设置中填写 API Key", ""
        return

    try:
        agent = agent_class(api_key=api_key, model_provider=provider)
    except Exception as e:
        yield f"❌ Agent 初始化失败：{e}", ""
        return

    process_log = ""
    final_message = ""
    try:
        for event in agent.process_message(message, file_paths or []):
            etype = event.get("type", "")
            if etype == "message":
                final_message += event.get("content", "") + "\n\n"
            else:
                process_log += format_event(event)
            yield process_log, final_message
    except Exception as e:
        process_log += f"\n❌ 执行异常：{e}\n"
        yield process_log, final_message


# ---------------------------------------------------------------------------
# 通用组件
# ---------------------------------------------------------------------------

def render_header_html(title: str, subtitle: str = "") -> str:
    """渲染tab顶部标题条"""
    sub_html = f'<div class="muted-note">{subtitle}</div>' if subtitle else ""
    return f"""
    <div style="padding: 8px 0 16px 0;">
        <h2 style="color: {ZHONGAN_BLUE}; margin: 0 0 4px 0; font-size: 18px;">{title}</h2>
        {sub_html}
    </div>
    """


def render_scenario_card_html(scenario: dict) -> str:
    """渲染单个场景卡的HTML"""
    return f"""
    <div class="scenario-card">
        <div class="title">📍 {scenario.get('title', '未命名场景')}</div>
        <div class="desc">{scenario.get('description', '')}</div>
    </div>
    """


def render_coming_soon_html(agent_name: str, hint: str = "") -> str:
    """占位：待改造"""
    return f"""
    <div style="padding: 40px; text-align: center; color: {ZHONGAN_TEXT_LIGHT}; background: {ZHONGAN_GRAY}; border-radius: 12px;">
        <h3 style="color: {ZHONGAN_BLUE}; margin-bottom: 8px;">🚧 {agent_name} 正在改造中</h3>
        <p style="margin: 0; font-size: 13px;">{hint or '下次迭代将上线。'}</p>
    </div>
    """
