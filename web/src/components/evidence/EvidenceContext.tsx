"use client";

/**
 * EvidenceContext — 整 workspace 共享一份 evidence_trail + unfilled_fields。
 *
 * 消费方:
 *   - <EvidenceTrail> 读 items 渲染证据链折叠列表
 *   - <HighlightCard refId=...> 按 ref_id 反查 item,在正文 claim 上挂高亮(Task B)
 *   - <UnfilledMarker fieldName=...> 按 fieldName 查 unfilled_fields 决定是否渲染标记(Task C)
 *
 * 测试注入:
 *   - 生产代码从 props 拿 items / unfilledFields
 *   - 测试通过 `window.__EVIDENCE_TEST__` 覆盖整个 payload(见 tests/evidence-trail.spec.ts)
 */

import { createContext, useContext, useMemo, useEffect, useState, type ReactNode } from "react";
import type { EvidenceItem, AuditPayload } from "./types";

interface EvidenceContextValue {
  items: EvidenceItem[];
  unfilledFields: string[];
  blocked: boolean;
  getByRefId(refId: string): EvidenceItem | undefined;
  isUnfilled(fieldName: string): boolean;
}

const EMPTY_ITEMS: EvidenceItem[] = [];
const EMPTY_FIELDS: string[] = [];

const EvidenceCtx = createContext<EvidenceContextValue>({
  items: EMPTY_ITEMS,
  unfilledFields: EMPTY_FIELDS,
  blocked: false,
  getByRefId: () => undefined,
  isUnfilled: () => false,
});

export interface EvidenceProviderProps {
  items?: EvidenceItem[];
  unfilledFields?: string[];
  blocked?: boolean;
  children: ReactNode;
}

type TestInjection = AuditPayload | undefined;

function readTestInjection(): TestInjection {
  if (typeof window === "undefined") return undefined;
  const raw = (window as unknown as { __EVIDENCE_TEST__?: AuditPayload }).__EVIDENCE_TEST__;
  return raw;
}

export function EvidenceProvider({
  items,
  unfilledFields,
  blocked,
  children,
}: EvidenceProviderProps) {
  const [testInjection, setTestInjection] = useState<TestInjection>(undefined);

  useEffect(() => {
    setTestInjection(readTestInjection());
  }, []);

  const value = useMemo<EvidenceContextValue>(() => {
    const resolvedItems =
      testInjection?.evidence_trail ?? items ?? EMPTY_ITEMS;
    const resolvedUnfilled =
      testInjection?.unfilled_fields ?? unfilledFields ?? EMPTY_FIELDS;
    const resolvedBlocked = testInjection?.blocked ?? blocked ?? false;
    const refIndex = new Map<string, EvidenceItem>();
    for (const it of resolvedItems) refIndex.set(it.ref_id, it);
    const unfilledSet = new Set(resolvedUnfilled);
    return {
      items: resolvedItems,
      unfilledFields: resolvedUnfilled,
      blocked: resolvedBlocked,
      getByRefId: (refId) => refIndex.get(refId),
      isUnfilled: (fieldName) => unfilledSet.has(fieldName),
    };
  }, [testInjection, items, unfilledFields, blocked]);

  return <EvidenceCtx.Provider value={value}>{children}</EvidenceCtx.Provider>;
}

export function useEvidence(): EvidenceContextValue {
  return useContext(EvidenceCtx);
}
