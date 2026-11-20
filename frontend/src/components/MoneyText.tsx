import type { Money } from "../api/types";

/** The only way money is rendered. It shows the server's formatted string; the client never
 * does arithmetic on money (AGENTS.md). */
export function MoneyText({ value }: { value: Money }) {
  return <span className="tabular-nums">{value.display}</span>;
}
