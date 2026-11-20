import { describe, expect, it } from "vitest";

import { paiseToRupeesInput, reportSummary, rupeesToPaise } from "../src/lib/format";

describe("format", () => {
  it.each([
    ["149", 14900],
    ["149.5", 14950],
    ["₹1,499.00", 149900],
    [" 99 ", 9900],
  ])("rupeesToPaise(%s)", (text, paise) => expect(rupeesToPaise(text)).toBe(paise));

  it.each(["", "abc", "1.999", "-5"])("rupeesToPaise rejects %s", (t) => expect(rupeesToPaise(t)).toBeNull());

  it("paiseToRupeesInput round-trips", () => {
    expect(paiseToRupeesInput(14900)).toBe("149");
    expect(paiseToRupeesInput(14950)).toBe("149.50");
    expect(paiseToRupeesInput(null)).toBe("");
  });

  it("extracts the summary section", () => {
    expect(reportSummary("# R\n\n## Summary\nSave a lot.\n\n## Plans\nx")).toBe("Save a lot.");
    expect(reportSummary("no summary")).toBe("");
  });
});
