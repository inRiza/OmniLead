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
from omnilead.approvals.executor import ChannelDisabled, Paused, RateLimited
from omnilead.approvals.queue import ApprovalQueue
from omnilead.autonomy import auto_approvable
from omnilead.models import (
    Action,
    ActionKind,
    Channel,
    Event,
    EventIn,
    Lead,
    ProposedAction,
)
from omnilead.dedup import excluded_pairs, propose_merge, scan_duplicates
from omnilead.identity import canon_email
from omnilead.store import Store
from omnilead.analysis_state import visible_analysis_state

WINDOW = timedelta(hours=24)
WINDOWED_CHANNELS = {Channel.WHATSAPP, Channel.INSTAGRAM, Channel.FACEBOOK}
TIMELINE_LIMIT = 10
PROTECTED_LIMIT = 200


class AnalysisSuperseded(Exception):
    pass


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


LABEL = {"phone": "Nomor HP", "email": "Email", "handle": "Akun"}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?<![\d+])(?:\+?62|0)8[\d\s.-]{7,14}\d")


def _item(kind: str, value: str | None) -> tuple[str, str, str] | None:
    if not value:
        return None
    key = f"email:{canon_email(value)}" if kind == "email" else f"{kind}:{value}"
    return kind, value, key


def identity_items(ev: EventIn) -> list[tuple[str, str, str]]:
    ids = identifiers(ev)
    items = [_item("phone", ids["phone"]), _item("email", ids["email"]), _item("handle", ids["handle"])]
    username = ev.meta.get("username") if isinstance(ev.meta, dict) else None
    alias = handle_key(ev.channel, username) if username else None
    if alias and alias != ids["handle"]:
        items.append(_item("handle", alias))
    seen: set[str] = set()
    out = []
    for item in items:
        if item and item[2] not in seen:
            seen.add(item[2])
            out.append(item)
    return out


def mentioned_contacts(text: str) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    for raw in EMAIL_RE.findall(text or ""):
        item = _item("email", norm_email(raw))
        if item:
            out.append(item)
    for raw in PHONE_RE.findall(text or ""):
        item = _item("phone", norm_phone(raw))
        if item and len(item[1]) >= 10:
            out.append(item)
    return list({i[2]: i for i in out}.values())


class IngestService:
    def __init__(
        self,
        store: Store,
        queue: ApprovalQueue,
        agent: AgentClient,
        executor=None,
        on_proposed: Callable[[Action, Event], Action] | None = None,
        profile: Callable[[], dict] | None = None,
    ):
        self._store = store
        self._queue = queue
        self._agent = agent
        self._executor = executor
        self._on_proposed = on_proposed
        self._profile = profile
        self._conflicts: list[tuple[Lead, list[str]]] = []
        self._identity_added = False

    @property
    def store(self) -> Store:
        return self._store

    # --- public ---

    def ingest(self, ev: EventIn, *, defer_analysis: Callable[[Event, bool], None] | None = None,
               analyze: bool = True) -> tuple[Event, bool]:
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
        identity_added = self._identity_added
        event = Event(**ev.model_dump(), id=str(uuid.uuid4()), lead_id=lead.id)
        if event.ts is None:
            event.ts = datetime.now(timezone.utc)
        self._store.save_event(event)
        self._merge_conflicts(event)
        self._store.audit(
            "event_received",
            f"{event.kind} dari {event.sender.handle or event.sender.email or event.sender.phone or '-'}",
            actor="ingest",
            channel=event.channel.value,
            lead_id=lead.id,
        )
        if not analyze:
            return event, False
        if defer_analysis:
            event = self.prepare(event)
            defer_analysis(event, created or identity_added)
            return event, False
        event = self.process_created(event, created, identity_added)
        return event, False

    def process_created(self, event: Event, created: bool, identity_added: bool = False) -> Event:
        expected_run = (event.trace or {}).get("run_id")
        event = self.process(event, expected_run_id=expected_run)
        if ((created or identity_added) and event.status in ("analyzed", "review")
                and (not expected_run or (event.trace or {}).get("run_id") == expected_run)):
            self._propose_merges(event)
        return event

    def _lease(self, run_id: str | None = None) -> dict:
        now = datetime.now(timezone.utc)
        timeout = float(getattr(self._agent, "timeout_seconds", 60))
        return {"run_id": run_id or uuid.uuid4().hex, "started_at": now.isoformat(),
                "lease_expires_at": (now + timedelta(seconds=max(1, timeout) + 30)).isoformat()}

    def prepare(self, event: Event) -> Event:
        event.status = "new"
        event.triage = None
        event.review_reason = ""
        event.trace = {**self._lease(), "goal": f"Menyiapkan tanggapan via {event.channel.value}",
                       "plan": [], "steps": [], "activity": [], "status": "Menunggu diproses"}
        self._store.save_event(event)
        return event

    def process(self, event: Event, *, expected_run_id: str | None = None) -> Event:
        """Jalankan agen untuk event. Dipanggil juga saat memproses ulang event tertahan."""
        if expected_run_id:
            current = self._store.get_event(event.id)
            if not current or (current.trace or {}).get("run_id") != expected_run_id or current.status != "new":
                return current or event
            current = visible_analysis_state(current)
            if current.status == "agent_error":
                self._store.save_event(current)
                return current
            event = current
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
        lease = self._lease(expected_run_id)
        run_id = lease["run_id"]
        event.trace = {**lease, "goal": f"Menyiapkan tanggapan via {event.channel.value}",
                       "plan": ["Kenali maksud pesan", "Baca konteks bisnis dan riwayat",
                                "Siapkan usulan", "Periksa usulan", "Minta persetujuan Anda"],
                       "steps": [], "activity": [], "status": "Memulai analisis"}
        self._store.save_event(event)

        def on_progress(item: dict) -> None:
            current = self._store.get_event(event.id)
            if current and (current.trace or {}).get("run_id") != run_id:
                raise AnalysisSuperseded()
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
            current = self._store.get_event(event.id)
            if current and (current.trace or {}).get("run_id") != run_id:
                raise AnalysisSuperseded()
            result.trace.update(lease)
            return self._apply(event, lead, result)
        except AnalysisSuperseded:
            return self._store.get_event(event.id) or event
        except AgentUnavailable as exc:
            current = self._store.get_event(event.id)
            if current and (current.trace or {}).get("run_id") != run_id:
                return current
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

    def _autopilot(self, action, event: Event) -> None:
        mode = self._store.get_settings().autonomy
        if self._executor is None or not auto_approvable(action, event, mode):
            return
        approved = self._queue.auto_approve(action.id, mode)
        try:
            self._executor.execute(approved)
        except (Paused, ChannelDisabled, RateLimited) as exc:
            self._queue.return_to_owner(action.id, str(exc))

    def reprocess_held(self) -> list[Event]:
        held = [e for e in self._store.list_events(limit=1000) if e.status == "held"]
        return [self.process(e) for e in reversed(held)]

    # --- identity ---

    def _resolve_lead(self, ev: EventIn) -> tuple[Lead, bool]:
        items = identity_items(ev)
        owners: dict[str, Lead] = {}
        owned_by: dict[str, set[str]] = {}
        for kind, value, key in items:
            for found in self._store.find_leads_by_identity(key):
                owners.setdefault(found.id, found)
                owned_by.setdefault(key, set()).add(found.id)

        now = datetime.now(timezone.utc)
        self._conflicts = []
        self._identity_added = False
        if not owners:
            lead = Lead(
                id=str(uuid.uuid4()),
                name=ev.sender.name or ev.sender.handle or None,
                created_at=now,
                updated_at=now,
            )
            for kind, value, key in items:
                self._attach(lead, kind, value, key, "created", 1.0, ev.channel, now)
            self._store.save_lead(lead)
            self._store.audit(
                "lead_created", lead.name or lead.id, actor="ingest",
                channel=ev.channel.value, lead_id=lead.id,
            )
            return lead, True

        ranked = [lid for kind, value, key in items for lid in sorted(owned_by.get(key, ()))]
        matched = owners[ranked[0]]
        matched_by = next(kind for kind, value, key in items if matched.id in owned_by.get(key, ()))
        others = [owners[lid] for lid in dict.fromkeys(ranked) if lid != matched.id]
        for other in others:
            shared = [f"{LABEL[kind]} sama: {value}" for kind, value, key in items if other.id in owned_by.get(key, ())]
            self._conflicts.append((other, shared))

        added: list[str] = []
        for kind, value, key in items:
            holders = owned_by.get(key, set())
            if holders and holders != {matched.id}:
                continue
            if self._attach(matched, kind, value, key, "exact", 1.0, ev.channel, now):
                added.append(f"{kind}={value}")
        if ev.sender.name and not matched.name:
            matched.name = ev.sender.name
        if added:
            matched.updated_at = now
            self._store.save_lead(matched)
            self._identity_added = True
            self._store.audit(
                "identity_merged",
                f"Cocok pasti lewat {matched_by}; identitas baru ditambahkan: {', '.join(added)}",
                actor="ingest",
                channel=ev.channel.value,
                lead_id=matched.id,
            )
        if others:
            self._store.audit(
                "identity_conflict",
                f"Identitas pesan ini juga tercatat di {', '.join(o.name or o.id for o in others)}; usulan gabung dibuat",
                actor="ingest",
                channel=ev.channel.value,
                lead_id=matched.id,
            )
        return matched, False

    @staticmethod
    def _attach(lead: Lead, kind: str, value: str, key: str, source: str, confidence: float,
                channel: Channel, now: datetime) -> bool:
        pool = {"phone": lead.phones, "email": lead.emails, "handle": lead.handles}[kind]
        if kind == "email":
            present = any(canon_email(e) == canon_email(value) for e in pool)
        else:
            present = value in pool
        if not present:
            pool.append(value)
        if key not in lead.identity_sources:
            lead.identity_sources[key] = {"source": source, "confidence": confidence,
                                          "channel": channel.value, "at": now.isoformat()}
        return not present

    def _merge_conflicts(self, event: Event) -> None:
        lead = self._store.get_lead(event.lead_id) if event.lead_id else None
        if lead is None:
            return
        excluded = excluded_pairs(self._store)
        for other, shared in getattr(self, "_conflicts", []):
            current = self._store.get_lead(other.id)
            if current is None:
                continue
            propose_merge(self._store, self._queue, current, lead, 0.97, shared, event.channel,
                          event_id=event.id, trace=event.trace, excluded=excluded, on_proposed=self._on_proposed)
        mentioned = mentioned_contacts(event.text)
        if mentioned:
            event.meta = {**event.meta, "mentioned_contacts": [v for _, v, _ in mentioned]}
            self._store.save_event(event)
        for kind, value, key in mentioned:
            for owner in self._store.find_leads_by_identity(key):
                if owner.id == lead.id:
                    continue
                propose_merge(self._store, self._queue, lead, owner, 0.85,
                              [f"{LABEL[kind]} {value} disebut di pesan dan tercatat di profil {owner.name or owner.id}"],
                              event.channel, event_id=event.id, trace=event.trace, excluded=excluded,
                              on_proposed=self._on_proposed)

    def _propose_merges(self, event: Event) -> None:
        lead = self._store.get_lead(event.lead_id) if event.lead_id else None
        if lead is None:
            return
        company = ((event.triage or {}).get("entities") or {}).get("company")
        scan_duplicates(self._store, self._queue, lead_ids=[lead.id], company_hint=company,
                        channel=event.channel, event_id=event.id, trace=event.trace,
                        on_proposed=self._on_proposed)

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
            payload["business_context"] = build_context(self._store, event.channel.value, event.text,
                                                        profile=self._profile() if self._profile else None)
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
        for a in self._store.list_actions(lead_id=lead.id):
            if a.result_ref and a.text:
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
            crm = result.crm or {}
            new_score = crm.get("score")
            before = (lead.score, lead.label)
            now = datetime.now(timezone.utc)
            # Pesan sepele ("halo?") tidak boleh menurunkan lead Hot atau menimpa ringkasannya.
            if crm and (lead.score is None or new_score is None or new_score >= lead.score):
                lead.summary = str(crm.get("summary", lead.summary))
                lead.score = new_score if new_score is not None else lead.score
                lead.label = crm.get("label", lead.label)
                lead.score_reason = str(crm.get("score_reason", lead.score_reason))
                lead.score_reasons = [str(r) for r in crm.get("reasons") or []] or lead.score_reasons
                lead.score_rubric = str(crm.get("rubric") or lead.score_rubric)
                lead.score_analysis = str(crm.get("score_analysis") or lead.score_analysis)
                lead.scored_at = now
            if crm:
                lead.needs = {**lead.needs, **(crm.get("needs") or {})}
                lead.next_step = str(crm.get("next_step") or lead.next_step)
                if lead.estimated_value is None and crm.get("estimated_value"):
                    lead.estimated_value = int(crm["estimated_value"])
            company = (result.triage.get("entities") or {}).get("company")
            if company and not lead.company:
                lead.company = str(company)
            lead.updated_at = now
            self._store.save_lead(lead)
            change = (f"skor {before[0]} {before[1] or ''} -> {lead.score} {lead.label or ''}".replace("  ", " ")
                      if before[0] is not None and before != (lead.score, lead.label)
                      else f"skor={lead.score} {lead.label or ''}".strip())
            reasons = "; ".join(lead.score_reasons)
            self._store.audit(
                "summary_updated",
                f"{change}. {reasons}" if reasons else change,
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

        queued: list[Action] = []
        for p in result.proposals:
            action = self._to_action(p, event)
            if action is None:
                continue
            proposed = self._queue.propose(action)
            queued.append(proposed)
            if self._on_proposed:
                self._on_proposed(proposed, event)
            else:
                self._autopilot(proposed, event)

        event.status = "review" if result.flagged_for_review else "analyzed"
        self._store.save_event(event)
        self._store.audit(
            "event_analyzed",
            f"{len(queued)} usulan masuk antrean; {result.trace.get('guard_summary', '')}".strip("; "),
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
