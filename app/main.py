import json
import logging
from collections.abc import AsyncIterator
from dataclasses import asdict
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse

from app.config import Settings, get_settings
from app.llm.errors import LLMConfigurationError, LLMUnavailable
from app.llm.factory import create_provider
from app.llm.reliable import AsyncReliableLLM
from app.llm.types import LLMRequest, Message
from app.schemas import AskRequest, AskResponse, ChatRequest, UsageResponse
from app.services.llm_service import ModelUnavailableError, generate_answer
from app.services.usage_service import get_daily_usage, record_usage

logger = logging.getLogger(__name__)

app = FastAPI(title="ISA Lens", version="0.3.0")

SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_llm(settings: SettingsDep) -> AsyncReliableLLM:
    return create_provider(settings)


LLMDep = Annotated[AsyncReliableLLM, Depends(get_llm)]


@app.get("/hello")
def say_hello():
    return "hello"


@app.get("/")
def say_root():
    return {"name": "ISA Lens", "health": "/health", "docs": "/docs"}


@app.get("/health")
def health(settings: SettingsDep) -> dict:
    """Liveness: the process is up. Must be fast and must not call the LLM or the DB."""
    return {"status": "ok", "app": settings.app_name, "environment": settings.environment}


@app.get("/usage", response_model=UsageResponse)
def usage(settings: SettingsDep) -> UsageResponse:
    """Return token totals and estimated costs per UTC day."""
    try:
        days = get_daily_usage(settings.cost_log_path)
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The usage log could not be read.",
        ) from exc
    return UsageResponse(days=days)


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest, settings: SettingsDep) -> AskResponse:
    """Compatibility endpoint for non-streaming Gemini answers."""
    try:
        result = generate_answer(request.question, settings)
    except ModelUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The answer service is temporarily unavailable. Please try again.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The answer service is not configured correctly.",
        ) from exc
    return AskResponse(**result)


def sse(data: dict, event: str | None = None) -> str:
    prefix = f"event: {event}\n" if event else ""
    return f"{prefix}data: {json.dumps(data)}\n\n"


@app.post("/chat")
async def chat(
    request: ChatRequest,
    provider: LLMDep,
    settings: SettingsDep,
) -> StreamingResponse:
    """Stream an answer and record token usage without storing message content."""
    llm_request = LLMRequest(
        messages=tuple(Message(role=message.role, content=message.content) for message in request.messages),
        model=request.model,
    )

    async def event_stream() -> AsyncIterator[str]:
        response_usage = None
        try:
            async for chunk in provider.stream(llm_request):
                if chunk.text:
                    yield sse({"delta": chunk.text})
                if chunk.usage is not None:
                    response_usage = chunk.usage
        except (LLMUnavailable, LLMConfigurationError) as error:
            yield sse({"error": str(error)}, event="error")
            return

        fallback_used = provider.last_provider_role == "fallback"
        model_used = settings.llm_fallback_model if fallback_used else settings.llm_model
        if response_usage is None:
            usage_data = {"input_tokens": 0, "output_tokens": 0, "estimated": True}
            tokens_in = None
            tokens_out = None
            cost_usd = None
        else:
            usage_data = asdict(response_usage)
            tokens_in = response_usage.input_tokens
            tokens_out = response_usage.output_tokens
            input_rate = (
                settings.fallback_input_cost_per_million
                if fallback_used
                else settings.primary_input_cost_per_million
            )
            output_rate = (
                settings.fallback_output_cost_per_million
                if fallback_used
                else settings.primary_output_cost_per_million
            )
            cost_usd = (tokens_in * input_rate + tokens_out * output_rate) / 1_000_000

        try:
            record_usage(
                settings.cost_log_path,
                model=model_used,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=cost_usd,
            )
        except OSError:
            logger.exception("Could not write the usage log")

        logger.info(
            "model=%s status=success fallback_used=%s tokens_in=%s tokens_out=%s",
            model_used,
            fallback_used,
            tokens_in,
            tokens_out,
        )
        yield sse(
            {
                "usage": usage_data,
                "cost_usd": cost_usd,
                "model_used": model_used,
                "fallback_used": fallback_used,
            },
            event="done",
        )

    return StreamingResponse(event_stream(), media_type="text/event-stream")
