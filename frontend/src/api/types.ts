// Types generated from the backend OpenAPI schema (npm run gen:api). Re-exported with short names.
import type { components } from "./schema";

type S = components["schemas"];

export type Money = S["Money"];
export type User = S["UserOut"];
export type Me = S["MeOut"];
export type Profile = S["ProfileOut"];
export type ProfileIn = S["ProfileIn"];
export type FeatureDef = S["FeatureDefOut"];
export type FeatureRequirement = S["FeatureRequirement"];
export type MemoryItem = S["MemoryItemOut"];
export type Subscription = S["SubscriptionOut"];
export type SubscriptionIn = S["SubscriptionIn"];
export type SubscriptionPatch = S["SubscriptionPatch"];
export type Provider = S["ProviderOut"];
export type Attempt = S["AttemptOut"];
export type PlanPrice = S["PlanPriceOut"];
export type PricePoint = S["PriceHistoryPoint"];
export type RefreshResult = S["RefreshOut"];
export type Run = S["RunOut"];
export type RunEvent = S["RunEventOut"];
export type Report = S["ReportOut"];
export type Evidence = S["EvidenceOut"];
export type Dashboard = S["DashboardOut"];
export type Health = S["HealthOut"];
export type ErrorBody = S["ErrorBody"];
export type ErrorEnvelope = S["ErrorEnvelope"];

export type PriceLabel =
  | "live_verified"
  | "cached_verified"
  | "partial"
  | "unverified"
  | "conflict"
  | "unavailable"
  | "user_entered";

/** Shape of `Report.facts` (built by the backend's core/report_facts.py). */
export interface PlanFact {
  plan_id: string;
  name: string;
  provider_name: string;
  monthly_display: string;
  price_display: string;
  billing_cycle_months: number;
  label: PriceLabel;
  observed_at: string | null;
  source_url: string | null;
  evidence: string | null;
  is_current: boolean;
}

export interface ReportFacts {
  status: "optimal" | "infeasible" | "no_candidates";
  budget_display: string | null;
  within_budget: boolean | null;
  current_total_display: string;
  current_items: { name: string; monthly_display: string; usage: string }[];
  recommended: PlanFact[];
  fixed_items: { name: string; monthly_display: string }[];
  recommended_total_display: string | null;
  monthly_saving_paise: number | null;
  monthly_saving_display: string | null;
  annual_saving_display: string | null;
  keep: string[];
  add: string[];
  drop: string[];
  features_covered: string[];
  features_lost: string[];
  missing_must_have: string[];
  missing_nice_to_have: string[];
  current_overlaps: Record<string, string[]>;
  rejected: { name: string; reason: string }[];
  alternatives: { plans: string[]; total_display: string; missing_nice_to_have: string[] }[];
  data_issues: string[];
  diagnosis: string | null;
  diagnosis_amounts: Record<string, string>;
}

export interface ClarifyQuestion {
  field: string;
  question: string;
}
