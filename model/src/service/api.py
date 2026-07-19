from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from schemas.model_contract import ChatRequest, ChatResponse


class ChatAPIRequest(BaseModel):
    request: ChatRequest
    course_relevance_score: float = Field(ge=0, le=1)
    unsafe: bool = False


def create_app(pipeline: Any) -> FastAPI:
    app = FastAPI(
        title="Learning Companion Model API",
        version="0.1.0",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "learning-companion-model",
        }

    @app.post(
        "/v1/chat",
        response_model=ChatResponse,
    )
    def chat(payload: ChatAPIRequest) -> ChatResponse:
        return pipeline.run(
            request=payload.request,
            course_relevance_score=(
                payload.course_relevance_score
            ),
            unsafe=payload.unsafe,
        )

    return app