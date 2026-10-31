import json

from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.llm.fake import FakeProvider
from app.llm.reliable import AsyncReliableLLM
from app.main import app, get_llm


def test_chat_streams_sse_events(tmp_path):
    cost_log_path = tmp_path / "chat-cost.jsonl"
    app.dependency_overrides[get_settings] = lambda: Settings(
        environment="test",
        cost_log_path=str(cost_log_path),
        _env_file=None,
    )
    app.dependency_overrides[get_llm] = lambda: AsyncReliableLLM(FakeProvider(chunks=("Hi", " there")))
    try:
        with TestClient(app) as client:
            response = client.post(
                "/chat",
                json={"messages": [{"role": "user", "content": "Hello"}], "model": "fake-model"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert 'data: {"delta": "Hi"}' in response.text
    assert 'data: {"delta": " there"}' in response.text
    assert "event: done" in response.text
    done = response.text.split("event: done\n")[1].split("\n\n")[0]
    done_data = json.loads(done.removeprefix("data: "))
    assert done_data["usage"]["output_tokens"] == 2
    assert done_data["model_used"] == "gemini-3.8-flash"
    assert done_data["fallback_used"] is False
    assert cost_log_path.exists()
