
"""Gemini generation with a single timeout-triggered fallback attempt."""

import logging
import time
from typing import Any

import httpx
from google import genai
from google.genai import types

from app.services.usage_service import record_usage

logger = logging.getLogger(__name__)


class ModelUnavailableError(Exception):
    """Raised when neither configured Gemini model returns a usable answer."""


def _generate_with_model(
    client: Any, model: str, prompt: str, timeout_ms: int
) -> tuple[str, int | None, int | None]:
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            http_options=types.HttpOptions(timeout=timeout_ms)
        ),
    )
    answer = response.text
    if not answer or not answer.strip():
        raise ModelUnavailableError(f"{model} returned no text")
    usage = getattr(response, "usage_metadata", None)
    tokens_in = getattr(usage, "prompt_token_count", None) if usage else None
    tokens_out = getattr(usage, "candidates_token_count", None) if usage else None
    return answer.strip(), tokens_in, tokens_out


def generate_answer(prompt: str, settings: Any) -> dict[str, Any]:
    """Call primary; retry once on fallback only when primary times out."""
    if not settings.gemini_api_key:
        raise ModelUnavailableError("Gemini API key is not configured")
    if settings.model_timeout_seconds <= 0:
        raise ValueError("MODEL_TIMEOUT_SECONDS must be greater than zero")
    if settings.primary_model == settings.fallback_model:
        raise ValueError("PRIMARY_MODEL and FALLBACK_MODEL must be different")

    timeout_ms = int(settings.model_timeout_seconds * 1000)
    client = genai.Client(api_key=settings.gemini_api_key)

    try:
        for attempt, model in enumerate((settings.primary_model, settings.fallback_model)):
            started = time.monotonic()
            try:
                answer, tokens_in, tokens_out = _generate_with_model(client, model, prompt, timeout_ms)
                duration_ms = (time.monotonic() - started) * 1000
                if attempt == 0:
                    input_rate = settings.primary_input_cost_per_million
                    output_rate = settings.primary_output_cost_per_million
                else:
                    input_rate = settings.fallback_input_cost_per_million
                    output_rate = settings.fallback_output_cost_per_million
                cost_usd = (
                    (tokens_in * input_rate + tokens_out * output_rate) / 1_000_000
                    if tokens_in is not None and tokens_out is not None
                    else None
                )
                record_usage(
                    settings.cost_log_path,
                    model=model,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    cost_usd=cost_usd,
                )
                logger.info(
                    "model=%s status=success fallback_used=%s duration_ms=%.0f "
                    "tokens_in=%s tokens_out=%s cost_usd=%s",
                    model,
                    attempt == 1,
                    duration_ms,
                    tokens_in,
                    tokens_out,
                    cost_usd,
                )
                return {
                    "answer": answer,
                    "model_used": model,
                    "fallback_used": attempt == 1,
                    "duration_ms": round(duration_ms, 2),
                    "tokens_in": tokens_in,
                    "tokens_out": tokens_out,
                }

            except (httpx.TimeoutException, TimeoutError) as exc:
                logger.warning(
                    "model=%s status=timeout fallback_used=%s error_type=%s",
                    model,
                    attempt == 1,
                    type(exc).__name__,
                )
                if attempt == 1:
                    raise ModelUnavailableError("Both Gemini models timed out") from exc
            except ModelUnavailableError as exc:
                logger.error(
                    "model=%s status=unavailable fallback_used=%s",
                    model,
                    attempt == 1,
                )
                raise ModelUnavailableError("Gemini returned no usable answer") from exc
            except Exception as exc:
                logger.exception(
                    "model=%s status=error fallback_used=%s error_type=%s",
                    model,
                    attempt == 1,
                    type(exc).__name__,
                )
                raise ModelUnavailableError("Gemini request failed") from exc

    finally:
        client.close()

    raise ModelUnavailableError("No Gemini model returned an answer")
