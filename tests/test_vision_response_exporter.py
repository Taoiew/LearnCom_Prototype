import json
from pathlib import Path

import fitz

from src.agents.multimodal_agent import (
    DemoMultimodalAgent,
)
from src.ingestion.pdf_ingestor import PDFIngestor
from src.ingestion.vision_request_builder import (
    VisionRequestBuilder,
)
from src.ingestion.vision_response_exporter import (
    VisionResponseExporter,
)
from src.service.multimodal_pipeline import (
    MultimodalPipeline,
)


def create_visual_pdf(pdf_path: Path) -> None:
    with fitz.open() as document:
        text_page = document.new_page()
        text_page.insert_text(
            (72, 72),
            "Text-only page",
        )

        visual_page = document.new_page()
        visual_page.insert_text(
            (72, 72),
            "Visual page",
        )
        visual_page.draw_rect(
            fitz.Rect(72, 100, 250, 180),
            color=(0, 0, 0),
            width=1,
        )

        document.save(pdf_path)


def create_text_only_pdf(pdf_path: Path) -> None:
    with fitz.open() as document:
        page = document.new_page()
        page.insert_text(
            (72, 72),
            "Text-only material",
        )
        document.save(pdf_path)


def test_export_demo_vision_response(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "lesson.pdf"

    create_visual_pdf(pdf_path)

    ingestor = PDFIngestor(render_dpi=72)

    result = ingestor.render_pages_with_assets(
        pdf_path=pdf_path,
        material_id="material-001",
        output_dir=tmp_path / "rendered",
    )

    requests = VisionRequestBuilder().build(result)

    pipeline = MultimodalPipeline(
        agent=DemoMultimodalAgent()
    )
    responses = pipeline.process(requests)

    output_path = VisionResponseExporter().export(
        result=result,
        responses=responses,
        output_dir=tmp_path / "manifests",
    )

    assert output_path.exists()
    assert output_path.name == "vision_responses.json"

    payload = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert payload["schema_version"] == "v1"
    assert payload["material_id"] == "material-001"
    assert payload["material_name"] == "lesson.pdf"
    assert payload["total_responses"] == 1
    assert payload["page_numbers"] == [2]
    assert payload["status_counts"] == {
        "needs_review": 1
    }

    response = payload["responses"][0]

    assert response["page_number"] == 2
    assert response["status"] == "needs_review"
    assert response["confidence"] == 0.5
    assert response["agent_model"] == (
        "demo-multimodal-agent"
    )

    assert len(response["visual_elements"]) == 1
    assert response["visual_elements"][0][
        "element_type"
    ] == "image"

    assert response["tables"] == []
    assert response["relationships"] == []
    assert len(response["warnings"]) == 1


def test_export_allows_zero_responses(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "text-only.pdf"

    create_text_only_pdf(pdf_path)

    ingestor = PDFIngestor(render_dpi=72)

    result = ingestor.render_pages_with_assets(
        pdf_path=pdf_path,
        material_id="text-material",
        output_dir=tmp_path / "rendered",
    )

    output_path = VisionResponseExporter().export(
        result=result,
        responses=[],
        output_dir=tmp_path / "manifests",
    )

    payload = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert payload["material_id"] == "text-material"
    assert payload["total_responses"] == 0
    assert payload["page_numbers"] == []
    assert payload["status_counts"] == {}
    assert payload["responses"] == []