import json
from pathlib import Path

import fitz

from src.ingestion.pdf_ingestor import PDFIngestor
from src.ingestion.vision_request_builder import (
    VisionRequestBuilder,
)
from src.ingestion.vision_request_exporter import (
    VisionRequestExporter,
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


def test_export_vision_requests(
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

    output_path = VisionRequestExporter().export(
        result=result,
        requests=requests,
        output_dir=tmp_path / "manifests",
    )

    assert output_path.exists()
    assert output_path.name == "vision_requests.json"

    payload = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert payload["schema_version"] == "v1"
    assert payload["material_id"] == "material-001"
    assert payload["material_name"] == "lesson.pdf"
    assert payload["total_requests"] == 1
    assert payload["page_numbers"] == [2]

    request = payload["requests"][0]

    assert request["request_id"].startswith("vision-")
    assert request["page_number"] == 2
    assert request["asset_id"].startswith("asset-")
    assert request["mime_type"] == "image/png"
    assert request["prompt_version"] == "vision-v1"

    assert request["tasks"] == [
        "describe_visuals",
        "extract_text",
        "extract_tables",
        "explain_relationships",
    ]

    assert Path(request["image_path"]).exists()


def test_export_allows_zero_vision_requests(
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

    requests = VisionRequestBuilder().build(result)

    assert requests == []

    output_path = VisionRequestExporter().export(
        result=result,
        requests=requests,
        output_dir=tmp_path / "manifests",
    )

    payload = json.loads(
        output_path.read_text(encoding="utf-8")
    )

    assert payload["material_id"] == "text-material"
    assert payload["total_requests"] == 0
    assert payload["page_numbers"] == []
    assert payload["requests"] == []