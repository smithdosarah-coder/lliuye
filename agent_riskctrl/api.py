# -*- coding: utf-8 -*-
"""agent_riskctrl.api — Agent2 风控策略运营 FastAPI 路由模块。

端点：
  POST /api/riskctrl/dsl_gen   — 自然语言 → 结构化规则集 (SSE)
  POST /api/riskctrl/backtest  — 上传历史数据回测策略 (SSE)

设计：
- 独立 FastAPI app，由 api_server.py 通过 routes 合并模式装载
- 业务逻辑全在 agent_riskctrl.agent.RiskControlAgent.process_message
  (走意图分流: rule_config / backtest / error_analysis)
- import 失败时 SSE 仍能 yield error 事件，前端不崩
- 输出前过 shared.qc.placeholder_guard (Task B 软降级)

字段契约：见 docs/contracts/field-naming.md
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.api_utils import sse_encode, to_jsonable  # noqa: E402

from agent_riskctrl.output_validator import soft_clean as _qc_scrub  # noqa: E402

# Stage E.1 · audit log decorator (silent fail if audit_service unavailable)
try:
    from audit_service.decorators import audit_llm_call  # noqa: E402
except ImportError:
    def audit_llm_call(**_kwargs):  # type: ignore[no-redef]
        def _passthrough(fn):
            return fn
        return _passthrough

app = FastAPI(title="Agent2 Risk Control API", version="3.1")


@app.get("/api/riskctrl/health")
async def riskctrl_health():
    """Agent2 sub-app 健康探针 (与 portal /health 平级, 用于精细化故障定位)。"""
    return {"status": "ok", "agent": "agent_riskctrl"}


class RiskCtrlDslRequest(BaseModel):
    rule_text: str                       # 自然语言策略意图
    provider: str | None = None
    api_key: str | None = None


class RiskCtrlBacktestRequest(BaseModel):
    instruction: str                     # 用户指令 (e.g. "回测我的拒绝策略")
    uploaded_files: list[str]            # CSV/Excel 路径列表
    provider: str | None = None
    api_key: str | None = None


def _stream_riskctrl(message: str, files: list[str] | None,
                     provider: str | None, api_key: str | None):
    """共用生成器: 跑 RiskControlAgent.process_message 并以 SSE 返回。"""
    try:
        from agent_riskctrl.agent import RiskControlAgent
    except ImportError as e:
        yield sse_encode({"event": "error", "message": f"agent import failed: {e}"})
        return

    try:
        agent = RiskControlAgent(
            api_key=api_key or "dummy",
            model_provider=provider or "deepseek",
        )
        for evt in agent.process_message(
            user_message=message,
            uploaded_files=files,
        ):
            payload = to_jsonable(evt)
            cleaned, hits = _qc_scrub(payload)
            wrap = {"event": "stage", "payload": cleaned}
            if hits:
                wrap["_qc_placeholder_hits"] = hits
            yield sse_encode(wrap)

        yield sse_encode({"event": "done"})
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError, ImportError) as e:
        traceback.print_exc()
        yield sse_encode({
            "event": "error",
            "message": f"{type(e).__name__}: {e}",
            "traceback": traceback.format_exc()[-2000:],
        })


@app.post("/api/riskctrl/dsl_gen")
@audit_llm_call(agent_id="riskctrl", endpoint="/api/riskctrl/dsl_gen", model="deepseek-chat")
async def riskctrl_dsl_gen(req: RiskCtrlDslRequest):
    """自然语言 → 结构化风控规则集 SSE。

    走 RiskControlAgent 的 rule_config 流程 (无 CSV 时默认意图)。
    """
    def gen():
        yield from _stream_riskctrl(req.rule_text, None, req.provider, req.api_key)
    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.post("/api/riskctrl/backtest")
async def riskctrl_backtest(req: RiskCtrlBacktestRequest):
    """上传历史授信数据回测策略效果 SSE。

    走 RiskControlAgent 的 backtest 流程 (有 CSV/Excel + 回测意图自动命中)。
    """
    def gen():
        # instruction 不带 "回测" 等关键词时, agent 会 fallback 到 rule_config;
        # 这里显式把 "回测" 拼进 message 头, 确保意图分流稳定。
        msg = ("回测 " + (req.instruction or "")).strip()
        yield from _stream_riskctrl(msg, req.uploaded_files, req.provider, req.api_key)
    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
