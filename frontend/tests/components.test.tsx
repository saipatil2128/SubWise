import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MoneyText } from "../src/components/MoneyText";
import { StatusBadge } from "../src/components/StatusBadge";

describe("components", () => {
  it.each([
    ["verified", "Verified"],
    ["partial", "Partial"],
    ["unverified", "Unverified"],
    ["conflict", "Conflict"],
    ["stale", "Stale"],
  ] as const)("StatusBadge %s", (status, label) => {
    render(<StatusBadge status={status} title="source: example" />);
    expect(screen.getByText(label)).toHaveAttribute("title", "source: example");
  });

  it("MoneyText shows the server-formatted string verbatim", () => {
    render(<MoneyText value={{ paise: 149900, display: "₹1,499.00" }} />);
    expect(screen.getByText("₹1,499.00")).toBeInTheDocument();
  });
});
