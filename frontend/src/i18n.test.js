import { describe, expect, it } from "vitest";
import { STRINGS, translate } from "./i18n.js";
import { inDays, rupees } from "./shared/format.js";
import { parseSpeech } from "./shared/speech.js";

describe("i18n", () => {
  it("returns Telugu text and null (caller falls back to English) for unknown keys", () => {
    expect(translate("te", "login")).toBe("లాగిన్");
    expect(translate("te", "no_such_key")).toBeNull();
    expect(translate("en", "login")).toBeNull();
  });
  it("every Telugu string is non-empty", () => {
    for (const v of Object.values(STRINGS.te)) expect(v.trim().length).toBeGreaterThan(0);
  });
});

describe("format", () => {
  it("formats rupees with Indian grouping", () => {
    expect(rupees(123456)).toBe("₹1,23,456");
    expect(rupees(null)).toBe("-");
  });
  it("computes future dates", () => {
    expect(inDays(1) > inDays(0)).toBe(true);
  });
});

describe("voice parsing", () => {
  it("parses English", () => {
    expect(parseSpeech("Paddy 120 quintals grade A")).toEqual({ crop: "paddy", quantity: 120, quality: "A" });
  });
  it("parses Telugu crop words and Telugu digits", () => {
    expect(parseSpeech("వరి ౧౫౦ క్వింటాళ్లు")).toEqual({ crop: "paddy", quantity: 150, quality: null });
    expect(parseSpeech("పత్తి 40").crop).toBe("cotton");
  });
  it("handles nothing recognised", () => {
    expect(parseSpeech("hello")).toEqual({ crop: null, quantity: null, quality: null });
  });
});
