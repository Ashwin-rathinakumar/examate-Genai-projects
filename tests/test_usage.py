import json

from app.services.usage_service import get_daily_usage, record_usage


def test_daily_usage_aggregates_tokens_and_cost(tmp_path):
    log_path = tmp_path / "logs" / "cost.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        "\n".join(
            [
                json.dumps({"date": "2026-10-26", "tokens_in": 100, "tokens_out": 50, "cost_usd": 0.000155}),
                json.dumps({"date": "2026-10-26", "tokens_in": 80, "tokens_out": 20, "cost_usd": 0.000074}),
                json.dumps({"date": "2026-10-27", "tokens_in": None, "tokens_out": None, "cost_usd": None}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    assert get_daily_usage(log_path) == [
        {
            "date": "2026-10-26",
            "tokens_in": 180,
            "tokens_out": 70,
            "cost_usd": 0.000229,
            "calls": 2,
            "calls_without_usage": 0,
        },
        {
            "date": "2026-10-27",
            "tokens_in": 0,
            "tokens_out": 0,
            "cost_usd": 0.0,
            "calls": 1,
            "calls_without_usage": 1,
        },
    ]


def test_usage_endpoint_reads_configured_cost_log(client, cost_log_path):
    record_usage(
        cost_log_path,
        model="gemini-2.5-flash",
        tokens_in=100,
        tokens_out=40,
        cost_usd=0.00013,
    )

    response = client.get("/usage")

    assert response.status_code == 200
    body = response.json()
    assert body["currency"] == "USD"
    assert body["days"][0]["tokens_in"] == 100
    assert body["days"][0]["tokens_out"] == 40
    assert body["days"][0]["cost_usd"] == 0.00013
