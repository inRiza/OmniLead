from collections.abc import Callable

from omnilead.approvals.queue import ApprovalQueue
from omnilead.identity import find_candidates
from omnilead.models import Action, ActionKind, ActionStatus, Channel, Lead, ProposedAction
from omnilead.store import Store

def excluded_pairs(store: Store) -> set[frozenset]:
    pairs: set[frozenset] = set()
    for action in store.list_actions(kind=ActionKind.MERGE):
        if action.status == ActionStatus.REJECTED or any(f.get("rating") == "bad" for f in action.feedback):
            src, dst = action.payload.get("source_lead_id"), action.payload.get("target_lead_id")
            if src and dst:
                pairs.add(frozenset((src, dst)))
    return pairs


def order_pair(a: Lead, b: Lead) -> tuple[Lead, Lead]:
    return (a, b) if a.created_at >= b.created_at else (b, a)


def propose_merge(
    store: Store,
    queue: ApprovalQueue,
    src: Lead,
    dst: Lead,
    confidence: float,
    evidence: list[str],
    channel: Channel,
    *,
    event_id: str | None = None,
    trace: dict | None = None,
    excluded: set[frozenset] | None = None,
    on_proposed: Callable[[Action, object], Action] | None = None,
) -> Action | None:
    if src.id == dst.id:
        return None
    pair = frozenset((src.id, dst.id))
    excluded = excluded_pairs(store) if excluded is None else excluded
    if pair in excluded:
        return None
    pending = next((a for a in store.list_actions(ActionStatus.PENDING, kind=ActionKind.MERGE)
                    if frozenset((a.payload.get("source_lead_id"), a.payload.get("target_lead_id"))) == pair), None)
    if pending is not None:
        if round(confidence, 2) <= float(pending.payload.get("confidence") or 0):
            return pending
        merged_evidence = list(dict.fromkeys([*evidence, *pending.payload.get("evidence", [])]))
        pending.payload = {**pending.payload, "source_lead_id": src.id, "target_lead_id": dst.id,
                           "confidence": round(confidence, 2), "evidence": merged_evidence, "_auto_held": False}
        pending.reason = f"Kemungkinan orang yang sama dengan {dst.name or 'profil lain'} (keyakinan {int(confidence * 100)}%)"
        pending.lead_id = src.id
        store.save_action(pending)
        store.audit("merge_strengthened", f"Keyakinan naik ke {int(confidence * 100)}%. {'; '.join(evidence)}",
                    pending.id, actor="ingest", channel=pending.channel.value, lead_id=src.id)
        return on_proposed(pending, None) if on_proposed else pending
    excluded.add(pair)
    action = queue.propose(ProposedAction(
        channel=channel,
        kind=ActionKind.MERGE,
        reason=f"Kemungkinan orang yang sama dengan {dst.name or 'profil lain'} (keyakinan {int(confidence * 100)}%)",
        payload={"source_lead_id": src.id, "target_lead_id": dst.id,
                 "confidence": round(confidence, 2), "evidence": evidence},
        lead_id=src.id,
        event_id=event_id,
        trace=trace,
    ))
    return on_proposed(action, None) if on_proposed else action


def scan_duplicates(
    store: Store,
    queue: ApprovalQueue,
    *,
    lead_ids: list[str] | None = None,
    company_hint: str | None = None,
    channel: Channel = Channel.WHATSAPP,
    event_id: str | None = None,
    trace: dict | None = None,
    on_proposed: Callable[[Action, object], Action] | None = None,
) -> list[Action]:
    leads = store.list_leads()
    targets = leads if lead_ids is None else [lead for lead in leads if lead.id in lead_ids]
    excluded = excluded_pairs(store)
    proposed: list[Action] = []
    for lead in targets:
        for cand in find_candidates(lead, leads, company_hint):
            src, dst = (lead, cand.lead) if lead_ids is not None else order_pair(lead, cand.lead)
            action = propose_merge(store, queue, src, dst, cand.confidence, cand.evidence, channel,
                                   event_id=event_id, trace=trace, excluded=excluded, on_proposed=on_proposed)
            if action is not None:
                proposed.append(action)
    return proposed
