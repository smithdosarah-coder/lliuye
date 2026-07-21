# -*- coding: utf-8 -*-
"""Agent5 合规巡检雷达 v2.0 — ComplianceRadarAgent

流程（对 client 原话："矩阵扫描，不是一对一"）：
  KB 装载 → rule_set_builder → event_extractor → matrix_matcher → ledger_exporter

关键设计：
  - 预置场景与自定义上传使用同一真实硬规则路径
  - 需要更深判定时可启用 LLM 兜底（默认关闭以控制时长）
  - 与旧 ComplianceAgent（v1.0）并存：旧名被重定向到雷达版
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Generator

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.base_agent import BaseAgent
from shared.kb_scan.models import RuleItem

from .knowledge_base import ComplianceKnowledgeBase
from .rule_set_builder import RuleSetBuilder
from .event_extractor import EventExtractor
from .matrix_matcher import (
    MatrixMatcher, ComplianceLedger,
)
from .ledger_exporter import export_ledger_excel, export_remediation_word


SCENARIO_ROOT = PROJECT_ROOT / "demo_data" / "agent_compliance" / "scenarios"


class ComplianceRadarAgent(BaseAgent):
    """合规巡检雷达 — 矩阵扫描编排器。"""

    agent_name = "compliance_radar"
    agent_title = "合规巡检雷达"

    # 最近一次运行的 Ledger / rules / events，供 UI 查询详情
    last_ledger: ComplianceLedger | None = None
    last_rules: list[RuleItem] = []
    last_events: list[dict] = []
    last_kb: ComplianceKnowledgeBase | None = None
    last_scenario_title: str = "合规巡检"

    # ------------------------------------------------------------------

    def process_message(
        self,
        user_message: str,
        uploaded_files: list[str] | None = None,
        scenario_id: str | None = None,
    ) -> Generator[dict, None, None]:
        # 从 user_message 中识别是否为场景触发
        scenario_id = scenario_id or self._parse_scenario_id(user_message)

        try:
            if scenario_id:
                yield from self._run_scenario(scenario_id)
            elif uploaded_files:
                yield from self._run_custom(uploaded_files)
            else:
                yield self._message(
                    "请选择预置场景（推荐：互联网贷款合规）或上传：监管政策 + 内部制度 + 业务数据 三类文件。"
                )
                yield self._done("等待输入")
        except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError) as e:
            yield self._message(f"❌ 执行异常：{type(e).__name__}: {e}")
            yield self._done("异常终止")

    # ==================================================================
    # 场景模式
    # ==================================================================

    def _run_scenario(self, scenario_id: str) -> Generator[dict, None, None]:
        t_all = time.time()
        meta_path = SCENARIO_ROOT / scenario_id / "scenario.json"
        if not meta_path.exists():
            yield self._message(f"❌ 场景不存在：{scenario_id}")
            yield self._done("场景不存在")
            return
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        self.last_scenario_title = meta.get("title", scenario_id)

        # 阶段 0：KB 装载
        yield self._thinking("装载知识库（3 类：监管政策 / 内部制度 / 业务数据）...")
        yield self._tool_call("kb_load")
        kb = ComplianceKnowledgeBase.from_scenario(scenario_id)
        self.last_kb = kb
        kb_summary = kb.summary()
        yield self._tool_result("kb_load", kb_summary)
        yield self._message(f"✅ KB 装载完成：{kb_summary}")

        # 阶段 1：规则抽取
        yield self._thinking("从政策与内部制度抽取规则集...")
        yield self._tool_call("rule_extract")
        rules = RuleSetBuilder().build(kb)
        self.last_rules = rules
        yield self._tool_result("rule_extract", f"{len(rules)} 条规则")
        yield self._message(
            f"📜 阶段 1 完成：抽出 **{len(rules)} 条规则**（含 "
            f"{sum(1 for r in rules if r.source_doc.endswith('online_loan.md'))} 政策1 + "
            f"{sum(1 for r in rules if 'supplement' in r.source_doc)} 政策2 + "
            f"{sum(1 for r in rules if 'internal' in r.source_doc)} 本行制度）"
        )

        # 阶段 2：事件抽取
        yield self._thinking("从业务 Excel 抽取事件集...")
        yield self._tool_call("event_extract")
        events = EventExtractor().extract(kb)
        self.last_events = events
        from collections import Counter
        by_type = Counter(e["event_type"] for e in events)
        yield self._tool_result("event_extract", f"{len(events)} 条事件 "
                                                  f"(loan={by_type.get('loan',0)} "
                                                  f"coop={by_type.get('cooperation',0)} "
                                                  f"model={by_type.get('model',0)})")
        yield self._message(
            f"📋 阶段 2 完成：抽出 **{len(events)} 条事件**（放款 {by_type.get('loan',0)} + "
            f"合作 {by_type.get('cooperation',0)} + 模型 {by_type.get('model',0)}）"
        )

        # 阶段 3：矩阵比对
        total_cells = len(rules) * len(events)
        yield self._thinking(f"矩阵比对：{len(rules)} × {len(events)} = {total_cells} 单元")
        yield self._tool_call("matrix_match")

        # 进度回调：每推进 10% 发一条消息
        progress_state = {"last": 0}
        def _progress(done, total):
            pct = int(done * 100 / max(1, total))
            if pct - progress_state["last"] >= 10 or done == total:
                progress_state["last"] = pct

        matcher = MatrixMatcher(use_llm=False)
        t0 = time.time()
        ledger = matcher.match(rules, events, progress_cb=_progress)
        t1 = time.time()

        self.last_ledger = ledger

        yield self._tool_result(
            "matrix_match",
            f"扫完 {total_cells} 单元 / {t1-t0:.1f}s | "
            f"🔴 {len(ledger.severe)}  🟡 {len(ledger.normal)}  🟢 {len(ledger.observation)}"
        )
        yield self._message(
            f"🎯 阶段 3 完成：矩阵比对 **{total_cells}** 单元，"
            f"用时 **{t1-t0:.1f}s**\n\n"
            f"违规榜单：🔴 **{len(ledger.severe)}** 严重 · "
            f"🟡 **{len(ledger.normal)}** 一般 · "
            f"🟢 **{len(ledger.observation)}** 观察"
        )

        # 违规详情摘要
        yield self._message(self._format_top_violations(ledger))

        # 阶段 4：导出
        yield self._thinking("导出违规榜单 Excel + 整改报告 Word...")
        try:
            xlsx_path = export_ledger_excel(
                ledger, rules, events,
                output_dir=str(PROJECT_ROOT / "outputs"),
                scenario_title=self.last_scenario_title,
            )
            yield self._file(xlsx_path)
            docx_path = export_remediation_word(
                ledger,
                output_dir=str(PROJECT_ROOT / "outputs"),
                scenario_title=self.last_scenario_title,
                kb_summary=kb_summary,
            )
            yield self._file(docx_path)
            yield self._message(
                f"📦 已导出：\n- 榜单 Excel：`{Path(xlsx_path).name}`\n"
                f"- 整改报告 Word：`{Path(docx_path).name}`"
            )
        except (OSError, RuntimeError, ValueError, TypeError, AttributeError, KeyError, ImportError) as e:
            yield self._message(f"⚠️ 导出异常：{e}")

        yield self._done(f"巡检完成（总用时 {time.time()-t_all:.1f}s）")

    # ==================================================================
    # 自定义上传模式（无场景）
    # ==================================================================

    def _run_custom(self, uploaded_files: list[str]) -> Generator[dict, None, None]:
        # 简单按文件名前缀分类
        policy_files, internal_files, business_files = [], [], []
        for f in uploaded_files:
            name = os.path.basename(f).lower()
            if any(k in name for k in ["internal", "本行", "制度", "规程"]):
                internal_files.append(f)
            elif any(k in name for k in ["政策", "办法", "通知", "policy", "law", "regulation"]):
                policy_files.append(f)
            elif any(k in name for k in [".xlsx", ".xls", ".csv", "台账", "放款", "合作", "模型"]):
                business_files.append(f)
            else:
                # 未识别默认扔到 policy
                policy_files.append(f)

        yield self._thinking(
            f"文件分类：政策 {len(policy_files)} / 内部 {len(internal_files)} / 业务 {len(business_files)}"
        )

        kb = ComplianceKnowledgeBase.from_uploads(
            policy_files=policy_files,
            internal_files=internal_files,
            business_files=business_files,
        )
        self.last_kb = kb
        yield self._message(f"✅ KB 装载：{kb.summary()}")

        rules = RuleSetBuilder().build(kb)
        self.last_rules = rules
        yield self._message(f"📜 规则抽取：{len(rules)} 条")

        events = EventExtractor().extract(kb)
        self.last_events = events
        yield self._message(f"📋 事件抽取：{len(events)} 条")

        ledger = MatrixMatcher(use_llm=False).match(rules, events)
        self.last_ledger = ledger
        yield self._message(
            f"🎯 矩阵比对：🔴 {len(ledger.severe)} 🟡 {len(ledger.normal)} 🟢 {len(ledger.observation)}"
        )
        try:
            xlsx_path = export_ledger_excel(
                ledger, rules, events,
                output_dir=str(PROJECT_ROOT / "outputs"),
            )
            yield self._file(xlsx_path)
        except (OSError, RuntimeError, ValueError, TypeError, AttributeError, KeyError, ImportError) as e:
            yield self._message(f"⚠️ 导出异常：{e}")
        yield self._done("自定义巡检完成")

    # ==================================================================
    # 工具方法
    # ==================================================================

    def scan_external_policies(self, query: str = "", limit: int = 10) -> list[dict]:
        """主动扫描外部政策源（事件驱动入口；与 process_message 解耦）。"""
        from .policy_scanner import scan_latest_policies
        return scan_latest_policies(query, limit, llm_fn=self.llm)

    def _parse_scenario_id(self, msg: str) -> str | None:
        if not msg:
            return None
        low = msg.lower()
        if "internet_loan" in low or "互联网贷款" in msg:
            return "internet_loan"
        return None

    # ---- Markdown 摘要 ----

    def _format_top_violations(self, ledger: ComplianceLedger) -> str:
        lines = ["\n### 🔴 严重违规明细"]
        for v in ledger.severe:
            eids = ", ".join(e["event_id"] for e in v.events[:5])
            lines.append(
                f"- **{v.violation_id}** {v.rule.title}  "
                f"({v.rule.source_doc}·{v.rule.source_page})"
            )
            lines.append(f"  - 涉及：{eids}")
            lines.append(f"  - 原因：{v.match_reason}")
        return "\n".join(lines)


# ----------------------------------------------------------------------
# 兼容旧名：ComplianceAgent → ComplianceRadarAgent
# ----------------------------------------------------------------------

class ComplianceAgent(ComplianceRadarAgent):
    agent_name = "compliance"
    agent_title = "合规巡检（Radar v2.0）"
