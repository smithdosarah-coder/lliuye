"use client";

import {
  createContext,
  useContext,
  useState,
  type ReactNode,
} from "react";

// A-015: cross-client description override for /archive/[agent] lede.
// Credit workspace pushes SEGMENT_META[segment].description on segment change;
// other agents leave slot=null and fall back to the static AgentDef.description.
type HeaderSlotCtx = {
  description: string | null;
  setDescription: (d: string | null) => void;
};

const HeaderSlotContext = createContext<HeaderSlotCtx | null>(null);

export function HeaderSlotProvider({ children }: { children: ReactNode }) {
  const [description, setDescription] = useState<string | null>(null);
  return (
    <HeaderSlotContext.Provider value={{ description, setDescription }}>
      {children}
    </HeaderSlotContext.Provider>
  );
}

export function useHeaderSlot(): HeaderSlotCtx | null {
  return useContext(HeaderSlotContext);
}
