# -*- coding: utf-8 -*-

from __future__ import annotations

import os

from form_filler import FormFillAgent


def llm_stub(a: str, b: str) -> str:
    return ""


def main() -> None:
    root = r"D:\刘野\众安\新建文件夹\2026.3.25续贷材料"

    paths = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if "银行流水" not in d]
        for fn in filenames:
            if fn.startswith(("~$", ".")):
                continue
            ext = os.path.splitext(fn)[1].lower()
            if ext not in (".txt", ".docx", ".doc", ".pdf", ".xlsx", ".xls", ".csv"):
                continue
            paths.append(os.path.join(dirpath, fn))

    paths = sorted(set(paths))

    mp = {}
    for fp in paths:
        fname = os.path.basename(fp)
        parent = os.path.basename(os.path.dirname(fp))
        dn = f"{parent}/{fname}" if parent else fname
        mp[dn] = fp

    print("FILES", len(mp))

    agent = FormFillAgent(llm_stub, {}, file_path_map=mp)
    fin, sources = agent._truth_build_financial_data(progress_cb=None)

    print("PERIODS", sorted(fin.keys()))

    for y in sorted(fin.keys()):
        d = fin.get(y, {})
        rev = d.get("主营业务收入") or d.get("营业收入")
        np = d.get("净利润")
        ar = d.get("应收账款")
        print(y, "rev", rev, "np", np, "ar", ar, "src", sources.get(y))


if __name__ == "__main__":
    main()
