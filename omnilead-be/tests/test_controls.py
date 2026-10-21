import pytest

from omnilead.approvals.executor import ChannelDisabled, Paused, RateLimited
from omnilead.approvals.queue import InvalidTransition
from omnilead.models import ActionKind, ActionStatus, Channel, ProposedAction


def proposal(channel=Channel.INSTAGRAM, **kw):
    base = dict(channel=channel, kind=ActionKind.REPLY_COMMENT, post_ref="p1",
                comment_ref="c1", text="halo kak")
    base.update(kw)
    return ProposedAction(**base)


def test_rejected_action_cannot_be_approved_or_executed(queue, executor, store):
    a = queue.propose(proposal())
    queue.reject(a.id, "salah")
    with pytest.raises(InvalidTransition):
        queue.approve(a.id)
    with pytest.raises(PermissionError):
        executor.execute(store.get_action(a.id))


def test_cannot_reject_or_mark_sent_after_decision(queue, executor):
    a = queue.propose(proposal())
    executor.execute(queue.approve(a.id))
    with pytest.raises(InvalidTransition):
        queue.reject(a.id, "terlambat")
    with pytest.raises(InvalidTransition):
        queue.mark_sent_manually(a.id)


def test_approve_sets_edited_status(queue):
    a = queue.propose(proposal())
    assert queue.approve(a.id, edited_text="versi baru").status == ActionStatus.EDITED


def test_pause_blocks_executor_even_if_approved(queue, executor, store, ig):
    a = queue.approve(queue.propose(proposal()).id)
    s = store.get_settings()
    s.paused = True
    store.save_settings(s)
    with pytest.raises(Paused):
        executor.execute(a)
    assert ig.posted == []
    s.paused = False
    store.save_settings(s)
    assert executor.execute(a).status == ActionStatus.EXECUTED


def test_disabled_channel_blocks(queue, executor, store):
    s = store.get_settings()
    s.disabled_channels = [Channel.INSTAGRAM]
    store.save_settings(s)
    a = queue.approve(queue.propose(proposal()).id)
    with pytest.raises(ChannelDisabled):
        executor.execute(a)


def test_dry_run_does_not_send(queue, executor, store, ig):
    s = store.get_settings()
    s.dry_run = True
    store.save_settings(s)
    a = executor.execute(queue.approve(queue.propose(proposal()).id))
    assert a.status == ActionStatus.EXECUTED and a.result_ref == "dry-run"
    assert ig.posted == []


def test_rate_limit(queue, executor, store):
    s = store.get_settings()
    s.rate_limit_per_hour = 1
    store.save_settings(s)
    executor.execute(queue.approve(queue.propose(proposal()).id))
    b = queue.approve(queue.propose(proposal(text="lagi")).id)
    with pytest.raises(RateLimited):
        executor.execute(b)


def test_failed_then_retry(queue, executor, ig):
    from omnilead.connectors.base import ConnectorError

    def boom(*a, **k):
        raise ConnectorError("token kedaluwarsa")

    ig.reply_comment = boom
    a = executor.execute(queue.approve(queue.propose(proposal()).id))
    assert a.status == ActionStatus.FAILED and "token" in a.error
    with pytest.raises(InvalidTransition):
        queue.approve(a.id)  # tidak bisa lewat approve
    ig.reply_comment = lambda ref, text: "ok-1"
    a = executor.execute(queue.retry(a.id))
    assert a.status == ActionStatus.EXECUTED


def test_send_message_without_api_goes_to_handoff(queue, executor):
    a = queue.propose(proposal(Channel.WHATSAPP, kind=ActionKind.SEND_MESSAGE,
                               recipient="6281234500001", comment_ref=None, post_ref=""))
    a = executor.execute(queue.approve(a.id))
    assert a.status == ActionStatus.AWAITING_MANUAL_SEND
    assert queue.mark_sent_manually(a.id).status == ActionStatus.SENT_MANUALLY


def test_crm_update_applies_to_lead_after_approval(queue, executor, store):
    from datetime import datetime, timezone

    from omnilead.models import Lead

    now = datetime.now(timezone.utc)
    store.save_lead(Lead(id="l1", created_at=now, updated_at=now))
    a = queue.propose(ProposedAction(channel=Channel.WHATSAPP, kind=ActionKind.CRM_UPDATE,
                                     lead_id="l1", payload={"stage": "penawaran"}))
    assert store.get_lead("l1").stage == "baru"  # belum disetujui
    executor.execute(queue.approve(a.id))
    assert store.get_lead("l1").stage == "penawaran"


def test_reject_reason_becomes_preference(queue, store):
    queue.reject(queue.propose(proposal()).id, "terlalu formal")
    assert "terlalu formal" in store.get_settings().preferences
