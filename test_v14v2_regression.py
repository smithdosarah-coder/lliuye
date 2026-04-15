# -*- coding: utf-8 -*-
"""V14v2 回归单元测试:3 处 V14 bug 必须在代码层被修复。

不依赖 LLM,直接把 V14 dump 里的典型片段喂给三个 fix 函数,断言输出符合预期。
"""
import sys, io, os
# 尝试把 stdout/stderr 转 utf-8;pipe redirect 时 .buffer 可能为 None
try:
    if hasattr(sys.stdout, "buffer") and sys.stdout.buffer is not None:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', line_buffering=True)
except Exception:
    pass
# 备用:若上面失败,至少强制 PYTHONIOENCODING
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from section_generator import (
    _fix_affiliates_deterministic,
    _fix_variation_phrases,
    _get_standard_variation_phrase,
    _ABSURD_VARIATION_RE,
    _FUZZY_FALLBACK_RE,
)


# ============================================================
# Fake anchor / indicator 对象,不依赖真材料
# ============================================================
class _FakeRC:
    def __init__(self, name, revenue, net_profit):
        self.name = name
        self.revenue = revenue              # str 万
        self.net_profit = net_profit        # str 万
        self.revenue_suspect = False
        self.profit_suspect = False
        self.suspect_reason = ""


class _FakeAnchor:
    def __init__(self, rcs):
        self.related_companies = rcs


class _FakePV:
    def __init__(self, current, previous, unit, compare_caption="同比"):
        self.current = current
        self.previous = previous
        self.unit = unit
        self.compare_caption = compare_caption
        if current is not None and previous is not None:
            self.yoy_abs = current - previous
            self.yoy_pct = ((current - previous) / abs(previous) * 100
                            if previous else None)
        else:
            self.yoy_abs = None
            self.yoy_pct = None


class _FakeFI:
    def __init__(self):
        # 模拟中锐网络真实数据: 毛利率 38.8% → 38.0% (下降 0.8pct)
        self.gross_margin = _FakePV(38.0, 38.8, "%", "同比")
        # 净利率 3.7% → 4.9% (上升 1.2pct)
        self.net_margin = _FakePV(4.9, 3.7, "%", "同比")
        # 资产负债率 50.2% → 42.5% (较年初下降 7.7pct)
        self.debt_to_asset_ratio = _FakePV(42.5, 50.2, "%", "较年初")
        # 应收账款周转天数 388 → 271 (同比缩短 117 天)
        self.ar_turnover_days = _FakePV(271, 388, "天", "同比")
        # 流动比率 1.58 → 1.82
        self.current_ratio = _FakePV(1.82, 1.58, "倍", "较年初")
        # 存货周转天数: 只有当期, 无previous (模拟缺失)
        self.inventory_turnover_days = _FakePV(200, None, "天", "较年初")
        # 速动比率、营业利润率: None 测试 fallback
        self.quick_ratio = _FakePV(1.51, None, "倍", "较年初")
        self.operating_margin = _FakePV(4.8, None, "%", "同比")


# ============================================================
# Test 1: 回归 1 - 多公司单子句 affiliate 修复
# ============================================================
def test_affiliates_multi_company_clause():
    print("\n" + "=" * 60)
    print("Test 1: 回归 1 - 关联企业多公司单子句")
    print("=" * 60)

    # L36 的原文(缩减版,5 家公司一个子句)
    text = (
        "集团主要子公司包括福建中锐汉鼎信息技术有限公司(智慧水利,收入1223万元,"
        "净亏损682万元)、福建中锐教育科技有限公司(智慧教育,收入21万元,"
        "净亏损1275万元)、北京中锐青云科技有限公司(产教融合,收入204万元,"
        "净利润493.77万元)、厦门中锐软件科技有限公司(软硬件销售,收入7万元,"
        "净亏损13万元)及中锐海沃水利技术(福建)有限公司"
        "(智慧水利,收入0万元,净利润493.77万元)。"
    )

    # 真值: 青云源材料净利润 16 万; 海沃 净利润 0.05 万(极小); 其他维持
    rcs = [
        _FakeRC("福建中锐汉鼎信息技术有限公司", "1223", "-682"),
        _FakeRC("福建中锐教育科技有限公司",     "21",   "-1275"),
        _FakeRC("北京中锐青云科技有限公司",     "204",  "16"),
        _FakeRC("厦门中锐软件科技有限公司",     "7",    "-13"),
        _FakeRC("中锐海沃水利技术(福建)有限公司", "0",  "0.05"),
    ]
    anchor = _FakeAnchor(rcs)

    fixed, n_fixes = _fix_affiliates_deterministic(text, anchor)
    print(f"n_fixes = {n_fixes}")
    print("fixed text:")
    print(fixed)

    # 断言
    # (a) 青云 净利润应纠正到 16 万附近,不再是 493.77
    assert "北京中锐青云科技有限公司" in fixed
    # 青云段落后面的 净利润 不应再出现 493.77
    qingyun_start = fixed.find("北京中锐青云")
    # 找下一个公司名结束当前段
    qingyun_end = fixed.find("厦门中锐", qingyun_start)
    qingyun_section = fixed[qingyun_start:qingyun_end] if qingyun_end > 0 else fixed[qingyun_start:]
    assert "493.77" not in qingyun_section, \
        f"青云段仍含 493.77: {qingyun_section}"
    assert ("净利润16" in qingyun_section or
            "净利润规模极小" in qingyun_section), \
        f"青云段没有修正: {qingyun_section}"

    # (b) 海沃 净利润 不再是 493.77(应变极小或正确值)
    haiwo_start = fixed.find("中锐海沃")
    haiwo_section = fixed[haiwo_start:]
    assert "493.77" not in haiwo_section, \
        f"海沃段仍含 493.77: {haiwo_section}"

    print("[PASS] 多公司单子句 affiliate 修复: 青云/海沃的 493.77 被剔除")
    return True


# ============================================================
# Test 2: 回归 2 - 变动值≈末值(数学荒谬)
# ============================================================
def test_absurd_variation():
    print("\n" + "=" * 60)
    print("Test 2: 回归 2 - 变动值≈末值(数学荒谬)")
    print("=" * 60)

    fi = _FakeFI()

    samples = [
        "但毛利率微降38.0个百分点至38.0%,仍处于行业",
        "但毛利率同比微降38.02个百分点至38.0%,仍处于行业",
        "应收账款周转天数同比缩短270.92天至271天,回收效率",
        "应收账款周转天数同比大幅缩短271天至271天,回款管理",
    ]

    for s in samples:
        fixed, n = _fix_variation_phrases(s, fi)
        print(f"IN : {s}")
        print(f"OUT: {fixed}  (n_fix={n})")
        # 关键断言: 不再出现 "X 个百分点至 X" 这种 delta=current 的模式
        # 也不再出现 "缩短 271 天至 271 天"
        import re
        m_pct = re.search(r"([\d.]+)\s*个百分点至\s*([\d.]+)%", fixed)
        m_day = re.search(r"(缩短|延长)\s*([\d.]+)\s*天至\s*([\d.]+)\s*天", fixed)
        if m_pct:
            d, c = float(m_pct.group(1)), float(m_pct.group(2))
            assert abs(d - c) / max(abs(d), abs(c), 1.0) >= 0.02, \
                f"修复后仍 delta==current: {fixed}"
        if m_day:
            d, c = float(m_day.group(2)), float(m_day.group(3))
            assert abs(d - c) / max(abs(d), abs(c), 1.0) >= 0.02, \
                f"修复后仍 delta==current: {fixed}"
        assert n >= 1, f"未触发修复: {s}"

    print("[PASS] 所有荒谬短语均被修复")
    return True


# ============================================================
# Test 3: 回归 3 - 模糊兜底话术替换
# ============================================================
def test_fuzzy_fallback():
    print("\n" + "=" * 60)
    print("Test 3: 回归 3 - 模糊兜底话术")
    print("=" * 60)

    fi = _FakeFI()

    samples = [
        ("资产负债率较年初有所变化,具体幅度以财务附表为准", True),   # fi 里有数据
        ("净利率较年初有所变化,具体幅度以财务附表为准", True),         # fi 里有数据
        ("存货周转天数较年初有所变化,具体幅度以财务附表为准", True),   # fi 里无 previous → fallback
        ("流动比率较年初有所变化,具体幅度以财务附表为准", True),        # fi 有数据
    ]
    for s, should_fix in samples:
        fixed, n = _fix_variation_phrases(s, fi)
        print(f"IN : {s}")
        print(f"OUT: {fixed}  (n_fix={n})")
        # 修复后不应保留"以财务附表为准"
        assert "以财务附表为准" not in fixed, f"仍含兜底话术: {fixed}"
        assert n >= 1
    print("[PASS] 所有模糊兜底短语均被替换")
    return True


# ============================================================
# Test 4: 标准短语生成(format_for_prompt 一致)
# ============================================================
def test_standard_phrase():
    print("\n" + "=" * 60)
    print("Test 4: 标准变动短语生成")
    print("=" * 60)
    fi = _FakeFI()

    cases = [
        ("资产负债率", "较年初下降7.7个百分点至42.5%"),
        ("毛利率",     "毛利率同比下降0.8个百分点至38.0%"),
        ("应收账款周转天数", "应收账款周转天数同比缩短117天至271天"),
    ]
    for metric, expected_substr in cases:
        got = _get_standard_variation_phrase(fi, metric)
        print(f"{metric} → {got}")
        # 关键数字存在即可
        for tok in expected_substr.replace(metric, "").split("个百分点"):
            if tok.strip() and tok.strip() not in ("至", ""):
                assert tok.strip().rstrip("%天倍").rstrip(".") in (got or "").replace(",", ""), \
                    f"{metric}: {tok} not in {got}"
    # 缺数据的 metric
    none_val = _get_standard_variation_phrase(fi, "速动比率")
    assert none_val is None, f"速动比率 previous=None 应返回 None: {none_val}"
    print("[PASS] 标准短语生成正确")
    return True


# ============================================================
# Test 5: 端到端(串跑三个 fix)
# ============================================================
def test_end_to_end():
    print("\n" + "=" * 60)
    print("Test 5: 端到端串跑(模拟 V14 dump 风格输入)")
    print("=" * 60)
    fi = _FakeFI()

    # 模拟一段综合了三个 bug 的 paragraph
    text = (
        "财务方面,企业2025年规模与盈利:营业收入同比增长14.9%至10009.6万元,"
        "净利润同比增长50.1%至493.8万元。净利率较年初有所变化,"
        "具体幅度以财务附表为准,但毛利率微降38.0个百分点至38.0%,"
        "仍处于软件信息业30-50%的典型区间。资产负债率较年初有所变化,"
        "具体幅度以财务附表为准。应收账款周转天数同比缩短270.92天至271天,"
        "回款管理成效显著。"
    )
    # 先跑变动短语兜底
    fixed, n_var = _fix_variation_phrases(text, fi)
    print(f"after _fix_variation_phrases: n={n_var}")
    print(fixed)

    # 检查
    assert "个百分点至38.0%" not in fixed or "0.8个百分点" in fixed, \
        "荒谬短语未修"
    assert "以财务附表为准" not in fixed, "兜底话术未修"
    assert "缩短270.92天至271天" not in fixed, "荒谬天数未修"
    print("[PASS] 端到端串跑通过")
    return True


if __name__ == "__main__":
    all_pass = True
    for fn in [
        test_affiliates_multi_company_clause,
        test_absurd_variation,
        test_fuzzy_fallback,
        test_standard_phrase,
        test_end_to_end,
    ]:
        try:
            fn()
        except AssertionError as e:
            print(f"[FAIL] {fn.__name__}: {e}")
            all_pass = False
        except Exception as e:
            print(f"[ERROR] {fn.__name__}: {type(e).__name__}: {e}")
            import traceback; traceback.print_exc()
            all_pass = False

    print("\n" + "=" * 60)
    print("ALL PASS" if all_pass else "SOME FAILED")
    print("=" * 60)
    sys.exit(0 if all_pass else 1)
