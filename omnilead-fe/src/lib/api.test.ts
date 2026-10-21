import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

async function loadApi(env: Record<string, string> = {}) {
  vi.resetModules();
  for (const [k, v] of Object.entries(env)) vi.stubEnv(k, v);
  return await import("./api");
}

function mockFetch(impl: (url: string, init?: RequestInit) => Promise<Response> | Response) {
  const fn = vi.fn(async (url: string, init?: RequestInit) => impl(url, init));
  vi.stubGlobal("fetch", fn);
  return fn;
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

beforeEach(() => vi.unstubAllEnvs());
afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("api client", () => {
  it("memakai NEXT_PUBLIC_API_URL tanpa slash akhir dan menambah X-API-Key bila ada", async () => {
    const { api } = await loadApi({ NEXT_PUBLIC_API_URL: "http://be:9000/", NEXT_PUBLIC_API_KEY: "rahasia" });
    const f = mockFetch(() => json([]));
    await api.leads();
    const [url, init] = f.mock.calls[0];
    expect(url).toBe("http://be:9000/leads");
    expect((init?.headers as Record<string, string>)["x-api-key"]).toBe("rahasia");
    expect(init?.cache).toBe("no-store");
  });

  it("tanpa API key tidak mengirim header x-api-key", async () => {
    const { api } = await loadApi({ NEXT_PUBLIC_API_KEY: "" });
    const f = mockFetch(() => json([]));
    await api.events();
    expect((f.mock.calls[0][1]?.headers as Record<string, string>)["x-api-key"]).toBeUndefined();
  });

  it("error HTTP membawa detail dari BE", async () => {
    const { api, ApiError } = await loadApi();
    mockFetch(() => json({ detail: "Agent dijeda. Semua aksi ditahan." }, 423));
    const err = await api.approve("a1").catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({ status: 423, message: "Agent dijeda. Semua aksi ditahan." });
  });

  it("body error non-JSON memakai statusText", async () => {
    const { api } = await loadApi();
    mockFetch(() => new Response("<html>", { status: 502, statusText: "Bad Gateway" }));
    await expect(api.summary()).rejects.toMatchObject({ status: 502, message: "Bad Gateway" });
  });

  it("BE tidak terjangkau = status 0 dengan alamat BE", async () => {
    const { api } = await loadApi({ NEXT_PUBLIC_API_URL: "http://be:9000" });
    mockFetch(() => {
      throw new TypeError("fetch failed");
    });
    await expect(api.channels()).rejects.toMatchObject({ status: 0, message: expect.stringContaining("http://be:9000") });
  });

  it("approve mengirim edited_text; reject mengirim alasan; pause mengirim flag", async () => {
    const { api } = await loadApi();
    const f = mockFetch(() => json({}));
    await api.approve("a1", "teks baru");
    await api.reject("a1", "terlalu formal");
    await api.setPause(true);
    await api.undoMerge("m1");
    const bodies = f.mock.calls.map(([u, i]) => [u, i?.body]);
    expect(bodies[0]).toEqual([expect.stringContaining("/actions/a1/approve"), '{"edited_text":"teks baru"}']);
    expect(bodies[1]).toEqual([expect.stringContaining("/actions/a1/reject"), '{"reason":"terlalu formal"}']);
    expect(bodies[2]).toEqual([expect.stringContaining("/settings/pause"), '{"paused":true}']);
    expect(String(bodies[3][0])).toContain("/actions/m1/undo-merge");
  });
});
