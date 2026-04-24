# -*- coding: utf-8 -*-
"""Agent1 v2.0 Portal Demo Tab: 知识库驱动的 look-alike 获客。

UI 结构：
  左栏：上传区（客户名录 / 政策文件 / 行业指引）+ 预置场景按钮
  中栏：进度日志
  右栏：Top N 线索瀑布流（Markdown 格式）+ 导出按钮
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import gradio as gr

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.demo_ui import (
    ZHONGAN_BLUE,
    ZHONGAN_TEXT_LIGHT,
    render_header_html,
)
from shared.kb_scan.exporters import (
    export_hitlist_excel,
    export_hitlist_csv,
    export_hitlist_markdown,
)

from agent_channel.agent import ChannelMatchAgent


SCENARIOS_DIR = PROJECT_ROOT / "demo_data" / "agent_channel" / "scenarios"


def _load_scenarios() -> list[dict]:
    """加载 demo_data/agent_channel/scenarios/*/scenario.json 的场景。"""
    if not SCENARIOS_DIR.exists():
        return []
    out = []
    for sub in sorted(SCENARIOS_DIR.iterdir()):
        if not sub.is_dir():
            continue
        meta_path = sub / "scenario.json"
        if not meta_path.exists():
            continue
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, ValueError, TypeError):
            continue
        # 把 files 展开成绝对路径
        abs_files = [str((sub / f).resolve()) for f in meta.get("files", [])]
        meta["_abs_files"] = abs_files
        meta["_dir"] = str(sub)
        out.append(meta)
    return out


def _format_event_line(event: dict) -> str:
    etype = event.get("type", "")
    if etype == "thinking":
        return f"💭 {event.get('content', '')}\n\n"
    if etype == "message":
        return ""   # message 另外拼到最终结果区
    if etype == "tool_call":
        return f"🔧 调用 `{event.get('name', '')}` ...\n\n"
    if etype == "tool_result":
        return f"✅ `{event.get('name', '')}` · {event.get('result', '')}\n\n"
    if etype == "profile":
        return f"📋 画像已生成\n\n"
    if etype == "hit_list":
        hits = event.get("hits") or []
        return f"🏆 Top{len(hits)} 线索榜生成完毕\n\n"
    if etype == "done":
        return f"✓ {event.get('content', '完成')}\n\n"
    return ""


def build_tab(api_key_state, provider_state):
    """Portal 构建函数。"""
    gr.HTML(render_header_html(
        "全渠道流量匹配 · look-alike 获客",
        "上传客户名录 + 政策文件 + 行业指引，AI 自动抽画像、扫外网、出 Top 线索 + 推荐产品 + 话术",
    ))

    scenarios = _load_scenarios()

    with gr.Row():
        # ============ 左栏：上传 + 场景 ============
        with gr.Column(scale=2):
            gr.Markdown("### 📥 上传知识库文件")
            gr.Markdown(
                f"<div class='muted-note'>支持：客户名录 (Excel/CSV)、政策文件 (Word/PDF/TXT)、"
                f"行业指引 (Word/PDF/TXT)。文件名含 客户 / 政策 / 指引 等关键字可自动识别类型。</div>"
            )
            customer_file = gr.File(
                label="① 客户名录（Excel / CSV）",
                file_count="single",
                file_types=[".xlsx", ".xls", ".csv"],
            )
            policy_file = gr.File(
                label="② 政策文件（Word / PDF / TXT）",
                file_count="single",
                file_types=[".docx", ".doc", ".pdf", ".txt", ".md"],
            )
            industry_file = gr.File(
                label="③ 行业指引（Word / PDF / TXT）",
                file_count="single",
                file_types=[".docx", ".doc", ".pdf", ".txt", ".md"],
            )

            top_n = gr.Slider(
                minimum=5, maximum=20, value=10, step=1,
                label="Top N 线索数量",
            )

            gr.Markdown("### 🚀 预置场景")
            scenario_buttons = []
            if scenarios:
                for sc in scenarios:
                    btn = gr.Button(
                        f"📍 {sc.get('title', '场景')}",
                        variant="secondary",
                        size="sm",
                    )
                    scenario_buttons.append((sc, btn))
            else:
                gr.Markdown(
                    f"<span style='color:{ZHONGAN_TEXT_LIGHT}'>*未发现预置场景目录*</span>"
                )

            run_btn = gr.Button(
                "🧭 开始扫描",
                variant="primary",
                elem_classes=["zhongan-btn-primary"],
                size="lg",
            )
            gr.Markdown(
                f"<div class='muted-note'>首次使用请先在顶部"
                f"「⚙️ 全局配置」中填写 API Key。</div>"
            )

        # ============ 中栏：进度日志 ============
        with gr.Column(scale=2):
            gr.Markdown("### 🔍 执行过程")
            process_log = gr.Markdown("*上传 3 类文件（或点击预置场景）→ 点击『开始扫描』*")

        # ============ 右栏：最终结果 ============
        with gr.Column(scale=4):
            gr.Markdown("### 🏆 Top N 线索榜")
            final_output = gr.Markdown("*结果将在扫描完成后展示*")
            export_btn = gr.Button("📊 导出 Excel 线索榜", variant="secondary", size="sm")
            export_file = gr.File(label="导出文件（点击下载）", visible=False)

    # ---- 场景按钮：点击后直接填入 3 个 File 控件 ----
    def _apply_scenario(sc: dict):
        files = sc.get("_abs_files", [])
        customer_path = next((f for f in files if "customer" in f.lower() or "客户" in f.lower() or f.endswith((".xlsx", ".csv"))), None)
        policy_path = next((f for f in files if "policy" in f.lower() or "政策" in f.lower() or "方案" in f.lower()), None)
        guide_path = next((f for f in files if "guide" in f.lower() or "指引" in f.lower() or "行业" in f.lower()), None)
        return customer_path, policy_path, guide_path

    for sc, btn in scenario_buttons:
        btn.click(
            (lambda s=sc: _apply_scenario(s)),
            inputs=None,
            outputs=[customer_file, policy_file, industry_file],
        )

    # ---- 扫描入口 ----
    _agent_cache = {"instance": None}

    def _collect_files(f1, f2, f3) -> list[str]:
        out = []
        for f in (f1, f2, f3):
            if f is None:
                continue
            path = f if isinstance(f, str) else getattr(f, "name", None)
            if path and os.path.exists(path):
                out.append(path)
        return out

    def _run(api_key, provider, f1, f2, f3, n_top):
        files = _collect_files(f1, f2, f3)
        if not files:
            yield "⚠️ 请先上传至少一个文件，或点击预置场景。", "*尚未开始*"
            return
        if not api_key:
            yield "⚠️ 请先在顶部「⚙️ 全局配置」填写 API Key（Demo 场景也需要 LLM 做画像抽取）。", "*未配置 API Key*"
            return
        try:
            agent = ChannelMatchAgent(api_key=api_key, model_provider=provider)
            _agent_cache["instance"] = agent
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError) as e:
            yield f"❌ Agent 初始化失败：{e}", ""
            return

        log = ""
        final_chunks: list[str] = []
        try:
            for ev in agent.process_message(
                user_message="",
                uploaded_files=files,
                top_n=int(n_top),
            ):
                line = _format_event_line(ev)
                if line:
                    log += line
                if ev.get("type") == "message":
                    final_chunks.append(ev.get("content", ""))
                yield log, "\n\n".join(final_chunks) if final_chunks else "*处理中…*"
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError) as e:
            log += f"\n❌ 执行异常：{e}\n"
            yield log, "\n\n".join(final_chunks)

    run_btn.click(
        _run,
        inputs=[api_key_state, provider_state, customer_file, policy_file, industry_file, top_n],
        outputs=[process_log, final_output],
    )

    # ---- 导出 ----
    def _export():
        agent = _agent_cache.get("instance")
        if agent is None:
            return gr.update(value=None, visible=False)
        hl = agent.get_last_hit_list()
        if hl is None or not hl.hits:
            return gr.update(value=None, visible=False)
        out_dir = str(PROJECT_ROOT / "outputs")
        try:
            path = export_hitlist_excel(hl, output_dir=out_dir)
        except (OSError, ImportError, ValueError, TypeError, AttributeError, KeyError):
            try:
                path = export_hitlist_csv(hl, output_dir=out_dir)
            except (OSError, ValueError, TypeError, AttributeError, KeyError):
                path = export_hitlist_markdown(hl, output_dir=out_dir)
        return gr.update(value=path, visible=True)

    export_btn.click(_export, inputs=None, outputs=export_file)


# ---- 独立启动（方便单独调试 Agent1） ----

def _standalone_main():
    import argparse
    from shared.demo_ui import CUSTOM_CSS

    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=7871)
    args = ap.parse_args()

    with gr.Blocks(title="全渠道流量匹配 — look-alike 获客", css=CUSTOM_CSS) as demo:
        api_key_state = gr.State("")
        provider_state = gr.State("deepseek")
        with gr.Accordion("⚙️  全局配置", open=True):
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
                    scale=3,
                )
                save_btn = gr.Button("保存", variant="primary", scale=1)
            status = gr.Markdown("")
            def _save(p, k):
                if not k or len(k) < 10:
                    return "", p, "❌ API Key 格式异常"
                return k, p, f"✅ 已保存：provider={p}"
            save_btn.click(_save, inputs=[provider_input, api_key_input],
                           outputs=[api_key_state, provider_state, status])

        build_tab(api_key_state, provider_state)

    demo.launch(server_name="0.0.0.0", server_port=args.port, show_error=True)


if __name__ == "__main__":
    _standalone_main()
