import logging
import random
import time
from collections.abc import AsyncIterator, Callable, Iterator

from app.llm.errors import LLMConfigurationError, LLMUnavailable
from app.llm.types import LLMProvider, LLMRequest, ProviderError, TextChunk

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
NON_RETRYABLE_STATUS_CODES = {400, 401, 403, 404}


def retry_delay(attempt: int, retry_after: float | None = None) -> float:
    """Return Retry-After when supplied, otherwise capped jittered backoff."""
    if retry_after is not None:
        return max(0.0, retry_after)
    return random.uniform(0.0, min(8.0, 0.5 * (2**attempt)))


def is_retryable(error: ProviderError) -> bool:
    return error.status_code is None or error.status_code in RETRYABLE_STATUS_CODES


class ReliableLLM:
    def __init__(
        self,
        primary: LLMProvider,
        fallback: LLMProvider | None = None,
        primary_retries: int = 3,
        fallback_retries: int = 1,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.primary_retries = primary_retries
        self.fallback_retries = fallback_retries
        self.sleep = sleep
        self.last_provider_role: str | None = None

    def stream(self, request: LLMRequest) -> Iterator[TextChunk]:
        self.last_provider_role = "primary"
        try:
            yield from self._stream_provider(
                self.primary,
                request,
                max_retries=self.primary_retries,
            )
            logger.info("llm_provider_role=primary status=success")
        except LLMUnavailable as error:
            if error.partial_output:
                raise
            if self.fallback is None:
                raise
            self.last_provider_role = "fallback"
            yield from self._stream_provider(
                self.fallback,
                request,
                max_retries=self.fallback_retries,
            )
            logger.info("llm_provider_role=fallback status=success")

    def _stream_provider(
        self,
        provider: LLMProvider,
        request: LLMRequest,
        max_retries: int,
    ) -> Iterator[TextChunk]:
        for attempt in range(max_retries + 1):
            emitted_text = False
            try:
                for chunk in provider.stream(request):
                    if chunk.text:
                        emitted_text = True
                    yield chunk
                return
            except ProviderError as error:
                if error.status_code in NON_RETRYABLE_STATUS_CODES:
                    raise LLMConfigurationError(str(error)) from error
                if emitted_text or not is_retryable(error):
                    raise LLMUnavailable(str(error), partial_output=emitted_text) from error
                if attempt == max_retries:
                    raise LLMUnavailable(str(error)) from error
                self.sleep(retry_delay(attempt, error.retry_after))


class AsyncReliableLLM:
    def __init__(
        self,
        primary: LLMProvider,
        fallback: LLMProvider | None = None,
        primary_retries: int = 3,
        fallback_retries: int = 1,
    ) -> None:
        self.primary = primary
        self.fallback = fallback
        self.primary_retries = primary_retries
        self.fallback_retries = fallback_retries
        self.last_provider_role: str | None = None

    async def stream(self, request: LLMRequest) -> AsyncIterator[TextChunk]:
        self.last_provider_role = "primary"
        try:
            async for chunk in self._stream_provider(self.primary, request, self.primary_retries):
                yield chunk
            logger.info("llm_provider_role=primary status=success")
        except LLMUnavailable as error:
            if error.partial_output or self.fallback is None:
                raise
            self.last_provider_role = "fallback"
            async for chunk in self._stream_provider(self.fallback, request, self.fallback_retries):
                yield chunk
            logger.info("llm_provider_role=fallback status=success")

    async def _stream_provider(
        self,
        provider: LLMProvider,
        request: LLMRequest,
        max_retries: int,
    ) -> AsyncIterator[TextChunk]:
        for attempt in range(max_retries + 1):
            emitted_text = False
            try:
                async for chunk in provider.stream_async(request):
                    if chunk.text:
                        emitted_text = True
                    yield chunk
                return
            except ProviderError as error:
                if error.status_code in NON_RETRYABLE_STATUS_CODES:
                    raise LLMConfigurationError(str(error)) from error
                if emitted_text or not is_retryable(error):
                    raise LLMUnavailable(str(error), partial_output=emitted_text) from error
                if attempt == max_retries:
                    raise LLMUnavailable(str(error)) from error
                import asyncio

                await asyncio.sleep(retry_delay(attempt, error.retry_after))
