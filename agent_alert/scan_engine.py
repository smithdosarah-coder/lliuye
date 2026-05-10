# -*- coding: utf-8 -*-
"""Agent4 Alert · Scan engine wrappers (Stage C · onboarding W-C3-A3).

新增 thin layer · 在 AlertRadarAgent 之上：
1. **Tavily 401 fallback** (Q-040 提) — 默认走 MockSearchProvider · 显式开
   `ALERT_USE_TAVILY=1` 才尝试 Web · 任何异常 (401 / NotImplementedError /
   network) 自动降级 mock · payload 标 mode
2. **持久化** — scan 结果存 `data/alert/sessions/{session_id}.json` ·
   写 `data/alert/latest.json` 指向最新
3. **drill detail** — 按 client_id 单查 + LLM 处置建议（含模板兜底）

不破坏既有：AlertRadarAgent / CustomerScanner / CrossMatcher / 内部规则全保留。
"""
from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALERT_DATA_DIR = PROJECT_ROOT / "data" / "alert"
SESSIONS_DIR = ALERT_DATA_DIR / "sessions"
LATEST_POINTER = ALERT_DATA_DIR / "latest.json"


# ---------------------------------------------------------------------------
# Tavily 401 fallback provider builder
# ---------------------------------------------------------------------------


def build_alert_provider(*, force_mock: bool = False) -> tuple[Any, str]:
    """构建 Agent4 用的 SearchProvider · 含 Tavily 401 fallback.

    ALL IN Phase B.2 (PM 2026-05-10 真意 reframe):
    "结果不能 mock" · MockSearchProvider 返合成数据 · silent fallback 路径已切
    NullSearchProvider (全方法返 []) · CrossMatcher 外部路径 0 hit · 仅内部规则真跑.
    用户必通过 banner 看见 trust model 降级 · 不假装"还有数据".

    Returns:
        (provider, mode_label) where mode_label ∈ {
          "demo_forced":         force_mock=True · 用户显式 (仅 Mock · 测试用)
          "tavily_disabled":     ALERT_USE_TAVILY=0 · 显式禁外搜 · Null
          "tavily_key_missing":  TAVILY_API_KEY 缺 · 主路径不可用 · Null
          "web_fallback_<Err>":  Tavily build 抛 · 主路径 fail · Null
          "web_live":            Tavily 真接通 · 生产场景 · 真 web
        }

    设计 (B.2 reframe):
      - force_mock=True (显式 demo testing): 用 MockSearchProvider · 历史路径 (低风险用例)
      - 其他 fallback 路径: NullSearchProvider · 不返合成结果 · 内部规则独跑
      - web_live: 真 Tavily · 与生产同
    """
    from shared.kb_scan.search_provider import build_search_provider

    from agent_alert.null_search_provider import NullSearchProvider

    if force_mock:
        # 仅显式 force_mock=True 走老 MockSearchProvider (e.g. CI smoke test ·
        # 客户走访演示双保险) · production demo 路径不会传 force_mock=True.
        return build_search_provider(demo_mode=True), "demo_forced"

    # ALL IN Phase B step 3 (2026-05-09): 默认 ALERT_USE_TAVILY=1 · 真接 Tavily
    use_web = os.environ.get("ALERT_USE_TAVILY", "1").strip() in {"1", "true", "yes"}
    if not use_web:
        # B.2 reframe: 不再 silent fallback to MockSearchProvider · 改 Null · banner 强 warn
        return NullSearchProvider(), "tavily_disabled"

    tavily_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not tavily_key:
        # B.2 reframe: 不再 silent mock · 改 Null · 内部规则真跑 · banner 强 warn
        return NullSearchProvider(), "tavily_key_missing"

    try:
        web = build_search_provider(demo_mode=False, api_keys={"tavily": tavily_key})
    except (RuntimeError, ValueError, ImportError, OSError, AttributeError) as e:
        # B.2 reframe: 不再 silent mock · 改 Null · banner 强 error
        return NullSearchProvider(), f"web_fallback_{type(e).__name__}"

    # 真 web 路径 · 不预 smoke (省成本) · 调用方使用时再 try/except
    return web, "web_live"


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _ensure_dirs() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def persist_hitlist(
    hit_list,
    dispositions: dict[str, dict],
    *,
    session_id: str = "",
    mode_label: str = "",
    scenario_key: str = "",
) -> str:
    """把 HitList + dispositions 序列化 → `data/alert/sessions/{session_id}.json`.

    返回 session_id。
    """
    _ensure_dirs()
    sid = (session_id or "").strip() or f"alert-{uuid.uuid4().hex[:12]}"

    payload: dict[str, Any] = {
        "session_id": sid,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "scenario_key": scenario_key,
        "mode": mode_label,
        "hit_list": hit_list.model_dump(mode="json") if hasattr(hit_list, "model_dump") else dict(hit_list),
        "dispositions": dispositions,
    }

    out_path = SESSIONS_DIR / f"{sid}.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 跨 drive (Windows tmp_path 在 C:, project 在 D:) relative_to 会抛 ·
    # 退化用 os.path.relpath / 实在不行存 abs path
    try:
        rel_path = str(out_path.relative_to(PROJECT_ROOT))
    except ValueError:
        try:
            rel_path = os.path.relpath(out_path, PROJECT_ROOT)
        except ValueError:
            rel_path = str(out_path)

    LATEST_POINTER.write_text(
        json.dumps({"session_id": sid, "path": rel_path}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return sid


class HitListNotFoundError(FileNotFoundError):
    """session_id 对应的 hitlist 文件不存在."""


def load_hitlist(session_id: str = "") -> dict[str, Any]:
    """加载持久化的 hitlist (session_id 留空 = latest).

    返回 raw dict (含 session_id / generated_at / mode / hit_list / dispositions)。
    """
    if session_id:
        path = SESSIONS_DIR / f"{session_id}.json"
        if not path.is_file():
            raise HitListNotFoundError(f"session_id={session_id} not found at {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    if not LATEST_POINTER.is_file():
        raise HitListNotFoundError(
            "尚无任何扫描记录 · 先调 POST /api/alert/scan 生成 session"
        )
    pointer = json.loads(LATEST_POINTER.read_text(encoding="utf-8"))
    return load_hitlist(pointer["session_id"])


# ---------------------------------------------------------------------------
# Drill detail
# ---------------------------------------------------------------------------


class ClientNotFoundError(KeyError):
    """drill 的 client_id 在 hitlist 里找不到."""


def find_hit_by_client_id(payload: dict, client_id: str) -> dict:
    """从 persisted payload 找单客户 hit dict.

    匹配优先级:
      1. hit_id == client_id
      2. target.target_id == client_id
      3. target.payload.company_name == client_id
    """
    hits = (payload.get("hit_list") or {}).get("hits") or []
    for h in hits:
        if h.get("hit_id") == client_id:
            return h
        target = h.get("target") or {}
        if target.get("target_id") == client_id:
            return h
        if (target.get("payload") or {}).get("company_name") == client_id:
            return h
    raise ClientNotFoundError(f"client_id={client_id} not in current hitlist")


def build_drill_payload(
    payload: dict,
    client_id: str,
    *,
    llm_caller=None,
) -> dict:
    """单客户 drill detail · 含信号 timeline + 处置建议 (LLM 优先 · 模板兜底).

    Args:
        payload: persisted hitlist payload (load_hitlist 产出)
        client_id: 见 find_hit_by_client_id 匹配规则
        llm_caller: 可选 (system, user) -> str · 优先调 LLM
    """
    hit = find_hit_by_client_id(payload, client_id)
    company_name = (hit.get("target") or {}).get("payload", {}).get("company_name", client_id)

    # 信号 timeline (从 evidences 抽取 · 按 source 分组)
    timeline = []
    for ev in hit.get("evidences") or []:
        timeline.append({
            "source": ev.get("source", ""),
            "snippet": ev.get("snippet", ""),
            "url": ev.get("url", ""),
        })

    # 已存的 disposition 优先（scan 阶段批量算过）
    dispositions = payload.get("dispositions") or {}
    saved_plan = dispositions.get(company_name)
    if saved_plan:
        return {
            "client_id": client_id,
            "company_name": company_name,
            "level": hit.get("level"),
            "score": hit.get("score"),
            "matched_rules": hit.get("matched_rules", []),
            "reasons": hit.get("reasons", []),
            "signal_timeline": timeline,
            "disposition": saved_plan,
            "disposition_source": "saved",
        }

    # LLM 路径
    if llm_caller is not None:
        try:
            disposition_text = _llm_disposition(hit, llm_caller)
            return {
                "client_id": client_id,
                "company_name": company_name,
                "level": hit.get("level"),
                "score": hit.get("score"),
                "matched_rules": hit.get("matched_rules", []),
                "reasons": hit.get("reasons", []),
                "signal_timeline": timeline,
                "disposition": {"narrative": disposition_text},
                "disposition_source": "llm",
            }
        except (RuntimeError, ValueError, OSError, AttributeError):
            pass  # 回退模板

    return {
        "client_id": client_id,
        "company_name": company_name,
        "level": hit.get("level"),
        "score": hit.get("score"),
        "matched_rules": hit.get("matched_rules", []),
        "reasons": hit.get("reasons", []),
        "signal_timeline": timeline,
        "disposition": _template_disposition(hit),
        "disposition_source": "template",
    }


def _llm_disposition(hit: dict, llm_caller) -> str:
    """调 LLM 为单客户生成处置建议（自然语言 · 80-150 字）."""
    company_name = (hit.get("target") or {}).get("payload", {}).get("company_name", "目标客户")
    level = hit.get("level", "yellow")
    reasons = hit.get("reasons", [])
    evidences = hit.get("evidences", [])

    from shared.prompts.agent_helpers import build_alert_ssot_prompt

    system = build_alert_ssot_prompt(
        task_type="disposition",
        schema_hint=(
            "处置建议自然语言 80-150 字 · 必含'立即/一周内/持续关注'分级 + 责任方 + 时限 · "
            "禁编造数字 · 必引用输入的命中规则与证据"
        ),
    )
    user = (
        f"【客户】{company_name}\n"
        f"【风险等级】{level}\n"
        f"【命中规则与原因】\n"
        + "\n".join(f"- {r}" for r in reasons[:6])
        + "\n【证据摘录】\n"
        + "\n".join(f"- {ev.get('source','')}: {ev.get('snippet','')[:120]}"
                    for ev in evidences[:4])
        + "\n\n请给出处置建议（80-150 字 · 含具体行动 + 责任方 + 时限）："
    )
    return llm_caller(system, user) or ""


def _template_disposition(hit: dict) -> dict:
    """模板兜底 · 不调 LLM · 按 level 走 disposition.py 模板（简化版）."""
    level = (hit.get("level") or "").lower()
    company_name = (hit.get("target") or {}).get("payload", {}).get("company_name", "")

    if level == "red":
        return {
            "company_name": company_name,
            "actions": [
                {"action_type": "现场核查", "urgency": "立即",
                 "description": "客户经理 48h 内现场核查经营状况 + 银行流水核验",
                 "responsible": "客户经理"},
                {"action_type": "风险上报", "urgency": "立即",
                 "description": "向分行风险管理部提交预警报告 · 启动处置预案",
                 "responsible": "分行风险管理部"},
                {"action_type": "授信审视", "urgency": "立即",
                 "description": "评估是否压缩额度 / 追加担保 / 提前收回部分贷款",
                 "responsible": "风险管理部"},
            ],
            "follow_up_date": "",
            "notes": "红灯客户 · 模板兜底",
        }
    if level == "yellow":
        return {
            "company_name": company_name,
            "actions": [
                {"action_type": "财务跟踪", "urgency": "一周内",
                 "description": "要求企业提供月度财务快报 · 关注现金流",
                 "responsible": "客户经理"},
                {"action_type": "舆情监控", "urgency": "持续关注",
                 "description": "持续关注涉诉/舆情动态 · 触达即上报",
                 "responsible": "风险管理部"},
            ],
            "follow_up_date": "",
            "notes": "黄灯客户 · 模板兜底",
        }
    return {
        "company_name": company_name,
        "actions": [{"action_type": "常规跟踪", "urgency": "持续关注",
                     "description": "无明显异常 · 维持季度复查频率",
                     "responsible": "客户经理"}],
        "follow_up_date": "",
        "notes": "绿灯客户 · 模板兜底",
    }


# ---------------------------------------------------------------------------
# 高层封装：跑 scan + 持久化（供 SSE endpoint 调用）
# ---------------------------------------------------------------------------


def run_scan_and_persist(
    *,
    scenario_key: str = "",
    uploaded_files: list[str] | None = None,
    api_key: str = "dummy",
    provider: str = "deepseek",
    force_mock: bool = False,
) -> Generator[dict, None, str]:
    """跑一次完整 scan · 流式 yield 事件 · 完成后持久化 · 返 session_id.

    与原 AlertRadarAgent.process_message 不同：本函数提供 fallback provider 切换 +
    持久化 + 返 session_id 给上层 endpoint，事件流 schema 保持向后兼容。
    """
    from agent_alert.agent import AlertRadarAgent
    from shared.kb_scan.models import RiskLevel

    search_provider, mode_label = build_alert_provider(force_mock=force_mock)
    yield {"type": "tool_result", "tool": "search_provider",
           "result": f"provider={search_provider.provider_name} · mode={mode_label}"}

    agent = AlertRadarAgent(api_key=api_key, model_provider=provider)

    # patch agent's provider builder · 不动原 agent.py 代码
    original_build = None
    try:
        from shared.kb_scan import search_provider as sp_mod
        original_build = sp_mod.build_search_provider

        def _patched_build(demo_mode=None, **kwargs):  # noqa: ARG001
            return search_provider
        sp_mod.build_search_provider = _patched_build

        for evt in agent.process_message(
            user_message=scenario_key, uploaded_files=uploaded_files,
        ):
            yield evt
    finally:
        if original_build is not None:
            from shared.kb_scan import search_provider as sp_mod
            sp_mod.build_search_provider = original_build

    # 持久化（即使 hitlist 为 None 也保留 mode 痕迹）
    hit_list = agent.last_hitlist
    if hit_list is None:
        return ""

    dispositions_json: dict[str, dict] = {}
    for name, plan in (agent.last_dispositions or {}).items():
        dispositions_json[name] = (
            plan.model_dump(mode="json") if hasattr(plan, "model_dump") else dict(plan)
        )

    sid = persist_hitlist(
        hit_list, dispositions_json,
        mode_label=mode_label, scenario_key=scenario_key,
    )
    yield {"type": "session", "session_id": sid, "mode": mode_label}
    return sid
