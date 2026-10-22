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


def test_public_business_name_is_independent_of_workspace_name():
    result = analyze(request(business="Nama Pemilik", public_business_name="Toko Pelanggan"), drafter=TemplateDrafter())
    text = " ".join(p.text for p in result.proposals)
    assert "Toko Pelanggan" in text and "Nama Pemilik" not in text


def test_missing_brand_or_knowledge_blocks_uninformed_replies():
    result = analyze(request(public_business_name=""), drafter=TemplateDrafter())
    assert result.flagged_for_review and not result.proposals
    result = analyze(request(public_business_name="Toko", documents=[], products=[]), drafter=TemplateDrafter())
    assert result.flagged_for_review and "knowledge base" in result.review_reason


def test_model_failure_template_requires_owner_review():
    class BrokenDrafter:
        def draft(self, ctx):
            raise RuntimeError("offline")
    result = analyze(request(), drafter=BrokenDrafter())
    outgoing = [p for p in result.proposals if p.kind in ("send_message", "reply_comment", "comment_post")]
    assert outgoing and all(any(g.check == "model_fallback" and g.status == "warn" for g in p.guard) for p in outgoing)


def test_thinking_config_matches_model_generation(monkeypatch):
    from omnilead_agent.adk_triage import generation_config
    monkeypatch.setenv("OMNILEAD_AGENT_THINKING", "low")
    legacy = generation_config("gemini-2.5-flash").thinking_config
    assert legacy.thinking_budget == 1024 and legacy.thinking_level is None
    modern = generation_config("gemini-3.8-flash").thinking_config
    assert modern.thinking_budget is None and modern.thinking_level is not None


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


def test_order_with_quantity_on_empty_knowledge_base_still_drafts():
    req = AnalyzeRequest.model_validate({
        "event": {"id": "kosong", "channel": "whatsapp", "kind": "message", "sender": {"phone": "0812", "name": "Dewi"},
                  "text": "Kak, mau pesan nasi box 50 pax buat Sabtu, harganya berapa ya?"},
        "business_context": {"business": "Toko Baru", "channel": "whatsapp"}})
    result = analyze(req, drafter=TemplateDrafter())
    assert any(p.kind == "send_message" for p in result.proposals)
    assert not any("Rp" in p.text for p in result.proposals if p.kind == "send_message")


def test_time_question_answers_faq_and_formal_greeting_drops_honorific():
    products = [{"id": "a", "name": "Paket A", "unit_price": 25000, "unit": "pax", "min_order": 30},
                {"id": "b", "name": "Paket B", "unit_price": 35000, "unit": "pax", "min_order": 30}]
    docs = [{"id": "faq", "name": "FAQ", "content": "Pengiriman: kami melayani antar dan kirim di area Bandung dan Cimahi."}]
    req = AnalyzeRequest.model_validate({
        "event": {"id": "fb", "channel": "facebook", "kind": "message", "sender": {"name": "Sari"},
                  "text": "bisa kirim ke Cimahi ga kak? buka jam berapa?"},
        "business_context": {"business": "Dapur", "channel": "facebook", "documents": docs, "products": products}})
    assert "tanya_harga" not in triage(req).intents
    text = " ".join(p.text for p in analyze(req, drafter=TemplateDrafter()).proposals)
    assert "Cimahi" in text and "cek dulu" not in text

    email = request(products=products)
    email.event.sender.name = "Pak Budi"
    email.event.text = "Mohon penawaran katering untuk acara kantor."
    text = " ".join(p.text for p in analyze(email, drafter=TemplateDrafter()).proposals)
    assert "Bapak/Ibu Budi" in text and "Paket A" in text and "Paket B" in text and " kak" not in text


def test_discount_request_without_policy_never_states_a_percentage():
    req = AnalyzeRequest.model_validate({
        "event": {"id": "d", "channel": "facebook", "kind": "message", "sender": {"name": "Sari"},
                  "text": "diskon 70% dong kak, nasi box 40 pax tgl 3 nov"},
        "business_context": {"business": "Dapur", "channel": "facebook",
                             "products": [{"id": "a", "name": "Paket A", "unit_price": 25000, "unit": "pax", "min_order": 30}]}})
    text = " ".join(p.text for p in analyze(req, drafter=TemplateDrafter()).proposals)
    assert "0%" not in text and "70%" not in text and "tanyakan dulu ke pemilik" in text
