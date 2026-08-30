import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { AnalyticsResult } from "./AnalyticsResult";

// A dashboard widget stores a `chart_type`, and an analytics operation may
// return its payload as an array (frequency_distribution, time_series_summary)
// rather than a scalar. Both were previously dropped on the floor, which made
// an array-only result render as a visibly empty card.
describe("AnalyticsResult", () => {
  const distribution = {
    operation: "frequency_distribution",
    column: "signup_score",
    distribution: [
      { value: 91, count: 2 },
      { value: 84, count: 1 },
    ],
    distinct_values_total: 2,
  };

  it("renders an array payload as a table with a column per key", () => {
    render(<AnalyticsResult result={distribution} display="table" />);

    expect(screen.getByRole("columnheader", { name: "value" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "count" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "91" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "84" })).toBeInTheDocument();
  });

  it("still renders the array payload when the widget asks for a stat it cannot show", () => {
    // No badge-able scalar exists here, so falling back to the table is what
    // keeps the card from rendering empty.
    render(<AnalyticsResult result={distribution} display="stat" />);

    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "91" })).toBeInTheDocument();
  });

  it("shows a scalar result as a badge and omits the table for a stat display", () => {
    render(<AnalyticsResult result={{ operation: "mean", value: 84 }} display="stat" />);

    expect(screen.getByText("value: 84")).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });

  it("falls back to a field/value table for a scalar result asked to display as a table", () => {
    render(<AnalyticsResult result={{ operation: "mean", value: 84 }} display="table" />);

    expect(screen.getByRole("cell", { name: "value" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "84" })).toBeInTheDocument();
  });

  it("always exposes the raw payload for inspection", () => {
    render(<AnalyticsResult result={distribution} display="table" />);

    expect(screen.getByText("Full result")).toBeInTheDocument();
  });
});
