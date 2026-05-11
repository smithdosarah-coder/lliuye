# -*- coding: utf-8 -*-
"""Agent2 风控 · LLM-as-judge 评判模块 (P3F 轨 8b Task C)

补足 Agent2 评估 PARTIAL 5/10 中 rule_interpretability 维度.

设计:
  · 基类 LLMJudge — prompt 渲染 + LLMClient 调用 + JSON 解析 + 失败降级
  · 子类 RuleInterpretabilityJudge — 单条 DSL 规则 3 维度 1-5 Likert 打分
       3 维度: executability / business_rationality / threshold_rationality
  · 模块级 compute_rule_interpretability(rules) — adapter 一行调用入口

失败降级 (onboarding §2 Task C 约束):
  · 无 DEEPSEEK_API_KEY → status='unavailable' 不 crash · 返回 (None, meta)
  · 网络 / API 错误 → 该规则记 status='judge_error' · 累计入 breakdown
  · JSON 解析失败 → status='parse_error' · 记入 breakdown · 不 crash
  · 任何场景 adapter 不抛异常

Method 标注 (schemas.py MetricMethod 枚举):
  · 有真值 → 'llm-judge'
  · 全失败 / 无 key → 'manual' value=None note 含 reason

历史溯源: P3F 轨 8b · 解决 PARTIAL 5/10 中 rule_interpretability pending.
路径选择: per AGENT_IDENTITY.md + GO 信令 → agent_riskctrl/llm_judge.py
         (onboarding §2/§3 CA-B3-8 写的 shared/llm_judge/base.py · spec 分歧
          已在 Task C commit body 标记 · Task D final 由主 CLI 裁决)
"""

from __future__ import annotations

import json
import os
import re
from typing import Any


JUDGE_VERSION = "v1.0"
DEFAULT_PROVIDER = "deepseek"

# 3 维度 · 1-5 Likert · 5 = 卓越 / 4 = 合理 / 3 = 一般 / 2 = 勉强 / 1 = 不合理
INTERP_DIMENSIONS = ("executability", "business_rationality", "threshold_rationality")
INTERP_DIM_LABELS = {
    "executability": "可执行性",
    "business_rationality": "业务合理性",
    "threshold_rationality": "阈值合理性",
}

INTERP_SYSTEM_PROMPT = """你是资深银行零售风控审计员。给定一条结构化 DSL 风控规则，按以下 3 个维度独立打 1-5 Likert 分。

## 评分维度

### executability (可执行性)
字段名 / 操作符 / value 类型是否能被规则引擎 (rule_engine) 正确执行。
  - 5 = 完全可执行 (字段标准 / 操作符规范 / value 类型匹配)
  - 4 = 可执行 (个别字段命名风格不统一但语义清晰)
  - 3 = 部分模糊 (如操作符在字符串字段上语义不严)
  - 2 = 有 bug (类型不匹配 / 操作符不支持)
  - 1 = 完全不可执行 (字段缺失或结构异常)

### business_rationality (业务合理性)
在零售/普惠风控场景下，规则触发条件 → action 的因果是否合理。
  - 5 = 完全合理 (触发→action 因果链强 · 业界惯例)
  - 4 = 较合理 (合理但 action 严苛度可商榷)
  - 3 = 可商榷 (条件触发与 action 关系一般)
  - 2 = 逻辑可疑 (条件→action 反直觉)
  - 1 = 明显错误 (会导致典型客群误杀 / 漏放)

### threshold_rationality (阈值合理性)
数值阈值是否合理 (不过激 / 不过松)，与业界普惠/零售 benchmark 对齐。
  - 5 = 精准 (阈值贴合业界 benchmark)
  - 4 = 可接受 (略偏严或略偏松但在合理区间)
  - 3 = 偏激或偏松 (显著偏离但可解释)
  - 2 = 显著偏离 (会引起明显误杀 / 漏放)
  - 1 = 完全离谱 (阈值无法解释)

## 输出格式 (严格 JSON)

```json
{
  "executability": <int 1-5>,
  "business_rationality": <int 1-5>,
  "threshold_rationality": <int 1-5>,
  "rationale": "<一句话理由 · 中文 · 不超 80 字>"
}
```

仅输出 JSON · 不要其他文字 · 不要 markdown 代码块。"""


# ---------------------------------------------------------------------------
# 基类 LLMJudge · prompt + parser + failure degradation
# ---------------------------------------------------------------------------


class LLMJudge:
    """LLM-as-judge 基类 · 子类 override _build_prompt / _parse_response."""

    method_tag = "llm-judge"  # MetricOutcome.method 枚举对齐

    def __init__(
        self,
        provider: str = DEFAULT_PROVIDER,
        api_key: str | None = None,
        cache_enabled: bool = True,
    ) -> None:
        self.provider = provider
        self.api_key = api_key if api_key is not None else os.environ.get(
            "DEEPSEEK_API_KEY"
        ) or os.environ.get("LLM_API_KEY") or ""
        self.cache_enabled = cache_enabled
        self._llm: Any = None  # lazy init · 避免无 key 时 import 也失败

    def is_available(self) -> bool:
        """是否具备调用条件 (有 key)."""
        return bool(self.api_key)

    def _get_client(self) -> Any | None:
        """Lazy init LLMCaller · 失败返回 None.

        Phase A worker-A4 (caller 3 deprecation) · 由 root llm.LLMClient 迁
        shared.llm_caller.LLMCaller (per A2 V2 ACK trailer · CLAUDE.md §3.6).
        cache_enabled 字段不再生效 (LLMCaller 内置 fallback chain · provider
        cache 由 root llm.LLMClient 兜底层处理).
        """
        if self._llm is not None:
            return self._llm
        if not self.api_key:
            return None
        try:
            from shared.llm_caller import LLMCaller
            self._llm = LLMCaller(
                agent_id="riskctrl",
                endpoint="judge",
            )
            return self._llm
        except (ImportError, RuntimeError, ValueError, TypeError, OSError):
            return None

    def judge(self, prompt: dict[str, str]) -> dict[str, Any]:
        """评判入口 · 返回 {score, rationale, status, raw}.

        status 枚举:
          · 'ok'           — 调用成功 + JSON 解析成功
          · 'unavailable'  — 无 key / 客户端初始化失败
          · 'judge_error'  — 网络/API 异常
          · 'parse_error'  — JSON 解析失败

        Args:
            prompt: {'system': str, 'user': str}

        Returns:
            {
                'score': float | None,    # 子类聚合分 · None 表示 不可用
                'rationale': str,         # 解释 · 失败时含 error 摘要
                'status': str,
                'raw': str,               # LLM 原始返回 · 调试用
                'detail': dict,           # 子类可附加细节
            }
        """
        client = self._get_client()
        if client is None:
            return {
                "score": None,
                "rationale": "LLM client unavailable (无 DEEPSEEK_API_KEY 或 init 失败)",
                "status": "unavailable",
                "raw": "",
                "detail": {},
            }
        try:
            # api_key 透传 LLMCaller.simple_chat (A4 caller 3 迁后 · api_key 由 caller 显式传)
            raw = client.simple_chat(prompt["system"], prompt["user"], api_key=self.api_key)
        except Exception as e:  # 兜底所有 LLM provider / 网络 / 认证异常 (judge 失败不能 crash worker)
            return {
                "score": None,
                "rationale": f"judge call failed: {type(e).__name__}: {str(e)[:120]}",
                "status": "judge_error",
                "raw": "",
                "detail": {"exception_type": type(e).__name__},
            }

        try:
            parsed = self._parse_response(raw)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as e:
            return {
                "score": None,
                "rationale": f"parse failed: {type(e).__name__}: {str(e)[:120]}",
                "status": "parse_error",
                "raw": raw[:500] if isinstance(raw, str) else str(raw)[:500],
                "detail": {"exception_type": type(e).__name__},
            }

        return {**parsed, "status": "ok", "raw": raw[:500] if isinstance(raw, str) else ""}

    def _parse_response(self, raw: str) -> dict[str, Any]:
        """子类 override · 默认裸 JSON 解析."""
        return _strip_json(raw)


# ---------------------------------------------------------------------------
# 子类 RuleInterpretabilityJudge · 3 维度 1-5 打分
# ---------------------------------------------------------------------------


class RuleInterpretabilityJudge(LLMJudge):
    """单条 DSL 规则 · 3 维度 (可执行性 / 业务合理性 / 阈值合理性) Likert 1-5."""

    SYSTEM_PROMPT = INTERP_SYSTEM_PROMPT
    DIMENSIONS = INTERP_DIMENSIONS

    def _build_prompt(self, rule: dict[str, Any]) -> dict[str, str]:
        # 仅暴露 rule 关键字段 · 隔离 backtest 等无关字段
        rule_view = {
            k: rule.get(k)
            for k in ("rule_id", "name", "description", "conditions", "action", "priority")
            if rule.get(k) is not None
        }
        user_msg = (
            "请评估以下 DSL 规则:\n\n"
            f"```json\n{json.dumps(rule_view, ensure_ascii=False, indent=2)}\n```\n\n"
            "按 system 指引输出 JSON。"
        )
        return {"system": self.SYSTEM_PROMPT, "user": user_msg}

    def _parse_response(self, raw: str) -> dict[str, Any]:
        """解析 LLM JSON · 返回 {score, rationale, detail}.

        score = 3 维度均分 · 1-5 浮点
        detail = 各维度原分 dict + 异常字段标 None
        """
        data = _strip_json(raw)
        dim_scores: dict[str, float | None] = {}
        valid: list[float] = []
        for dim in self.DIMENSIONS:
            v = data.get(dim)
            if isinstance(v, (int, float)) and 1 <= v <= 5:
                dim_scores[dim] = float(v)
                valid.append(float(v))
            else:
                dim_scores[dim] = None
        if not valid:
            raise ValueError(f"no valid dimension scores in: {raw[:200]}")

        rationale = str(data.get("rationale") or "").strip()
        score = sum(valid) / len(valid)
        # 风险经理 interpretation label · 让 Likert 分数有 business 意义
        # (per docs/contracts/agent-output-rubric-2026-05-11.md §3.6 riskctrl · audit P4 fix)
        if score >= 4.5:
            label = "优秀 (4.5-5) · 规则可执行 + 业务合理 + 阈值精准 · 可上线"
        elif score >= 3.5:
            label = "可用 (3.5-4.5) · 主体合理 · 个别维度可优化 · 建议上线后监控"
        elif score >= 2.5:
            label = "需改进 (2.5-3.5) · 字段 / 阈值 / 业务覆盖需调整 · 不建议上线"
        else:
            label = "不可用 (<2.5) · 规则不合理 · 必须重写 · 检查策略诉求映射"
        return {
            "score": round(score, 3),
            "label": label,
            "rationale": rationale,
            "detail": {"dim_scores": dim_scores, "n_valid_dims": len(valid)},
        }

    def judge_rule(self, rule: dict[str, Any]) -> dict[str, Any]:
        """便捷入口 · 组 prompt + 调 judge."""
        prompt = self._build_prompt(rule)
        return self.judge(prompt)

    def judge_ruleset(self, rules: list[dict[str, Any]]) -> dict[str, Any]:
        """对一组规则逐条打分 · 聚合.

        Returns:
            {
                'mean_score': float | None,    # 全部规则 score 均值 · 全部失败 → None
                'n_total': int,
                'n_judged': int,                # status=ok 计数
                'status_breakdown': {status: count},
                'per_rule': [{rule_id, score, status, rationale, dim_scores}, ...],
                'overall_status': 'ok' | 'unavailable' | 'partial',
            }
        """
        per_rule: list[dict[str, Any]] = []
        status_breakdown: dict[str, int] = {}
        scores: list[float] = []

        for r in rules:
            res = self.judge_rule(r)
            status = res.get("status", "unknown")
            status_breakdown[status] = status_breakdown.get(status, 0) + 1
            score = res.get("score")
            entry = {
                "rule_id": str(r.get("rule_id") or ""),
                "score": score,
                "status": status,
                "rationale": res.get("rationale", ""),
                "dim_scores": res.get("detail", {}).get("dim_scores", {}),
            }
            per_rule.append(entry)
            if isinstance(score, (int, float)):
                scores.append(float(score))

        n_total = len(rules)
        n_judged = status_breakdown.get("ok", 0)

        if n_total == 0:
            overall_status = "unavailable"
        elif n_judged == 0:
            # 全失败 — 若全是 unavailable 则 unavailable, 否则 partial (含 error)
            if status_breakdown.get("unavailable", 0) == n_total:
                overall_status = "unavailable"
            else:
                overall_status = "partial"
        elif n_judged == n_total:
            overall_status = "ok"
        else:
            overall_status = "partial"

        mean_score = sum(scores) / len(scores) if scores else None

        return {
            "mean_score": round(mean_score, 3) if mean_score is not None else None,
            "n_total": n_total,
            "n_judged": n_judged,
            "status_breakdown": status_breakdown,
            "per_rule": per_rule,
            "overall_status": overall_status,
        }


# ---------------------------------------------------------------------------
# 模块级便捷入口 · adapter 一行调用
# ---------------------------------------------------------------------------


def compute_rule_interpretability(
    rules: list[dict[str, Any]],
    judge: RuleInterpretabilityJudge | None = None,
) -> tuple[float | None, dict[str, Any]]:
    """对 rules 跑 RuleInterpretabilityJudge · 返回 (mean_score, meta).

    Failure 不抛异常 · adapter 直接消费.

    Returns:
        (mean_score, meta) ·
            mean_score ∈ [1.0, 5.0] · 全部失败或 unavailable → None
            meta = {n_total, n_judged, overall_status, status_breakdown,
                    per_rule_summary, judge_version, dimensions}
    """
    if judge is None:
        try:
            judge = RuleInterpretabilityJudge()
        except (RuntimeError, ValueError, TypeError, OSError) as e:
            return None, {
                "overall_status": "unavailable",
                "n_total": len(rules),
                "n_judged": 0,
                "reason": f"judge init failed: {type(e).__name__}: {e}",
                "judge_version": JUDGE_VERSION,
                "dimensions": list(INTERP_DIMENSIONS),
            }

    if not rules:
        return None, {
            "overall_status": "unavailable",
            "n_total": 0,
            "n_judged": 0,
            "reason": "empty ruleset",
            "judge_version": JUDGE_VERSION,
            "dimensions": list(INTERP_DIMENSIONS),
        }

    if not judge.is_available():
        return None, {
            "overall_status": "unavailable",
            "n_total": len(rules),
            "n_judged": 0,
            "reason": "DEEPSEEK_API_KEY missing (env unset)",
            "judge_version": JUDGE_VERSION,
            "dimensions": list(INTERP_DIMENSIONS),
        }

    result = judge.judge_ruleset(rules)
    per_rule_summary = [
        {
            "rule_id": e["rule_id"],
            "score": e["score"],
            "status": e["status"],
        }
        for e in result["per_rule"]
    ]
    meta = {
        "overall_status": result["overall_status"],
        "n_total": result["n_total"],
        "n_judged": result["n_judged"],
        "status_breakdown": result["status_breakdown"],
        "per_rule_summary": per_rule_summary,
        "judge_version": JUDGE_VERSION,
        "dimensions": list(INTERP_DIMENSIONS),
    }
    return result["mean_score"], meta


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.+?)\s*```", re.DOTALL)


def _strip_json(raw: str) -> dict[str, Any]:
    """从 LLM 输出中抽 JSON · 容忍 ```json``` 围栏 + 周围说明文字."""
    if not isinstance(raw, str):
        raise ValueError(f"raw not str: {type(raw)}")
    text = raw.strip()
    m = _JSON_FENCE_RE.search(text)
    if m:
        text = m.group(1)
    # 找首个 { 与最后 }
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"no JSON object found in: {raw[:200]}")
    obj_text = text[start : end + 1]
    return json.loads(obj_text)
