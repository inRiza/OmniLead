import { NextRequest, NextResponse } from "next/server";

// Browser talks only to this origin. Backend keys and platform tokens stay server-side.
const backend = (process.env.OMNILEAD_BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const allowed = new Set(["auth", "workspaces", "knowledge-bases", "connections", "events", "actions", "leads", "channels", "audit", "settings", "summary", "agent", "test-mode", "instagram", "content-ideas", "handoff", "health", "webhooks"]);
const metaWebhooks = new Set(["instagram", "facebook", "whatsapp"]);

async function forward(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  if (!allowed.has(path[0]) || path.some((p) => p === "." || p === ".." || p.includes("/"))) {
    return NextResponse.json({ detail: "Tidak ditemukan" }, { status: 404 });
  }
  if (path[0] === "webhooks" && (path.length !== 2 || !metaWebhooks.has(path[1]) || !["GET", "POST"].includes(request.method))) {
    return NextResponse.json({ detail: "Tidak ditemukan" }, { status: 404 });
  }
  const headers = new Headers();
  for (const name of ["content-type", "cookie", "origin", "sec-fetch-site", "x-omnilead-workspace", "x-hub-signature-256"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  if (process.env.OMNILEAD_API_KEY) headers.set("x-api-key", process.env.OMNILEAD_API_KEY);
  try {
    const response = await fetch(`${backend}/${path.map(encodeURIComponent).join("/")}${request.nextUrl.search}`, {
      method: request.method, headers, cache: "no-store", redirect: "manual",
      body: ["GET", "HEAD"].includes(request.method) ? undefined : await request.arrayBuffer(),
      signal: AbortSignal.timeout(120_000),
    });
    const outgoing = new Headers({ "Cache-Control": "no-store", "Referrer-Policy": "no-referrer" });
    for (const name of ["content-type", "location"]) {
      const value = response.headers.get(name);
      if (value) outgoing.set(name, value);
    }
    for (const cookie of response.headers.getSetCookie()) outgoing.append("set-cookie", cookie);
    return new Response(response.body, { status: response.status, headers: outgoing });
  } catch {
    return NextResponse.json({ detail: "Backend belum dapat dihubungi. Coba kembali sebentar lagi." }, { status: 502 });
  }
}

export const GET = forward;
export const POST = forward;
export const PATCH = forward;
export const PUT = forward;
export const DELETE = forward;
