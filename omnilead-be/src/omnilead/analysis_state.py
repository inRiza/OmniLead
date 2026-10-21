"""Expose expired processing leases as recoverable errors, including after restart."""

from datetime import datetime, timezone

from omnilead.models import Event


def visible_analysis_state(event: Event, now: datetime | None = None) -> Event:
    if event.status not in {"new", "processing"}:
        return event
    trace = dict(event.trace or {})
    expiry = trace.get("lease_expires_at")
    if not expiry and event.status == "new":
        return event
    try:
        deadline = datetime.fromisoformat(expiry)
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if deadline > (now or datetime.now(timezone.utc)):
            return event
    except (TypeError, ValueError):
        pass  # Legacy processing records without a lease are recoverable too.
    trace["status"] = "Proses sebelumnya terhenti atau melewati batas waktu"
    return event.model_copy(update={"status": "agent_error", "trace": trace,
        "review_reason": "Analisis sebelumnya terhenti atau melewati batas waktu. Proses ulang pesan."})
