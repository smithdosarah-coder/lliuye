"use client";

import { forwardRef } from "react";
import { useDeskStore } from "./_desk-store";

type Props = {
  placeholder?: string;
};

export const DeskSearch = forwardRef<HTMLInputElement, Props>(
  function DeskSearch({ placeholder = "搜客户 / 卷宗 / 政策 / 对话" }, ref) {
    const query = useDeskStore((s) => s.query);
    const setQuery = useDeskStore((s) => s.setQuery);

    return (
      <div className="dr-search">
        <input
          ref={ref}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
        />
        <kbd>⌘K</kbd>
      </div>
    );
  },
);
