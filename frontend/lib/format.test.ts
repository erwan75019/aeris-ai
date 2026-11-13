import { describe, expect, it } from "vitest";

import { formatAltitude, formatRate, formatUtc } from "./format";

describe("aviation value formatting", () => {
  it("does not turn missing values into zero", () => {
    expect(formatAltitude(null)).toBe("—");
    expect(formatRate(null)).toBe("—");
  });

  it("formats feet and signed vertical rate", () => {
    expect(formatAltitude(31250)).toBe("31,250 ft");
    expect(formatRate(-820)).toBe("−820 fpm");
  });

  it("renders replay timestamps explicitly in UTC", () => {
    expect(formatUtc("2025-01-15T12:30:00Z")).toBe("12:30:00 UTC");
  });
});
