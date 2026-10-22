import { describe, expect, it } from "vitest";
import { applyEvent, finishTurn, parseLine, readNdjson, type ChatEvent, type ChatTurn } from "./chat";

const blank = (): ChatTurn => ({ id: "t", role: "agent", text: "", steps: [], error: "", done: false });

describe("chat stream", () => {
  it("parseLine ignores blanks and junk", () => {
    expect(parseLine("")).toBeNull();
    expect(parseLine("bukan json")).toBeNull();
    expect(parseLine('{"type":"message","text":null}')).toBeNull();
    expect(parseLine('{"type":"unknown"}')).toBeNull();
    expect(parseLine('{"type":"message","text":"hai"}')).toEqual({ type: "message", text: "hai" });
  });

  it("shows thought summary deltas during work and attaches them to the right step", () => {
    let turn = applyEvent(blank(), { type: "thoughts", text: "Periksa " });
    turn = applyEvent(turn, { type: "thoughts", text: "jadwal." });
    expect(turn.thinking).toBe("Periksa jadwal.");
    turn = applyEvent(turn, { type: "step", tool: "lihat_tugas", args: {}, label: "Lihat tugas", say: "Saya periksa." });
    expect(turn.steps[0].thoughts).toBe("Periksa jadwal.");
    expect(turn.thinking).toBe("");
    turn = applyEvent(turn, { type: "thoughts", text: "Rangkum hasil." });
    turn = applyEvent(turn, { type: "message", text: "Tidak ada tugas." });
    expect(turn.thoughts).toBe("Rangkum hasil.");
  });

  it("cancellation settles every running indicator", () => {
    const turn = applyEvent(blank(), { type: "step", tool: "x", args: {}, label: "X", say: "" });
    expect(finishTurn(turn, "Dihentikan")).toMatchObject({ done: true, error: "Dihentikan", steps: [{ status: "stopped" }] });
  });

  it("matches tool results by tool name", () => {
    let turn = applyEvent(blank(), { type: "step", tool: "x", args: {}, label: "X", say: "" });
    turn = applyEvent(turn, { type: "tool_result", tool: "y", ok: true, summary: "Y selesai", data: {}, refresh: false });
    expect(turn.steps[0].status).toBe("running");
  });

  it("step -> tool_result -> message builds one finished turn", () => {
    let t = blank();
    t = applyEvent(t, { type: "step", tool: "cari_lead", args: { label: "Hot" }, label: "Mencari prospek", say: "Aku cari dulu." });
    expect(t.steps[0].status).toBe("running");
    t = applyEvent(t, { type: "tool_result", tool: "cari_lead", ok: true, summary: "1 prospek ditemukan.", data: { daftar: [] }, refresh: false });
    expect(t.steps[0]).toMatchObject({ status: "done", summary: "1 prospek ditemukan.", say: "Aku cari dulu." });
    t = applyEvent(t, { type: "message", text: "Ani paling panas." });
    expect(t).toMatchObject({ text: "Ani paling panas.", done: true });
  });

  it("failed tool and error event", () => {
    let t = applyEvent(blank(), { type: "step", tool: "x", args: {}, label: "X", say: "" });
    t = applyEvent(t, { type: "tool_result", tool: "x", ok: false, summary: "gagal", data: {}, refresh: false });
    expect(t.steps[0].status).toBe("failed");
    t = applyEvent(t, { type: "error", message: "Agen mati" });
    expect(t).toMatchObject({ error: "Agen mati", done: true });
  });

  it("readNdjson handles lines split across chunks", async () => {
    const enc = new TextEncoder();
    const chunks = ['{"type":"message","te', 'xt":"a"}\n{"type":"mess', 'age","text":"b"}'];
    const body = new ReadableStream<Uint8Array>({
      start(c) { chunks.forEach((x) => c.enqueue(enc.encode(x))); c.close(); },
    });
    const seen: ChatEvent[] = [];
    await readNdjson(body, (e) => seen.push(e));
    expect(seen.map((e) => (e as { text: string }).text)).toEqual(["a", "b"]);
  });
});
