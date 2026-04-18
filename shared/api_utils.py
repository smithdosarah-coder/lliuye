# -*- coding: utf-8 -*-
"""shared.api_utils — FastAPI / SSE 共享工具。

只放跨 Agent 通用的小工具：
  - sse_encode: 统一 SSE event 编码
  - to_jsonable: 递归把 dataclass / pydantic / 自定义对象转成 JSON-safe

业务逻辑不放这里。修改本文件需按 docs/contracts/shared-change-protocol.md 走 RFC。
"""
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any

from pydantic import BaseModel


def to_jsonable(obj: Any) -> Any:
    """递归将 dataclass / pydantic / 自定义对象转成 JSON-safe 结构。"""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple, set)):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if is_dataclass(obj):
        return to_jsonable(asdict(obj))
    if isinstance(obj, BaseModel):
        return to_jsonable(obj.model_dump())
    if hasattr(obj, "to_dict") and callable(obj.to_dict):
        try:
            return to_jsonable(obj.to_dict())
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        return to_jsonable({k: v for k, v in obj.__dict__.items()
                            if not k.startswith("_")})
    return str(obj)


def sse_encode(evt: dict) -> str:
    """SSE event 统一编码：data: <json>\\n\\n。"""
    return f"data: {json.dumps(evt, ensure_ascii=False, default=str)}\n\n"
