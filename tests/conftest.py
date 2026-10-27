import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app


@pytest.fixture
def cost_log_path(tmp_path):
    return tmp_path / "cost_log.jsonl"


@pytest.fixture
def client(cost_log_path):
    app.dependency_overrides[get_settings] = lambda: Settings(
        app_name="examate-rag", environment="test", cost_log_path=str(cost_log_path)
    )
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
