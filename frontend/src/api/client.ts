import type {
  Attempt,
  Dashboard,
  ErrorBody,
  FeatureDef,
  FeatureRequirement,
  Health,
  Me,
  MemoryItem,
  PlanPrice,
  PricePoint,
  Profile,
  ProfileIn,
  Provider,
  RefreshResult,
  Report,
  Run,
  RunEvent,
  Subscription,
  SubscriptionIn,
  SubscriptionPatch,
  User,
} from "./types";

export const API_BASE = "/api/v1";
export const CSRF_HEADER = "X-SubWise-CSRF";

/** Every non-2xx response from the backend uses the same envelope (blueprint J.1). */
export class ApiError extends Error {
  readonly status: number;
  readonly body: ErrorBody;

  constructor(status: number, body: ErrorBody) {
    super(body.message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

function isEnvelope(value: unknown): value is { error: ErrorBody } {
  return (
    typeof value === "object" &&
    value !== null &&
    "error" in value &&
    typeof (value as { error: { code?: unknown } }).error?.code === "string"
  );
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...init,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      [CSRF_HEADER]: "1",
      ...init.headers,
    },
  });
  if (response.status === 204) return undefined as T;
  const payload: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const body: ErrorBody = isEnvelope(payload)
      ? payload.error
      : {
          code: "INTERNAL_ERROR",
          message: `Unexpected ${response.status} response`,
          retryable: false,
          details: {},
          request_id: null,
        };
    throw new ApiError(response.status, body);
  }
  return payload as T;
}

const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body) });
const post = <T>(path: string, body?: unknown) => apiFetch<T>(path, { method: "POST", ...json(body ?? {}) });
const put = <T>(path: string, body: unknown) => apiFetch<T>(path, { method: "PUT", ...json(body) });
const patch = <T>(path: string, body: unknown) => apiFetch<T>(path, { method: "PATCH", ...json(body) });
const del = (path: string) => apiFetch<void>(path, { method: "DELETE" });

export const api = {
  health: () => apiFetch<Health>("/health"),
  register: (b: { email: string; password: string; display_name: string }) => post<User>("/auth/register", b),
  login: (b: { email: string; password: string }) => post<User>("/auth/login", b),
  logout: () => post<void>("/auth/logout"),
  me: () => apiFetch<Me>("/me"),
  putProfile: (b: ProfileIn) => put<Profile>("/me/profile", b),
  requirements: () => apiFetch<{ requirements: FeatureRequirement[] }>("/me/requirements"),
  putRequirements: (requirements: FeatureRequirement[]) =>
    put<{ requirements: FeatureRequirement[] }>("/me/requirements", { requirements }),
  memory: () => apiFetch<MemoryItem[]>("/me/memory"),
  forget: (kind: string, key: string) => del(`/me/memory/${encodeURIComponent(kind)}/${encodeURIComponent(key)}`),
  features: () => apiFetch<FeatureDef[]>("/features"),
  subscriptions: () => apiFetch<Subscription[]>("/subscriptions"),
  createSubscription: (b: SubscriptionIn) => post<Subscription>("/subscriptions", b),
  updateSubscription: (id: string, b: SubscriptionPatch) => patch<Subscription>(`/subscriptions/${id}`, b),
  deleteSubscription: (id: string) => del(`/subscriptions/${id}`),
  providers: () => apiFetch<Provider[]>("/catalog/providers"),
  plans: (providerId?: string) =>
    apiFetch<PlanPrice[]>(`/catalog/plans${providerId ? `?provider_id=${encodeURIComponent(providerId)}` : ""}`),
  priceHistory: (planId: string) => apiFetch<PricePoint[]>(`/prices/${encodeURIComponent(planId)}/history`),
  refreshPrices: (provider_ids?: string[]) => post<RefreshResult[]>("/prices/refresh", { provider_ids }),
  attempts: () => apiFetch<Attempt[]>("/prices/attempts"),
  runs: () => apiFetch<Run[]>("/runs"),
  run: (id: string) => apiFetch<Run>(`/runs/${id}`),
  events: (id: string, after = 0) => apiFetch<RunEvent[]>(`/runs/${id}/events/list?after_seq=${after}`),
  startRun: (b: { message: string; mode: string; thread_id?: string | null }) => post<Run>("/runs", b),
  clarify: (id: string, answers: Record<string, string>) => post<void>(`/runs/${id}/clarification`, { answers }),
  approve: (id: string, b: { report_id: string; decision: "approved" | "rejected"; reason?: string; remember?: string[] }) =>
    post<void>(`/runs/${id}/approval`, b),
  cancelRun: (id: string) => post<void>(`/runs/${id}/cancel`),
  resumeRun: (id: string) => post<void>(`/runs/${id}/resume`),
  runReports: (id: string) => apiFetch<Report[]>(`/runs/${id}/reports`),
  report: (id: string) => apiFetch<Report>(`/reports/${id}`),
  dashboard: () => apiFetch<Dashboard>("/dashboard"),
};

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    const errors = (err.body.details as { errors?: { loc?: unknown[]; msg?: string }[] } | undefined)?.errors;
    if (Array.isArray(errors) && errors.length) {
      const detail = errors
        .slice(0, 3)
        .map((e) => {
          const field = (e.loc ?? []).filter((x) => x !== "body").join(".");
          return field ? `${field}: ${e.msg ?? ""}` : (e.msg ?? "");
        })
        .join("; ");
      return `${err.body.message} ${detail}`.trim();
    }
    return err.body.message;
  }
  if (err instanceof Error) return err.message;
  return "Something went wrong.";
}
