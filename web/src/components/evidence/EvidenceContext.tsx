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
import type { EvidenceItem, AuditPayload, UnfilledReason } from "./types";

interface EvidenceContextValue {
  items: EvidenceItem[];
  unfilledFields: string[];
  /** 可选 per-field reason 覆盖(比默认 qc_blocked 更精细)。 */
  unfilledReasons: Record<string, UnfilledReason>;
  blocked: boolean;
  getByRefId(refId: string): EvidenceItem | undefined;
  isUnfilled(fieldName: string): boolean;
  getUnfilledReason(fieldName: string): UnfilledReason | undefined;
}

const EMPTY_ITEMS: EvidenceItem[] = [];
const EMPTY_FIELDS: string[] = [];

const EMPTY_REASONS: Record<string, UnfilledReason> = {};

const EvidenceCtx = createContext<EvidenceContextValue>({
  items: EMPTY_ITEMS,
  unfilledFields: EMPTY_FIELDS,
  unfilledReasons: EMPTY_REASONS,
  blocked: false,
  getByRefId: () => undefined,
  isUnfilled: () => false,
  getUnfilledReason: () => undefined,
});

export interface EvidenceProviderProps {
  items?: EvidenceItem[];
  unfilledFields?: string[];
  unfilledReasons?: Record<string, UnfilledReason>;
  blocked?: boolean;
  children: ReactNode;
}

type TestInjection = (AuditPayload & { unfilled_reasons?: Record<string, UnfilledReason> }) | undefined;

function readTestInjection(): TestInjection {
  if (typeof window === "undefined") return undefined;
  const raw = (window as unknown as { __EVIDENCE_TEST__?: TestInjection }).__EVIDENCE_TEST__;
  return raw;
}

export function EvidenceProvider({
  items,
  unfilledFields,
  unfilledReasons,
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
    const resolvedReasons =
      testInjection?.unfilled_reasons ?? unfilledReasons ?? EMPTY_REASONS;
    const resolvedBlocked = testInjection?.blocked ?? blocked ?? false;
    const refIndex = new Map<string, EvidenceItem>();
    for (const it of resolvedItems) refIndex.set(it.ref_id, it);
    const unfilledSet = new Set(resolvedUnfilled);
    return {
      items: resolvedItems,
      unfilledFields: resolvedUnfilled,
      unfilledReasons: resolvedReasons,
      blocked: resolvedBlocked,
      getByRefId: (refId) => refIndex.get(refId),
      isUnfilled: (fieldName) => unfilledSet.has(fieldName),
      getUnfilledReason: (fieldName) => resolvedReasons[fieldName],
    };
  }, [testInjection, items, unfilledFields, unfilledReasons, blocked]);

  return <EvidenceCtx.Provider value={value}>{children}</EvidenceCtx.Provider>;
}

export function useEvidence(): EvidenceContextValue {
  return useContext(EvidenceCtx);
}
