export const CYCLE_LABEL: Record<number, string> = { 1: "Monthly", 3: "Quarterly", 6: "Every 6 months", 12: "Annual" };

export const USAGE_LABEL: Record<string, string> = {
  daily: "Daily",
  weekly: "Weekly",
  occasionally: "Occasionally",
  never: "Never",
  unknown: "Not set",
};

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

/** Rupees typed by the user -> integer paise. Returns null for empty/invalid input. */
export function rupeesToPaise(text: string): number | null {
  const cleaned = text.replace(/[₹,\s]/g, "");
  if (!/^\d+(\.\d{1,2})?$/.test(cleaned)) return null;
  const [whole = "0", frac = ""] = cleaned.split(".");
  return Number(whole) * 100 + Number(frac.padEnd(2, "0"));
}

export function paiseToRupeesInput(paise: number | null | undefined): string {
  if (paise === null || paise === undefined) return "";
  return paise % 100 === 0 ? String(paise / 100) : (paise / 100).toFixed(2);
}

/** Extract the "## Summary" paragraph from a report's markdown. */
export function reportSummary(markdown: string): string {
  const m = markdown.match(/## Summary\s+([\s\S]*?)(?:\n## |$)/);
  return (m?.[1] ?? "").trim();
}
