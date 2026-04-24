# -*- coding: utf-8 -*-
"""placeholder_guard — 跨 Agent 占位符 QC 闸门 (CLAUDE.md §8 第 1 条)

5 个非 Agent6 智能体（channel / credit / alert / compliance / riskctrl）
最终输出前 call ``scan(text)``。命中即阻断: 调用 ``assert_clean()`` 抛
``PlaceholderViolation``, 或调用 ``mark_unfilled()`` 把残留替换为显式的
"未能自动填写" 标记 (符合 CLAUDE.md "字段填不了就标未能自动填写" 红线)。

设计原则:
- 治本不治标: 用规则化的 *残留模式* 而非业务关键词黑名单。模板/工程占位符
  是有限规则（``[待补充]`` / ``{{name}}`` / ``<占位>`` / ``…`` 等），不依赖
  对具体业务实体名的硬编。
- 容忍假阳低、假阴零: 闸门是 *阻断* 而非 *分析*; 宁可严格也不漏过未填字段。
- 与 ``quality_scorer.py:936-942`` 现有占位符正则保持兼容超集; quality_scorer
  内部检查只读, 不改。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


# ---------------------------------------------------------------------------
# 占位符模式集 (有限闭集, 工程化标记 + 模板未渲染 + 省略号)
# ---------------------------------------------------------------------------

# 注意: 使用命名捕获是为了在多模式联合 finditer 时拿到 hit 来源类型。
_PATTERNS: tuple[tuple[str, str], ...] = (
    # 1) 中括号占位 — [待补充] [待确认] [TBD] [TODO] [占位] [待填] [N/A] [pending]
    ("bracket_zh", r"\[\s*(?:待补充|待确认|待填写|待填|占位|TBD|TODO|tbd|todo|N/A|pending|Pending)\s*\]"),
    # 2) Mustache / Jinja-style 双花括号 {{name}} {{ company }} {{any.path}} 等
    ("mustache", r"\{\{[^{}]{1,80}\}\}"),
    # 3) Python f-string 残留 {variable} (单层, 不与 JSON 混淆: 要求名字纯标识符)
    #    收紧到 *单词标识符* 减少误伤 JSON 体: {company_name} {amount}
    ("fstring", r"(?<![a-zA-Z0-9_]){[A-Za-z_][A-Za-z0-9_\.]{0,40}}"),
    # 4) 尖括号占位 <占位> <name> <amount> <未填>
    ("angle_zh", r"<\s*(?:占位|待补充|待确认|未填|未知|N/A|TBD|TODO)\s*>"),
    # 5) 中文省略号 / 英文省略号 — 三点以上视为残留
    ("ellipsis", r"(?<![\.])(?:…{1,}|\.{3,})"),
    # 6) 中文未填 — "暂无" / "未提供" / "待补充" 紧跟冒号/句号/换行的孤立短语
    #    分隔符同时容忍中英文 (中文 ，。；：、 / 英文 ,.;: / 换行)
    ("zh_unfilled", r"(?:^|[，。；：、,\.;:\n\r])\s*(?:暂无|未提供|待补充|待确认|信息不全)\s*(?=[，。；：、,\.;:\n\r]|$)"),
    # 7) markdown table 内空格仅占位 ` |  | ` 三连空 cell
    ("md_empty_cell", r"\|\s*\|\s*\|\s*\|"),
)

_COMPILED = [(name, re.compile(p, re.MULTILINE)) for name, p in _PATTERNS]

UNFILLED_MARKER = "未能自动填写"


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PlaceholderHit:
    """一处占位符命中。"""
    kind: str
    snippet: str
    span: tuple[int, int]

    def __str__(self) -> str:
        return f"[{self.kind}] {self.snippet!r} @ {self.span[0]}-{self.span[1]}"


class PlaceholderViolation(RuntimeError):
    """``assert_clean`` 命中时抛出。``hits`` 暴露所有 hit 给上游做日志/降级。"""

    def __init__(self, agent: str, hits: list[PlaceholderHit]):
        self.agent = agent
        self.hits = hits
        msg = (
            f"[QC blocker · {agent}] 输出含 {len(hits)} 处占位符残留, 已阻断:\n  "
            + "\n  ".join(str(h) for h in hits[:8])
        )
        super().__init__(msg)


# ---------------------------------------------------------------------------
# 公共 API
# ---------------------------------------------------------------------------

def scan(text: str) -> list[PlaceholderHit]:
    """扫描文本, 返回所有占位符命中。空字符串/None 返回空列表。"""
    if not text:
        return []
    if not isinstance(text, str):
        text = str(text)

    hits: list[PlaceholderHit] = []
    for kind, regex in _COMPILED:
        for m in regex.finditer(text):
            snippet = m.group(0)
            # zh_unfilled 模式头部可能含分隔符, strip 后展示
            hits.append(PlaceholderHit(
                kind=kind,
                snippet=snippet.strip(),
                span=(m.start(), m.end()),
            ))
    # 按位置排序便于上游定位
    hits.sort(key=lambda h: h.span[0])
    return hits


def is_clean(text: str) -> bool:
    """便捷布尔判断, 等价于 ``not scan(text)``。"""
    return not scan(text)


def assert_clean(text: str, *, agent: str) -> None:
    """命中即抛 ``PlaceholderViolation``。Agent api.py / output validator 在
    最终对外发响应前调用本函数, 让 QC blocker 阻断而非"安静放过"。"""
    hits = scan(text)
    if hits:
        raise PlaceholderViolation(agent=agent, hits=hits)


def mark_unfilled(text: str) -> str:
    """把所有占位符段替换为 ``未能自动填写`` 标记 (软降级模式)。

    适用于 *streaming partial chunk* 场景: 阻断会牺牲已经可用的合法段, 用
    本函数把残留位置可见化更友好。CLAUDE.md "字段填不了就标未能自动填写"
    红线就是这个语义。
    """
    if not text:
        return text or ""
    out = text
    # 反向替换以保 span 稳定 — 但对不同 kind 拼出统一 marker
    hits = scan(text)
    for hit in reversed(hits):
        s, e = hit.span
        out = out[:s] + UNFILLED_MARKER + out[e:]
    return out


def hits_to_summary(hits: Iterable[PlaceholderHit]) -> str:
    """供日志/UI 摘要"""
    pairs = [(h.kind, h.snippet) for h in hits]
    if not pairs:
        return "OK · no placeholder"
    return "; ".join(f"{k}:{s}" for k, s in pairs[:8])
