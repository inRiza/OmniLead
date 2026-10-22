"""Chat pemilik: agen memilih tool atau menjawab (model palsu, tanpa jaringan)."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from google.genai import types

from omnilead_agent.chat import (
    TOOLS,
    ChatStepRequest,
    ChatTurn,
    ChatUnavailable,
    build_contents,
    chat_step,
    stream_chat_step,
    _declarations,
    system_instruction,
    clean_args,
)
from omnilead_agent.main import create_app, get_chat_client


def response(*parts):
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=list(parts)))]
    )


def call(name, **args):
    return types.Part(function_call=types.FunctionCall(name=name, args=args))


class FakeClient:
    def __init__(self, reply=None, error=None):
        self.reply, self.error, self.calls = reply, error, []
        self.models = SimpleNamespace(generate_content=self._generate)

    def _generate(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        if self.error:
            raise self.error
        return self.reply


def req(*turns, business="Dapur Bu Rina"):
    return ChatStepRequest(turns=list(turns), business=business)


def test_returns_tool_call_with_cleaned_args():
    client = FakeClient(response(call("siapkan_balasan", lead="Ani", instruksi="bilang stok ready", sembarang="x")))
    out = chat_step(req(ChatTurn(role="user", text="balas Ani bilang stok ready")), client)
    assert out.type == "tool_call" and out.tool == "siapkan_balasan"
    assert out.args == {"lead": "Ani", "instruksi": "bilang stok ready"}  # argumen di luar skema dibuang


def test_returns_final_text():
    out = chat_step(req(ChatTurn(role="user", text="halo")), FakeClient(response(types.Part(text="Halo juga!"))))
    assert (out.type, out.text) == ("final", "Halo juga!")


def test_stream_exposes_summaries_before_the_tool_decision():
    def generate(**kw):
        assert kw["config"].thinking_config.include_thoughts is True
        yield response(types.Part(text="Periksa tugas.", thought=True))
        yield response(types.Part(text="Saya cek jadwal dulu."))
        yield response(call("lihat_tugas"))
    client = SimpleNamespace(models=SimpleNamespace(generate_content_stream=generate))
    events = list(stream_chat_step(req(ChatTurn(role="user", text="lihat jadwal")), client))
    assert [e["type"] for e in events] == ["thoughts", "say", "decision"]
    assert events[-1]["data"]["tool"] == "lihat_tugas"
    assert events[-1]["data"]["thoughts"] == "Periksa tugas."


def test_stream_propagates_provider_failure():
    def generate(**kw):
        raise RuntimeError("offline")
    client = SimpleNamespace(models=SimpleNamespace(generate_content_stream=generate))
    with pytest.raises(ChatUnavailable):
        list(stream_chat_step(req(ChatTurn(role="user", text="halo")), client))


def test_scheduled_execution_cannot_schedule_itself():
    names = [tool.name for tool in _declarations("scheduled", "instagram").function_declarations]
    assert "buat_tugas" not in names and "ubah_tugas" not in names
    assert "cari_lead" in names
    request = req(ChatTurn(role="user", text="Daftarkan pelanggan"))
    request.execution_mode = "scheduled"
    assert "MODE EKSEKUSI TUGAS" in system_instruction(request)


def test_whatsapp_scope_does_not_offer_instagram_inbox_tool():
    names = [tool.name for tool in _declarations("interactive", "whatsapp").function_declarations]
    assert "baca_pesan_baru" not in names


def test_thought_summary_is_separated_from_answer_and_say():
    thought = types.Part(text="Pemilik minta lead panas; perlu cari_lead label Hot.", thought=True)
    out = chat_step(req(ChatTurn(role="user", text="lead panas?")),
                    FakeClient(response(thought, types.Part(text="Aku cari dulu."), call("cari_lead", label="Hot"))))
    assert out.thoughts == "Pemilik minta lead panas; perlu cari_lead label Hot."
    assert out.say == "Aku cari dulu."
    out = chat_step(req(ChatTurn(role="user", text="halo")),
                    FakeClient(response(types.Part(text="sapaan saja", thought=True), types.Part(text="Halo!"))))
    assert (out.text, out.thoughts) == ("Halo!", "sapaan saja")


def test_thinking_summaries_are_requested():
    client = FakeClient(response(types.Part(text="ok")))
    chat_step(req(ChatTurn(role="user", text="x")), client)
    assert client.calls[0]["config"].thinking_config.include_thoughts is True


def test_unknown_tool_is_refused_not_executed():
    out = chat_step(req(ChatTurn(role="user", text="kirim semua")), FakeClient(response(call("kirim_pesan", to="x"))))
    assert out.type == "final" and out.tool == ""


def test_empty_model_answer_has_fallback_text():
    out = chat_step(req(ChatTurn(role="user", text="?")), FakeClient(types.GenerateContentResponse(candidates=[])))
    assert out.type == "final" and out.text


def test_model_failure_is_unavailable():
    with pytest.raises(ChatUnavailable):
        chat_step(req(ChatTurn(role="user", text="x")), FakeClient(error=RuntimeError("quota")))


def test_args_are_truncated_and_only_declared_keys_kept():
    long = "x" * 1000
    cleaned = clean_args("cari_lead", {"query": long, "label": "Hot", "evil": "1"})
    assert set(cleaned) == {"query", "label"} and len(cleaned["query"]) == 300


def test_history_and_tool_results_are_sent_to_model_in_order():
    turns = [
        ChatTurn(role="user", text="cek DM"),
        ChatTurn(role="tool_call", tool="baca_pesan_baru"),
        ChatTurn(role="tool_result", tool="baca_pesan_baru", result={"ringkasan": "2 DM baru"}),
    ]
    client = FakeClient(response(types.Part(text="Ada 2 DM baru.")))
    chat_step(req(*turns), client)
    sent = client.calls[0]
    roles = [c.role for c in sent["contents"]]
    assert roles == ["user", "model", "user"]
    assert sent["contents"][1].parts[0].function_call.name == "baca_pesan_baru"
    assert sent["contents"][2].parts[0].function_response.response == {"ringkasan": "2 DM baru"}
    # semua tool terdaftar dan tidak ada tool kirim
    names = [d.name for d in sent["config"].tools[0].function_declarations]
    assert names == list(TOOLS) and not any("kirim" in n for n in names)
    assert sent["config"].automatic_function_calling.disable is True
    assert "DATA TIDAK TEPERCAYA" in sent["config"].system_instruction


def test_bulk_reply_and_paging_tools_are_declared_and_explained():
    assert clean_args("siapkan_balasan_massal", {"sasaran": "semua_lead", "instruksi": "tawarkan merch", "mulai": 20, "x": "y"}) == {
        "sasaran": "semua_lead", "instruksi": "tawarkan merch", "mulai": "20"}
    assert clean_args("cari_lead", {"mulai": 8}) == {"mulai": "8"}
    prompt = system_instruction(ChatStepRequest(turns=[ChatTurn(role="user", text="halo")]))
    assert "siapkan_balasan_massal" in prompt and "24 jam" in prompt and "mulai=`berikutnya`" in prompt
    assert not any("kirim" in name for name in TOOLS)  # tetap tanpa tool kirim


def test_string_tool_result_is_wrapped():
    contents = build_contents([ChatTurn(role="tool_result", tool="daftar_menunggu", result="kosong")])
    assert contents[0].parts[0].function_response.response == {"hasil": "kosong"}


def test_endpoint_ok_and_missing_credentials_503(monkeypatch):
    app = create_app()
    fake = FakeClient(response(types.Part(text="Siap.")))
    app.dependency_overrides[get_chat_client] = lambda: (lambda: fake)
    body = {"turns": [{"role": "user", "text": "halo"}], "business": "Toko"}
    r = TestClient(app).post("/v1/chat/step", json=body)
    assert r.status_code == 200 and r.json() == {"type": "final", "tool": "", "args": {}, "text": "Siap.", "say": "", "thoughts": ""}

    for k in ("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_GENAI_USE_VERTEXAI"):
        monkeypatch.delenv(k, raising=False)
    app2 = create_app()
    r = TestClient(app2).post("/v1/chat/step", json=body)
    assert r.status_code == 503 and "Kredensial" in r.json()["detail"]


def test_endpoint_validates_size():
    c = TestClient(create_app())
    assert c.post("/v1/chat/step", json={"turns": []}).status_code == 422
    too_many = {"turns": [{"role": "user", "text": "x"}] * 41}
    assert c.post("/v1/chat/step", json=too_many).status_code == 422
