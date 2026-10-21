from omnilead.connectors import handoff
from omnilead.models import Channel


def test_ingest_pasted_text_jadi_comment():
    c = handoff.ingest_pasted_text(
        channel=Channel.LINKEDIN,
        post_ref="post-x",
        author_handle="budi",
        text="  halo pak, masih ada slot?  ",
    )
    assert c.channel == Channel.LINKEDIN
    assert c.text == "halo pak, masih ada slot?"
    assert c.author_handle == "budi"
    assert c.id.startswith("handoff-linkedin-")


def test_build_handoff_berisi_teks_dan_url():
    pkg = handoff.build_handoff(Channel.LINKEDIN, "balasan draf")
    assert pkg["copy_text"] == "balasan draf"
    assert "linkedin.com" in pkg["open_url"]
