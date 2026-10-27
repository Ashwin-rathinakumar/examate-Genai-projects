"""Append-only local token/cost log and daily aggregation."""

import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def record_usage(
    log_path: str | Path,
    *,
    model: str,
    tokens_in: int | None,
    tokens_out: int | None,
    cost_usd: float | None,
) -> None:
    """Append usage metadata without storing prompts or model answers."""
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "date": datetime.now(UTC).date().isoformat(),
        "model": model,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": round(cost_usd, 10) if cost_usd is not None else None,
    }
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, separators=(",", ":")) + "\n")


def get_daily_usage(log_path: str | Path) -> list[dict[str, Any]]:
    """Return UTC-day totals from the append-only usage log."""
    path = Path(log_path)
    totals: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "date": "",
            "tokens_in": 0,
            "tokens_out": 0,
            "cost_usd": 0.0,
            "calls": 0,
            "calls_without_usage": 0,
        }
    )
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
                day = item["date"]
                day_totals = totals[day]
                day_totals["date"] = day
                day_totals["calls"] += 1
                if item.get("tokens_in") is None or item.get("tokens_out") is None:
                    day_totals["calls_without_usage"] += 1
                else:
                    day_totals["tokens_in"] += int(item["tokens_in"])
                    day_totals["tokens_out"] += int(item["tokens_out"])
                if item.get("cost_usd") is not None:
                    day_totals["cost_usd"] += float(item["cost_usd"])
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(f"Invalid cost log entry at line {line_number}") from exc
    return [
        {**totals[day], "cost_usd": round(totals[day]["cost_usd"], 10)}
        for day in sorted(totals)
    ]
