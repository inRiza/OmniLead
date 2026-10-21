from datetime import datetime, timezone

import pytest

from omnilead_agent.schemas import (
    AnalyzeRequest,
    EventIn,
    LeadContext,
    Sender,
    TimelineItem,
)

NOW = datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc)


def make_req(text, channel="instagram", kind="comment", lead=None, **kw) -> AnalyzeRequest:
    return AnalyzeRequest(
        event=EventIn(
            id="e1", channel=channel, kind=kind,
            sender=Sender(handle="@ani.majujaya", name="Ani"),
            text=text, ts=NOW, post_ref="p1", comment_ref="c1",
        ),
        lead=lead,
        **kw,
    )


@pytest.fixture
def ani_lead():
    return LeadContext(
        id="ani", name="Ani", company="PT Maju Jaya", stage="baru",
        timeline=[TimelineItem(channel="email", direction="in", text="info katering kantor")],
    )
