from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status

from app.config import Settings, get_settings
from app.schemas import AskRequest, AskResponse, UsageResponse
from app.services.llm_service import ModelUnavailableError, generate_answer
from app.services.usage_service import get_daily_usage

app = FastAPI(title="ISA Lens", version="0.2.0")

SettingsDep = Annotated[Settings, Depends(get_settings)]

@app.get("/hello")
def greet():
    return "Hello world"

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
    """Ask Gemini; try the fallback exactly once if the primary times out."""
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

