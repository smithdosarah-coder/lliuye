# -*- coding: utf-8 -*-
"""Per-Agent BaseScanner 适配器集合 · D.5 共享底座 impls.

每个适配器包装现有 agent_*/scanner 实装 · 转 ScanRunResult · 给 Router/Degrader
统一调度。

约束:
  - **不重写**业务逻辑 · 仅做 ScanRequest → 现有调用 → ScanRunResult 转换
  - import 现有 scanner 失败时 health() 返 False · degrader 跳过即可
"""
from __future__ import annotations

# 各 adapter 类按需 lazy import (避免循环依赖) · 见 bootstrap()
__all__: list[str] = []
