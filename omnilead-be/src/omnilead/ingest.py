"""Ingest: event masuk -> identitas -> panggil service agen -> antrean persetujuan.

Urutan:
  1. Dedup berdasarkan (kanal, external_id).
  2. Identity resolution deterministik: nomor HP / email / handle yang sama
     persis digabung otomatis dan dicatat di audit log. Kemiripan saja tidak
     pernah digabung diam-diam.
  3. Jika Pause aktif, event ditahan (`held`) dan agen tidak dipanggil.
  4. Agen dipanggil lewat HTTP; hanya usulan yang kembali. Usulan masuk antrean.
"""

import re
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from omnilead.agent_client import AgentClient, AgentResult, AgentUnavailable
from omnilead.approvals.queue import ApprovalQueue
from omnilead.models import (
    Action,
    ActionKind,
    Channel,
    Event,
    EventIn,
    Lead,
    ProposedAction,
)
from omnilead.identity import find_candidates
from omnilead.store import Store

WINDOW = timedelta(hours=24)
WINDOWED_CHANNELS = {Channel.WHATSAPP, Channel.INSTAGRAM, Channel.FACEBOOK}
TIMELINE_LIMIT = 10
PROTECTED_LIMIT = 200


def norm_phone(raw: str | None) -> str | None:
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    if digits.startswith("0"):
        digits = "62" + digits[1:]
    return digits


def norm_email(raw: str | None) -> str | None:
    return raw.strip().lower() if raw and raw.strip() else None


def handle_key(channel: Channel, handle: str | None) -> str | None:
    if not handle or not handle.strip():
        return None
    return f"{channel.value}:{handle.strip().lstrip('@').lower()}"


def identifiers(ev: EventIn) -> dict[str, str | None]:
    return {
        "phone": norm_phone(ev.sender.phone),
        "email": norm_email(ev.sender.email),
        "handle": handle_key(ev.channel, ev.sender.handle),
    }


class IngestService:
    def __init__(self, store: Store, queue: ApprovalQueue, agent: AgentClient):
        self._store = store
        self._queue = queue
        self._agent = agent

    # --- public ---

    def ingest(self, ev: EventIn, *, defer_analysis: Callable[[Event, bool], None] | None = None) -> tuple[Event, bool]:
        """Mengembalikan (event, duplikat)."""
        bindings = self._queue.account_bindings
        if bindings is not None:
            meta = dict(ev.meta)
            meta.setdefault("business_account_id", bindings.get(ev.channel.value, ""))
            original = meta.setdefault("platform_external_id", ev.external_id)
            account = meta["business_account_id"]
            ev = ev.model_copy(update={"meta": meta, "external_id": f"{account}:{original}" if account else original})
        existing = self._store.find_event(ev.channel.value, ev.external_id)
        if existing:
            return existing, True

        lead, created = self._resolve_lead(ev)
        event = Event(**ev.model_dump(), id=str(uuid.uuid4()), lead_id=lead.id)
        if event.ts is None:
            event.ts = datetime.now(timezone.utc)
        self._store.save_event(event)
        self._store.audit(
            "event_received",
            f"{event.kind} dari {event.sender.handle or event.sender.email or event.sender.phone or '-'}",
            actor="ingest",
            channel=event.channel.value,
            lead_id=lead.id,
        )
        if defer_analysis:
            defer_analysis(event, created)
            return event, False
        event = self.process_created(event, created)
        return event, False

    def process_created(self, event: Event, created: bool) -> Event:
        event = self.process(event)
        if created and event.status in ("analyzed", "review"):
            self._propose_merges(event)
        return event

    def process(self, event: Event) -> Event:
        """Jalankan agen untuk event. Dipanggil juga saat memproses ulang event tertahan."""
        if self._store.get_settings().paused:
            event.status = "held"
            self._store.save_event(event)
            self._store.audit(
                "event_held",
                "Agent dijeda; event ditahan",
                actor="system",
                channel=event.channel.value,
                lead_id=event.lead_id,
            )
            return event

        lead = self._store.get_lead(event.lead_id) if event.lead_id else None
        event.status = "processing"
        event.review_reason = ""
        event.triage = None
        event.trace = {"goal": f"Menyiapkan tanggapan via {event.channel.value}",
                       "plan": ["Kenali maksud pesan", "Baca konteks bisnis dan riwayat",
                                "Siapkan usulan", "Periksa usulan", "Minta persetujuan Anda"],
                       "steps": [], "activity": [], "status": "Memulai analisis"}
        self._store.save_event(event)

        def on_progress(item: dict) -> None:
            trace = event.trace
            if len(trace["activity"]) >= 128:
                return
            trace["activity"].append(item)
            trace["status"] = item.get("label", "Memproses pesan")
            if item.get("phase") == "plan":
                trace["plan"] = item.get("plan", trace["plan"])
                trace["goal"] = item.get("goal", trace["goal"])
            elif item.get("phase") == "tool":
                trace["steps"].append({"n": len(trace["steps"]) + 1, "tool": item.get("tool", ""),
                                       "input": item.get("input", {}), "result": item.get("result", "")})
            elif item.get("phase") == "triage_done":
                event.triage = {"intents": item.get("intents", []), "urgency": item.get("urgency", "rendah"),
                                "urgency_reason": item.get("reason", "")}
            self._store.save_event(event)

        try:
            payload = self._payload(event, lead)
            if hasattr(self._agent, "analyze_stream"):
                result = self._agent.analyze_stream(payload, on_progress)
            else:
                result = self._agent.analyze(payload)
        except AgentUnavailable as exc:
            event.status = "agent_error"
            event.review_reason = f"Service agen tidak tersedia: {exc}"
            event.trace["status"] = "Analisis gagal; perlu diproses ulang"
            self._store.save_event(event)
            self._store.audit(
                "agent_error",
                str(exc),
                actor="system",
                channel=event.channel.value,
                lead_id=event.lead_id,
            )
            return event
        return self._apply(event, lead, result)

    def reprocess_held(self) -> list[Event]:
        held = [e for e in self._store.list_events(limit=1000) if e.status == "held"]
        return [self.process(e) for e in reversed(held)]

    # --- identity ---

    def _resolve_lead(self, ev: EventIn) -> tuple[Lead, bool]:
        """Mengembalikan (lead, baru_dibuat)."""
        ids = identifiers(ev)
        matched: Lead | None = None
        matched_by: str | None = None
        for lead in self._store.list_leads():
            for kind, value in ids.items():
                pool = {"phone": lead.phones, "email": lead.emails, "handle": lead.handles}[kind]
                if value and value in pool:
                    matched, matched_by = lead, kind
                    break
            if matched:
                break

        now = datetime.now(timezone.utc)
        if matched is None:
            lead = Lead(
                id=str(uuid.uuid4()),
                name=ev.sender.name or ev.sender.handle or None,
                phones=[ids["phone"]] if ids["phone"] else [],
                emails=[ids["email"]] if ids["email"] else [],
                handles=[ids["handle"]] if ids["handle"] else [],
                created_at=now,
                updated_at=now,
            )
            self._store.save_lead(lead)
            self._store.audit(
                "lead_created", lead.name or lead.id, actor="ingest",
                channel=ev.channel.value, lead_id=lead.id,
            )
            return lead, True

        added: list[str] = []
        for kind, value in ids.items():
            pool = {"phone": matched.phones, "email": matched.emails, "handle": matched.handles}[kind]
            if value and value not in pool:
                pool.append(value)
                added.append(f"{kind}={value}")
        if ev.sender.name and not matched.name:
            matched.name = ev.sender.name
        if added:
            matched.updated_at = now
            self._store.save_lead(matched)
            self._store.audit(
                "identity_merged",
                f"Cocok pasti lewat {matched_by}; identitas baru ditambahkan: {', '.join(added)}",
                actor="ingest",
                channel=ev.channel.value,
                lead_id=matched.id,
            )
        return matched, False

    def _propose_merges(self, event: Event) -> None:
        """Identitas ambigu: usulkan merge beserta bukti. Tidak pernah menggabung sendiri."""
        lead = self._store.get_lead(event.lead_id) if event.lead_id else None
        if lead is None:
            return
        company = ((event.triage or {}).get("entities") or {}).get("company")
        others = self._store.list_leads()
        pending = {
            (a.payload.get("source_lead_id"), a.payload.get("target_lead_id"))
            for a in self._store.list_actions()
            if a.kind == ActionKind.MERGE and a.status.value == "pending"
        }
        for cand in find_candidates(lead, others, company):
            if (lead.id, cand.lead.id) in pending:
                continue
            self._queue.propose(
                ProposedAction(
                    channel=event.channel,
                    kind=ActionKind.MERGE,
                    reason=(
                        f"Kemungkinan orang yang sama dengan {cand.lead.name} "
                        f"(keyakinan {int(cand.confidence * 100)}%)"
                    ),
                    payload={
                        "source_lead_id": lead.id,
                        "target_lead_id": cand.lead.id,
                        "confidence": cand.confidence,
                        "evidence": cand.evidence,
                    },
                    lead_id=lead.id,
                    event_id=event.id,
                    trace=event.trace,
                )
            )

    # --- agent I/O ---

    def _payload(self, event: Event, lead: Lead | None) -> dict:
        settings = self._store.get_settings()
        windows: dict[str, bool] = {}
        if event.channel in WINDOWED_CHANNELS and event.kind in ("message", "dm") and event.ts:
            ts = event.ts if event.ts.tzinfo else event.ts.replace(tzinfo=timezone.utc)
            windows[event.channel.value] = datetime.now(timezone.utc) - ts <= WINDOW

        # Identitas pengirim sendiri bukan "data pelanggan lain", walau ada profil lain
        # yang namanya sama dan belum digabung.
        own = {
            t.lower()
            for t in (
                event.sender.name, event.sender.handle.lstrip("@"),
                (event.sender.name or "").split(" ")[0],
                norm_phone(event.sender.phone), norm_email(event.sender.email),
            )
            if t
        }
        protected: list[str] = []
        for other in self._store.list_leads():
            if lead and other.id == lead.id:
                continue
            protected += [
                t for t in [other.name, *other.phones, *other.emails]
                if t and len(t) >= 3 and t.lower() not in own
            ]
        payload = {
            "event": {
                "id": event.id,
                "channel": event.channel.value,
                "kind": event.kind,
                "sender": event.sender.model_dump(),
                "text": event.text,
                "ts": event.ts.isoformat() if event.ts else None,
                "post_ref": event.post_ref,
                "comment_ref": event.comment_ref,
            },
            "lead": self._lead_context(event, lead) if lead else None,
            "preferences": settings.preferences,
            "windows": windows,
            "protected_terms": protected[:PROTECTED_LIMIT],
        }
        if self._queue.account_bindings is not None or settings.agent_channels:
            from omnilead.knowledge import build_context
            payload["business_context"] = build_context(self._store, event.channel.value, event.text)
        return payload

    def _lead_context(self, event: Event, lead: Lead) -> dict:
        items: list[tuple[str, dict]] = []
        for e in self._store.list_events(lead_id=lead.id, limit=50):
            if e.id == event.id:
                continue
            items.append((
                (e.ts or datetime.min.replace(tzinfo=timezone.utc)).isoformat(),
                {"ts": e.ts.isoformat() if e.ts else None, "channel": e.channel.value,
                 "direction": "in", "text": e.text},
            ))
        for a in self._store.list_actions():
            if a.lead_id == lead.id and a.result_ref and a.text:
                items.append((
                    a.created_at.isoformat(),
                    {"ts": a.created_at.isoformat(), "channel": a.channel.value,
                     "direction": "out", "text": a.text},
                ))
        items.sort(key=lambda x: x[0])
        return {
            "id": lead.id,
            "name": lead.name,
            "company": lead.company,
            "stage": lead.stage,
            "summary": lead.summary,
            "timeline": [i[1] for i in items[-TIMELINE_LIMIT:]],
        }

    def _apply(self, event: Event, lead: Lead | None, result: AgentResult) -> Event:
        event.triage = result.triage
        event.trace = result.trace
        event.review_reason = result.review_reason

        if lead:
            new_score = (result.crm or {}).get("score")
            # Pesan sepele ("halo?") tidak boleh menurunkan lead Hot atau menimpa ringkasannya.
            if result.crm and (lead.score is None or new_score is None or new_score >= lead.score):
                lead.summary = str(result.crm.get("summary", lead.summary))
                lead.score = new_score if new_score is not None else lead.score
                lead.label = result.crm.get("label", lead.label)
                lead.score_reason = str(result.crm.get("score_reason", lead.score_reason))
            company = (result.triage.get("entities") or {}).get("company")
            if company and not lead.company:
                lead.company = str(company)
            lead.updated_at = datetime.now(timezone.utc)
            self._store.save_lead(lead)
            self._store.audit(
                "summary_updated",
                f"skor={lead.score} {lead.label or ''}".strip(),
                actor="agent",
                channel=event.channel.value,
                lead_id=lead.id,
            )

        if result.flagged_for_review:
            self._store.audit(
                "flag_for_review",
                result.review_reason,
                actor="agent",
                channel=event.channel.value,
                lead_id=event.lead_id,
            )

        queued = 0
        for p in result.proposals:
            action = self._to_action(p, event)
            if action is None:
                continue
            self._queue.propose(action)
            queued += 1

        event.status = "review" if result.flagged_for_review else "analyzed"
        self._store.save_event(event)
        self._store.audit(
            "event_analyzed",
            f"{queued} usulan masuk antrean; {result.trace.get('guard_summary', '')}".strip("; "),
            actor="agent",
            channel=event.channel.value,
            lead_id=event.lead_id,
        )
        return event

    def _to_action(self, p, event: Event) -> ProposedAction | None:
        try:
            due = datetime.fromisoformat(p.due_at) if p.due_at else None
            return ProposedAction(
                channel=Channel(p.channel),
                kind=ActionKind(p.kind),
                post_ref=p.post_ref,
                comment_ref=p.comment_ref,
                text=p.text,
                reason=p.reason,
                recipient=p.recipient,
                due_at=due,
                payload=p.payload,
                guard=p.guard,
                public=p.public,
                lead_id=event.lead_id,
                event_id=event.id,
                trace=event.trace,
            )
        except ValueError as exc:
            self._store.audit(
                "proposal_skipped",
                f"Usulan {p.kind}/{p.channel} dilewati: {exc}",
                actor="system",
                lead_id=event.lead_id,
            )
            return None


__all__ = ["IngestService", "Action"]
