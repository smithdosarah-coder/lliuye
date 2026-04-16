# -*- coding: utf-8 -*-
"""信贷AI智能体矩阵 — 统一 Portal 入口

6 个 Agent 通过 Gradio Tab 整合展示，统一品牌视觉（众安蓝）。
- 全局配置抽屉：API Key + 模型厂商（一次设置，所有 Tab 共享）
- 每个 Tab 调用对应 agent_XXX/app_demo.py 的 build_tab() 函数
- 若某 Agent 尚未改造完成，显示"建设中"占位符
"""

from __future__ import annotations

import os
import sys
import gradio as gr

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.demo_ui import (
    CUSTOM_CSS,
    ZHONGAN_BLUE,
    ZHONGAN_BLUE_DARK,
    render_coming_soon_html,
)


# ---------------------------------------------------------------------------
# Portal 头部
# ---------------------------------------------------------------------------

PORTAL_HEADER_HTML = f"""
<div class="portal-header">
    <h1>众安信科 · 信贷 AI 智能体矩阵</h1>
    <div class="subtitle">获客 · 授信 · 风控 · 贷中 · 合规 — 6 大智能体覆盖信贷业务全流程</div>
</div>
"""


# ---------------------------------------------------------------------------
# 各 Tab 构建函数（优先调用 agent_XXX/app_demo.py，缺失时显示占位）
# ---------------------------------------------------------------------------

def _safe_build_tab(import_path: str, build_fn_name: str,
                    api_key_state, provider_state, agent_label: str):
    """尝试导入某 agent 的 app_demo.build_tab() 并构建；失败则显示占位符"""
    try:
        module = __import__(import_path, fromlist=[build_fn_name])
        build_fn = getattr(module, build_fn_name, None)
        if build_fn is None:
            raise AttributeError(f"{import_path} 缺少 {build_fn_name}()")
        build_fn(api_key_state, provider_state)
    except Exception as e:
        gr.HTML(render_coming_soon_html(
            agent_label,
            f"demo 模块尚未就绪：{type(e).__name__}: {str(e)[:120]}"
        ))


def build_report_tab(api_key_state, provider_state):
    """Tab 0: 授信报告生成助手（已有成熟产品，用简化入口引导跳转 app.py）"""
    gr.HTML(f"""
    <div style="padding: 24px; background: white; border-radius: 12px; border: 1px solid #E5E7EB;">
        <h2 style="color: {ZHONGAN_BLUE}; margin: 0 0 12px 0;">📄 授信调查报告生成助手</h2>
        <p style="color: #6B7280; line-height: 1.8;">
            上传企业材料（财务报表 / 工商资料 / 征信报告等），AI 自动生成约 15000 字的授信调查报告。<br/>
            此功能已作为独立产品上线，启动方式：
        </p>
        <pre style="background: #F5F7FA; padding: 12px 16px; border-radius: 8px; font-size: 13px;">python app.py  # 独立启动，端口 7860</pre>
        <p style="color: #6B7280; margin-top: 12px; font-size: 13px;">
            后续版本将把报告生成流程嵌入到 Portal，并与其他 5 个 Agent 共享企业画像。
        </p>
    </div>
    """)


def build_channel_tab(api_key_state, provider_state):
    _safe_build_tab("agent_channel.app_demo", "build_tab",
                    api_key_state, provider_state, "全渠道流量匹配")


def build_credit_tab(api_key_state, provider_state):
    _safe_build_tab("agent_credit.app_demo", "build_tab",
                    api_key_state, provider_state, "授信决策辅助")


def build_riskctrl_tab(api_key_state, provider_state):
    _safe_build_tab("agent_riskctrl.app_demo", "build_tab",
                    api_key_state, provider_state, "风控策略运营")


def build_alert_tab(api_key_state, provider_state):
    _safe_build_tab("agent_alert.app_demo", "build_tab",
                    api_key_state, provider_state, "贷中风险预警")


def build_compliance_tab(api_key_state, provider_state):
    _safe_build_tab("agent_compliance.app_demo", "build_tab",
                    api_key_state, provider_state, "合规巡检")


# ---------------------------------------------------------------------------
# Portal 主入口
# ---------------------------------------------------------------------------

def create_portal():
    """构建 Portal 界面"""
    with gr.Blocks(
        title="众安信科 · 信贷 AI 智能体矩阵",
    ) as portal:

        # 全局状态：API Key + Provider，所有 Tab 共享
        api_key_state = gr.State("")
        provider_state = gr.State("deepseek")

        # 顶部品牌条
        gr.HTML(PORTAL_HEADER_HTML)

        # 配置抽屉（折叠，默认展开以便首次使用提示设置）
        with gr.Accordion("⚙️  全局配置（API Key + 模型厂商）", open=False):
            with gr.Row():
                provider_input = gr.Dropdown(
                    choices=["deepseek", "kimi", "minimax", "openai", "anthropic"],
                    value="deepseek",
                    label="模型厂商",
                    scale=1,
                )
                api_key_input = gr.Textbox(
                    label="API Key",
                    type="password",
                    placeholder="粘贴你的 API Key，所有 Tab 共享",
                    scale=3,
                )
                save_btn = gr.Button("保存配置", variant="primary", scale=1,
                                     elem_classes=["zhongan-btn-primary"])
            config_status = gr.Markdown("*未配置 API Key — 请填写后保存*")

            def _save_config(provider, api_key):
                if not api_key or len(api_key) < 10:
                    return "", provider, "❌ API Key 格式异常，请检查"
                return api_key, provider, (
                    f"✅ 配置已保存：provider = **{provider}**，"
                    f"API Key = `{api_key[:6]}...{api_key[-4:]}`"
                )

            save_btn.click(
                _save_config,
                inputs=[provider_input, api_key_input],
                outputs=[api_key_state, provider_state, config_status],
            )

        # 6 Tabs
        with gr.Tabs():
            with gr.Tab("📄 报告生成"):
                build_report_tab(api_key_state, provider_state)
            with gr.Tab("🎯 全渠道流量匹配"):
                build_channel_tab(api_key_state, provider_state)
            with gr.Tab("💼 授信决策辅助"):
                build_credit_tab(api_key_state, provider_state)
            with gr.Tab("⚙️ 风控策略运营"):
                build_riskctrl_tab(api_key_state, provider_state)
            with gr.Tab("🚨 贷中风险预警"):
                build_alert_tab(api_key_state, provider_state)
            with gr.Tab("✅ 合规巡检"):
                build_compliance_tab(api_key_state, provider_state)

        # 底部备注
        gr.HTML(f"""
        <div style="text-align: center; padding: 16px; color: #9CA3AF; font-size: 12px;">
            众安信科 · 乾策平台 X-Nexus / Credit Intelligence Matrix v1.0 · Demo
        </div>
        """)

    return portal


if __name__ == "__main__":
    portal = create_portal()
    portal.launch(
        server_name="0.0.0.0",
        server_port=7870,
        share=False,
        show_error=True,
        css=CUSTOM_CSS,
        theme=gr.themes.Soft(primary_hue="blue"),
    )
