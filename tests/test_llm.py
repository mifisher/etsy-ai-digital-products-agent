import json

from radar.config import Lane
from radar.llm import judge_lane
from radar.models import LaneSignals

LANE = Lane(id="x", keywords=["kw"], credibility=0.9, brand_fit="careeros")
SIGNALS = LaneSignals(
    lane_id="x",
    keyword="kw",
    active_listings=500,
    median_favorites=40,
    median_price=18.0,
    sample_titles=["A", "B"],
    sample_size=2,
)

VALID_PAYLOAD = {
    "pain_urgency": 0.8,
    "willingness_to_pay": 0.7,
    "differentiation": 0.6,
    "ease_to_create": 0.9,
    "buildability": "factory",
    "buyer": "Solo consultants",
    "product_format": "Google Sheets + PDF",
    "differentiation_angle": "cash flow, not projects",
    "why_this_could_sell": "because reasons",
    "price_range_usd": [12, 29],
}


class _FakeClient:
    def __init__(self, content):
        self._content = content
        self.chat = self

    @property
    def completions(self):
        return self

    def create(self, **kwargs):
        class Msg:
            content = self._content

        class Choice:
            message = Msg()

        class Resp:
            choices = [Choice()]

        return Resp()


def test_judge_lane_parses_valid_payload():
    client = _FakeClient(json.dumps(VALID_PAYLOAD))
    j = judge_lane(client, "kimi", LANE, SIGNALS)

    assert j is not None
    assert j.pain_urgency == 0.8
    assert j.buildability == "factory"
    assert j.price_range_usd == [12, 29]


def test_judge_lane_clamps_out_of_range_scores():
    payload = dict(VALID_PAYLOAD, pain_urgency=1.7, differentiation=-0.4)
    client = _FakeClient(json.dumps(payload))
    j = judge_lane(client, "kimi", LANE, SIGNALS)

    assert j.pain_urgency == 1.0
    assert j.differentiation == 0.0


def test_judge_lane_returns_none_on_bad_json():
    client = _FakeClient("not json at all")
    assert judge_lane(client, "kimi", LANE, SIGNALS) is None


def test_judge_lane_returns_none_when_client_raises():
    class Boom:
        def __getattr__(self, name):
            raise RuntimeError("provider down")

    assert judge_lane(Boom(), "kimi", LANE, SIGNALS) is None
