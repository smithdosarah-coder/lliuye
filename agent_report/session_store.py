# -*- coding: utf-8 -*-
"""SessionStore — 内存 session 字典 + 30min TTL 过期清理.

用途:
  fill 端点生成 session_id 后,refine 端点需要凭 session_id 拿回
  原始 EnterpriseProfile / docx 路径 / 已写 section 列表,用于续跑。

约束:
  - 单进程内存(本项目无多实例部署需求)
  - UUID4 key
  - 30 分钟 TTL,惰性清理(每次 get/put 时扫一遍)

附带:
  - audit_log(event) + hash_input(payload):DoD L2-12 钩子,
    把 Agent6 每次对外调用落盘 data/audit/YYYY-MM-DD.jsonl,
    不进入 SessionStore 状态,仅复用本模块承担"会话层横切关注"。
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


_TTL_SECONDS = 30 * 60

# 审计日志落盘根目录:项目根下 data/audit/。目录在首次写入时按需创建。
_AUDIT_DIR = Path(__file__).resolve().parent.parent / "data" / "audit"


class SessionStore:
    def __init__(self, ttl_seconds: int = _TTL_SECONDS):
        self._lock = threading.RLock()
        self._data: dict[str, dict[str, Any]] = {}
        self._ttl = ttl_seconds

    def _gc(self) -> None:
        """惰性清理已过期 session."""
        now = time.time()
        expired = [k for k, v in self._data.items()
                   if now - v.get("_ts", now) > self._ttl]
        for k in expired:
            self._data.pop(k, None)

    def create(self, payload: dict[str, Any]) -> str:
        """创建新 session,返回 session_id."""
        sid = str(uuid.uuid4())
        with self._lock:
            self._gc()
            payload = dict(payload)
            payload["_ts"] = time.time()
            self._data[sid] = payload
        return sid

    def get(self, sid: str) -> Optional[dict[str, Any]]:
        with self._lock:
            self._gc()
            return self._data.get(sid)

    def update(self, sid: str, patch: dict[str, Any]) -> bool:
        with self._lock:
            self._gc()
            if sid not in self._data:
                return False
            self._data[sid].update(patch)
            self._data[sid]["_ts"] = time.time()
            return True

    def delete(self, sid: str) -> bool:
        with self._lock:
            return self._data.pop(sid, None) is not None

    def list_ids(self) -> list[str]:
        with self._lock:
            self._gc()
            return list(self._data.keys())


# 单例
store = SessionStore()


# ---------------------------------------------------------------------------
# 审计日志钩子 (DoD L2-12)
# 仅 append 写,不回读;失败静默不阻塞主流程。
# 事件不落原始客户材料,只落 input_hash;用户 id 由调用方传入(默认 "mock_wangzhe")。
# ---------------------------------------------------------------------------

def hash_input(payload: Any) -> str:
    """稳定序列化 + sha256 取前 16 hex;不入 PII,用于审计去重/追溯。"""
    try:
        s = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    except Exception:
        s = str(payload)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def audit_log(event: dict[str, Any]) -> None:
    """把一条审计事件 append 到 data/audit/YYYY-MM-DD.jsonl。

    推荐字段:timestamp / user_id / endpoint / input_hash / output_status / latency_ms。
    写入失败不抛,只打到 stderr,不影响 Agent 主流程。
    """
    try:
        _AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        date = datetime.now().strftime("%Y-%m-%d")
        path = _AUDIT_DIR / f"{date}.jsonl"
        line = json.dumps(event, ensure_ascii=False, default=str)
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:  # noqa: BLE001 — 审计失败不阻塞主流程
        import sys
        print(f"[audit_log] write failed: {e}", file=sys.stderr)
