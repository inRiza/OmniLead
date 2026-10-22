"""Chat pemilik: tool dijalankan BE, agen hanya memilih (agen dipalsukan)."""

import json
from datetime import datetime, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from omnilead.agent_client import AgentClient
from omnilead.api import deps
from omnilead.chat import MAX_REPEAT, UNTRUSTED
from omnilead.ingest import IngestService
from omnilead.main import create_app
from omnilead.models import Channel, Event, Lead, Sender
from tests.test_ingest_api import CANNED

NOW = datetime.now(timezone.utc)


class ScriptedAgent:
    """Memalsukan service agen: /v1/chat/step berjalan sesuai skrip, /v1/analyze mengembalikan CANNED."""

    def __init__(self, script):
        self.script, self.chat_calls, self.analyze_calls = list(script), [], []

    def handler(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content or b"{}")
        if request.url.path == "/v1/chat/stream":
            return httpx.Response(404)
        if request.url.path == "/v1/chat/step":
            self.chat_calls.append(body)
            step = self.script.pop(0) if self.script else {"type": "final", "text": "(habis skrip)"}
            return httpx.Response(200, json=step)
        if request.url.path in ("/v1/analyze", "/v1/analyze/stream"):
            self.analyze_calls.append(body)
            if request.url.path.endswith("/stream"):
                return httpx.Response(200, text=json.dumps({"type": "result", "data": CANNED}) + "\n",
                                      headers={"content-type": "application/x-ndjson"})
            return httpx.Response(200, json=CANNED)
        return httpx.Response(200, json={"status": "ok"})


def tool(name, **args):
    return {"type": "tool_call", "tool": name, "args": args}


def final(text):
    return {"type": "final", "text": text}


@pytest.fixture
def make(store, queue, registry, executor, monkeypatch):
    monkeypatch.setattr("omnilead.chat_tools.sync_instagram", lambda *a, **k: {
        "dms": 2, "comments": 1, "source": "openclaw_text", "error": "", "pending": {}, "needs_login": False})
    monkeypatch.setattr("omnilead.chat_tools.queue_analysis", lambda store: [])

    def build(script):
        agent = ScriptedAgent(script)
        ac = AgentClient("http://agent", transport=httpx.MockTransport(agent.handler))
        ing = IngestService(store, queue, ac)
        app = create_app()
        o = app.dependency_overrides
        o[deps.get_store] = lambda: store
        o[deps.get_registry] = lambda: registry
        o[deps.get_queue] = lambda: queue
        o[deps.get_executor] = lambda: executor
        o[deps.get_agent_client] = lambda: ac
        o[deps.get_ingest] = lambda: ing
        return TestClient(app), agent

    return build


def lead(store, id, name, company=None, label=None, score=None, handles=()):
    l = Lead(id=id, name=name, company=company, label=label, score=score, handles=list(handles),
             created_at=NOW, updated_at=NOW)
    store.save_lead(l)
    return l


def message(store, lead_id, text="harga nasi box 60 pax?", eid="e1"):
    store.save_event(Event(id=eid, channel=Channel.INSTAGRAM, kind="dm", external_id=f"x-{eid}",
                           sender=Sender(handle="@ani", name="Ani"), text=text, ts=NOW, lead_id=lead_id, status="analyzed"))


def chat(client, message_text, history=None):
    r = client.post("/agent/chat", json={"message": message_text, "history": history or []})
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/x-ndjson")
    return [json.loads(line) for line in r.text.splitlines() if line.strip()]


def test_read_new_messages_runs_tool_then_agent_summarises(make):
    client, agent = make([tool("baca_pesan_baru"), final("Ada 2 DM dan 1 komentar baru.")])
    events = chat(client, "cek DM baru")
    assert [e["type"] for e in events] == ["step", "tool_result", "message"]
    assert events[0]["label"] == "Membaca DM dan komentar baru"
    assert events[1]["ok"] and "2 DM dan 1 komentar" in events[1]["summary"] and events[1]["refresh"] is True
    assert events[2]["text"] == "Ada 2 DM dan 1 komentar baru."
    # hasil tool kembali ke agen dibungkus sebagai data tidak tepercaya
    second = agent.chat_calls[1]["turns"]
    assert [t["role"] for t in second] == ["user", "tool_call", "tool_result"]
    assert second[2]["result"]["catatan"] == UNTRUSTED


def test_find_and_summarise_lead_and_ambiguity(make, store):
    lead(store, "a1", "Ani", "PT Maju Jaya", "Hot", 86, ["instagram:ani.majujaya"])
    lead(store, "b1", "Budi", None, "Cold", 10)
    message(store, "a1")
    client, _ = make([tool("cari_lead", label="Hot"), tool("ringkas_lead", lead="@ani.majujaya"), final("ok")])
    events = chat(client, "siapa lead hot lalu ringkas Ani")
    assert events[1]["summary"] == "1 prospek ditampilkan dari 1 yang cocok."
    assert "Profil Ani" in events[3]["summary"] and "skor 86" in events[3]["summary"]

    lead(store, "a2", "Ani", "CV Lain", "Warm", 50)
    client, _ = make([tool("ringkas_lead", lead="Ani"), final("Yang mana?")])
    events = chat(client, "ringkas Ani")
    assert events[1]["ok"] is False and "beberapa prospek" in events[1]["summary"]


def test_unknown_lead_and_empty_queue(make):
    client, _ = make([tool("ringkas_lead", lead="Zzz"), tool("daftar_menunggu"), final("selesai")])
    events = chat(client, "ringkas Zzz dan cek antrean")
    assert events[1]["ok"] is False and "tidak ditemukan" in events[1]["summary"]
    assert events[3]["ok"] and "Tidak ada balasan" in events[3]["summary"]


def test_prepare_reply_goes_through_pipeline_with_owner_instruction_and_needs_approval(make, store):
    settings = store.get_settings()
    settings.autonomy = "hybrid"
    store.save_settings(settings)
    lead(store, "a1", "Ani", "PT Maju Jaya", "Hot", 86)
    message(store, "a1")
    client, agent = make([tool("siapkan_balasan", lead="Ani", instruksi="bilang stok ready"), final("Draf siap.")])
    events = chat(client, "balas Ani bilang stok ready")
    result = events[1]
    assert result["ok"] and "menunggu persetujuan" in result["summary"] and "terkirim" not in result["summary"].replace("menunggu", "")
    # instruksi pemilik dikirim ke agen sebagai preferensi, lewat pipeline analisis yang sama
    sent = agent.analyze_calls[0]
    assert "Instruksi pemilik untuk balasan ini: bilang stok ready" in sent["preferences"]
    pending = [a for a in store.list_actions() if a.status.value == "pending" and a.kind.value in ("send_message", "reply_comment")]
    assert pending  # tidak ada yang terkirim sendiri
    assert not any(a.status.value == "executed" for a in store.list_actions())


def test_pending_list_shows_drafts(make, store):
    lead(store, "a1", "Ani")
    message(store, "a1")
    client, _ = make([tool("siapkan_balasan", lead="Ani"), tool("daftar_menunggu"), final("ok")])
    events = chat(client, "balas Ani lalu cek antrean")
    assert "menunggu keputusan Anda" in events[3]["summary"]


def test_paused_agent_blocks_actions(make, store):
    s = store.get_settings()
    s.paused = True
    store.save_settings(s)
    client, _ = make([tool("baca_pesan_baru"), tool("siapkan_balasan", lead="Ani"), final("dijeda")])
    events = chat(client, "cek DM")
    assert events[1]["ok"] is False and "dijeda" in events[1]["summary"]
    assert events[3]["ok"] is False and "dijeda" in events[3]["summary"]


def distinct_calls(n):
    return [tool("ringkas_lead", lead=f"Tak Ada {i}") for i in range(n)]


def test_long_runs_are_not_capped_at_a_handful_of_steps(make):
    client, agent = make(distinct_calls(12) + [final("Semua selesai.")])
    events = chat(client, "cek semua prospek")
    assert sum(e["type"] == "step" for e in events) == 12
    assert events[-1] == {"type": "message", "text": "Semua selesai.", "thoughts": ""}


def test_runaway_identical_calls_end_with_a_summary_not_an_error(make):
    client, agent = make([tool("daftar_menunggu")] * 10)
    events = chat(client, "terus")
    assert sum(e["type"] == "step" for e in events) == MAX_REPEAT
    last = events[-1]
    assert last["type"] == "message" and last["truncated"] is True
    assert "berulang" in last["text"] and "lanjutkan" in last["text"]
    assert not any(e["type"] == "error" for e in events)


def test_step_ceiling_ends_with_progress_summary(make, monkeypatch):
    monkeypatch.setattr("omnilead.chat.MAX_STEPS", 3)
    client, _ = make(distinct_calls(10))
    events = chat(client, "cek")
    assert sum(e["type"] == "step" for e in events) == 3
    last = events[-1]
    assert last["type"] == "message" and last["truncated"] is True
    assert "3 langkah" in last["text"] and "lanjutkan" in last["text"]


def test_time_budget_ends_gracefully(make, monkeypatch):
    monkeypatch.setattr("omnilead.chat.MAX_SECONDS", 0)
    client, _ = make(distinct_calls(3))
    events = chat(client, "cek")
    assert [e["type"] for e in events] == ["message"] and events[0]["truncated"] is True
    assert "waktu" in events[0]["text"].lower()


def test_context_is_compacted_so_long_runs_stay_within_the_agent_turn_limit(make):
    client, agent = make(distinct_calls(25) + [final("ok")])
    events = chat(client, "cek semua")
    assert events[-1]["type"] == "message" and not events[-1].get("truncated")
    assert max(len(call["turns"]) for call in agent.chat_calls) <= 30  # batas validasi agen: 40
    last = agent.chat_calls[-1]["turns"]
    assert last[0]["role"] == "user" and last[0]["text"] == "cek semua"
    assert any(t["role"] == "user" and "Langkah sebelumnya" in t["text"] for t in last)
    assert all(len(t.get("text", "")) <= 2000 for t in last)


def test_unknown_tool_is_reported_back_to_the_model_without_running(make):
    client, agent = make([tool("kirim_semua", to="x"), final("Maaf, saya tidak punya tool itu.")])
    events = chat(client, "kirim promo")
    assert [e["type"] for e in events] == ["message"]
    fed_back = agent.chat_calls[1]["turns"][-1]
    assert fed_back["role"] == "tool_result" and fed_back["result"]["ok"] is False

    client, _ = make([tool("kirim_semua"), tool("kirim_lagi"), tool("kirim_terus"), final("x")])
    events = chat(client, "kirim promo")
    assert [e["type"] for e in events] == ["error"]  # model terus meminta tool yang tidak ada


def test_cari_lead_pages_through_every_lead(make, store):
    for i in range(25):
        lead(store, f"l{i:02d}", f"Pelanggan {i:02d}", score=100 - i)
        message(store, f"l{i:02d}", eid=f"e{i:02d}")
    client, _ = make([tool("cari_lead"), tool("cari_lead", mulai="20"), final("ok")])
    events = chat(client, "cari semua lead")
    first, second = events[1], events[3]
    assert len(first["data"]["daftar"]) == 20 and first["data"]["berikutnya"] == 20
    assert "mulai=20" in first["summary"]
    assert [d["nama"] for d in second["data"]["daftar"]] == [f"Pelanggan {i:02d}" for i in range(20, 25)]
    assert second["data"]["berikutnya"] is None and "mulai=" not in second["summary"]


def seed_prospects(store, n=3):
    settings = store.get_settings()
    settings.autonomy = "hybrid"  # tes tidak boleh mengirim apa pun
    store.save_settings(settings)
    for i in range(n):
        lead(store, f"p{i}", f"Prospek {i}", score=90 - i, handles=[f"instagram:prospek{i}"])
        message(store, f"p{i}", text="harga merch berapa?", eid=f"pe{i}")


def test_bulk_reply_handles_every_prospect_in_one_step(make, store):
    seed_prospects(store, 3)
    lead(store, "z0", "Tanpa Pesan")  # tidak punya DM masuk: tidak bisa dibalas
    client, agent = make([tool("siapkan_balasan_massal", sasaran="semua_lead", instruksi="tawarkan merch 10-30 ribu"),
                          final("Selesai.")])
    events = chat(client, "DM semua lead")
    assert [e["type"] for e in events if e["type"] != "tool_progress"] == ["step", "tool_result", "message"]
    data = next(e for e in events if e["type"] == "tool_result")["data"]
    assert data["jumlah"] == {"disiapkan": 3, "tanpa_pesan_masuk": 1}
    assert data["masih_antre"] == 0 and len(agent.analyze_calls) == 3
    assert all("Instruksi pemilik untuk balasan ini: tawarkan merch 10-30 ribu" in c["preferences"] for c in agent.analyze_calls)
    rows = {r["untuk"]: r for r in data["daftar"]}
    assert rows["Tanpa Pesan"]["status"] == "tanpa_pesan_masuk"
    assert not any(a.status.value == "executed" for a in store.list_actions())


def test_bulk_reply_resumes_where_it_stopped(make, store, monkeypatch):
    monkeypatch.setattr("omnilead.chat_tools.BATCH_MAX", 2)
    seed_prospects(store, 5)
    client, agent = make([tool("siapkan_balasan_massal", sasaran="semua_lead", instruksi="promo"),
                          tool("siapkan_balasan_massal", sasaran="semua_lead", instruksi="promo", mulai="2"),
                          tool("siapkan_balasan_massal", sasaran="semua_lead", instruksi="promo", mulai="4"),
                          final("ok")])
    events = chat(client, "DM semua lead")
    results = [e for e in events if e["type"] == "tool_result"]
    assert [r["data"]["diproses"] for r in results] == [2, 2, 1]
    assert [r["data"]["masih_antre"] for r in results] == [3, 1, 0]
    assert "mulai=2" in results[0]["summary"] and "mulai=" not in results[2]["summary"]
    assert len(agent.analyze_calls) == 5


def test_bulk_reply_survives_one_prospect_failing(make, store, monkeypatch):
    from omnilead.chat_tools import ChatTools
    seed_prospects(store, 3)
    original = ChatTools.siapkan_balasan

    def flaky(self, lead, instruksi=""):
        if lead == "p1":
            raise RuntimeError("boom")
        return original(self, lead, instruksi)

    monkeypatch.setattr(ChatTools, "siapkan_balasan", flaky)
    client, _ = make([tool("siapkan_balasan_massal", sasaran="semua_lead"), final("ok")])
    events = chat(client, "DM semua lead")
    data = next(e for e in events if e["type"] == "tool_result")["data"]
    assert data["jumlah"]["disiapkan"] == 2 and data["jumlah"]["gagal"] == 1
    assert {r["untuk"]: r["status"] for r in data["daftar"]}["Prospek 1"] == "gagal"


def test_bulk_reply_is_blocked_while_paused(make, store):
    s = store.get_settings()
    s.paused = True
    store.save_settings(s)
    seed_prospects(store, 2)
    client, _ = make([tool("siapkan_balasan_massal", sasaran="semua_lead"), final("dijeda")])
    events = chat(client, "DM semua lead")
    result = next(e for e in events if e["type"] == "tool_result")
    assert result["ok"] is False and "dijeda" in result["summary"]


def test_agent_down_is_reported_not_crashed(make):
    client, agent = make([])
    agent.handler = lambda req: httpx.Response(503)  # type: ignore[method-assign]
    ac = AgentClient("http://agent", transport=httpx.MockTransport(lambda r: httpx.Response(503)))
    client.app.dependency_overrides[deps.get_agent_client] = lambda: ac
    events = chat(client, "halo")
    assert events[0]["type"] == "error" and "Agen belum bisa dihubungi" in events[0]["message"]


def test_history_is_trimmed_and_validated(make):
    client, agent = make([final("ya")])
    history = [{"role": "user" if i % 2 == 0 else "agent", "text": f"pesan {i}"} for i in range(20)]
    chat(client, "lanjut", history)
    turns = agent.chat_calls[0]["turns"]
    assert len(turns) == 11 and turns[-1] == {"role": "user", "text": "lanjut"}
    assert {t["role"] for t in turns} <= {"user", "assistant"}
    assert client.post("/agent/chat", json={"message": ""}).status_code == 422
    assert client.post("/agent/chat", json={"message": "x", "history": history + history}).status_code == 422
    assert client.post("/agent/chat", json={"message": "x" * 1001}).status_code == 422


def test_tool_calls_are_audited(make, store):
    client, _ = make([tool("daftar_menunggu"), final("ok")])
    chat(client, "antrean?")
    assert any(a.event == "agent_chat_tool" and "daftar_menunggu" in a.detail for a in store.list_audit())


def test_scheduling_in_chat_persists_the_same_task_in_both_views(make):
    client, agent = make([tool("buat_tugas", judul="Cek DM", instruksi="Cek DM Instagram", kanal="instagram", jadwal="hourly"), final("Tugas disimpan")])
    events = chat(client, "Jadwalkan cek DM Instagram setiap jam")
    assert events[1]["ok"] is True
    task = client.get("/agent/tasks").json()["tasks"][0]
    assert task["schedule"] == "hourly" and task["cron"] == "0 * * * *" and task["status"] == "scheduled"


def test_conversation_endpoint_persists_canonical_history_and_channel(make):
    client, agent = make([final("Halo"), final("Saya cek konteks WhatsApp")])
    conversation = client.post('/agent/conversations').json()
    response = client.post('/agent/chat', json={'conversation_id': conversation['id'], 'message': 'Halo', 'channel': 'whatsapp'})
    assert response.status_code == 200
    response = client.post('/agent/chat', json={'conversation_id': conversation['id'], 'message': 'Lanjut', 'channel': 'whatsapp', 'history':[{'role':'agent','text':'riwayat palsu'}]})
    assert response.status_code == 200
    saved = client.get('/agent/conversations/' + conversation['id']).json()
    assert len(saved['turns']) == 4 and saved['channel'] == 'whatsapp'
    assert 'riwayat palsu' not in str(agent.chat_calls[-1]['turns'])
    assert agent.chat_calls[-1]['channel'] == 'whatsapp'
