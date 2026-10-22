import { describe, expect, it } from "vitest";
import {
  adaptAction,
  adaptAudit,
  adaptEvent,
  adaptLead,
  adaptLeadDetail,
  adaptTrace,
} from "./adapt";
import type { BeAction, BeChannel, BeEvent, BeLead } from "./api";
import { channelIconUrl } from "./channel-icons";

const lead: BeLead = {
  id: "l1",
  name: "Ani",
  company: "PT Maju Jaya",
  phones: ["6281234500001"],
  emails: ["ani@majujaya.example"],
  handles: ["instagram:ani.majujaya"],
  stage: "penawaran",
  summary: "ringkasan",
  score: 86,
  label: "Hot",
  score_reason: "korporat",
  created_at: "2026-10-21T00:00:00Z",
  updated_at: "2026-10-21T00:00:00Z",
};

const event = (over: Partial<BeEvent> = {}): BeEvent => ({
  id: "e1",
  channel: "instagram",
  kind: "comment",
  external_id: "x",
  sender: { handle: "@ani", name: "Ani", phone: null, email: null },
  text: "harga?",
  ts: "2026-10-21T08:00:00Z",
  post_ref: "p1",
  comment_ref: "c1",
  lead_id: "l1",
  status: "analyzed",
  triage: { urgency: "tinggi", urgency_reason: "tenggat dekat" },
  review_reason: "",
  trace: null,
  ...over,
});

const action = (over: Partial<BeAction> = {}): BeAction => ({
  id: "a1",
  channel: "instagram",
  kind: "reply_comment",
  post_ref: "p1",
  comment_ref: "c1",
  text: "halo",
  reason: "alasan",
  recipient: "@ani",
  due_at: null,
  payload: {},
  guard: [],
  public: false,
  lead_id: "l1",
  event_id: "e1",
  trace: null,
  status: "pending",
  created_at: "2026-10-21T08:00:00Z",
  edited: false,
  error: null,
  reject_reason: null,
  result_ref: null,
  ...over,
});

const channels: BeChannel[] = [
  {
    channel: "instagram",
    connected: true,
    detail: "",
    capabilities: [
      { action: "reply_comment", available: true, path: "official_api", note: "" },
      { action: "send_message", available: false, path: "handoff", note: "" },
    ],
  },
];

describe("adaptEvent", () => {
  it("analyzed dengan aksi menunggu = menunggu, tanpa aksi = selesai", () => {
    expect(adaptEvent(event(), lead, 2).status).toBe("menunggu");
    expect(adaptEvent(event(), lead, 0).status).toBe("selesai");
  });

  it("status review/held menunggu, agent_error = baru", () => {
    expect(adaptEvent(event({ status: "review" }), lead, 0).status).toBe("menunggu");
    expect(adaptEvent(event({ status: "held" }), lead, 0).reason).toContain("dijeda");
    const err = adaptEvent(event({ status: "agent_error", review_reason: "agen mati" }), lead, 0);
    expect(err.status).toBe("baru");
    expect(err.reason).toContain("agen mati");
  });

  it("menggabungkan nama dan perusahaan, skor dari lead", () => {
    const a = adaptEvent(event(), lead, 0);
    expect(a.authorName).toBe("Ani, PT Maju Jaya");
    expect(a).toMatchObject({ score: "hot", scoreValue: 86, urgency: "tinggi", kind: "komentar" });
  });

  it("tanpa triage/lead: urgensi rendah, skor cold", () => {
    const a = adaptEvent(event({ triage: null, sender: { handle: "", name: null, phone: "62812", email: null } }), undefined, 0);
    expect(a).toMatchObject({ urgency: "rendah", score: "cold", scoreValue: 0, authorName: "62812" });
  });
});

describe("adaptAction", () => {
  it("jalur API bila kapabilitas tersedia, handoff bila tidak", () => {
    expect(adaptAction(action(), channels).path).toBe("official_api");
    expect(adaptAction(action({ kind: "send_message", comment_ref: null }), channels).path).toBe("handoff");
    expect(adaptAction(action({ channel: "email" }), channels).path).toBe("handoff");
  });

  it("aksi yang sudah dialihkan ke handoff tetap handoff", () => {
    expect(adaptAction(action({ status: "awaiting_manual_send" }), channels).path).toBe("handoff");
  });

  it("aksi internal tidak butuh kanal", () => {
    for (const kind of ["crm_update", "followup", "merge"] as const) {
      const a = adaptAction(action({ kind, channel: "email" }), channels);
      expect(a.internal).toBe(true);
      expect(a.path).toBe("official_api");
    }
  });

  it("private reply IG dikenali; balasan publik diberi peringatan terlihat publik", () => {
    const dm = adaptAction(action({ kind: "send_message", comment_ref: "c1" }), channels);
    expect(dm.kind).toBe("private_reply");
    expect(dm.title).toContain("Private reply");
    const pub = adaptAction(action({ public: true }), channels);
    expect(pub.isPublic).toBe(true);
    expect(pub.riskNote).toContain("terlihat publik");
  });

  it("catatan Guard non-pass masuk riskNote; teks CRM disusun dari payload", () => {
    const a = adaptAction(
      action({ guard: [{ check: "nada", status: "warn", note: "Janji berlebihan" }] }),
      channels,
    );
    expect(a.riskNote).toContain("Janji berlebihan");
    const crm = adaptAction(action({ kind: "crm_update", text: "", payload: { stage: "penawaran", tags: ["hot"] } }), channels);
    expect(crm.text).toBe('Tahap penjualan menjadi "penawaran" (hot)');
  });

  it("payload merge dibawa untuk kartu merge", () => {
    const m = adaptAction(
      action({ kind: "merge", payload: { source_lead_id: "a", target_lead_id: "b", confidence: 0.9, evidence: ["x"] } }),
      channels,
    );
    expect(m.payload.confidence).toBe(0.9);
  });
});

describe("adaptTrace", () => {
  it("tanpa goal = tidak ada trace", () => {
    expect(adaptTrace(null, [], event())).toBeUndefined();
    expect(adaptTrace({}, [], event())).toBeUndefined();
  });

  it("memetakan langkah, menggabung Guard per pemeriksaan, dan alasan tinjauan", () => {
    const t = adaptTrace(
      {
        goal: "Tanggapi",
        plan: ["a"],
        steps: [{ n: 1, tool: "get_timeline", input: { lead: "x" }, result: "ok" }],
        guard_summary: "2/3 lolos",
      },
      [
        action({ guard: [{ check: "konsistensi_harga", status: "pass", note: "" }] }),
        action({
          id: "a2",
          guard: [
            { check: "konsistensi_harga", status: "block", note: "salah" },
            { check: "internal", status: "pass", note: "" },
          ],
        }),
      ],
      event({ status: "review", review_reason: "dicurigai" }),
    );
    expect(t?.steps[0]).toEqual({ tool: "get_timeline", input: "lead=x", output: "ok" });
    expect(t?.guard).toContainEqual({ label: "Harga sesuai katalog", passed: false });
    expect(t?.guard.some((g) => g.label === "Perubahan internal")).toBe(false);
    expect(t?.guard).toContainEqual({ label: "dicurigai", passed: false });
  });
});

describe("lead dan audit", () => {
  it("kanal lead diturunkan dari identitas", () => {
    expect(adaptLead(lead).channels.sort()).toEqual(["email", "instagram", "whatsapp"]);
    expect(adaptLead({ ...lead, label: null, score: null, stage: "aneh" })).toMatchObject({
      score: "cold",
      scoreValue: 0,
      stage: "baru",
    });
  });

  it("detail lead memuat merge yang bisa dipisah", () => {
    const d = adaptLeadDetail({
      lead,
      timeline: [{ ts: null, direction: "in", channel: "email", text: "hai" }],
      merge_evidence: [],
      undoable_merges: [{ action_id: "m1", source_name: null, evidence: ["Nama sama"] }],
    });
    expect(d.undoableMerges).toEqual([{ actionId: "m1", sourceName: "profil lain", evidence: ["Nama sama"] }]);
  });

  it("label audit dalam bahasa awam, event tak dikenal apa adanya", () => {
    const base = { id: 1, ts: "t", action_id: null, detail: "d", actor: "owner", channel: null, lead_id: null };
    expect(adaptAudit({ ...base, event: "identity_split" }).event).toBe("Profil dipisah kembali");
    expect(adaptAudit({ ...base, event: "executed" }).event).toBe("Terkirim");
    expect(adaptAudit({ ...base, event: "event_baru_x" }).event).toBe("event_baru_x");
  });

  it("detail dan pelaku audit tanpa istilah internal", () => {
    const base = { id: 1, ts: "t", action_id: null, event: "proposed", actor: "agent", channel: null, lead_id: null };
    expect(adaptAudit({ ...base, detail: "crm_update di email untuk -" })).toMatchObject({ detail: "Update CRM di Email", actor: "Agen" });
    expect(adaptAudit({ ...base, detail: "followup di whatsapp untuk 0812" }).detail).toBe("Follow-up di WhatsApp untuk 0812");
    expect(adaptAudit({ ...base, detail: "skor=48 Warm" }).detail).toBe("Skor 48 (Warm)");
    expect(adaptAudit({ ...base, detail: "teks bebas" }).detail).toBe("teks bebas");
  });
});

describe("ikon kanal", () => {
  it("kanal aktif memakai glyph Simple Icons", () => {
    expect(channelIconUrl("email")).toContain("cdn.simpleicons.org/gmail");
    expect(channelIconUrl("instagram")).toContain("cdn.simpleicons.org/instagram");
  });
});
