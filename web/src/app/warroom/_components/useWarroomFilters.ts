"use client";

/**
 * URL ⇄ ticket filter 双向同步。
 *
 * query keys:
 *   scope     = mine | all                (默认 mine; 无 currentUser 时 fallback all)
 *   customer  = cust_xxx
 *   assignee  = u_xxx
 *   from      = agent id (report/credit/…)
 *   to        = agent id
 *   priority  = normal | urgent
 *
 * 写入用 router.replace（不堆历史栈）。
 */
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";

import { AGENT_IDS, useAuthStore, type AgentId } from "@/lib/store";
import type { TicketFilters } from "../_store/ticket-store";

export type FilterKey =
  | "scope"
  | "customer"
  | "assignee"
  | "from"
  | "to"
  | "priority";

const AGENT_SET = new Set<string>(AGENT_IDS as readonly string[]);

function parseAgent(v: string | null): AgentId | undefined {
  if (!v) return undefined;
  return AGENT_SET.has(v) ? (v as AgentId) : undefined;
}

function parsePriority(v: string | null) {
  return v === "urgent" || v === "normal" ? v : undefined;
}

function parseScope(v: string | null) {
  return v === "mine" || v === "all" ? v : undefined;
}

export function useWarroomFilters(): {
  filters: TicketFilters;
  raw: Partial<Record<FilterKey, string>>;
  set: (key: FilterKey, value: string | null) => void;
  clear: () => void;
} {
  const router = useRouter();
  const params = useSearchParams();
  const currentUser = useAuthStore((s) => s.currentUser);

  const raw: Partial<Record<FilterKey, string>> = useMemo(
    () => ({
      scope: params.get("scope") ?? undefined,
      customer: params.get("customer") ?? undefined,
      assignee: params.get("assignee") ?? undefined,
      from: params.get("from") ?? undefined,
      to: params.get("to") ?? undefined,
      priority: params.get("priority") ?? undefined,
    }),
    [params],
  );

  const scope = parseScope(raw.scope ?? null) ?? (currentUser ? "mine" : "all");

  const filters: TicketFilters = useMemo(
    () => ({
      scope,
      currentUserId: currentUser?.id,
      customerId: raw.customer || undefined,
      assignedTo: raw.assignee || undefined,
      fromAgent: parseAgent(raw.from ?? null),
      toAgent: parseAgent(raw.to ?? null),
      priority: parsePriority(raw.priority ?? null),
    }),
    [scope, currentUser?.id, raw.customer, raw.assignee, raw.from, raw.to, raw.priority],
  );

  const set = useCallback(
    (key: FilterKey, value: string | null) => {
      const next = new URLSearchParams(params.toString());
      if (value === null || value === "") next.delete(key);
      else next.set(key, value);
      const q = next.toString();
      router.replace(q ? `/warroom?${q}` : "/warroom", { scroll: false });
    },
    [params, router],
  );

  const clear = useCallback(() => {
    router.replace("/warroom", { scroll: false });
  }, [router]);

  return { filters, raw, set, clear };
}
