# -*- coding: utf-8 -*-
"""
信贷报告智能助手 — Gradio 前端 v9.0

v9.0: Velvet Noir 主题 — 暖色调深色奢华金融风格
- gr.HTML() 自定义 Header 突破 Gradio 默认美学
- 暖灰色调 + 琥珀/铜色点缀，拒绝冷蓝致郁
- 玻璃质感卡片 + 微妙纹理 + 层次阴影
- 完整 Gradio 主题 API 覆盖 100+ 变量
"""

import os
import gradio as gr
import time
from agent import CreditReportAgent


agents: dict[str, CreditReportAgent] = {}
_pending_templates: dict[str, str] = {}
_pending_form_templates: dict[str, str] = {}


def get_agent(session_id: str, api_key: str, provider: str) -> CreditReportAgent:
    if session_id not in agents or not api_key:
        agent = CreditReportAgent(api_key=api_key, provider=provider)
        agent.session_id = session_id
        agents[session_id] = agent
        if session_id in _pending_templates:
            tpl_path = _pending_templates.pop(session_id)
            if os.path.exists(tpl_path):
                agent.set_template(tpl_path)
        if session_id in _pending_form_templates:
            form_path = _pending_form_templates.pop(session_id)
            if os.path.exists(form_path):
                agent.form_template_path = form_path
    return agents[session_id]


WELCOME_NARRATIVE = """你好，欢迎使用授信报告智能助手。

功能说明：
- 上传企业材料，自动生成授信调查报告（约15000字）
- 撰写完成后自动导出 Word 文件，可在顶部区域直接下载
- 左侧可上传模板文件（支持热替换）
- 支持网络搜索、自省修正、模板深度参考、侧栏批注

请上传材料文件并告知客户信息即可开始。"""

WELCOME_FORM_FILL = """你好，欢迎使用授信报告智能助手 - 填空模式。

本模式专为普惠授信申报表等结构化表格设计：
- 自动替换所有 XX 占位符为真实数据
- 自动勾选正确的复选框
- 逐段落智能填写（12主逻辑段落）

操作步骤：
1. 左侧上传填空模板（.docx 格式）
2. 在右侧上传企业材料文件（PDF/Word/Excel）
3. 发送"开始填写"即可

注意：模板必须是 .docx 格式（如有 .doc 请先用 WPS 另存为 .docx）。"""


# ═══════════════════════════════════════════════════════════
#  Velvet Noir — 暖色调深色奢华金融主题
# ═══════════════════════════════════════════════════════════

def _build_theme():
    """Gradio 原生主题：暖灰底色 + 琥珀点缀"""
    # 暖色调色板（告别冷蓝）
    BG       = "#121218"   # 最深底色（暖黑）
    BG1      = "#18181f"   # 一级面板
    BG2      = "#1f1f28"   # 二级卡片
    BG3      = "#282832"   # 三级高亮
    BD       = "rgba(255,255,255,0.07)"
    BD2      = "rgba(255,255,255,0.12)"
    TX       = "#ede8e0"   # 主文本（暖白）
    TX2      = "#9e9590"   # 副文本（暖灰）
    TX3      = "#6b625c"   # 占位符
    COPPER   = "#d4956a"   # 主色：暖铜
    COPPER_B = "#e8b88a"   # 亮铜
    COPPER_G = "rgba(212,149,106,0.12)"  # 铜色光晕
    GREEN    = "#5dba8c"   # 成功绿（sage）

    return gr.themes.Base(
        primary_hue=gr.themes.colors.orange,
        secondary_hue=gr.themes.colors.stone,
        neutral_hue=gr.themes.colors.stone,
        font=("Inter", "Noto Sans SC", "Microsoft YaHei", "PingFang SC", "system-ui", "sans-serif"),
        font_mono=("JetBrains Mono", "Cascadia Code", "Consolas", "monospace"),
    ).set(
        # ── Body ──
        body_background_fill=BG,
        body_background_fill_dark=BG,
        body_text_color=TX,
        body_text_color_dark=TX,
        body_text_color_subdued=TX2,
        body_text_color_subdued_dark=TX2,

        # ── Block ──
        block_background_fill=BG2,
        block_background_fill_dark=BG2,
        block_border_color=BD,
        block_border_color_dark=BD,
        block_border_width="1px",
        block_label_background_fill=BG3,
        block_label_background_fill_dark=BG3,
        block_label_text_color=TX2,
        block_label_text_color_dark=TX2,
        block_label_border_color=BD,
        block_label_border_color_dark=BD,
        block_title_background_fill=BG3,
        block_title_background_fill_dark=BG3,
        block_title_text_color=TX,
        block_title_text_color_dark=TX,
        block_shadow="0 1px 3px rgba(0,0,0,0.12), 0 4px 16px rgba(0,0,0,0.08)",
        block_shadow_dark="0 1px 3px rgba(0,0,0,0.20), 0 4px 16px rgba(0,0,0,0.15)",

        # ── Panel ──
        panel_background_fill=BG1,
        panel_background_fill_dark=BG1,
        panel_border_color=BD,
        panel_border_color_dark=BD,

        # ── Backgrounds ──
        background_fill_primary=BG1,
        background_fill_primary_dark=BG1,
        background_fill_secondary=BG2,
        background_fill_secondary_dark=BG2,

        # ── Input ──
        input_background_fill=BG1,
        input_background_fill_dark=BG1,
        input_background_fill_focus=BG1,
        input_background_fill_focus_dark=BG1,
        input_background_fill_hover=BG1,
        input_background_fill_hover_dark=BG1,
        input_border_color=BD2,
        input_border_color_dark=BD2,
        input_border_color_focus=COPPER,
        input_border_color_focus_dark=COPPER,
        input_border_color_hover="rgba(212,149,106,0.25)",
        input_border_color_hover_dark="rgba(212,149,106,0.25)",
        input_placeholder_color=TX3,
        input_placeholder_color_dark=TX3,
        input_shadow="none",
        input_shadow_dark="none",
        input_shadow_focus=f"0 0 0 3px {COPPER_G}, 0 0 16px rgba(212,149,106,0.08)",
        input_shadow_focus_dark=f"0 0 0 3px {COPPER_G}, 0 0 16px rgba(212,149,106,0.08)",
        input_radius="10px",

        # ── Border ──
        border_color_primary=BD2,
        border_color_primary_dark=BD2,
        border_color_accent=COPPER,
        border_color_accent_dark=COPPER,
        border_color_accent_subdued="rgba(212,149,106,0.18)",
        border_color_accent_subdued_dark="rgba(212,149,106,0.18)",
        color_accent=COPPER,
        color_accent_soft=COPPER_G,
        color_accent_soft_dark=COPPER_G,

        # ── Button Primary (铜色渐变) ──
        button_primary_background_fill=f"linear-gradient(135deg, {COPPER} 0%, #b87a4a 100%)",
        button_primary_background_fill_dark=f"linear-gradient(135deg, {COPPER} 0%, #b87a4a 100%)",
        button_primary_background_fill_hover=f"linear-gradient(135deg, {COPPER_B} 0%, {COPPER} 100%)",
        button_primary_background_fill_hover_dark=f"linear-gradient(135deg, {COPPER_B} 0%, {COPPER} 100%)",
        button_primary_text_color="#121218",
        button_primary_text_color_dark="#121218",
        button_primary_text_color_hover="#121218",
        button_primary_text_color_hover_dark="#121218",
        button_primary_border_color="transparent",
        button_primary_border_color_dark="transparent",
        button_primary_shadow=f"0 2px 8px rgba(212,149,106,0.25)",
        button_primary_shadow_dark=f"0 2px 8px rgba(212,149,106,0.30)",
        button_primary_shadow_hover=f"0 4px 20px rgba(212,149,106,0.40)",
        button_primary_shadow_hover_dark=f"0 4px 20px rgba(212,149,106,0.40)",

        # ── Button Secondary ──
        button_secondary_background_fill=BG3,
        button_secondary_background_fill_dark=BG3,
        button_secondary_background_fill_hover=COPPER_G,
        button_secondary_background_fill_hover_dark=COPPER_G,
        button_secondary_text_color=TX2,
        button_secondary_text_color_dark=TX2,
        button_secondary_text_color_hover=COPPER_B,
        button_secondary_text_color_hover_dark=COPPER_B,
        button_secondary_border_color=BD2,
        button_secondary_border_color_dark=BD2,
        button_secondary_border_color_hover="rgba(212,149,106,0.30)",
        button_secondary_border_color_hover_dark="rgba(212,149,106,0.30)",

        # ── Checkbox / Radio ──
        checkbox_background_color=BG1,
        checkbox_background_color_dark=BG1,
        checkbox_background_color_selected=COPPER,
        checkbox_background_color_selected_dark=COPPER,
        checkbox_background_color_hover=BG3,
        checkbox_background_color_hover_dark=BG3,
        checkbox_border_color=BD2,
        checkbox_border_color_dark=BD2,
        checkbox_border_color_selected=COPPER,
        checkbox_border_color_selected_dark=COPPER,
        checkbox_border_color_focus=COPPER,
        checkbox_border_color_focus_dark=COPPER,
        checkbox_label_background_fill=BG1,
        checkbox_label_background_fill_dark=BG1,
        checkbox_label_background_fill_hover=COPPER_G,
        checkbox_label_background_fill_hover_dark=COPPER_G,
        checkbox_label_background_fill_selected=COPPER_G,
        checkbox_label_background_fill_selected_dark=COPPER_G,
        checkbox_label_border_color=BD2,
        checkbox_label_border_color_dark=BD2,
        checkbox_label_border_color_selected=COPPER,
        checkbox_label_border_color_selected_dark=COPPER,
        checkbox_label_text_color=TX2,
        checkbox_label_text_color_dark=TX2,
        checkbox_label_text_color_selected=COPPER_B,
        checkbox_label_text_color_selected_dark=COPPER_B,

        # ── Accordion ──
        accordion_text_color=TX,
        accordion_text_color_dark=TX,

        # ── Table ──
        table_border_color=BD,
        table_border_color_dark=BD,
        table_even_background_fill=BG1,
        table_even_background_fill_dark=BG1,
        table_odd_background_fill=BG2,
        table_odd_background_fill_dark=BG2,
        table_text_color=TX,
        table_text_color_dark=TX,
        table_row_focus=COPPER_G,
        table_row_focus_dark=COPPER_G,

        # ── Shadow ──
        shadow_drop="0 1px 3px rgba(0,0,0,0.10), 0 4px 16px rgba(0,0,0,0.06)",
        shadow_drop_lg="0 8px 32px rgba(0,0,0,0.20)",
        shadow_spread="3px",
        shadow_spread_dark="3px",
        shadow_inset="inset 0 1px 3px rgba(0,0,0,0.10)",
    )


# ── 自定义 HTML Header ──
HEADER_HTML = """
<div style="
    position: relative;
    background: linear-gradient(160deg, #1a1520 0%, #1e1a22 30%, #201c1a 60%, #1a1520 100%);
    border-radius: 20px;
    padding: 40px 44px 36px;
    margin-bottom: 24px;
    overflow: hidden;
    border: 1px solid rgba(212,149,106,0.10);
    box-shadow: 0 8px 40px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.03);
">
    <!-- 装饰性网格纹理 -->
    <div style="
        position: absolute; top: 0; left: 0; right: 0; bottom: 0;
        background-image:
            linear-gradient(rgba(212,149,106,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(212,149,106,0.03) 1px, transparent 1px);
        background-size: 40px 40px;
        pointer-events: none;
    "></div>

    <!-- 右侧装饰光晕 -->
    <div style="
        position: absolute; top: -30%; right: -5%;
        width: 320px; height: 320px;
        background: radial-gradient(circle, rgba(212,149,106,0.08) 0%, transparent 70%);
        pointer-events: none;
    "></div>

    <!-- 左下装饰光晕 -->
    <div style="
        position: absolute; bottom: -40%; left: 10%;
        width: 240px; height: 240px;
        background: radial-gradient(circle, rgba(93,186,140,0.05) 0%, transparent 70%);
        pointer-events: none;
    "></div>

    <!-- 内容 -->
    <div style="position: relative; z-index: 1;">
        <div style="
            display: inline-block;
            background: rgba(212,149,106,0.12);
            border: 1px solid rgba(212,149,106,0.20);
            border-radius: 20px;
            padding: 4px 14px;
            margin-bottom: 16px;
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
        ">
            <span style="
                color: #e8b88a;
                font-size: 0.72rem;
                font-weight: 600;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                font-family: 'Inter', sans-serif;
            ">AI-Powered</span>
        </div>

        <h1 style="
            color: #ede8e0;
            font-size: 1.85rem;
            font-weight: 700;
            letter-spacing: 0.02em;
            margin: 0 0 8px 0;
            font-family: 'Inter', 'Noto Sans SC', sans-serif;
            line-height: 1.2;
        ">授信报告智能助手</h1>

        <p style="
            color: #9e9590;
            font-size: 0.95rem;
            font-weight: 300;
            margin: 0;
            letter-spacing: 0.02em;
            font-family: 'Inter', 'Noto Sans SC', sans-serif;
        ">信贷审批文书自动化平台 · 智能填写 · 精准分析 · 一键导出</p>
    </div>

    <!-- 底部渐变线 -->
    <div style="
        position: absolute;
        bottom: 0; left: 5%; right: 5%;
        height: 1px;
        background: linear-gradient(90deg, transparent 0%, rgba(212,149,106,0.35) 30%, rgba(232,184,138,0.5) 50%, rgba(212,149,106,0.35) 70%, transparent 100%);
    "></div>
</div>
"""


CSS = """
@import url('https://fonts.loli.net/css2?family=Inter:wght@300;400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;700&display=swap');

/* ═══ Layout ═══ */
.gradio-container {
    max-width: 1440px !important;
    margin: 0 auto !important;
}

/* ═══ 全局微妙噪点纹理 ═══ */
body::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
    opacity: 0.4;
    pointer-events: none;
    z-index: 9999;
}

/* ═══ Sidebar 玻璃质感 ═══ */
#sidebar-col {
    border-radius: 18px !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    background: rgba(31,31,40,0.85) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.15), inset 0 1px 0 rgba(255,255,255,0.03) !important;
    overflow: hidden;
    padding: 4px !important;
}

/* ═══ Sidebar 顶部铜色装饰线 ═══ */
#sidebar-col::before {
    content: '';
    display: block;
    height: 2px;
    margin: 0 12px 8px;
    border-radius: 1px;
    background: linear-gradient(90deg, transparent, rgba(212,149,106,0.4), transparent);
}

/* ═══ Chatbot 容器 ═══ */
#chatbot-box {
    border-radius: 18px !important;
    border: 1px solid rgba(255,255,255,0.05) !important;
    box-shadow: 0 4px 24px rgba(0,0,0,0.12), inset 0 1px 0 rgba(255,255,255,0.02) !important;
    overflow: hidden;
    background: linear-gradient(180deg, #1a1a22 0%, #18181f 40%, #1c1920 100%) !important;
    position: relative;
}

/* Chatbot 底部微妙光晕 */
#chatbot-box::after {
    content: '';
    position: absolute;
    bottom: -20%; left: 20%; right: 20%;
    height: 40%;
    background: radial-gradient(ellipse, rgba(212,149,106,0.03) 0%, transparent 70%);
    pointer-events: none;
}

/* ═══ 右侧整体区域：微妙渐变底色 ═══ */
#chat-col {
    background: linear-gradient(175deg, rgba(26,21,32,0.3) 0%, transparent 30%, rgba(32,28,26,0.2) 100%) !important;
    border-radius: 18px !important;
    padding: 12px !important;
}

/* ═══ 所有 Block 容器加微妙内渐变 ═══ */
.gradio-container .block {
    background: linear-gradient(180deg, rgba(31,31,40,0.5) 0%, rgba(24,24,31,0.8) 100%) !important;
    border-radius: 12px !important;
}

/* ═══ Accordion 内容区域纹理 ═══ */
.gradio-container .accordion .content {
    background: linear-gradient(180deg, rgba(24,24,31,0.6) 0%, rgba(18,18,24,0.8) 100%) !important;
    border-top: 1px solid rgba(255,255,255,0.03) !important;
}

/* ═══ 输入行 ═══ */
#chat-input-row {
    background: linear-gradient(135deg, rgba(31,31,40,0.7) 0%, rgba(26,21,32,0.6) 100%) !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 14px !important;
    padding: 10px 14px !important;
    margin-top: 14px !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.10), inset 0 1px 0 rgba(255,255,255,0.02) !important;
}

/* ═══ 文件上传区域装饰 ═══ */
.gradio-container .upload-area,
.gradio-container [data-testid="upload-area"] {
    background: linear-gradient(135deg, rgba(31,31,40,0.4) 0%, rgba(24,24,31,0.6) 100%) !important;
    border: 1px dashed rgba(212,149,106,0.15) !important;
    border-radius: 12px !important;
    transition: all 0.3s ease !important;
}

.gradio-container .upload-area:hover,
.gradio-container [data-testid="upload-area"]:hover {
    border-color: rgba(212,149,106,0.35) !important;
    background: linear-gradient(135deg, rgba(212,149,106,0.06) 0%, rgba(31,31,40,0.5) 100%) !important;
}

/* ═══ Dropdown 列表 ═══ */
.gradio-container ul[role="listbox"] {
    background: #1f1f28 !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 10px !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.30) !important;
}

.gradio-container ul[role="listbox"] li {
    transition: background 0.15s ease !important;
}

.gradio-container ul[role="listbox"] li:hover {
    background: rgba(212,149,106,0.10) !important;
}

/* ═══ Status Bar ═══ */
#status-bar {
    border-left: 3px solid #d4956a !important;
    border-radius: 10px !important;
}

/* ═══ 待补充标签 ═══ */
#pending-tags {
    max-height: 220px;
    overflow-y: auto;
    line-height: 1.7 !important;
}

/* ═══ 下载横幅 ═══ */
.download-banner {
    background: linear-gradient(135deg, rgba(93,186,140,0.10) 0%, rgba(93,186,140,0.04) 100%) !important;
    border: 1px solid rgba(93,186,140,0.18) !important;
    border-left: 3px solid #5dba8c !important;
    border-radius: 14px !important;
    padding: 14px 20px !important;
}

/* ═══ Scrollbar ═══ */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: rgba(212,149,106,0.18);
    border-radius: 10px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(212,149,106,0.35);
}

/* ═══ Misc ═══ */
footer { display: none !important; }
.chatbot-container { overflow: hidden !important; }

/* ═══ 消息气泡进入动画 ═══ */
@keyframes msg-in {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
}
"""


DL_HIDDEN = ""
DL_BANNER = "### \u2713 报告已生成，请点击下方文件下载"

TOOL_NAMES = {
    "read_files": "读取文件",
    "classify_documents": "分类文件",
    "extract_financial_data": "提取财务",
    "audit_materials": "盘点材料",
    "search_web": "网络搜索",
    "write_chapter": "撰写章节",
    "write_all_chapters": "撰写全部章节",
    "self_reflect": "自省审视",
    "review_report": "审查报告",
    "revise_chapter": "修改章节",
    "export_to_word": "导出 Word",
    "ask_user": "请求确认",
    "form_fill": "填写申报表",
}


# ═══════════════════════════════════════════════════════════
#  核心逻辑
# ═══════════════════════════════════════════════════════════

def stream_chat(text, files, chatbot, api_key, provider, session_state, mode_state):
    """流式聊天处理"""
    chatbot = chatbot or []
    _pending_md = gr.update()

    def out(cb, txt="", banner=None, dl=None, exp=None, status="",
            ptags_md=None):
        return (
            cb,
            txt,
            gr.update(),
            gr.update(value=banner) if banner is not None else gr.update(),
            gr.update(value=dl, visible=True) if dl else gr.update(),
            gr.update(visible=True) if exp else (gr.update(visible=False) if exp is False else gr.update()),
            status,
            gr.update(value=ptags_md) if ptags_md is not None else gr.update(),
        )

    if not api_key or not api_key.strip():
        chatbot.append({"role": "assistant", "content": "请先在左侧填写 API 密钥。"})
        yield out(chatbot, status="请填写 API 密钥")
        return

    user_text = text or ""
    file_paths = []
    if files:
        for f in files:
            if isinstance(f, str):
                file_paths.append(f)
            elif hasattr(f, "name"):
                file_paths.append(f.name)

    if not user_text and not file_paths:
        chatbot.append({"role": "assistant", "content": "请输入消息或上传文件"})
        yield out(chatbot, status="等待输入")
        return

    user_display = user_text
    if file_paths:
        fnames = [p.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] for p in file_paths]
        user_display += f"\n附件: {', '.join(fnames)}"

    chatbot.append({"role": "user", "content": user_display})
    yield out(chatbot, status="Agent 启动中...")

    sid = session_state or "default"
    agent = get_agent(sid, api_key, provider)

    current_mode = mode_state or "叙述报告"
    agent.mode = "form_fill" if "填空" in current_mode else "narrative"

    start_time = time.time()
    thinking_parts = []
    full_response = ""
    pending_file = None

    for event in agent.process_message(user_text, file_paths or None):
        elapsed = time.time() - start_time
        evt_type = event.get("type", "")

        if evt_type == "thinking":
            thinking_parts.append(f"{event['content']}")
            msg = "\n".join(thinking_parts)
            temp = chatbot + [{"role": "assistant", "content": msg}]
            yield out(temp, status=f"{event['content']} ({elapsed:.0f}秒)")

        elif evt_type == "tool_call":
            name = event["name"]
            dn = TOOL_NAMES.get(name, name)
            if event.get("status") == "skipped":
                thinking_parts.append(f"[跳过] {dn}（已缓存）")
            else:
                thinking_parts.append(f"[执行] {dn}...")
            msg = "\n".join(thinking_parts)
            temp = chatbot + [{"role": "assistant", "content": msg}]
            yield out(temp, status=f"{dn} ({elapsed:.0f}秒)")

        elif evt_type == "tool_result":
            name = event["name"]
            dn = TOOL_NAMES.get(name, name)
            thinking_parts.append(f"[完成] {dn}")
            msg = "\n".join(thinking_parts)
            temp = chatbot + [{"role": "assistant", "content": msg}]
            yield out(temp, status=f"{dn} 完成 ({elapsed:.0f}秒)")

        elif evt_type == "message":
            full_response = event["content"]
            msg = "\n".join(thinking_parts)
            if msg:
                msg += "\n\n---\n\n"
            msg += full_response
            temp = chatbot + [{"role": "assistant", "content": msg}]
            yield out(temp, status=f"回复中... ({elapsed:.0f}秒)")

        elif evt_type == "file":
            pending_file = event["path"]
            fname = os.path.basename(pending_file)
            thinking_parts.append(f"\n*报告已生成: {fname}*\n请在聊天区上方下载")
            msg = "\n".join(thinking_parts)
            temp = chatbot + [{"role": "assistant", "content": msg}]
            yield out(temp, banner=DL_BANNER, dl=pending_file, exp=False,
                      status=f"报告就绪（{elapsed:.0f}秒）")

        elif evt_type == "export_error":
            err = event.get("content", "未知错误")
            thinking_parts.append(f"自动导出失败: {err}\n可点击「手动导出」按钮")
            msg = "\n".join(thinking_parts)
            temp = chatbot + [{"role": "assistant", "content": msg}]
            yield out(temp, exp=True, status=f"导出失败 ({elapsed:.0f}秒)")

        elif evt_type == "pending_tags":
            tags = event.get("tags", [])
            if tags:
                by_cat = {}
                for t in tags:
                    cat = t.get("category", "可能在材料中")
                    by_cat.setdefault(cat, []).append(t)

                lines = [f"**共 {len(tags)} 处待完善**\n"]
                for cat, cat_tags in sorted(by_cat.items()):
                    lines.append(f"\n**{cat}**")
                    for t in cat_tags[:20]:
                        lines.append(f"- {t['label'][:45]}")
                    if len(cat_tags) > 20:
                        lines.append(f"- *...还有{len(cat_tags)-20}项*")
                _pending_md = "\n".join(lines)
                msg = "\n".join(thinking_parts)
                temp = chatbot + [{"role": "assistant", "content": msg}]
                yield out(temp, status="待补充清单已更新",
                          ptags_md=_pending_md)

        elif evt_type == "done":
            pass

    elapsed = time.time() - start_time
    if full_response:
        final = ("\n".join(thinking_parts) + "\n\n---\n\n" + full_response) if thinking_parts else full_response
    elif thinking_parts:
        final = "\n".join(thinking_parts)
    else:
        final = "（处理完成）"

    chatbot.append({"role": "assistant", "content": final})

    if pending_file:
        yield out(chatbot, banner=DL_BANNER, dl=pending_file, exp=False,
                  status=f"完成，请在上方下载 ({elapsed:.0f}秒)",
                  ptags_md=_pending_md if isinstance(_pending_md, str) else None)
    else:
        show_export = False
        if sid in agents:
            ag = agents[sid]
            has = any(ag.chapters.get(f"ch{i}") for i in range(1, 5))
            if has and not ag.report_exported:
                show_export = True
        yield out(chatbot, exp=show_export if show_export else False,
                  status=f"完成 ({elapsed:.0f}秒)",
                  ptags_md=_pending_md if isinstance(_pending_md, str) else None)


def on_manual_export(session_state):
    """手动导出按钮"""
    sid = session_state or "default"
    if sid not in agents:
        return gr.update(), gr.update(), gr.update(), "没有活跃的 Agent"

    agent = agents[sid]
    if not any(agent.chapters.get(f"ch{i}") for i in range(1, 5)):
        return gr.update(), gr.update(), gr.update(), "还没有写好的章节"

    try:
        client_name = agent._guess_client_name()
        if agent.template_path:
            from word_export import make_word_from_template
            path = make_word_from_template(
                agent.template_path, agent.chapters,
                client_name=client_name,
            )
        else:
            from word_export import make_word_report
            path = make_word_report(
                client_name, "", "", "", "", "",
                agent.chapters,
            )
        agent.report_exported = True

        # 导出 ReportJSON 供 Agent3（授信决策辅助）消费
        json_hint = ""
        try:
            from shared.report_handoff import dump_report_json
            json_path = dump_report_json(
                client_name=client_name,
                sections=agent.chapters,
                docx_path=path,
                template_path=agent.template_path or "",
            )
            agent.report_json_path = json_path
            json_hint = f"\n\n📤 ReportJSON 已生成：`{os.path.basename(json_path)}`\n→ 可切换到 Portal「授信决策辅助」Tab 加载做决策"
        except Exception as _je:
            json_hint = f"\n\n⚠️ ReportJSON 生成失败：{_je}"

        return (gr.update(value=DL_BANNER),
                gr.update(value=path, visible=True),
                gr.update(visible=False),
                "导出成功，请下载" + json_hint)
    except Exception as e:
        return (gr.update(),
                gr.update(),
                gr.update(visible=True),
                f"导出失败: {e}")


def on_template_upload(template_file, session_state, mode_state):
    """模板上传处理"""
    if template_file is None:
        return "未检测到模板文件"
    sid = session_state or "default"
    path = template_file.name if hasattr(template_file, "name") else str(template_file)

    import shutil
    persist_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates_cache")
    os.makedirs(persist_dir, exist_ok=True)
    basename = os.path.basename(path)
    persist_path = os.path.join(persist_dir, basename)
    try:
        shutil.copy2(path, persist_path)
        path = persist_path
    except Exception:
        pass

    current_mode = mode_state or "叙述报告"
    is_form_fill = "填空" in current_mode

    if sid not in agents:
        if is_form_fill:
            _pending_form_templates[sid] = path
        else:
            _pending_templates[sid] = path
        return f"已暂存模板（发送消息后自动加载）: {basename}"

    agent = agents[sid]

    if is_form_fill:
        agent.form_template_path = path
        agent.form_fill_done = False
        agent.form_fill_output = ""
        return f"填空模板已加载: {basename}\n请上传材料文件后发送「开始填写」"
    else:
        old_template = agent.template_path
        agent.set_template(path)
        has_old_chapters = any(agent.chapters.get(f"ch{i}") for i in range(1, 5))
        if has_old_chapters:
            agent.chapters.clear()
            agent.report_exported = False
            agent.report_reviewed = False
            agent.self_reflected = False
            return f"模板已更换: {basename}\n已清除旧报告缓存，下次生成将使用新模板"
        return f"已加载模板: {basename}"


def on_mode_change(mode_choice):
    """模式切换"""
    if "填空" in mode_choice:
        welcome = WELCOME_FORM_FILL
        tpl_label = "上传填空模板（.docx，必填）"
    else:
        welcome = WELCOME_NARRATIVE
        tpl_label = "上传 Word 模板（可选）"
    return (
        [{"role": "assistant", "content": welcome}],
        gr.update(label=tpl_label),
        mode_choice,
    )


def on_feedback(feedback_text, session_state):
    if not feedback_text or not feedback_text.strip():
        return ""
    sid = session_state or "default"
    if sid in agents:
        agents[sid].memory.knowledge.add_preference("user_feedback", feedback_text.strip())
        return "反馈已记录，感谢！"
    return "请先启动 Agent"


# ═══════════════════════════════════════════════════════════
#  构建界面
# ═══════════════════════════════════════════════════════════

def build_app():
    with gr.Blocks(
        title="授信报告智能助手",
        css=CSS,
        theme=_build_theme(),
    ) as app:
        session_state = gr.State("default")
        mode_state = gr.State("叙述报告")

        # ── 自定义 HTML Header（突破 Gradio 默认美学）──
        gr.HTML(HEADER_HTML)

        with gr.Row(equal_height=False):
            # ═════ 左侧配置面板 ═════
            with gr.Column(scale=1, min_width=300, elem_id="sidebar-col"):
                with gr.Accordion("系统配置", open=True):
                    api_key_input = gr.Textbox(
                        label="API 密钥",
                        placeholder="sk-xxx",
                        type="password",
                    )
                    provider_select = gr.Dropdown(
                        label="模型供应商",
                        choices=["deepseek", "kimi-k2.5", "openai", "claude"],
                        value="deepseek",
                    )
                    mode_select = gr.Radio(
                        label="工作模式",
                        choices=["叙述报告", "填空申报表"],
                        value="叙述报告",
                    )

                with gr.Accordion("模板管理", open=True):
                    template_upload = gr.File(
                        label="上传 Word 模板（可选）",
                        file_types=[".docx", ".doc"],
                    )
                    template_status = gr.Markdown("")

                with gr.Accordion("待补充字段", open=True, visible=True) as pending_accordion:
                    pending_tags_display = gr.Markdown(
                        value="*填写完成后，待补充字段列表将显示在此处*",
                        elem_id="pending-tags",
                    )

                with gr.Accordion("意见反馈", open=False):
                    feedback_input = gr.Textbox(
                        label="改进建议",
                        placeholder="告诉我哪里需要改进...",
                        lines=2,
                    )
                    feedback_btn = gr.Button("提交反馈", variant="secondary", size="sm")
                    feedback_result = gr.Markdown("")

                status_display = gr.Textbox(
                    label="运行状态",
                    value="等待输入",
                    interactive=False,
                    max_lines=2,
                    elem_id="status-bar",
                )

            # ═════ 右侧聊天区 ═════
            with gr.Column(scale=3, elem_id="chat-col"):
                dl_banner = gr.Markdown(
                    value="",
                    elem_classes=["download-banner"],
                )
                dl_file = gr.File(
                    label="点击下载报告",
                    visible=False,
                )
                manual_export_btn = gr.Button(
                    "手动导出 Word 报告",
                    variant="primary",
                    visible=False,
                )

                chatbot = gr.Chatbot(
                    value=[{"role": "assistant", "content": WELCOME_NARRATIVE}],
                    height=560,
                    elem_id="chatbot-box",
                    elem_classes=["chatbot-container"],
                )

                with gr.Row(elem_id="chat-input-row"):
                    chat_input = gr.Textbox(
                        placeholder="输入消息，按回车发送...",
                        show_label=False,
                        scale=3,
                        container=False,
                    )
                    file_upload = gr.File(
                        label="上传材料",
                        file_types=[".txt", ".docx", ".doc", ".pdf", ".xlsx", ".xls"],
                        file_count="multiple",
                        scale=2,
                        min_width=200,
                    )
                    send_btn = gr.Button("发送", variant="primary", scale=0, min_width=90)

        # ═════ 事件绑定 ═════
        send_inputs = [chat_input, file_upload, chatbot, api_key_input,
                       provider_select, session_state, mode_state]
        send_outputs = [chatbot, chat_input, file_upload,
                        dl_banner, dl_file, manual_export_btn, status_display,
                        pending_tags_display]

        send_btn.click(fn=stream_chat, inputs=send_inputs, outputs=send_outputs)
        chat_input.submit(fn=stream_chat, inputs=send_inputs, outputs=send_outputs)

        manual_export_btn.click(
            fn=on_manual_export,
            inputs=[session_state],
            outputs=[dl_banner, dl_file, manual_export_btn, status_display],
        )

        template_upload.change(
            fn=on_template_upload,
            inputs=[template_upload, session_state, mode_state],
            outputs=[template_status],
        )

        mode_select.change(
            fn=on_mode_change,
            inputs=[mode_select],
            outputs=[chatbot, template_upload, mode_state],
        )

        feedback_btn.click(
            fn=on_feedback,
            inputs=[feedback_input, session_state],
            outputs=[feedback_result],
        )

    return app


if __name__ == "__main__":
    app = build_app()
    app.launch(share=True, server_name="0.0.0.0", server_port=7860)
