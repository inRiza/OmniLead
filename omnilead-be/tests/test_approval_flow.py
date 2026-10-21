"""Tes alur inti: propose -> approve -> execute, dan kontrol manusia."""

from omnilead.models import ActionKind, ActionStatus, Channel, ProposedAction


def _proposal(channel=Channel.INSTAGRAM):
    return ProposedAction(
        channel=channel,
        kind=ActionKind.COMMENT_POST,
        post_ref="post-1",
        text="Halo kak, sudah kami DM ya 🙏",
        reason="Komentar menanyakan harga",
    )


def test_propose_masuk_antrean_pending(queue):
    action = queue.propose(_proposal())
    assert action.status == ActionStatus.PENDING
    assert queue.pending()[0].id == action.id


def test_executor_menolak_aksi_belum_disetujui(executor, queue):
    action = queue.propose(_proposal())
    # belum approve -> decided_at None
    try:
        executor.execute(action)
        assert False, "harus menolak"
    except PermissionError:
        pass


def test_approve_lalu_execute_mengirim_via_connector(queue, executor, ig):
    action = queue.propose(_proposal())
    approved = queue.approve(action.id)
    result = executor.execute(approved)
    assert result.status == ActionStatus.EXECUTED
    assert result.result_ref == "posted-id-1"
    assert ig.posted == [("post-1", "Halo kak, sudah kami DM ya 🙏")]


def test_edit_saat_approve_mengubah_teks(queue, executor, ig):
    action = queue.propose(_proposal())
    approved = queue.approve(action.id, edited_text="Halo kak, cek DM ya 😊")
    assert approved.edited is True
    executor.execute(approved)
    assert ig.posted[0][1] == "Halo kak, cek DM ya 😊"


def test_reject_tidak_mengirim(queue, executor, ig):
    action = queue.propose(_proposal())
    rejected = queue.reject(action.id, reason="terlalu formal")
    assert rejected.status == ActionStatus.REJECTED
    assert ig.posted == []


def test_execute_idempoten_tidak_kirim_ganda(queue, executor, ig):
    action = queue.propose(_proposal())
    approved = queue.approve(action.id)
    executor.execute(approved)
    executor.execute(approved)  # panggil dua kali
    assert len(ig.posted) == 1


def test_aksi_tanpa_api_jatuh_ke_handoff(queue, handoff_executor, ig_no_write):
    action = queue.propose(_proposal())
    approved = queue.approve(action.id)
    result = handoff_executor.execute(approved)
    assert result.status == ActionStatus.AWAITING_MANUAL_SEND
    assert ig_no_write.posted == []  # tidak ada kirim paksa


def test_audit_mencatat_langkah(queue, executor, store):
    action = queue.propose(_proposal())
    approved = queue.approve(action.id)
    executor.execute(approved)
    events = [e.event for e in store.list_audit()]
    assert "proposed" in events
    assert "approved" in events
    assert "executed" in events
