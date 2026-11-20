import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../api/client";

export const keys = {
  me: ["me"] as const,
  health: ["health"] as const,
  dashboard: ["dashboard"] as const,
  subscriptions: ["subscriptions"] as const,
  providers: ["providers"] as const,
  plans: ["plans"] as const,
  features: ["features"] as const,
  requirements: ["requirements"] as const,
  memory: ["memory"] as const,
  runs: ["runs"] as const,
  run: (id: string) => ["run", id] as const,
  report: (id: string) => ["report", id] as const,
  runReports: (id: string) => ["runReports", id] as const,
  history: (planId: string) => ["history", planId] as const,
  attempts: ["attempts"] as const,
};

export const useMe = () => useQuery({ queryKey: keys.me, queryFn: api.me, retry: false });
export const useHealth = () => useQuery({ queryKey: keys.health, queryFn: api.health, refetchInterval: 30_000, retry: 1 });
export const useDashboard = () => useQuery({ queryKey: keys.dashboard, queryFn: api.dashboard });
export const useSubscriptions = () => useQuery({ queryKey: keys.subscriptions, queryFn: api.subscriptions });
export const useProviders = () => useQuery({ queryKey: keys.providers, queryFn: api.providers });
export const usePlans = () => useQuery({ queryKey: keys.plans, queryFn: () => api.plans() });
export const useFeatures = () => useQuery({ queryKey: keys.features, queryFn: api.features, staleTime: Infinity });
export const useRequirements = () => useQuery({ queryKey: keys.requirements, queryFn: api.requirements });
export const useMemory = () => useQuery({ queryKey: keys.memory, queryFn: api.memory });
export const useRuns = () => useQuery({ queryKey: keys.runs, queryFn: api.runs });
export const useRun = (id: string | undefined) =>
  useQuery({
    queryKey: keys.run(id ?? ""),
    queryFn: () => api.run(id!),
    enabled: !!id,
    // Backup to the event stream: poll while the run is active.
    refetchInterval: (q) => (q.state.data && ["queued", "running"].includes(q.state.data.status) ? 3000 : false),
  });
export const useReport = (id: string | null | undefined) =>
  useQuery({ queryKey: keys.report(id ?? ""), queryFn: () => api.report(id!), enabled: !!id });
export const useRunReports = (id: string | undefined) =>
  useQuery({ queryKey: keys.runReports(id ?? ""), queryFn: () => api.runReports(id!), enabled: !!id });
export const usePriceHistory = (planId: string | null) =>
  useQuery({ queryKey: keys.history(planId ?? ""), queryFn: () => api.priceHistory(planId!), enabled: !!planId });

/** Mutation that invalidates the given query keys on success. */
export function useInvalidatingMutation<TArgs, TResult>(
  fn: (args: TArgs) => Promise<TResult>,
  invalidate: readonly (readonly unknown[])[],
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      for (const key of invalidate) void qc.invalidateQueries({ queryKey: key });
    },
  });
}
