# -*- coding: utf-8 -*-
from types import SimpleNamespace

import v16_op_handlers as handlers
from shared.evidence.protocol import UNFILLED_MARKER
from v16_generator import Materials
from v16_step1_extract import Element


FORBIDDEN_FABRICATION = (
    "本企业",
    "成立多年",
    "详见证照",
    "符合本行准入",
    "详见补充材料",
)


def _element(text: str) -> Element:
    return Element(source="test", kind="para", location="P0", text=text)


def _assert_explicitly_unfilled(result) -> None:
    assert UNFILLED_MARKER in (result.new_text or "")
    assert result.pending_tag is not None
    for phrase in FORBIDDEN_FABRICATION:
        assert phrase not in (result.new_text or "")


def test_missing_values_use_unfilled_marker_without_fabricated_copy():
    placeholder_result = handlers.placeholder_replace(
        _element("企业名称：{{CLIENT_FULL_NAME}}"),
        SimpleNamespace(),
        Materials(client_metadata={}),
    )
    kb_result = handlers.kb_lookup_fill(
        _element("企业名称："),
        SimpleNamespace(),
        Materials(),
    )

    _assert_explicitly_unfilled(placeholder_result)
    _assert_explicitly_unfilled(kb_result)


def test_demo_safe_fallback_dictionary_is_removed():
    assert not hasattr(handlers, "_DEMO_SAFE_FALLBACK")


def test_multi_slot_all_miss_has_one_pending_entry_per_marker():
    result = handlers.multi_slot_decompose(
        _element("员工人数：XXX人；注册资本：XXX万元"),
        SimpleNamespace(),
        Materials(),
    )

    pending = result.pending_tag if isinstance(result.pending_tag, list) else [result.pending_tag]
    assert "详见补充材料" not in (result.new_text or "")
    assert (result.new_text or "").count(UNFILLED_MARKER) == 2
    assert len(pending) == 2
    assert all(item is not None for item in pending)
