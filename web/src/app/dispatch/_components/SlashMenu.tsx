"use client";

import { SLASH_COMMANDS, type SlashCommandDef } from "./composer-commands";

interface SlashMenuProps {
  query: string;
  highlightIndex: number;
  onPick: (cmd: SlashCommandDef) => void;
  onHover: (index: number) => void;
}

export function SlashMenu({ query, highlightIndex, onPick, onHover }: SlashMenuProps) {
  const items = filterCommands(query);
  if (items.length === 0) return null;
  return (
    <div className="dpx-slash">
      <div className="dpx-slash-head">COMMANDS · TYPE TO FILTER</div>
      <ul>
        {items.map((c, i) => (
          <li
            key={c.key}
            className={i === highlightIndex ? "on" : undefined}
            onMouseEnter={() => onHover(i)}
            onMouseDown={(e) => {
              // mousedown to fire before input blur
              e.preventDefault();
              onPick(c);
            }}
          >
            <span className="cmd">{c.label}</span>
            <span className="hint">{c.hint}</span>
            <span className="ex">{c.example}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function filterCommands(query: string): SlashCommandDef[] {
  const q = query.replace(/^\//, "").trim().toLowerCase();
  if (!q) return SLASH_COMMANDS;
  return SLASH_COMMANDS.filter(
    (c) => c.key.startsWith(q) || c.label.toLowerCase().includes(q),
  );
}
