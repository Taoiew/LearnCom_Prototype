import json
from pathlib import Path

import fitz
import pytest

from schemas.material_contract import MaterialFileType
from schemas.material_contract import (
    MaterialStoredProcessingStatus,
)
from schemas.material_processing_contract import (
    MaterialProcessingStatus,
)
from schemas.vision_contract import (
    VisionRequest,
    VisionResponse,
    VisionResponseStatus,
    VisualElement,
    VisualElementType,
)
from src.agents.multimodal_agent import MultimodalAgent
from src.ingestion.material_storage import MaterialStorage
from src.ingestion.pdf_ingestor import PDFIngestor
from src.service.material_processing_service import (
    MaterialProcessingError,
    MaterialProcessingService,
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
            page_summary="Verified diagram page.",
            ocr_text="",
            visual_elements=[
                VisualElement(
                    element_id="element-001",
                    element_type=VisualElementType.DIAGRAM,
                    title="Diagram",
                    description="A visible diagram on the page.",
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


def create_text_only_pdf_bytes() -> bytes:
    with fitz.open() as document:
        page = document.new_page()
        page.insert_text(
            (72, 72),
            "Text-only explanation of gradient descent.",
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
    pixmap.clear_with(230)

    image_path = tmp_path / filename
    pixmap.save(str(image_path))

    return image_path.read_bytes()


def store_pdf(
    tmp_path: Path,
    content: bytes,
) -> tuple[MaterialStorage, str]:
    storage = MaterialStorage(tmp_path / "storage")
    stored = storage.store(
        filename="lesson.pdf",
        content_type="application/pdf",
        content=content,
    )

    return storage, stored.material_id


def store_image(
    tmp_path: Path,
    *,
    filename: str,
    content_type: str,
    content: bytes,
) -> tuple[MaterialStorage, str]:
    storage = MaterialStorage(tmp_path / "storage")
    stored = storage.store(
        filename=filename,
        content_type=content_type,
        content=content,
    )

    return storage, stored.material_id


def create_service(
    storage: MaterialStorage,
    work_root: Path,
) -> MaterialProcessingService:
    return MaterialProcessingService(
        storage=storage,
        work_root=work_root,
        ingestor=PDFIngestor(render_dpi=72),
    )


def test_processes_valid_pdf(
    tmp_path: Path,
) -> None:
    storage, material_id = store_pdf(
        tmp_path,
        create_visual_pdf_bytes(),
    )
    agent = RecordingMultimodalAgent()

    response = create_service(
        storage,
        tmp_path / "work",
    ).process(material_id, agent=agent)

    assert response.material_id == material_id
    assert response.file_type is MaterialFileType.PDF
    assert response.status is MaterialProcessingStatus.COMPLETED
    assert response.total_pages == 1
    assert response.total_vision_requests == 1
    assert response.total_vision_responses == 1
    assert response.error is None


def test_creates_page_and_asset_manifests(
    tmp_path: Path,
) -> None:
    storage, material_id = store_pdf(
        tmp_path,
        create_visual_pdf_bytes(),
    )

    response = create_service(
        storage,
        tmp_path / "work",
    ).process(material_id, agent=RecordingMultimodalAgent())

    pages_path = Path(response.pages_manifest_path)
    assets_path = Path(response.assets_manifest_path)

    assert pages_path.is_file()
    assert assets_path.is_file()

    pages_payload = json.loads(
        pages_path.read_text(encoding="utf-8")
    )
    assets_payload = json.loads(
        assets_path.read_text(encoding="utf-8")
    )

    assert pages_payload["material_id"] == material_id
    assert pages_payload["total_pages"] == 1
    assert assets_payload["material_id"] == material_id
    assert assets_payload["total_assets"] == 1


def test_creates_vision_request_manifest(
    tmp_path: Path,
) -> None:
    storage, material_id = store_pdf(
        tmp_path,
        create_visual_pdf_bytes(),
    )

    response = create_service(
        storage,
        tmp_path / "work",
    ).process(material_id, agent=RecordingMultimodalAgent())

    requests_path = Path(response.vision_requests_path)
    payload = json.loads(
        requests_path.read_text(encoding="utf-8")
    )

    assert requests_path.is_file()
    assert payload["material_id"] == material_id
    assert payload["total_requests"] == 1


def test_runs_injected_agent_when_visual_page_exists(
    tmp_path: Path,
) -> None:
    storage, material_id = store_pdf(
        tmp_path,
        create_visual_pdf_bytes(),
    )
    agent = RecordingMultimodalAgent()

    create_service(
        storage,
        tmp_path / "work",
    ).process(material_id, agent=agent)

    assert len(agent.requests) == 1
    assert agent.requests[0].material_id == material_id


def test_reports_verification_counts(
    tmp_path: Path,
) -> None:
    storage, material_id = store_pdf(
        tmp_path,
        create_visual_pdf_bytes(),
    )

    response = create_service(
        storage,
        tmp_path / "work",
    ).process(material_id, agent=RecordingMultimodalAgent())

    assert response.verified_count == 1
    assert response.needs_review_count == 0
    assert response.rejected_count == 0
    assert response.vision_responses_path is not None
    assert response.vision_verifications_path is not None


def test_handles_text_only_pdf_with_zero_vision_requests(
    tmp_path: Path,
) -> None:
    storage, material_id = store_pdf(
        tmp_path,
        create_text_only_pdf_bytes(),
    )
    agent = RecordingMultimodalAgent()

    response = create_service(
        storage,
        tmp_path / "work",
    ).process(material_id, agent=agent)

    assert response.status is MaterialProcessingStatus.COMPLETED
    assert response.total_pages == 1
    assert response.total_vision_requests == 0
    assert response.total_vision_responses == 0
    assert agent.requests == []
    assert response.vision_responses_path is None
    assert response.vision_verifications_path is None


def test_rejects_unknown_material_id(
    tmp_path: Path,
) -> None:
    service = create_service(
        MaterialStorage(tmp_path / "storage"),
        tmp_path / "work",
    )

    with pytest.raises(
        MaterialProcessingError,
        match="not found",
    ):
        service.process(
            "material-0000000000000000",
            agent=RecordingMultimodalAgent(),
        )


def test_rejects_tampered_stored_file(
    tmp_path: Path,
) -> None:
    storage, material_id = store_pdf(
        tmp_path,
        create_visual_pdf_bytes(),
    )
    stored = storage.get(material_id)
    Path(stored.stored_path).write_bytes(b"tampered")

    with pytest.raises(
        MaterialProcessingError,
        match="checksum mismatch",
    ):
        create_service(
            storage,
            tmp_path / "work",
        ).process(material_id, agent=RecordingMultimodalAgent())


@pytest.mark.parametrize(
    (
        "filename",
        "content_type",
        "expected_file_type",
        "width",
        "height",
    ),
    [
        (
            "diagram.png",
            "image/png",
            MaterialFileType.PNG,
            7,
            5,
        ),
        (
            "photo.jpeg",
            "image/jpeg",
            MaterialFileType.JPEG,
            9,
            4,
        ),
    ],
)
def test_processes_standalone_image_material(
    tmp_path: Path,
    filename: str,
    content_type: str,
    expected_file_type: MaterialFileType,
    width: int,
    height: int,
) -> None:
    storage, material_id = store_image(
        tmp_path,
        filename=filename,
        content_type=content_type,
        content=create_image_bytes(
            tmp_path,
            filename=f"source-{filename}",
            width=width,
            height=height,
        ),
    )
    agent = RecordingMultimodalAgent()

    response = create_service(
        storage,
        tmp_path / "work",
    ).process(
        material_id,
        agent=agent,
    )

    requests_payload = json.loads(
        Path(response.vision_requests_path).read_text(
            encoding="utf-8"
        )
    )

    assert response.file_type is expected_file_type
    assert response.status is MaterialProcessingStatus.COMPLETED
    assert response.total_pages == 1
    assert response.total_vision_requests == 1
    assert response.total_vision_responses == 1
    assert response.verified_count == 1
    assert len(agent.requests) == 1

    request = requests_payload["requests"][0]
    assert request["mime_type"] == content_type
    assert request["image_width_pixels"] == width
    assert request["image_height_pixels"] == height
    assert request["extracted_text"] == ""


def test_image_processing_uses_deterministic_asset_and_request_ids(
    tmp_path: Path,
) -> None:
    content = create_image_bytes(
        tmp_path,
        filename="source.png",
        width=5,
        height=3,
    )
    storage, material_id = store_image(
        tmp_path,
        filename="diagram.png",
        content_type="image/png",
        content=content,
    )

    service = create_service(
        storage,
        tmp_path / "work",
    )
    first = service.process(
        material_id,
        agent=RecordingMultimodalAgent(),
    )
    second = service.process(
        material_id,
        agent=RecordingMultimodalAgent(),
    )

    first_assets = json.loads(
        Path(first.assets_manifest_path).read_text(
            encoding="utf-8"
        )
    )
    second_assets = json.loads(
        Path(second.assets_manifest_path).read_text(
            encoding="utf-8"
        )
    )
    first_requests = json.loads(
        Path(first.vision_requests_path).read_text(
            encoding="utf-8"
        )
    )
    second_requests = json.loads(
        Path(second.vision_requests_path).read_text(
            encoding="utf-8"
        )
    )

    assert (
        first_assets["assets"][0]["asset_id"]
        == second_assets["assets"][0]["asset_id"]
    )
    assert (
        first_requests["requests"][0]["request_id"]
        == second_requests["requests"][0]["request_id"]
    )


def test_rejects_missing_stored_image(
    tmp_path: Path,
) -> None:
    storage, material_id = store_image(
        tmp_path,
        filename="diagram.png",
        content_type="image/png",
        content=create_image_bytes(
            tmp_path,
            filename="source.png",
            width=3,
            height=2,
        ),
    )
    stored = storage.get(material_id)
    Path(stored.stored_path).unlink()

    with pytest.raises(
        MaterialProcessingError,
        match="missing",
    ):
        create_service(
            storage,
            tmp_path / "work",
        ).process(material_id, agent=RecordingMultimodalAgent())


def test_uses_deterministic_artifact_directory(
    tmp_path: Path,
) -> None:
    storage, material_id = store_pdf(
        tmp_path,
        create_visual_pdf_bytes(),
    )
    work_root = tmp_path / "work"

    response = create_service(
        storage,
        work_root,
    ).process(material_id, agent=RecordingMultimodalAgent())

    artifact_dir = (work_root / material_id).resolve()

    assert Path(response.pages_manifest_path).parent == artifact_dir
    assert Path(response.assets_manifest_path).parent == artifact_dir
    assert Path(response.vision_requests_path).parent == artifact_dir


def test_persists_processing_status_across_service_instances(
    tmp_path: Path,
) -> None:
    storage, material_id = store_pdf(
        tmp_path,
        create_visual_pdf_bytes(),
    )
    work_root = tmp_path / "work"
    first_service = create_service(storage, work_root)

    processing_status = first_service.mark_processing(
        material_id
    )
    result = first_service.process(
        material_id,
        agent=RecordingMultimodalAgent(),
    )
    final_status = first_service.persist_result(result)

    second_service = create_service(storage, work_root)
    loaded_status = second_service.get_status(material_id)

    assert (
        processing_status.processing_status
        is MaterialStoredProcessingStatus.PROCESSING
    )
    assert (
        final_status.processing_status
        is MaterialStoredProcessingStatus.PROCESSED
    )
    assert loaded_status == final_status
    assert loaded_status.total_pages == 1
    assert loaded_status.total_assets == 1
