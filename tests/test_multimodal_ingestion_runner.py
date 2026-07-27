import json
from pathlib import Path

import fitz
import httpx

from src.agents.multimodal_agent import (
    ExternalMultimodalAgent,
)
from src.agents.multimodal_client import (
    MultimodalConfig,
    OpenAICompatibleMultimodalClient,
)
from src.ingestion.pdf_ingestor import PDFIngestor
from src.service.multimodal_ingestion_runner import (
    MultimodalIngestionRunner,
)


def create_visual_pdf(pdf_path: Path) -> None:
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
        document.save(pdf_path)


def create_result(
    tmp_path: Path,
):
    pdf_path = tmp_path / "lesson.pdf"
    create_visual_pdf(pdf_path)

    return PDFIngestor(
        render_dpi=72
    ).render_pages_with_assets(
        pdf_path=pdf_path,
        material_id="material-001",
        output_dir=tmp_path / "rendered",
    )


def test_runner_exports_requests_when_agent_disabled(
    tmp_path: Path,
) -> None:
    result = create_result(tmp_path)

    artifacts = MultimodalIngestionRunner().run(
        result=result,
        agent=None,
        output_dir=tmp_path / "manifests",
    )

    assert artifacts.total_requests == 1
    assert artifacts.total_responses == 0
    assert artifacts.requests_path.exists()

    assert artifacts.responses_path is None
    assert artifacts.verifications_path is None
    assert artifacts.verified_count == 0


def test_external_runner_end_to_end_with_mock_transport(
    tmp_path: Path,
) -> None:
    result = create_result(tmp_path)

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.url.path == (
            "/v1/chat/completions"
        )

        provider_payload = {
            "status": "success",
            "page_summary": (
                "A diagram shows an exception flow."
            ),
            "ocr_text": "",
            "visual_elements": [
                {
                    "element_id": "element-001",
                    "element_type": "diagram",
                    "title": "Exception flow",
                    "description": (
                        "A visible box represents an "
                        "exception flow."
                    ),
                    "extracted_text": (
                        "Exception flowchart"
                    ),
                    "bounding_box": [
                        72.0,
                        100.0,
                        250.0,
                        180.0,
                    ],
                    "confidence": 0.92,
                }
            ],
            "tables": [],
            "relationships": [],
            "warnings": [],
            "confidence": 0.92,
        }

        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                provider_payload
                            )
                        }
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)

    with httpx.Client(
        transport=transport,
        base_url="https://provider.example/v1/",
    ) as http_client:
        client = OpenAICompatibleMultimodalClient(
            config=MultimodalConfig(
                base_url=(
                    "https://provider.example/v1"
                ),
                model="vision-model",
                api_key="test-key",
            ),
            http_client=http_client,
        )

        agent = ExternalMultimodalAgent(
            client=client,
            agent_model="vision-model",
        )

        artifacts = MultimodalIngestionRunner().run(
            result=result,
            agent=agent,
            output_dir=tmp_path / "manifests",
        )

    assert artifacts.total_requests == 1
    assert artifacts.total_responses == 1

    assert artifacts.requests_path.exists()
    assert artifacts.responses_path is not None
    assert artifacts.responses_path.exists()

    assert artifacts.verifications_path is not None
    assert artifacts.verifications_path.exists()

    assert artifacts.verified_count == 1
    assert artifacts.needs_review_count == 0
    assert artifacts.rejected_count == 0

    verification_payload = json.loads(
        artifacts.verifications_path.read_text(
            encoding="utf-8"
        )
    )

    assert verification_payload[
        "verified_count"
    ] == 1
    assert verification_payload[
        "needs_review_count"
    ] == 0