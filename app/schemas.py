"""API request and response models."""

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=20_000)


class AskResponse(BaseModel):
    answer: str
    model_used: str
    fallback_used: bool
    duration_ms: float


class DailyUsage(BaseModel):
    date: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    calls: int
    calls_without_usage: int


class UsageResponse(BaseModel):
    currency: str = "USD"
    cost_basis: str = "estimated from configured model rates"
    days: list[DailyUsage]
