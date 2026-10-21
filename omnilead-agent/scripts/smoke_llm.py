"""Uji koneksi LLM (Vertex AI atau AI Studio) dari service agen.

    cd omnilead-agent
    uv run python scripts/smoke_llm.py

Membaca `.env` di folder agen. Berbeda dari pipeline (yang diam-diam jatuh ke
templat bila LLM gagal), skrip ini MENAMPILKAN error aslinya: kredensial salah,
API belum aktif, model tidak ditemukan di region, dll.
"""

import asyncio
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from omnilead_agent.adk_orchestrator import AdkDrafter, DEFAULT_MODEL  # noqa: E402
from omnilead_agent.adk_triage import DEFAULT_MODEL as TRIAGE_MODEL  # noqa: E402
from omnilead_agent.adk_triage import _run as run_triage  # noqa: E402
from omnilead_agent.adk_triage import build_triage_agent  # noqa: E402
from omnilead_agent.catalog import default_catalog  # noqa: E402
from omnilead_agent.orchestrator import DraftContext, Tools  # noqa: E402
from omnilead_agent.schemas import AnalyzeRequest, Trace  # noqa: E402
from omnilead_agent.triage import triage  # noqa: E402

TEXT = "Kak, bisa buat 60 orang tgl 30? harga? PT Maju Jaya"


def show_env() -> None:
    vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "")
    key = bool(os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"))
    print("== Konfigurasi")
    print(f"  mode            : {'Vertex AI' if vertex.lower() in ('1', 'true') else 'AI Studio (API key)' if key else 'TIDAK ADA KREDENSIAL'}")
    print(f"  project         : {os.environ.get('GOOGLE_CLOUD_PROJECT', '-')}")
    print(f"  location        : {os.environ.get('GOOGLE_CLOUD_LOCATION', '-')}")
    print(f"  model drafter   : {os.environ.get('OMNILEAD_AGENT_MODEL', DEFAULT_MODEL)}")
    print(f"  model triage    : {os.environ.get('OMNILEAD_AGENT_TRIAGE_MODEL', TRIAGE_MODEL)}")


def main() -> int:
    show_env()
    req = AnalyzeRequest.model_validate({
        "event": {"id": "smoke", "channel": "instagram", "kind": "comment",
                  "sender": {"handle": "@ani.majujaya", "name": "Ani"}, "text": TEXT,
                  "ts": datetime.now(timezone.utc).isoformat(), "post_ref": "p1", "comment_ref": "c1"},
    })
    failures = 0

    print("\n== 1. Triage LLM")
    try:
        out = asyncio.run(run_triage(build_triage_agent(), TEXT))
        print("  OK:", out)
    except Exception:
        failures += 1
        print("  GAGAL:")
        traceback.print_exc(limit=3)

    print("\n== 2. Orchestrator ADK (tool propose_*)")
    try:
        tri, cat = triage(req), default_catalog()
        ctx = DraftContext(req=req, tri=tri, catalog=cat, tools=Tools(req, tri, cat, Trace(goal="smoke")))
        proposals = AdkDrafter().draft(ctx)
        for step in ctx.tools.trace.steps:
            print(f"  [{step.n}] {step.tool}: {step.result[:80]}")
        print(f"  {len(proposals)} usulan:", [p.kind for p in proposals])
        if not proposals:
            failures += 1
            print("  PERINGATAN: LLM jalan tetapi tidak membuat usulan; cek model dan instruksi.")
    except Exception:
        failures += 1
        print("  GAGAL:")
        traceback.print_exc(limit=3)

    print("\n== Hasil:", "semua OK" if not failures else f"{failures} langkah gagal")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
