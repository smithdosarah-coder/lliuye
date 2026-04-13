# -*- coding: utf-8 -*-

from __future__ import annotations

import os

from form_filler import FormFillAgent


def llm_stub(a: str, b: str) -> str:
    return ""


def build_map(root: str) -> dict[str, str]:
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
    return mp


def main() -> None:
    root = r"D:\刘野\众安\新建文件夹\2026.3.25续贷材料"
    mp = build_map(root)
    agent = FormFillAgent(llm_stub, {}, file_path_map=mp)
    fin, sources = agent._truth_build_financial_data(progress_cb=None)

    for y in sorted(fin.keys()):
        d = fin[y]
        keys = sorted([k for k in d.keys() if any(x in str(k) for x in ("收入", "净利润", "利润", "营业"))])
        print("====", y, "src=", sources.get(y), "====")
        for k in keys[:30]:
            print(k, d.get(k))


if __name__ == "__main__":
    main()
