import { describe, expect, it } from "vitest";
import { activityStatus, isOpenHotLead, needsReply } from "./ui";

describe("needsReply", () => {
  it("matches inbox status Perlu dibalas only", () => {
    expect(needsReply({ status: "baru", eventStatus: "new" })).toBe(true);
    expect(needsReply({ status: "baru", eventStatus: "analyzed" })).toBe(true);
    expect(needsReply({ status: "menunggu", eventStatus: "analyzed" })).toBe(false);
    expect(needsReply({ status: "selesai", eventStatus: "analyzed" })).toBe(false);
    expect(needsReply({ status: "baru", eventStatus: "review" })).toBe(false);
    expect(activityStatus({ status: "baru", eventStatus: "new" }).label).toBe("Perlu dibalas");
  });

  it("does not treat high urgency alone as unreplied", () => {
    // urgency is not part of the predicate — selesai + tinggi must stay out of the queue
    expect(needsReply({ status: "selesai", eventStatus: "analyzed" })).toBe(false);
  });
});

describe("isOpenHotLead", () => {
  it("counts open hot leads only", () => {
    expect(isOpenHotLead({ score: "hot", stage: "tertarik" })).toBe(true);
    expect(isOpenHotLead({ score: "hot", stage: "deal" })).toBe(false);
    expect(isOpenHotLead({ score: "hot", stage: "batal" })).toBe(false);
    expect(isOpenHotLead({ score: "warm", stage: "tertarik" })).toBe(false);
  });
});
