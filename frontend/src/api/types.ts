// Hand-written mirrors of the backend's shared shapes. Once the backend runs, regenerate the full
// typed schema with `npm run gen:api` (writes src/api/schema.d.ts) and prefer those types.

export interface Money {
  paise: number;
  display: string; // formatted server-side, e.g. "₹499.00" — never compute money in the client
}

export type ObservationStatus = "verified" | "partial" | "unverified" | "conflict";
export type Freshness = "fresh" | "stale" | "expired";

export interface ErrorBody {
  code: string;
  message: string;
  retryable: boolean;
  details: Record<string, unknown>;
  request_id: string | null;
}

export interface ErrorEnvelope {
  error: ErrorBody;
}

export interface Health {
  status: "ok" | "degraded";
  version: string;
  environment: string;
  llm: string;
  search: "enabled" | "disabled";
  database: string;
}
