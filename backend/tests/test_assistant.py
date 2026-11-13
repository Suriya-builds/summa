from types import SimpleNamespace

import pytest

from app.services import assistant, llm
from app.services.assistant import check_figures, safe_eval


def test_safe_eval_arithmetic():
    assert safe_eval("(38000 - 21450.5) / 38000 * 100") == pytest.approx(43.551, rel=1e-3)
    assert safe_eval("1,200 + 300") == 1500


@pytest.mark.parametrize("expr", ["__import__('os')", "a + 1", "open('x')", "2 ** 99999"])
def test_safe_eval_rejects(expr):
    with pytest.raises((ValueError, SyntaxError)):
        safe_eval(expr)


def test_figure_check_flags_invented_numbers():
    tools = [{"total_amount": 3794.0, "change_pct": 74.8}]
    ok = check_figures("You spent ₹3,794 on food, up 74.8% on 12 Nov.", tools)
    assert ok["unverified"] == [] and ok["checked"] == 2
    bad = check_figures("You spent ₹5,000 on food.", tools)
    assert bad["unverified"] == ["₹5,000"]


def _block(**kw):
    return SimpleNamespace(**kw)


def test_tool_loop_uses_session_user_and_cites(client, monkeypatch):
    client.post("/api/auth/demo")
    calls = []

    def fake_create(*, system, messages, tools=None, output_schema=None, max_tokens=16000):
        calls.append(messages)
        if len(calls) == 1:
            return _block(stop_reason="tool_use", model="fake", content=[
                _block(type="tool_use", id="t1", name="search_transactions",
                       input={"counterparty_contains": "netflix", "user_id": 999})])
        result = messages[-1]["content"][0]["content"]
        import json
        total = json.loads(result)["total_amount"]
        return _block(stop_reason="end_turn", model="fake",
                      content=[_block(type="text", text=f"You paid Netflix ₹{total:,.0f} in total.")])

    monkeypatch.setattr(llm, "create_message", fake_create)
    monkeypatch.setattr(llm, "is_enabled", lambda: True)
    r = client.post("/api/assistant/ask", json={"question": "How much on Netflix?"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["figure_check"]["unverified"] == []
    assert body["citations"] and all("NETFLIX" in c["counterparty"] for c in body["citations"])
    assert body["tools"][0]["name"] == "search_transactions"


def test_ask_without_key_returns_503(client, user):
    assert client.post("/api/assistant/ask", json={"question": "hello"}).status_code == 503


def test_tool_error_returned_to_model():
    with pytest.raises(ValueError):
        assistant.run_tool(None, 1, "spending_breakdown", {"group_by": "planet"})
