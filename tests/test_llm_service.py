from types import SimpleNamespace

import pytest

from app.services import llm_service


class FakeModels:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = []

    def generate_content(self, *, model, contents, config):
        self.calls.append((model, contents, config))
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(
            text=outcome,
            usage_metadata=SimpleNamespace(prompt_token_count=12, candidates_token_count=8),
        )


class FakeClient:
    def __init__(self, outcomes):
        self.models = FakeModels(outcomes)
        self.closed = False

    def close(self):
        self.closed = True


@pytest.fixture
def settings():
    return SimpleNamespace(
        gemini_api_key="test-key",
        primary_model="primary-model",
        fallback_model="fallback-model",
        model_timeout_seconds=15.0,
        cost_log_path="unused-cost-log.jsonl",
        primary_input_cost_per_million=0.30,
        primary_output_cost_per_million=2.50,
        fallback_input_cost_per_million=0.10,
        fallback_output_cost_per_million=0.40,
    )


def test_primary_success_does_not_call_fallback(monkeypatch, settings, tmp_path):
    settings.cost_log_path = str(tmp_path / "cost.jsonl")
    client = FakeClient(["primary answer"])
    monkeypatch.setattr(llm_service.genai, "Client", lambda **kwargs: client)

    result = llm_service.generate_answer("question", settings)

    assert result["answer"] == "primary answer"
    assert result["model_used"] == "primary-model"
    assert result["fallback_used"] is False
    assert [call[0] for call in client.models.calls] == ["primary-model"]
    assert client.closed
    assert (tmp_path / "cost.jsonl").exists()


def test_primary_timeout_retries_fallback_once(monkeypatch, settings, tmp_path):
    settings.cost_log_path = str(tmp_path / "cost.jsonl")
    client = FakeClient([TimeoutError("primary timed out"), "fallback answer"])
    monkeypatch.setattr(llm_service.genai, "Client", lambda **kwargs: client)

    result = llm_service.generate_answer("question", settings)

    assert result["answer"] == "fallback answer"
    assert result["model_used"] == "fallback-model"
    assert result["fallback_used"] is True
    assert [call[0] for call in client.models.calls] == ["primary-model", "fallback-model"]
    assert client.closed
    log_line = (tmp_path / "cost.jsonl").read_text(encoding="utf-8").strip()
    assert '"model":"fallback-model"' in log_line


def test_two_timeouts_raise_controlled_error_and_do_not_retry_again(monkeypatch, settings):
    client = FakeClient([TimeoutError("primary timed out"), TimeoutError("fallback timed out")])
    monkeypatch.setattr(llm_service.genai, "Client", lambda **kwargs: client)

    with pytest.raises(llm_service.ModelUnavailableError, match="Both Gemini models timed out"):
        llm_service.generate_answer("question", settings)

    assert len(client.models.calls) == 2
    assert client.closed


def test_missing_api_key_fails_before_client_creation(settings, monkeypatch):
    settings.gemini_api_key = ""

    def unexpected_client(**kwargs):
        pytest.fail("client must not be created without an API key")

    monkeypatch.setattr(llm_service.genai, "Client", unexpected_client)
    with pytest.raises(llm_service.ModelUnavailableError, match="API key is not configured"):
        llm_service.generate_answer("question", settings)
