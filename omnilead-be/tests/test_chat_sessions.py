import json
from datetime import datetime, timedelta, timezone

import pytest

from omnilead.chat_sessions import begin_turn, new_conversation, record_stream
from omnilead.store import Store


def test_transcript_and_tools_survive_database_reopen(tmp_path):
    path = tmp_path / "history.db"
    store = Store(path)
    conversation = new_conversation(store)
    saved, reply, history = begin_turn(store, conversation["id"], "Cek jadwal Instagram")
    assert history == []
    events = [
        {"type": "thoughts", "text": "Perlu membaca jadwal."},
        {"type": "step", "tool": "lihat_tugas", "args": {}, "label": "Membaca jadwal", "say": "Saya cek."},
        {"type": "tool_result", "tool": "lihat_tugas", "ok": True, "summary": "1 tugas", "data": {"tugas": []}},
        {"type": "message", "text": "Ada 1 tugas."},
    ]
    assert list(record_stream(store, saved, reply, iter(events))) == events
    loaded = Store(path).get_conversation(conversation["id"])
    assert loaded["turns"][-1]["text"] == "Ada 1 tugas."
    assert loaded["turns"][-1]["steps"][0]["thoughts"] == "Perlu membaca jadwal."
    assert loaded["lease_until"] is None
    assert Store(tmp_path / "other-business.db").get_conversation(conversation["id"]) is None


def test_concurrent_turn_is_rejected_and_server_history_is_used(store):
    conversation = new_conversation(store)
    saved, reply, history = begin_turn(store, conversation["id"], "Halo")
    with pytest.raises(ValueError):
        begin_turn(store, conversation["id"], "Duplikat")
    list(record_stream(store, saved, reply, iter([{"type": "message", "text": "Halo juga"}])))
    saved, reply, history = begin_turn(store, conversation["id"], "Jadwalkan cek DM setiap jam")
    assert history == [{"role": "user", "text": "Halo"}, {"role": "agent", "text": "Halo juga"}]
    assert saved["title"] == "Jadwalkan cek DM setiap jam"


def test_interrupted_stream_closes_running_indicators(store):
    conversation = new_conversation(store)
    saved, reply, _ = begin_turn(store, conversation["id"], "Cek pesan")
    events = iter([{"type": "step", "tool": "x", "args": {}, "label": "X", "say": ""}])
    list(record_stream(store, saved, reply, events))
    loaded = store.get_conversation(conversation["id"])
    assert loaded["turns"][-1]["done"] and loaded["turns"][-1]["error"]
    assert loaded["turns"][-1]["steps"][0]["status"] == "stopped"


def test_saved_channel_name_round_trip_and_explicit_knowledge_name(store):
    from fastapi.testclient import TestClient
    from omnilead.api import deps
    from omnilead.main import create_app
    from omnilead.models import ChannelAgentConfig, KnowledgeBase
    from omnilead.knowledge import build_context, channel_business_name
    app = create_app()
    app.dependency_overrides[deps.get_store] = lambda: store
    client = TestClient(app)
    response = client.patch('/agent/channel-settings/instagram', json={
        'business_name': 'Toko Satu', 'knowledge_base_ids': [], 'tone': 'casual', 'custom_tone': ''})
    assert response.status_code == 200
    assert client.get('/agent/channel-settings').json()['instagram']['business_name'] == 'Toko Satu'
    assert client.get('/settings').json()['agent_channels']['instagram']['business_name'] == 'Toko Satu'
    assert build_context(store, 'instagram', '')['public_business_name'] == 'Toko Satu'
    source = KnowledgeBase(id='source', name='Profil toko', content='Jualan merchandise. Namanya its.holaderry. Ramah dan jelas.', updated_at=datetime.now(timezone.utc))
    store.save_knowledge(source)
    assert channel_business_name(store, ChannelAgentConfig(knowledge_base_ids=['source'])) == 'its.holaderry'
