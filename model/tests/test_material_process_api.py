from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import fitz
import pytest
from fastapi.testclient import TestClient

from schemas.model_contract import (
    ChatResponse,
    ScopeDecision,
)
from schemas.vision_contract import (
    VisionRequest,
    VisionResponse,
    VisionResponseStatus,
    VisualElement,
    VisualElementType,
)
from src.agents.gemini_multimodal_agent import (
    GeminiMultimodalProviderError,
)
from src.agents.multimodal_agent import MultimodalAgent
from src.agents.multimodal_client import (
    MultimodalTransportError,
)
from src.ingestion.material_storage import MaterialStorage
from src.service.api import create_app
from src.service.material_processing_service import (
    MaterialProcessingService,
)


class FakePipeline:
    def run(
        self,
        request,
        course_relevance_score,
        unsafe=False,
    ) -> ChatResponse:
        return ChatResponse(
            answer="test answer",
            scope=ScopeDecision.IN_MATERIAL,
            confidence=0.90,
        )


class RecordingMultimodalAgent(MultimodalAgent):
    def __init__(self) -> None:
        self.requests: list[VisionRequest] = []

    def analyze(
        self,
        request: VisionRequest,
    ) -> VisionResponse:
        self.requests.append(request)

        return VisionResponse(
            request_id=request.request_id,
            material_id=request.material_id,
            material_name=request.material_name,
            page_number=request.page_number,
            asset_id=request.asset_id,
            status=VisionResponseStatus.SUCCESS,
            page_summary="Verified visual content.",
            ocr_text="",
            visual_elements=[
                VisualElement(
                    element_id="element-001",
                    element_type=VisualElementType.DIAGRAM,
                    title="Visual",
                    description="A visible material visual.",
                    confidence=0.95,
                )
            ],
            tables=[],
            relationships=[],
            warnings=[],
            confidence=0.95,
            agent_model="fake-vision-model",
            prompt_version=request.prompt_version,
        )


class FailingMultimodalAgent(MultimodalAgent):
    def analyze(
        self,
        request: VisionRequest,
    ) -> VisionResponse:
        raise MultimodalTransportError(
            "provider transport failed with secret-key"
        )


class FailingGeminiMultimodalAgent(MultimodalAgent):
    def analyze(
        self,
        request: VisionRequest,
    ) -> VisionResponse:
        raise GeminiMultimodalProviderError(
            "Gemini Vision request was rejected with HTTP status 400: "
            "models/gemini-3.5-flash is not found"
        )


def create_visual_pdf_bytes() -> bytes:
    with fitz.open() as document:
        page = document.new_page()
        page.insert_text(
            (72, 72),
            "Exception flowchart",
        )
        page.draw_rect(
            fitz.Rect(72, 100, 250, 180),
            color=(0, 0, 0),
            width=1,
        )
        return document.tobytes()


def create_image_bytes(
    tmp_path: Path,
    *,
    filename: str,
    width: int,
    height: int,
) -> bytes:
    pixmap = fitz.Pixmap(
        fitz.csRGB,
        fitz.IRect(0, 0, width, height),
        0,
    )
    pixmap.clear_with(220)

    image_path = tmp_path / filename
    pixmap.save(str(image_path))

    return image_path.read_bytes()


def create_client(
    tmp_path: Path,
    *,
    agent: MultimodalAgent | None = None,
) -> tuple[TestClient, MaterialStorage]:
    storage = MaterialStorage(tmp_path / "uploads")
    processing_service = MaterialProcessingService(
        storage=storage,
        work_root=tmp_path / "processing",
    )

    @contextmanager
    def agent_context(
        mode: str,
    ) -> Iterator[MultimodalAgent | None]:
        assert mode in {"none", "demo", "external"}
        yield agent

    app = create_app(
        pipeline=FakePipeline(),
        material_storage=storage,
        material_processing_service=processing_service,
        multimodal_agent_context_factory=agent_context,
    )

    return TestClient(app), storage


def store_pdf(
    storage: MaterialStorage,
) -> str:
    stored = storage.store(
        filename="lesson.pdf",
        content_type="application/pdf",
        content=create_visual_pdf_bytes(),
    )

    return stored.material_id


def store_image(
    tmp_path: Path,
    storage: MaterialStorage,
    *,
    filename: str,
    content_type: str,
) -> str:
    stored = storage.store(
        filename=filename,
        content_type=content_type,
        content=create_image_bytes(
            tmp_path,
            filename=f"source-{filename}",
            width=6,
            height=4,
        ),
    )

    return stored.material_id


@pytest.mark.parametrize(
    (
        "store_material",
        "expected_file_type",
    ),
    [
        (
            lambda tmp_path, storage: store_pdf(storage),
            "pdf",
        ),
        (
            lambda tmp_path, storage: store_image(
                tmp_path,
                storage,
                filename="diagram.png",
                content_type="image/png",
            ),
            "png",
        ),
        (
            lambda tmp_path, storage: store_image(
                tmp_path,
                storage,
                filename="photo.jpeg",
                content_type="image/jpeg",
            ),
            "jpeg",
        ),
    ],
)
def test_process_material_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    store_material: Any,
    expected_file_type: str,
) -> None:
    monkeypatch.setenv(
        "MATERIAL_MULTIMODAL_AGENT",
        "demo",
    )
    agent = RecordingMultimodalAgent()
    client, storage = create_client(
        tmp_path,
        agent=agent,
    )
    material_id = store_material(tmp_path, storage)

    response = client.post(
        f"/v1/materials/{material_id}/process"
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["material_id"] == material_id
    assert payload["file_type"] == expected_file_type
    assert payload["processing_status"] == "completed"
    assert payload["total_pages"] == 1
    assert payload["total_assets"] == 1
    assert payload["total_vision_requests"] == 1
    assert payload["total_vision_responses"] == 1
    assert payload["verified_count"] == 1
    assert payload["needs_review_count"] == 0
    assert payload["rejected_count"] == 0
    assert not Path(payload["pages_manifest_ref"]).is_absolute()
    assert not Path(payload["assets_manifest_ref"]).is_absolute()
    assert "stored_path" not in payload
    assert len(agent.requests) == 1


def test_unknown_material_id_returns_404(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "MATERIAL_MULTIMODAL_AGENT",
        "demo",
    )
    client, _storage = create_client(
        tmp_path,
        agent=RecordingMultimodalAgent(),
    )

    response = client.post(
        "/v1/materials/material-0000000000000000/process"
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_unsupported_multimodal_mode_returns_400(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "MATERIAL_MULTIMODAL_AGENT",
        "unsupported",
    )
    client, storage = create_client(
        tmp_path,
        agent=RecordingMultimodalAgent(),
    )
    material_id = store_pdf(storage)

    response = client.post(
        f"/v1/materials/{material_id}/process"
    )

    assert response.status_code == 400
    assert (
        "MATERIAL_MULTIMODAL_AGENT"
        in response.json()["detail"]
    )


def test_tampered_or_missing_stored_file_returns_400(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "MATERIAL_MULTIMODAL_AGENT",
        "demo",
    )
    client, storage = create_client(
        tmp_path,
        agent=RecordingMultimodalAgent(),
    )
    material_id = store_pdf(storage)
    stored = storage.get(material_id)
    Path(stored.stored_path).write_bytes(b"tampered")

    response = client.post(
        f"/v1/materials/{material_id}/process"
    )

    assert response.status_code == 400
    assert "checksum mismatch" in response.json()["detail"]


def test_external_provider_failure_returns_502(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "MATERIAL_MULTIMODAL_AGENT",
        "external",
    )
    client, storage = create_client(
        tmp_path,
        agent=FailingMultimodalAgent(),
    )
    material_id = store_pdf(storage)

    response = client.post(
        f"/v1/materials/{material_id}/process"
    )

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "External multimodal provider failed"
    )
    assert "secret-key" not in response.text


def test_gemini_provider_failure_returns_safe_detail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "MATERIAL_MULTIMODAL_AGENT",
        "external",
    )
    client, storage = create_client(
        tmp_path,
        agent=FailingGeminiMultimodalAgent(),
    )
    material_id = store_pdf(storage)

    response = client.post(
        f"/v1/materials/{material_id}/process"
    )

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "External multimodal provider failed: "
        "Gemini Vision request was rejected with HTTP status 400: "
        "models/gemini-3.5-flash is not found"
    )


def test_existing_health_chat_and_upload_remain_green(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "MATERIAL_MULTIMODAL_AGENT",
        "demo",
    )
    client, _storage = create_client(
        tmp_path,
        agent=RecordingMultimodalAgent(),
    )

    health_response = client.get("/health")
    chat_response = client.post(
        "/v1/chat",
        json={
            "request": {
                "student_id": "student-001",
                "course_id": "course-001",
                "class_session_id": "session-001",
                "phase": "during_class",
                "question": "Gradient descent คืออะไร",
            },
            "course_relevance_score": 0.90,
            "unsafe": False,
        },
    )
    upload_response = client.post(
        "/v1/materials/upload",
        files={
            "file": (
                "lesson.pdf",
                create_visual_pdf_bytes(),
                "application/pdf",
            )
        },
    )

    assert health_response.status_code == 200
    assert chat_response.status_code == 200
    assert upload_response.status_code == 201
