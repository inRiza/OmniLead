from omnilead_agent.adk_orchestrator import build_agent, build_tools
from omnilead_agent.knowledge import business_catalog
from omnilead_agent.orchestrator import DraftContext, TemplateDrafter, Tools
from omnilead_agent.pipeline import analyze
from omnilead_agent.schemas import AnalyzeRequest, BusinessContext, Trace
from omnilead_agent.triage import triage


def request(**overrides):
    context = {"business": "Toko Biru", "channel": "email", "tone": "professional",
               "tone_instruction": "Gunakan bahasa formal dan profesional, tanpa emoji.",
               "documents": [{"id": "faq", "name": "Jam operasional", "content": "Kami buka setiap hari pukul 09.00–17.00 WIB."}],
               "products": []}
    context.update(overrides)
    return AnalyzeRequest.model_validate({"event": {"id": "knowledge", "channel": "email", "kind": "email",
        "sender": {"email": "customer@example.com", "name": "Ani"}, "text": "Jam buka toko kapan?"}, "business_context": context})


def test_rule_fallback_uses_owner_facts_and_tone_without_demo_business():
    result = analyze(request(), drafter=TemplateDrafter())
    text = " ".join(p.text for p in result.proposals)
    assert "09.00–17.00" in text and "Toko Biru" in text and "Bapak/Ibu" in text
    assert "Bu Rina" not in text and "🙏" not in text
    assert any("Knowledge base email" in line for line in result.trace.plan)


def test_workspace_product_prices_replace_demo_catalog():
    req = request(products=[{"id": "shirt", "name": "Kaos Basic", "unit_price": 75000, "unit": "pcs", "min_order": 1}])
    req.event.text = "harga kaos basic berapa?"
    result = analyze(req, drafter=TemplateDrafter())
    text = " ".join(p.text for p in result.proposals)
    assert "Rp75.000" in text and "Rp35.000" not in text and "Paket B" not in text
    assert not any(n.status == "block" for p in result.proposals for n in p.guard)


def test_adk_read_tool_receives_documents_and_workspace_catalog(monkeypatch):
    req = request()
    tri = triage(req)
    catalog = business_catalog(req.business_context)
    ctx = DraftContext(req=req, tri=tri, catalog=catalog, tools=Tools(req, tri, catalog, Trace(goal="test")))
    tools = {fn.__name__: fn for fn in build_tools(ctx, [])}
    data = tools["search_catalog_faq"]("jam buka")
    assert data["knowledge_sources"][0]["name"] == "Jam operasional"
    assert data["packages"] == []
    monkeypatch.setenv("OMNILEAD_AGENT_USE_MCP", "1")
    agent = build_agent(ctx, [])
    assert "Toko Biru" in agent.instruction
    assert all(callable(tool) for tool in agent.tools)  # global MCP catalog is not used for a tenant


def test_empty_business_context_never_inherits_another_catalog():
    catalog = business_catalog(BusinessContext(business="Empty", channel="instagram"))
    assert catalog.packages == () and catalog.allowed_amounts(60) == set()
