# -*- coding: utf-8 -*-
"""Agent4 贷中风险预警雷达 — 批量扫描编排器（v2.0）

核心流程：
    1. 装载知识库（在贷客户 + 预警规则 + 内部制度）
    2. 调用 CustomerScanner 遍历全池，对每家客户做双路（外部/内部）交叉命中
    3. 通过 yield 事件流把「进度 tick / 命中 tick / 完成汇总」实时推给前端
    4. 对红/黄灯客户批量生成 DispositionPlan（复用 disposition.py 模板）
    5. 最终产出 HitList（可导出 Excel）

保留模块：
    - alert_engine.py: 单客户 22 规则打分内核（供 CrossMatcher 做外部信号补充）
    - disposition.py:  处置模板（批量调用时对每个红/黄客户复用）
    - trend_analyzer.py: 财务趋势（Demo 阶段不主动调用，保留供单客户深度详情）
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, Generator

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.base_agent import BaseAgent
from shared.kb_scan.models import HitItem, HitList, RiskLevel
from shared.kb_scan.search_provider import build_search_provider

from .knowledge_base import AlertKnowledgeBase, DEFAULT_SCENARIO_DIR
from .customer_scanner import CustomerScanner, ScanProgress
from .cross_matcher import CrossMatcher
from .alert_engine import AlertReport, AlertSignal
from .disposition import generate_disposition, DispositionPlan
from .ledger_exporter import export_ledger_excel


class AlertRadarAgent(BaseAgent):
    """贷中风险预警雷达 Agent（v2.0）。"""

    agent_name = "alert_radar"
    agent_title = "贷中风险预警雷达"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 每次请求独立状态
        self.last_hitlist: HitList | None = None
        self.last_dispositions: dict[str, DispositionPlan] = {}

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------
    def process_message(
        self,
        user_message: str = "",
        uploaded_files: list[str] | None = None,
    ) -> Generator[dict, None, None]:
        """执行一次批量扫描。

        Args:
            user_message: 场景名（如 'micro_credit_100'）或自由文本
            uploaded_files: 可选；包含客户名录 / 规则 JSON / 制度 Word
        """
        yield self._thinking("装载贷中预警知识库（客户名录 · 规则库 · 管理制度）...")

        # ---- 1. 装载 KB ----
        kb = self._load_kb(uploaded_files, user_message)
        if kb is None or not kb.companies:
            yield self._message("❌ 未找到在贷客户名录。请上传客户名录 Excel 或选择预置场景。")
            yield self._done("需要更多输入")
            return

        yield self._tool_result("load_kb", kb.summary())

        # ---- 2. 构造 SearchProvider（禁止 isinstance）----
        yield self._thinking("初始化搜索数据源（MockSearchProvider 走 demo_data/mock_pool/）...")
        provider = build_search_provider(demo_mode=True)
        yield self._tool_result(
            "search_provider",
            f"provider={provider.provider_name} 就绪",
        )

        # ---- 3. 启动批量扫描 ----
        yield self._thinking(
            f"开始批量扫描 {len(kb.companies)} 家在贷客户（双路交叉命中）..."
        )
        scanner = CustomerScanner(kb=kb, search_provider=provider,
                                  matcher=CrossMatcher(provider))

        hit_list: HitList | None = None
        all_hits: list[HitItem] = []
        scan_gen = scanner.scan()
        try:
            while True:
                evt = next(scan_gen)
                mapped = self._map_progress_event(evt)
                if mapped is not None:
                    yield mapped
                if evt.kind == "hit" and evt.hit is not None:
                    all_hits.append(evt.hit)
        except StopIteration as stop:
            hit_list = stop.value
        if hit_list is None:
            # 兜底（极少数 StopIteration 不带 value 的边界情况）
            hit_list = scanner._build_hitlist(all_hits)

        # ---- 4. 批量处置建议（仅红/黄）----
        yield self._thinking("为红/黄灯客户批量生成处置建议...")
        dispositions: dict[str, DispositionPlan] = {}
        for h in hit_list.hits:
            if h.level not in (RiskLevel.RED, RiskLevel.YELLOW):
                continue
            report = self._hit_to_alert_report(h)
            try:
                plan = generate_disposition(report)
                dispositions[h.target.payload.get("company_name", "")] = plan
            except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError):
                continue
        yield self._tool_result(
            "dispositions",
            f"已生成 {len(dispositions)} 家客户的处置建议",
        )

        # ---- 5. 汇总输出 ----
        self.last_hitlist = hit_list
        self.last_dispositions = dispositions
        summary = (
            f"✅ 扫描完成：共 {hit_list.total_scanned} 家 · "
            f"🔴 {hit_list.red_count}  🟡 {hit_list.yellow_count}  🟢 {hit_list.green_count}"
        )
        yield self._message(summary)
        yield {
            "type": "hitlist",
            "hitlist": hit_list,
            "dispositions": dispositions,
        }
        yield self._done(summary)

    # ------------------------------------------------------------------
    # 便捷：直接一次性得到 HitList + dispositions（不用事件流）
    # ------------------------------------------------------------------
    def scan_once(
        self,
        uploaded_files: list[str] | None = None,
        scenario_key: str = "",
    ) -> tuple[HitList, dict[str, DispositionPlan]]:
        """同步扫描，返回 (HitList, dispositions)。供批处理/测试调用。"""
        kb = self._load_kb(uploaded_files, scenario_key)
        if kb is None or not kb.companies:
            raise RuntimeError("知识库未能装载在贷客户名录")
        provider = build_search_provider(demo_mode=True)
        scanner = CustomerScanner(kb=kb, search_provider=provider,
                                  matcher=CrossMatcher(provider))
        hl = scanner.scan_all()
        dispositions: dict[str, DispositionPlan] = {}
        for h in hl.hits:
            if h.level in (RiskLevel.RED, RiskLevel.YELLOW):
                dispositions[h.target.payload.get("company_name", "")] = \
                    generate_disposition(self._hit_to_alert_report(h))
        self.last_hitlist = hl
        self.last_dispositions = dispositions
        return hl, dispositions

    # ------------------------------------------------------------------
    # 导出
    # ------------------------------------------------------------------
    def export_excel(self, output_dir: str = "outputs") -> str:
        if self.last_hitlist is None:
            raise RuntimeError("尚未完成扫描，无法导出")
        return export_ledger_excel(
            self.last_hitlist, self.last_dispositions, output_dir=output_dir,
        )

    # ------------------------------------------------------------------
    # 内部：KB 装载策略
    # ------------------------------------------------------------------
    def _load_kb(
        self,
        uploaded_files: list[str] | None,
        user_message: str = "",
    ) -> AlertKnowledgeBase | None:
        """KB 装载：
        - 若 uploaded_files 中包含客户名录/规则/制度，按类型分派
        - 否则走预置场景目录（demo_data/agent_alert）
        """
        if uploaded_files:
            customer_files, rule_files, policy_files = [], [], []
            for fp in uploaded_files:
                name = Path(fp).name.lower()
                if any(k in name for k in ["customer", "客户", "名录", ".xlsx", ".xls", ".csv"]):
                    customer_files.append(fp)
                elif any(k in name for k in ["rule", "规则", "预警"]) or name.endswith(".json"):
                    rule_files.append(fp)
                elif any(k in name for k in ["policy", "制度", "办法"]) or name.endswith(
                    (".md", ".docx", ".pdf", ".doc")):
                    policy_files.append(fp)
                else:
                    # 未识别的按客户名录兜底
                    customer_files.append(fp)
            kb = AlertKnowledgeBase.from_uploads(
                customer_files=customer_files,
                rule_files=rule_files,
                policy_files=policy_files,
            )
            # 若规则文件没上传，补充预置规则以保证命中表达完整
            if not kb.rules:
                default_rule = DEFAULT_SCENARIO_DIR / "warning_rules.json"
                if default_rule.exists():
                    kb.load_file(str(default_rule), doc_type="rule")
            return kb
        # 走预置场景
        return AlertKnowledgeBase.from_scenario()

    # ------------------------------------------------------------------
    # 进度事件 → BaseAgent 标准事件
    # ------------------------------------------------------------------
    def _map_progress_event(self, evt: ScanProgress) -> dict | None:
        if evt.kind == "start":
            return self._tool_call("scan_start")
        if evt.kind == "tick":
            return {
                "type": "scan_tick",
                "index": evt.index,
                "total": evt.total,
                "customer_name": evt.customer_name,
                "level": evt.level.value if evt.level else "",
            }
        if evt.kind == "hit":
            if evt.hit is None or evt.level in (None, RiskLevel.GREEN):
                return None
            return {
                "type": "scan_hit",
                "index": evt.index,
                "total": evt.total,
                "customer_name": evt.customer_name,
                "level": evt.level.value,
                "rules": evt.hit.matched_rules,
            }
        if evt.kind == "done":
            return self._tool_result("scan_done", evt.message)
        return None

    # ------------------------------------------------------------------
    # HitItem → AlertReport（供 disposition 模板消费）
    # ------------------------------------------------------------------
    @staticmethod
    def _hit_to_alert_report(hit: HitItem) -> AlertReport:
        payload = hit.target.payload
        signals: list[AlertSignal] = []
        # category 从规则 ID 前缀推断
        cat_by_prefix = {
            "FIN": "财务恶化", "LAW": "法律诉讼", "BIZ": "经营异常",
            "IND": "行业风险", "REL": "关联风险", "POL": "内部制度",
        }
        rule_titles = (hit.extras or {}).get("rule_titles", {})
        for i, rid in enumerate(hit.matched_rules):
            prefix = rid.split("-")[0]
            category = cat_by_prefix.get(prefix, "其他")
            # POL 类别复用"财务/经营/法律"模板取红/黄处置，使处置建议覆盖更完整
            if prefix == "POL":
                category = "经营异常"
            reason = hit.reasons[i] if i < len(hit.reasons) else ""
            signals.append(AlertSignal(
                signal_id=rid,
                category=category,
                level=hit.level.value,
                description=reason or rule_titles.get(rid, rid),
                evidence=reason,
            ))
        return AlertReport(
            company_name=payload.get("company_name", ""),
            overall_level=hit.level.value,
            signals=signals,
            summary=" · ".join(hit.reasons[:3]),
        )


# 向后兼容：保留旧名（portal 若有引用）
AlertMonitorAgent = AlertRadarAgent
