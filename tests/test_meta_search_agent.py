import json
from io import BytesIO

import numpy as np
import pytest

from scripts import meta_search_agent as agent
from scripts.pilot_math_revision import repair


def test_action_validation():
    assert (
        agent.parse_action('{"action":"local","reason":"refine"}')["action"] == "local"
    )
    with pytest.raises(ValueError):
        agent.parse_action('{"action":"execute_shell","reason":"bad"}')


def test_budget_reservation_and_usage(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "load_key", lambda: "test-only")
    response = dict(
        usage=dict(prompt_tokens=100, completion_tokens=20),
        choices=[dict(message=dict(content='{"action":"local","reason":"refine"}'))],
    )
    monkeypatch.setattr(
        agent.urllib.request,
        "urlopen",
        lambda *a, **kw: BytesIO(json.dumps(response).encode()),
    )
    ledger = tmp_path / "ledger.jsonl"
    result = agent.choose({"score": 2.5}, ledger)
    events = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert len(events) == 2
    assert agent.ledger_total(events) == result["estimated_usd"]
    ledger.write_text(json.dumps(dict(id="previous", charged_usd=9.99)) + "\n")
    with pytest.raises(RuntimeError, match="allowance"):
        agent.choose({}, ledger)


def test_failure_keeps_reservation(tmp_path, monkeypatch):
    monkeypatch.setattr(agent, "load_key", lambda: "test-only")

    def fail(*args, **kwargs):
        raise TimeoutError

    monkeypatch.setattr(agent.urllib.request, "urlopen", fail)
    ledger = tmp_path / "ledger.jsonl"
    with pytest.raises(RuntimeError, match="reservation retained"):
        agent.choose({}, ledger)
    events = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert agent.ledger_total(events) == agent.RESERVATION


def test_window_budget_and_incumbent():
    initial = repair(np.random.default_rng(2).uniform(0.1, 0.7, 12))
    final, steps = agent.search_window(initial, "local", 25, 1, 17)
    assert sum(s["function_evaluations"] for s in steps) == 17
    assert final[2::3].sum() >= initial[2::3].sum()
