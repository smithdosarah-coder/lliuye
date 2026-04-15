# -*- coding: utf-8 -*-
"""SessionStore — 内存 session 字典 + 30min TTL 过期清理.

用途:
  fill 端点生成 session_id 后,refine 端点需要凭 session_id 拿回
  原始 EnterpriseProfile / docx 路径 / 已写 section 列表,用于续跑。

约束:
  - 单进程内存(本项目无多实例部署需求)
  - UUID4 key
  - 30 分钟 TTL,惰性清理(每次 get/put 时扫一遍)
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Optional


_TTL_SECONDS = 30 * 60


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
