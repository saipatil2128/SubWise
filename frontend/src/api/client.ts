import type { ErrorBody, ErrorEnvelope, Health } from "./types";

export const API_BASE = "/api/v1";

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

  get notImplemented(): boolean {
    return this.body.code === "NOT_IMPLEMENTED";
  }
}

function isEnvelope(value: unknown): value is ErrorEnvelope {
  return (
    typeof value === "object" &&
    value !== null &&
    "error" in value &&
    typeof (value as { error: { code?: unknown } }).error?.code === "string"
  );
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include", // session cookie (M3)
    ...init,
    headers: { Accept: "application/json", "Content-Type": "application/json", ...init.headers },
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

export const getHealth = () => apiFetch<Health>("/health");
