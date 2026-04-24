# -*- coding: utf-8 -*-
"""风险偏好配置 — Agent3 v2.0

对应 PRD 第 6.10 / 第 12 章。
默认配置来自 mock_data/risk_appetite_default.json，
客户自定义可存放于 config/risk_appetite_{client_id}.json。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

_AGENT_DIR = Path(__file__).parent
_DEFAULT_PATH = _AGENT_DIR / "mock_data" / "risk_appetite_default.json"
_CUSTOM_DIR = _AGENT_DIR.parent / "config"


def _load_default_raw() -> dict:
    try:
        with open(_DEFAULT_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return {}


@dataclass
class RiskAppetiteConfig:
    """单板块的风险偏好配置（对公或对私）"""

    segment: str = "corporate"
    dimension_weights: dict = field(default_factory=dict)
    grade_thresholds: list = field(default_factory=list)
    rule_threshold_overrides: dict = field(default_factory=dict)
    rate_tier_map: dict = field(default_factory=dict)
    lpr_base: float = 0.045

    @classmethod
    def default(cls, segment: str = "corporate") -> "RiskAppetiteConfig":
        raw = _load_default_raw()
        data = raw.get(segment, {}) or {}
        return cls(
            segment=segment,
            dimension_weights=data.get("dimension_weights", {}) or {},
            grade_thresholds=data.get("grade_thresholds", []) or [],
            rule_threshold_overrides=data.get("rule_threshold_overrides", {}) or {},
            rate_tier_map=data.get("rate_tier_map", {}) or {},
            lpr_base=data.get("lpr_base", 0.045),
        )

    @classmethod
    def load(cls, client_id: str = "", segment: str = "corporate") -> "RiskAppetiteConfig":
        if client_id:
            path = _CUSTOM_DIR / f"risk_appetite_{client_id}.json"
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as fh:
                        raw = json.load(fh) or {}
                    data = raw.get(segment, {}) or {}
                    if data:
                        merged = cls.default(segment)
                        merged.segment = segment
                        for k, v in data.items():
                            if hasattr(merged, k):
                                setattr(merged, k, v)
                        return merged
                except (OSError, json.JSONDecodeError, ValueError, TypeError, AttributeError):
                    pass
        return cls.default(segment)

    def save(self, client_id: str) -> str:
        _CUSTOM_DIR.mkdir(parents=True, exist_ok=True)
        path = _CUSTOM_DIR / f"risk_appetite_{client_id}.json"
        existing = {}
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    existing = json.load(fh) or {}
            except (OSError, json.JSONDecodeError, ValueError, TypeError):
                existing = {}
        existing[self.segment] = asdict(self)
        existing["version"] = "v2.0"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(existing, fh, ensure_ascii=False, indent=2)
        return str(path)

    def get_threshold(self, rule_id: str, default_threshold: Any) -> Any:
        """红线规则阈值：overrides 优先，否则用规则默认值"""
        if rule_id in self.rule_threshold_overrides:
            return self.rule_threshold_overrides[rule_id]
        return default_threshold

    def to_dict(self) -> dict:
        return asdict(self)

    def update_from_ui(self, changes: dict) -> None:
        """从 UI 表单回写"""
        for k, v in (changes or {}).items():
            if hasattr(self, k):
                setattr(self, k, v)
