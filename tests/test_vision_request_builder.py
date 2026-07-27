from pathlib import Path

import fitz
import pytest

from src.ingestion.pdf_ingestor import (
    MaterialPage,
    PDFIngestor,
    PageRenderResult,
)
from src.ingestion.vision_request_builder import (
    VisionRequestBuilder,
)


def create_builder_test_pdf(pdf_path: Path) -> None:
    with fitz.open() as document:
        text_page = document.new_page()
        text_page.insert_text(
            (72, 72),
            "Text-only content",
        )

        visual_page = document.new_page()
        visual_page.insert_text(
            (72, 72),
            "Diagram explanation",
        )
        visual_page.draw_rect(
            fitz.Rect(72, 100, 250, 180),
            color=(0, 0, 0),
            width=1,
        )

        document.save(pdf_path)


def test_builder_creates_request_only_for_vision_page(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "lesson.pdf"

    create_builder_test_pdf(pdf_path)

    ingestor = PDFIngestor(render_dpi=72)

    result = ingestor.render_pages_with_assets(
        pdf_path=pdf_path,
        material_id="material-001",
        output_dir=tmp_path / "rendered",
    )

    builder = VisionRequestBuilder()
    requests = builder.build(result)

    assert len(requests) == 1

    request = requests[0]
    vision_page = result.pages[1]
    vision_asset = result.assets[1]

    assert request.request_id.startswith("vision-")
    assert request.material_id == "material-001"
    assert request.material_name == "lesson.pdf"
    assert request.page_number == 2

    assert request.asset_id == vision_asset.asset_id
    assert request.image_path == vision_asset.file_path
    assert request.mime_type == "image/png"

    assert request.extracted_text == (
        vision_page.extracted_text
    )
    assert request.prompt_version == "vision-v1"


def test_request_id_is_stable(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "lesson.pdf"

    create_builder_test_pdf(pdf_path)

    ingestor = PDFIngestor(render_dpi=72)
    builder = VisionRequestBuilder()

    first_result = ingestor.render_pages_with_assets(
        pdf_path=pdf_path,
        material_id="material-001",
        output_dir=tmp_path / "first-render",
    )

    second_result = ingestor.render_pages_with_assets(
        pdf_path=pdf_path,
        material_id="material-001",
        output_dir=tmp_path / "second-render",
    )

    first_requests = builder.build(first_result)
    second_requests = builder.build(second_result)

    assert (
        first_requests[0].request_id
        == second_requests[0].request_id
    )


def test_builder_rejects_missing_page_asset(
    tmp_path: Path,
) -> None:
    page = MaterialPage(
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=2,
        extracted_text="Diagram",
        image_ids=("missing-asset",),
        has_visual_content=True,
        requires_vision=True,
    )

    result = PageRenderResult(
        pages=(page,),
        assets=(),
    )

    builder = VisionRequestBuilder()

    with pytest.raises(
        ValueError,
        match="No page-render asset found",
    ):
        builder.build(result)