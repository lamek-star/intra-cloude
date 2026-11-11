import { describe, expect, it } from "vitest";
import { licenceNotice, type Licence } from "./license";

const base: Licence = {
  state: "trial",
  enforced: true,
  trial_days: 30,
  trial_ends: "2026-12-11T00:00:00Z",
  days_left: 23,
  clock_back: false,
  pc_code: "PC-0F7A-EA68-C3B9-C607",
  serial: null,
  kind: null,
  activated_at: null,
  can_activate: true,
};

describe("the licence banner", () => {
  it("counts the trial days and warns in the last week", () => {
    expect(licenceNotice(base)).toEqual({ tone: "info", text: "Trial: 23 days left. Enter your serial number any time." });
    expect(licenceNotice({ ...base, days_left: 1 })?.tone).toBe("warning");
    expect(licenceNotice({ ...base, days_left: 1 })?.text).toContain("1 day left");
  });

  it("says read-only after the trial, and why when the clock was set back", () => {
    expect(licenceNotice({ ...base, state: "expired" })?.tone).toBe("danger");
    expect(licenceNotice({ ...base, state: "expired", clock_back: true })?.text).toContain("clock was set back");
  });

  it("says nothing when licensed or where no licence is needed", () => {
    expect(licenceNotice({ ...base, state: "active" })).toBeNull();
    expect(licenceNotice({ ...base, state: "not_enforced", enforced: false })).toBeNull();
    expect(licenceNotice(undefined)).toBeNull();
  });
});
