"""API request and response models."""

from typing import Literal

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=20_000)


class AskResponse(BaseModel):
    answer: str
    model_used: str
    fallback_used: bool
    duration_ms: float


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=20_000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=100)
    model: str = Field(default="", max_length=200)


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
