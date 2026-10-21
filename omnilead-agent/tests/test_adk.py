"""Tes orkestrator ADK dengan model palsu (tanpa kredensial Gemini)."""

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from omnilead_agent.adk_orchestrator import AdkDrafter
from omnilead_agent.pipeline import analyze
from tests.conftest import make_req

GOLDEN = "Kak, bisa buat 60 orang tgl 30? harga? PT Maju Jaya"


def _call(name, **args):
    return types.Part(function_call=types.FunctionCall(name=name, args=args))


class ScriptedLlm(BaseLlm):
    """Memutar rangkaian tool call lalu menutup dengan teks."""

    model: str = "scripted"
    script: list = []

    async def generate_content_async(self, llm_request, stream=False):
        done = sum(
            1 for c in llm_request.contents for p in c.parts if p.function_response
        )
        # satu giliran = satu kelompok tool call; jalankan berurutan per giliran
        if done < len(self.script):
            yield LlmResponse(content=types.Content(role="model", parts=[self.script[done]]))
        else:
            yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text="selesai")]))


def _script():
    return [
        _call("get_timeline"),
        _call("search_catalog_faq", query="nasi box 60 pax"),
        _call("check_channel_window", channel="instagram"),
        _call("score_lead"),
        _call("propose_reply", text="Detailnya sudah kami DM ya kak", reason="harga tidak di publik"),
        _call("propose_private_reply",
              text="Paket B Rp35.000/pax, total Rp2.100.000 untuk 60 pax, min. 30 pax.",
              reason="detail harga dari katalog"),
        _call("propose_crm_update", stage="penawaran", reason="minta penawaran"),
    ]


def test_adk_agent_proposes_only(ani_lead):
    drafter = AdkDrafter(model=ScriptedLlm(script=_script()))
    r = analyze(make_req(GOLDEN, lead=ani_lead), drafter=drafter)
    kinds = [p.kind for p in r.proposals]
    assert kinds == ["reply_comment", "send_message", "crm_update"]
    pub = r.proposals[0]
    assert pub.public and pub.comment_ref == "c1" and pub.recipient == "@ani.majujaya"
    assert [s.tool for s in r.trace.steps][:4] == [
        "get_timeline", "search_catalog_faq", "check_channel_window", "score_lead"
    ]
    assert len(r.trace.steps) <= 8
    assert all(n.status == "pass" for p in r.proposals for n in p.guard)


def test_adk_wrong_price_is_revised_by_guard(ani_lead):
    script = _script()
    script[5] = _call("propose_private_reply", text="Paket B cuma Rp20.000/pax kak", reason="x")
    r = analyze(make_req(GOLDEN, lead=ani_lead), drafter=AdkDrafter(model=ScriptedLlm(script=script)))
    dm = next(p for p in r.proposals if p.kind == "send_message")
    assert "Rp20.000" not in dm.text and "Rp2.100.000" in dm.text
    assert r.trace.revisions == 1


def test_llm_failure_falls_back_to_template(ani_lead):
    class Boom(BaseLlm):
        model: str = "boom"

        async def generate_content_async(self, llm_request, stream=False):
            raise RuntimeError("down")
            yield  # pragma: no cover

    r = analyze(make_req(GOLDEN, lead=ani_lead), drafter=AdkDrafter(model=Boom()))
    assert r.proposals and any("templat" in x for x in r.trace.plan)
