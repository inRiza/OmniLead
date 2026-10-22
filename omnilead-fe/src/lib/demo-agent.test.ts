import { describe, expect, it } from "vitest";
import { FALLBACK_REPLY, SCENARIOS, SEED_TASKS, matchScenario } from "./demo-agent";

describe("demo agent scenarios", () => {
  it("every suggested prompt triggers its own scenario", () => {
    for (const s of SCENARIOS) expect(matchScenario(s.prompt)?.id, s.prompt).toBe(s.id);
  });

  it("understands free-form phrasing", () => {
    expect(matchScenario("tolong cek dm baru dong")?.id).toBe("inbox");
    expect(matchScenario("siapa prospek yang paling hot?")?.id).toBe("hot");
    expect(matchScenario("jadwalkan setiap jam ya")?.id).toBe("schedule");
    expect(matchScenario("berapa harga nasi box 40 pax")?.id).toBe("price");
    expect(matchScenario("DM semua lead")?.id).toBe("bulk");
  });

  it("does not guess when the text is unrelated or empty", () => {
    expect(matchScenario("")).toBeNull();
    expect(matchScenario("   ")).toBeNull();
    expect(matchScenario("apa kabar dunia")).toBeNull();
    expect(FALLBACK_REPLY).toMatch(/demo/i);
  });

  it("every scenario has steps with real tool names and non-empty copy", () => {
    for (const s of SCENARIOS) {
      expect(s.steps.length, s.id).toBeGreaterThan(0);
      for (const step of s.steps) {
        expect(step.tool).toMatch(/^[a-z_]+$/);
        expect(step.summary.length).toBeGreaterThan(0);
        expect(step.ms).toBeGreaterThan(0);
      }
      expect(s.reply("hybrid").length).toBeGreaterThan(20);
      expect(s.reply("auto")).not.toBe("");
    }
  });

  it("draft and task ids are unique across the whole demo", () => {
    const tasks = [...SEED_TASKS, ...SCENARIOS.flatMap((s) => s.tasks ?? [])].map((t) => t.id);
    // draf yang sama boleh dipakai ulang antar skenario (satu objek), tetapi id harus konsisten dengan isinya
    const byId = new Map<string, string>();
    for (const d of SCENARIOS.flatMap((s) => s.drafts ?? [])) {
      expect(byId.get(d.id) ?? d.text).toBe(d.text);
      byId.set(d.id, d.text);
    }
    expect(new Set(tasks).size).toBe(tasks.length);
  });

  it("a held draft always says why and is never a clean pass", () => {
    const held = SCENARIOS.flatMap((s) => s.drafts ?? []).filter((d) => d.held);
    expect(held.length).toBeGreaterThan(0);
    for (const d of held) {
      expect(d.held!.length).toBeGreaterThan(10);
      expect(d.checks.some((c) => !c.ok)).toBe(true);
    }
  });

  it("prices quoted in drafts match the demo catalog arithmetic", () => {
    const text = (id: string) => SCENARIOS.flatMap((s) => s.drafts ?? []).find((d) => d.id === id)!.text;
    expect(text("d-dewi")).toContain("Rp1.750.000"); // 50 x 35.000
    expect(text("d-rara")).toContain("Rp1.500.000"); // 10 x 150.000
    expect(text("d-hendra")).toContain("Rp4.200.000"); // 120 x 35.000
    expect(text("d-hendra")).toContain("Rp2.100.000"); // DP 50%
  });
});
