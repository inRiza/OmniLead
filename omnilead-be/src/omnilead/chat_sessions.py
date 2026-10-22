"""Workspace scoped conversation transcripts with optimistic single-turn claims."""
import json
import time
import re
from datetime import datetime, timedelta, timezone
from uuid import uuid4


def now():
    return datetime.now(timezone.utc)


def new_conversation(store) -> dict:
    stamp = now().isoformat()
    session = {"id": uuid4().hex, "title": "Percakapan baru", "created_at": stamp, "updated_at": stamp,
               "turns": [], "revision": 0, "lease_until": None, "channel": None}
    store.save_conversation(session)
    return session


def begin_turn(store, session_id: str, message: str, channel: str | None = None):
    session = store.get_conversation(session_id)
    if not session:
        raise KeyError(session_id)
    if session["lease_until"] and datetime.fromisoformat(session["lease_until"]) > now():
        raise ValueError("Percakapan ini masih memproses pesan. Tunggu selesai atau mulai chat baru.")
    if len(session["turns"]) >= 100 or len(json.dumps(session).encode()) > 650_000:
        raise ValueError("Percakapan ini sudah panjang. Mulai chat baru untuk melanjutkan.")
    for turn in session["turns"]:
        if not turn["done"]:
            turn.update(done=True, error="Proses sebelumnya terputus. Periksa hasil sebelum mencoba lagi.")
            for step in turn["steps"]:
                if step["status"] == "running":
                    step["status"] = "stopped"
    history = [{"role": t["role"], "text": t["text"]} for t in session["turns"] if t["text"] and not t["error"]]
    # Do not leave a conversation named "halo" after its actual topic is known.
    greeting = re.compile(r"^(ha+l+o+|hai+|hi+|hey|pagi|siang|malam|tes|test|oke|ok|lanjut)[!.? ]*$", re.I)
    meaningful = [t["text"] for t in session["turns"] if t["role"] == "user" and not greeting.fullmatch(t["text"].strip())]
    if not greeting.fullmatch(message.strip()):
        meaningful.append(message)
    topic = meaningful[0] if meaningful else message
    title = re.sub(r"^(?:tolong|coba|bisa tolong|aku mau|saya mau)\s+", "", " ".join(topic.split()), flags=re.I)
    session["title"] = title[:64].rsplit(" ", 1)[0] + "…" if len(title) > 64 else title
    def turn(role, text=""):
        return {"id": uuid4().hex, "role": role, "text": text, "steps": [], "error": "", "done": role == "user",
                "thoughts": "", "thinking": "", "narration": ""}
    reply = turn("agent")
    session["turns"] += [turn("user", message), reply]
    session["channel"] = channel
    previous = session["revision"]
    session.update(revision=previous + 1, lease_until=(now() + timedelta(minutes=30)).isoformat(), updated_at=now().isoformat())
    if not store.save_conversation(session, previous):
        raise ValueError("Percakapan sedang diperbarui oleh tab lain; muat ulang.")
    return session, reply, history


def apply_event(turn: dict, event: dict):
    kind = event["type"]
    if kind == "thoughts":
        turn["thinking"] = (turn["thinking"] + event["text"])[:4000]
    elif kind == "say":
        turn["narration"] = (turn["narration"] + event["text"])[:8000]
    elif kind == "step":
        turn["steps"].append({"tool": event["tool"], "label": event["label"], "args": event["args"], "say": event["say"],
            "thoughts": event.get("thoughts") or turn["thinking"], "status": "running", "summary": "", "data": {}})
        turn.update(thinking="", narration="")
    elif kind in ("tool_result", "tool_progress"):
        step = next((s for s in reversed(turn["steps"]) if s["tool"] == event["tool"] and s["status"] == "running"), None)
        if step and kind == "tool_result":
            step.update(status="done" if event["ok"] else "failed", summary=event["summary"], data=event["data"])
        elif step:
            step.update(progress=event["label"], elapsed=event["elapsed_s"])
    elif kind == "message":
        turn.update(text=event["text"], thoughts=event.get("thoughts") or turn["thinking"], done=True, thinking="", narration="")
    elif kind == "error":
        turn.update(error=event["message"], thoughts=turn["thinking"], done=True)


def record_stream(store, session: dict, reply: dict, events):
    saved = time.monotonic()

    def save():
        previous = session["revision"]
        session.update(revision=previous + 1, updated_at=now().isoformat())
        if not store.save_conversation(session, previous):
            raise ValueError("Percakapan berubah saat diproses")

    try:
        for event in events:
            apply_event(reply, event)
            if event["type"] not in ("thoughts", "say") or time.monotonic() - saved > 2:
                save()
                saved = time.monotonic()
            yield event
    finally:
        if not reply["done"]:
            reply.update(done=True, error="Koneksi terputus. Periksa hasil langkah terakhir sebelum mencoba lagi.",
                         thoughts=reply["thoughts"] or reply["thinking"])
        for step in reply["steps"]:
            if step["status"] == "running":
                step["status"] = "stopped"
        session["lease_until"] = None
        save()
