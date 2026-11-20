import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { RunEvent } from "../src/api/types";
import { MoneyText } from "../src/components/MoneyText";
import { ReportView } from "../src/components/ReportView";
import { StatusBadge } from "../src/components/StatusBadge";
import { Timeline } from "../src/components/Timeline";
import { makeReport } from "./helpers";

describe("StatusBadge", () => {
  it.each([
    ["live_verified", "Live · verified"],
    ["cached_verified", "Cached · verified"],
    ["partial", "Partial"],
    ["unverified", "Unverified"],
    ["conflict", "Conflict"],
    ["user_entered", "You entered"],
  ])("%s", (status, label) => {
    render(<StatusBadge status={status} title="source: example" />);
    expect(screen.getByText(label)).toHaveAttribute("title", "source: example");
  });

  it("explains itself when no title is given", () => {
    render(<StatusBadge status="cached_verified" />);
    expect(screen.getByText("Cached · verified").getAttribute("title")).toMatch(/earlier fetch/);
  });
});

it("MoneyText shows the server-formatted string verbatim", () => {
  render(<MoneyText value={{ paise: 149900, display: "₹1,499.00" }} />);
  expect(screen.getByText("₹1,499.00")).toBeInTheDocument();
});

describe("Timeline", () => {
  const events: RunEvent[] = [
    { seq: 1, node: "research", event_type: "node_start", message: "Fetching 2 providers", payload: {}, duration_ms: null, created_at: "2026-11-01T10:00:00Z" },
    { seq: 2, node: "research", event_type: "tool_error", message: "TestProv fetch failed", payload: { error: "DNS failure" }, duration_ms: null, created_at: "2026-11-01T10:00:01Z" },
    { seq: 3, node: "research", event_type: "node_end", message: "Research finished", payload: {}, duration_ms: 1500, created_at: "2026-11-01T10:00:02Z" },
  ];

  it("renders backend events with node labels and errors", () => {
    render(<Timeline events={events} live />);
    expect(screen.getByText("Fetching prices from providers")).toBeInTheDocument();
    expect(screen.getByText("Fetching 2 providers")).toBeInTheDocument();
    expect(screen.getByText("DNS failure")).toBeInTheDocument();
    expect(screen.getByText("Research finished")).toBeInTheDocument();
    expect(screen.getByText("Working…")).toBeInTheDocument();
  });

  it("shows an empty state", () => {
    render(<Timeline events={[]} live={false} />);
    expect(screen.getByText("No events recorded.")).toBeInTheDocument();
  });
});

describe("ReportView", () => {
  it("renders costs, changes, features, limitations and evidence", () => {
    render(<ReportView report={makeReport()} />);
    expect(screen.getByText("Switch to Test Basic to save ₹400.00 a month.")).toBeInTheDocument();
    expect(screen.getByText("₹800.00")).toBeInTheDocument();
    expect(screen.getAllByText("₹400.00").length).toBeGreaterThan(0);
    expect(screen.getByText("₹4,800.00 per year")).toBeInTheDocument();
    expect(screen.getByText("Old Plan", { selector: "span" })).toBeInTheDocument();
    expect(screen.getByText("4K Ultra HD")).toBeInTheDocument();
    expect(screen.getByText(/page could not be reached/)).toBeInTheDocument();
    expect(screen.getByText("Local cable")).toBeInTheDocument();
    expect(screen.getByText("Pricey Plan")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Show" }));
    expect(screen.getAllByText(/Basic ₹300\/month/).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: "https://example.test/pricing" })[0]).toHaveAttribute("href", "https://example.test/pricing");
  });

  it("explains an infeasible result instead of inventing one", () => {
    render(
      <ReportView
        report={makeReport({
          status: "infeasible",
          recommended: [],
          recommended_total_display: null,
          monthly_saving_display: null,
          monthly_saving_paise: null,
          annual_saving_display: null,
          diagnosis: "Your must-have features cost more than your budget.",
          diagnosis_amounts: { min_cost_for_must_haves: "₹650.00" },
        })}
      />,
    );
    expect(screen.getByText("No plan combination satisfies all your constraints.")).toBeInTheDocument();
    expect(screen.getByText("Your must-have features cost more than your budget.")).toBeInTheDocument();
    expect(screen.getByText(/min cost for must haves: ₹650.00/)).toBeInTheDocument();
    expect(screen.queryByText("Recommended plans")).not.toBeInTheDocument();
  });
});

