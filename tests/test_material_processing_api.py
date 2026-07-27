from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

from schemas.material_contract import (
    MaterialStoredProcessingStatus,
)
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
    def __init__(
        self,
        status_reader=None,
    ) -> None:
        self.requests: list[VisionRequest] = []
        self.status_reader = status_reader
        self.observed_status: str | None = None

    def analyze(
        self,
        request: VisionRequest,
    ) -> VisionResponse:
        self.requests.append(request)

        if self.status_reader is not None:
            self.observed_status = self.status_reader(
                request.material_id
            )

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
            "provider failed with api-key-secret"
        )


def create_visual_pdf_bytes() -> bytes:
    with fitz.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "Exception flowchart")
        page.draw_rect(
            fitz.Rect(72, 100, 250, 180),
            color=(0, 0, 0),
            width=1,
        )
        return document.tobytes()


def create_image_bytes(
    tmp_path: Path,
    filename: str,
) -> bytes:
    pixmap = fitz.Pixmap(
        fitz.csRGB,
        fitz.IRect(0, 0, 6, 4),
        0,
    )
    pixmap.clear_with(210)

    image_path = tmp_path / filename
    pixmap.save(str(image_path))

    return image_path.read_bytes()


def create_client(
    *,
    storage_root: Path,
    work_root: Path,
    agent: MultimodalAgent | None,
) -> tuple[
    TestClient,
    MaterialStorage,
    MaterialProcessingService,
]:
    storage = MaterialStorage(storage_root)
    service = MaterialProcessingService(
        storage=storage,
        work_root=work_root,
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
        material_processing_service=service,
        multimodal_agent_context_factory=agent_context,
    )

    return TestClient(app), storage, service


def store_pdf(
    storage: MaterialStorage,
) -> str:
    stored = storage.store(
        filename="lesson.pdf",
        content_type="application/pdf",
        content=create_visual_pdf_bytes(),
    )

    return stored.material_id


def test_status_for_uploaded_unprocessed_material_is_stored(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MATERIAL_MULTIMODAL_AGENT", "demo")
    client, storage, _service = create_client(
        storage_root=tmp_path / "uploads",
        work_root=tmp_path / "processing",
        agent=RecordingMultimodalAgent(),
    )
    material_id = store_pdf(storage)

    response = client.get(
        f"/v1/materials/{material_id}/status"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["material_id"] == material_id
    assert payload["processing_status"] == "stored"
    assert payload["original_filename"] == "lesson.pdf"
    assert payload["stored_path"]
    assert payload["total_pages"] == 0
    assert payload["total_assets"] == 0
    assert payload["error_message"] is None


@pytest.mark.parametrize(
    (
        "filename",
        "content_type",
        "expected_file_type",
        "content_factory",
    ),
    [
        (
            "lesson.pdf",
            "application/pdf",
            "pdf",
            lambda tmp_path: create_visual_pdf_bytes(),
        ),
        (
            "diagram.png",
            "image/png",
            "png",
            lambda tmp_path: create_image_bytes(
                tmp_path,
                "source.png",
            ),
        ),
        (
            "photo.jpeg",
            "image/jpeg",
            "jpeg",
            lambda tmp_path: create_image_bytes(
                tmp_path,
                "source.jpg",
            ),
        ),
    ],
)
def test_process_persists_processed_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    filename: str,
    content_type: str,
    expected_file_type: str,
    content_factory,
) -> None:
    monkeypatch.setenv("MATERIAL_MULTIMODAL_AGENT", "demo")
    agent = RecordingMultimodalAgent()
    client, storage, _service = create_client(
        storage_root=tmp_path / "uploads",
        work_root=tmp_path / "processing",
        agent=agent,
    )
    stored = storage.store(
        filename=filename,
        content_type=content_type,
        content=content_factory(tmp_path),
    )

    process_response = client.post(
        f"/v1/materials/{stored.material_id}/process"
    )
    status_response = client.get(
        f"/v1/materials/{stored.material_id}/status"
    )

    assert process_response.status_code == 200
    assert status_response.status_code == 200
    payload = status_response.json()
    assert payload["file_type"] == expected_file_type
    assert payload["processing_status"] == "processed"
    assert payload["total_pages"] == 1
    assert payload["total_assets"] == 1
    assert payload["total_vision_requests"] == 1
    assert payload["total_vision_responses"] == 1
    assert payload["verified_count"] == 1
    assert payload["needs_review_count"] == 0
    assert payload["rejected_count"] == 0


def test_process_sets_processing_before_work_begins(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MATERIAL_MULTIMODAL_AGENT", "demo")
    storage_root = tmp_path / "uploads"
    work_root = tmp_path / "processing"

    captured_service: dict[str, MaterialProcessingService] = {}

    def read_status(material_id: str) -> str:
        return captured_service[
            "service"
        ].get_status(material_id).processing_status.value

    agent = RecordingMultimodalAgent(
        status_reader=read_status
    )
    client, storage, service = create_client(
        storage_root=storage_root,
        work_root=work_root,
        agent=agent,
    )
    captured_service["service"] = service
    material_id = store_pdf(storage)

    response = client.post(
        f"/v1/materials/{material_id}/process"
    )

    assert response.status_code == 200
    assert agent.observed_status == "processing"


def test_status_survives_server_restart(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MATERIAL_MULTIMODAL_AGENT", "demo")
    storage_root = tmp_path / "uploads"
    work_root = tmp_path / "processing"

    first_client, first_storage, _first_service = create_client(
        storage_root=storage_root,
        work_root=work_root,
        agent=RecordingMultimodalAgent(),
    )
    material_id = store_pdf(first_storage)
    assert first_client.post(
        f"/v1/materials/{material_id}/process"
    ).status_code == 200

    second_client, _second_storage, _second_service = create_client(
        storage_root=storage_root,
        work_root=work_root,
        agent=RecordingMultimodalAgent(),
    )

    response = second_client.get(
        f"/v1/materials/{material_id}/status"
    )

    assert response.status_code == 200
    assert response.json()["processing_status"] == "processed"
    assert response.json()["total_assets"] == 1


def test_unknown_material_status_returns_404(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MATERIAL_MULTIMODAL_AGENT", "demo")
    client, _storage, _service = create_client(
        storage_root=tmp_path / "uploads",
        work_root=tmp_path / "processing",
        agent=RecordingMultimodalAgent(),
    )

    response = client.get(
        "/v1/materials/material-0000000000000000/status"
    )

    assert response.status_code == 404


def test_tampered_material_status_returns_conflict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MATERIAL_MULTIMODAL_AGENT", "demo")
    client, storage, _service = create_client(
        storage_root=tmp_path / "uploads",
        work_root=tmp_path / "processing",
        agent=RecordingMultimodalAgent(),
    )
    material_id = store_pdf(storage)
    stored = storage.get(material_id)
    Path(stored.stored_path).write_bytes(b"tampered")

    response = client.get(
        f"/v1/materials/{material_id}/status"
    )

    assert response.status_code == 409
    assert "checksum mismatch" in response.json()["detail"]


def test_process_failure_persists_failed_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MATERIAL_MULTIMODAL_AGENT", "external")
    client, storage, _service = create_client(
        storage_root=tmp_path / "uploads",
        work_root=tmp_path / "processing",
        agent=FailingMultimodalAgent(),
    )
    material_id = store_pdf(storage)

    process_response = client.post(
        f"/v1/materials/{material_id}/process"
    )
    status_response = client.get(
        f"/v1/materials/{material_id}/status"
    )

    assert process_response.status_code == 502
    assert status_response.status_code == 200
    assert status_response.json()["processing_status"] == "failed"
    assert status_response.json()["error_message"] == (
        "External multimodal provider failed"
    )
    assert "api-key-secret" not in status_response.text


def test_existing_health_chat_and_upload_remain_green(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MATERIAL_MULTIMODAL_AGENT", "demo")
    client, _storage, _service = create_client(
        storage_root=tmp_path / "uploads",
        work_root=tmp_path / "processing",
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
